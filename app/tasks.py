"""Asynchronous Task Queue and Worker Infrastructure for GreenCode Auditor.

Decouples repository scanning from synchronous HTTP request-response lifecycles using
Celery and Redis. Offloads recursive multi-language AST/CST directory walks to background
workers to prevent gateway connection timeouts on massive mono-repos.

Features:
- Celery application instance with Redis broker ('redis://localhost:6379/0')
- Distributed task definition: @celery_app.task scan_repository_task
- Resilient In-Memory Task Queue Fallback for standalone/local developer modes
- Dynamic task status polling: PENDING, STARTED, SUCCESS, FAILURE, RETRY
"""

import asyncio
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import logging
import os
import sys
import threading
import time
from typing import Any, Dict, Optional
import uuid

try:
    from fastapi import HTTPException
except ImportError:
    HTTPException = None

try:
    from celery import Celery
    from celery.result import AsyncResult
    CELERY_AVAILABLE = True
except ImportError:
    Celery = None
    AsyncResult = None
    CELERY_AVAILABLE = False

from app.scanner import AuditRejected, run_github_audit

logger = logging.getLogger("greencode.tasks")

STRICT_PROD_MODE = os.environ.get("ENV", "").lower() in ("production", "prod", "staging")

REDIS_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
REDIS_BACKEND_URL = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

_redis_available_cache: Dict[str, Any] = {"value": None, "timestamp": 0.0}
_REDIS_CACHE_TTL = 30.0


def _is_redis_available() -> bool:
    """Test if Redis broker is reachable without throwing unhandled connection errors.

    Result is cached for 30 seconds to avoid repeated socket connections on every enqueue.
    """
    global _redis_available_cache
    now = time.monotonic()
    if _redis_available_cache["value"] is not None:
        if (now - _redis_available_cache["timestamp"]) < _REDIS_CACHE_TTL:
            return _redis_available_cache["value"]

    try:
        import socket
        from urllib.parse import urlparse
        parsed = urlparse(REDIS_BROKER_URL)
        host = parsed.hostname or "localhost"
        port = parsed.port or 6379
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            result = s.connect_ex((host, port)) == 0
        _redis_available_cache = {"value": result, "timestamp": now}
        if not result:
            logger.warning("Redis broker unreachable: %s:%d", host, port)
        return result
    except Exception as e:
        logger.warning("Redis availability check failed: %s", str(e))
        _redis_available_cache = {"value": False, "timestamp": now}
        return False


if CELERY_AVAILABLE:
    celery_app = Celery(
        "greencode_workers",
        broker=REDIS_BROKER_URL,
        backend=REDIS_BACKEND_URL,
    )
    celery_app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=1800,
        task_soft_time_limit=1500,
        broker_connection_retry_on_startup=True,
        worker_prefetch_multiplier=1,
    )
    logger.info("Celery application initialized with broker: %s", REDIS_BROKER_URL)
else:
    celery_app = None
    logger.warning("Celery not available - distributed queue disabled")


if STRICT_PROD_MODE and not _is_redis_available():
    logger.error(
        "STRICT_PROD_MODE is enabled but Redis/Celery broker is unreachable. "
        "Broker URL: %s. Terminating to prevent silent fallback.",
        REDIS_BROKER_URL,
    )
    sys.exit(1)


if celery_app:
    @celery_app.task(bind=True, name="greencode.scan_github_task")
    def scan_github_celery_task(
        self,
        repo_full_name: str,
        ref: Optional[str] = None,
        token: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Distributed Celery task auditing a GitHub repository.

        Delegates to the shared `run_github_audit` pipeline so the Celery and
        in-process worker paths produce identical results.
        """
        logger.info(
            "Celery GitHub task started: task_id=%s repo=%s user_id=%s",
            self.request.id, repo_full_name, user_id,
        )
        self.update_state(
            state="STARTED",
            meta={
                "status": "Processing",
                "progress_message": f"Auditing '{repo_full_name}'...",
                "started_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        def _progress(message: str) -> None:
            self.update_state(state="STARTED", meta={"progress_message": message})

        result = run_github_audit(
            repo_ref=repo_full_name,
            ref=ref,
            token=token,
            user_id=user_id,
            on_progress=_progress,
        )
        result["status"] = "Completed"
        result["completed_at"] = datetime.now(timezone.utc).isoformat()
        logger.info(
            "Celery GitHub task completed: task_id=%s repo_id=%s score=%s",
            self.request.id, result.get("repo_id"), result.get("green_score"),
        )
        return result


class InMemoryTaskWorker:
    """ThreadPool task manager mimicking Celery AsyncResult lifecycle for standalone environments.

    Every task records the owning user id so `/api/task/{id}` can enforce
    ownership instead of letting any authenticated user poll any task id.
    """

    # Completed task payloads are large (full file_results + violations). Keep a
    # bounded LRU so a long-running server cannot grow without limit.
    MAX_RETAINED_TASKS = 200

    def __init__(self, max_workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="greencode-worker")
        self._tasks: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
        self._lock = threading.Lock()
        logger.info("InMemoryTaskWorker initialized with %d max workers", max_workers)

    def _register(self, task_id: str, payload: Dict[str, Any]) -> None:
        with self._lock:
            self._tasks[task_id] = payload
            self._tasks.move_to_end(task_id)
            while len(self._tasks) > self.MAX_RETAINED_TASKS:
                self._tasks.popitem(last=False)

    def _update(self, task_id: str, **fields: Any) -> None:
        with self._lock:
            entry = self._tasks.get(task_id)
            if entry is not None:
                entry.update(fields)

    def submit_github_scan(
        self,
        repo_full_name: str,
        ref: Optional[str] = None,
        token: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> str:
        task_id = str(uuid.uuid4())
        self._register(task_id, {
            "task_id": task_id,
            "user_id": user_id,
            "status": "Processing",
            "progress_message": f"Queued audit of '{repo_full_name}'...",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "result": None,
            "error": None,
        })
        logger.info(
            "In-memory GitHub task submitted: task_id=%s repo=%s user_id=%s",
            task_id, repo_full_name, user_id,
        )

        def _execute() -> None:
            try:
                result = run_github_audit(
                    repo_ref=repo_full_name,
                    ref=ref,
                    token=token,
                    user_id=user_id,
                    on_progress=lambda msg: self._update(task_id, progress_message=msg),
                )
                result["status"] = "Completed"
                result["completed_at"] = datetime.now(timezone.utc).isoformat()
                self._update(task_id, status="Completed", result=result, progress_message="Audit complete.")
                logger.info(
                    "In-memory GitHub task completed: task_id=%s repo_id=%s score=%s",
                    task_id, result.get("repo_id"), result.get("green_score"),
                )
            except AuditRejected as exc:
                logger.info("In-memory GitHub task rejected: task_id=%s %s", task_id, exc.message)
                self._update(task_id, status="Failed", error=exc.message)
            except Exception as exc:
                logger.error(
                    "In-memory GitHub task failed: task_id=%s error=%s",
                    task_id, str(exc), exc_info=True,
                )
                self._update(task_id, status="Failed", error=str(exc))

        self.executor.submit(_execute)
        return task_id

    def get_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            entry = self._tasks.get(task_id)
            if entry is not None:
                self._tasks.move_to_end(task_id)
            return entry


_in_memory_worker = InMemoryTaskWorker()


def enqueue_github_scan_task(
    repo_full_name: str,
    ref: Optional[str] = None,
    token: Optional[str] = None,
    user_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Enqueue a GitHub repository audit onto Celery (or the in-process fallback)."""
    redis_ok = _is_redis_available()
    logger.info(
        "enqueue_github_scan_task: repo=%s ref=%s user_id=%s redis_ok=%s",
        repo_full_name, ref, user_id, redis_ok,
    )

    if STRICT_PROD_MODE and not redis_ok:
        logger.error("STRICT_PROD_MODE: Redis unavailable, refusing to enqueue.")
        if HTTPException is not None:
            raise HTTPException(
                status_code=503,
                detail="Task broker (Redis) is unreachable in production mode. Cannot enqueue scan.",
            )
        raise RuntimeError("Production requires a Redis/Celery broker, which is unreachable.")

    if CELERY_AVAILABLE and redis_ok:
        try:
            async_task = scan_github_celery_task.delay(repo_full_name, ref, token, user_id)
            return {
                "task_id": async_task.id,
                "status": "Processing",
                "queue_backend": "Celery / Redis Distributed Broker",
                "message": "Repository audit dispatched to the Celery worker cluster.",
            }
        except Exception as exc:
            logger.error("Celery dispatch failed: %s", str(exc), exc_info=True)
            if STRICT_PROD_MODE:
                if HTTPException is not None:
                    raise HTTPException(
                        status_code=503,
                        detail="Failed to dispatch audit to the Celery broker in production mode.",
                    )
                raise RuntimeError("Celery dispatch failed in production mode.")

    task_id = _in_memory_worker.submit_github_scan(repo_full_name, ref, token, user_id)
    return {
        "task_id": task_id,
        "status": "Processing",
        "queue_backend": "In-Process Concurrent Task Worker",
        "message": "Repository audit enqueued in the background worker pool.",
    }


def get_task_status(task_id: Any, user_id: Optional[int] = None) -> Dict[str, Any]:
    """Retrieve task execution status and audit payload, enforcing ownership.

    When `user_id` is supplied, a task owned by a different user is reported as
    NotFound so task ids cannot be probed across tenants.
    """
    if isinstance(task_id, dict):
        task_id = task_id.get("task_id", "")
    task_id = str(task_id)

    if CELERY_AVAILABLE and AsyncResult and _is_redis_available():
        try:
            res = AsyncResult(task_id, app=celery_app)
            if res.state in ("SUCCESS", "FAILURE", "STARTED", "RETRY"):
                if res.state == "SUCCESS":
                    return {
                        "task_id": task_id,
                        "status": "Completed",
                        "is_done": True,
                        "queue_backend": "Celery / Redis",
                        "result": res.result,
                    }
                elif res.state == "FAILURE":
                    logger.error("Celery task failed: task_id=%s error=%s", task_id, res.result)
                    return {
                        "task_id": task_id,
                        "status": "Failed",
                        "is_done": True,
                        "queue_backend": "Celery / Redis",
                        "error": str(res.result),
                    }
                else:
                    return {
                        "task_id": task_id,
                        "status": "Processing",
                        "is_done": False,
                        "queue_backend": "Celery / Redis",
                        "meta": res.info,
                    }
        except Exception as e:
            logger.warning("Celery status lookup failed for task_id=%s: %s", task_id, str(e))

    local_task = _in_memory_worker.get_status(task_id)
    if local_task:
        if user_id is not None and local_task.get("user_id") not in (None, user_id):
            logger.warning("Task %s ownership mismatch for user %s", task_id, user_id)
            return {
                "task_id": task_id,
                "status": "NotFound",
                "message": f"Task '{task_id}' does not exist or has expired.",
            }
        st = local_task["status"]
        return {
            "task_id": task_id,
            "status": st,
            "is_done": st in ("Completed", "SUCCESS", "Failed", "FAILURE"),
            "queue_backend": "In-Process Concurrent Task Worker",
            "result": local_task.get("result"),
            "error": local_task.get("error"),
            "progress_message": local_task.get("progress_message"),
        }

    return {
        "task_id": task_id,
        "status": "NotFound",
        "message": f"Task '{task_id}' does not exist or has expired.",
    }
