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
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import logging
import os
import sys
import time
from typing import Any, Dict, Optional
import uuid

# Configure Celery
try:
    from celery import Celery
    from celery.result import AsyncResult
    CELERY_AVAILABLE = True
except ImportError:
    Celery = None
    AsyncResult = None
    CELERY_AVAILABLE = False

from app.database import save_scan_results
from app.parser import audit_repository

logger = logging.getLogger("greencode.tasks")

# Environment parameters
REDIS_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
REDIS_BACKEND_URL = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# Celery Application Setup
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
        task_time_limit=1800,       # 30 minutes max execution
        task_soft_time_limit=1500,  # 25 minutes soft limit
        broker_connection_retry_on_startup=True,
        worker_prefetch_multiplier=1,
    )
else:
    celery_app = None


# ---------------------------------------------------------------------------
# CELERY TASK DEFINITION
# ---------------------------------------------------------------------------
if celery_app:
    @celery_app.task(bind=True, name="greencode.scan_repository_task")
    def scan_repository_celery_task(self, repo_path: str, name: Optional[str] = None) -> Dict[str, Any]:
        """Distributed Celery background task auditing an entire multi-language repository path."""
        self.update_state(
            state="STARTED",
            meta={
                "status": "Processing",
                "progress_message": f"Analyzing repository directory at '{repo_path}'...",
                "started_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        abs_path = os.path.abspath(repo_path)
        scan_result = audit_repository(abs_path)
        repo_name = name or os.path.basename(abs_path) or "Repository"

        # Persist results in database
        saved_repo = save_scan_results(
            name=repo_name,
            path_or_url=abs_path,
            total_files=scan_result["total_files"],
            total_lines=scan_result["total_lines"],
            green_score=scan_result["green_score"],
            violations_data=scan_result["violations"],
            summary_json=json.dumps(scan_result["violation_breakdown"]),
        )
        scan_result["repo_id"] = saved_repo.id
        scan_result["status"] = "Completed"
        scan_result["completed_at"] = datetime.now(timezone.utc).isoformat()
        return scan_result


# ---------------------------------------------------------------------------
# IN-MEMORY ASYNCHRONOUS TASK QUEUE FALLBACK
# Ensures zero failures if Redis daemon is not running on local developer hosts
# ---------------------------------------------------------------------------
class InMemoryTaskWorker:
    """ThreadPool task manager mimicking Celery AsyncResult lifecycle for standalone environments."""

    def __init__(self, max_workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="greencode-worker")
        self._tasks: Dict[str, Dict[str, Any]] = {}

    def submit_scan(self, repo_path: str, name: Optional[str] = None) -> str:
        task_id = str(uuid.uuid4())
        self._tasks[task_id] = {
            "task_id": task_id,
            "status": "Processing",
            "progress_message": f"Scanning repository path '{repo_path}' in asynchronous background worker...",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "result": None,
            "error": None,
        }

        def _execute():
            try:
                abs_path = os.path.abspath(repo_path)
                scan_res = audit_repository(abs_path)
                repo_name = name or os.path.basename(abs_path) or "Repository"

                saved = save_scan_results(
                    name=repo_name,
                    path_or_url=abs_path,
                    total_files=scan_res["total_files"],
                    total_lines=scan_res["total_lines"],
                    green_score=scan_res["green_score"],
                    violations_data=scan_res["violations"],
                    summary_json=json.dumps(scan_res["violation_breakdown"]),
                )
                scan_res["repo_id"] = saved.id
                scan_res["status"] = "Completed"
                scan_res["completed_at"] = datetime.now(timezone.utc).isoformat()

                self._tasks[task_id]["status"] = "Completed"
                self._tasks[task_id]["result"] = scan_res
            except Exception as e:
                self._tasks[task_id]["status"] = "Failed"
                self._tasks[task_id]["error"] = str(e)

        self.executor.submit(_execute)
        return task_id

    def get_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self._tasks.get(task_id)


_in_memory_worker = InMemoryTaskWorker()


def _is_redis_available() -> bool:
    """Test if Redis broker is reachable without throwing unhandled connection errors."""
    try:
        import socket
        from urllib.parse import urlparse
        parsed = urlparse(REDIS_BROKER_URL)
        host = parsed.hostname or "localhost"
        port = parsed.port or 6379
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex((host, port)) == 0
    except Exception:
        return False


# ---------------------------------------------------------------------------
# PUBLIC API WRAPPER
# ---------------------------------------------------------------------------
def enqueue_scan_task(repo_path: str, name: Optional[str] = None) -> Dict[str, Any]:
    """Enqueue a repository scan task.
    
    Dispatches to Celery if Redis broker is online, else falls back to in-memory
    background thread workers to prevent HTTP gateway connection timeouts.
    """
    if CELERY_AVAILABLE and _is_redis_available():
        try:
            async_task = scan_repository_celery_task.delay(repo_path, name)
            return {
                "task_id": async_task.id,
                "status": "Processing",
                "queue_backend": "Celery / Redis Distributed Broker",
                "message": "Repository audit task successfully dispatched to Celery worker cluster.",
            }
        except Exception:
            pass

    # In-memory worker fallback
    task_id = _in_memory_worker.submit_scan(repo_path, name)
    return {
        "task_id": task_id,
        "status": "Processing",
        "queue_backend": "In-Process Concurrent Task Worker",
        "message": "Repository audit task enqueued in background worker pool.",
    }


def get_task_status(task_id: Any) -> Dict[str, Any]:
    """Retrieve task execution status and audit payload."""
    if isinstance(task_id, dict):
        task_id = task_id.get("task_id", "")
    task_id = str(task_id)

    # Check Celery if active and Redis is reachable
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
        except Exception:
            pass

    # Check in-memory worker
    local_task = _in_memory_worker.get_status(task_id)
    if local_task:
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

