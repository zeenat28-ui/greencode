"""HuggingFace Inference API client for code-aware refactoring.

Replaces the previous IBM watsonx integration with the public HuggingFace
Inference API, reached through its OpenAI-compatible router endpoint.

Design notes:
- The router endpoint (``router.huggingface.co/v1/chat/completions``) is used
  because it is stable and provider-agnostic. The classic per-model endpoint is
  kept as a fallback for deployments pinned to ``api-inference``.
- Errors are *classified*, not swallowed. A 401 (bad key) will not be fixed by
  retrying; a 503 (cold model loading) will. Retrying the wrong thing wastes
  minutes and hides the real fault.
- The API key is never echoed into logs or returned payloads.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger("greencode.llm")

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass


ROUTER_URL = "https://router.huggingface.co/v1/chat/completions"
LEGACY_URL = "https://api-inference.huggingface.co/models/{model}"

# Preference order. Qwen2.5-Coder is a code-specialised model, which is exactly
# the right tool for behaviour-preserving refactors; the general instruct
# models are fallbacks in case the specialised one is unavailable.
DEFAULT_MODELS: Tuple[str, ...] = (
    "Qwen/Qwen2.5-Coder-32B-Instruct",
    "Qwen/Qwen2.5-Coder-7B-Instruct",
    "meta-llama/Llama-3.1-8B-Instruct",
    "deepseek-ai/DeepSeek-V3-0324",
)


class LLMError(RuntimeError):
    """A classified failure from the HuggingFace Inference API."""

    def __init__(self, message: str, *, kind: str, status_code: Optional[int] = None,
                 retryable: bool = False):
        super().__init__(message)
        self.message = message
        self.kind = kind  # auth|rate_limit|unavailable|bad_request|network|unknown
        self.status_code = status_code
        self.retryable = retryable


@dataclass
class LLMUsage:
    """Token accounting for one call, surfaced so callers can budget."""

    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class HuggingFaceClient:
    """Thin, dependency-light client for the HuggingFace Inference API.

    Uses a pooled ``requests.Session`` so repeated refactors reuse one TLS
    connection instead of paying a fresh handshake each time.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = ROUTER_URL,
        timeout: float = 60.0,
        max_retries: int = 3,
    ):
        self.api_key = (
            api_key
            or os.environ.get("HUGGINGFACE_API_KEY", "")
            or os.environ.get("HF_TOKEN", "")
        )
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self._local = threading.local()
        self._lock = threading.Lock()
        self._healthy_model: Optional[str] = None
        self._unavailable: set[str] = set()

    # -- plumbing ----------------------------------------------------------
    def _session(self) -> requests.Session:
        s = getattr(self._local, "session", None)
        if s is None:
            s = requests.Session()
            s.headers.update({"Content-Type": "application/json"})
            adapter = requests.adapters.HTTPAdapter(pool_connections=4, pool_maxsize=8)
            s.mount("https://", adapter)
            self._local.session = s
        return s

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    def _classify(self, status: int, body: str) -> LLMError:
        detail = (body or "")[:300]
        if status in (401, 403):
            return LLMError(
                "HuggingFace rejected the API key. Check HUGGINGFACE_API_KEY.",
                kind="auth", status_code=status,
            )
        if status == 429:
            return LLMError(
                "HuggingFace rate limit reached. Retry shortly.",
                kind="rate_limit", status_code=status, retryable=True,
            )
        if status in (500, 502, 503, 504):
            return LLMError(
                f"HuggingFace inference temporarily unavailable ({status}).",
                kind="unavailable", status_code=status, retryable=True,
            )
        if status == 400 and "not supported by any provider" in (body or ""):
            return LLMError(
                "Model is not enabled for this account.", kind="bad_request", status_code=status
            )
        return LLMError(
            f"HuggingFace request failed ({status}): {detail}",
            kind="bad_request", status_code=status,
        )

    # -- public API --------------------------------------------------------
    @staticmethod
    def list_models() -> Tuple[str, ...]:
        return DEFAULT_MODELS

    def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
        stop: Optional[List[str]] = None,
    ) -> Tuple[str, LLMUsage, str]:
        """Run a chat completion. Returns (content, usage, model_actually_used)."""
        if not self.configured:
            raise LLMError(
                "No HuggingFace API key configured. Set HUGGINGFACE_API_KEY.",
                kind="auth",
            )

        if model:
            candidates = [model]
        else:
            candidates = []
            cached = self._healthy_model
            if cached and cached not in self._unavailable:
                candidates.append(cached)
            candidates.extend(m for m in DEFAULT_MODELS if m not in candidates)

        last_error: Optional[LLMError] = None
        for candidate in candidates:
            if candidate in self._unavailable:
                continue
            try:
                content, usage = self._chat_once(
                    candidate, messages, max_tokens, temperature, stop
                )
                with self._lock:
                    self._healthy_model = candidate
                return content, usage, candidate
            except LLMError as exc:
                last_error = exc
                # A bad key will not fix itself by trying a different model, and
                # a retryable error was already retried inside _chat_once.
                if exc.kind == "auth" or exc.retryable:
                    raise
                with self._lock:
                    self._unavailable.add(candidate)
                continue
        raise last_error or LLMError("No model produced a completion.", kind="unknown")

    def _chat_once(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float,
        stop: Optional[List[str]],
    ) -> Tuple[str, LLMUsage]:
        url = self.base_url.format(model=model) if "{model}" in self.base_url else self.base_url

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if stop:
            payload["stop"] = stop

        delay = 0.8
        last_exc: Optional[LLMError] = None
        for attempt in range(self.max_retries):
            try:
                resp = self._session().post(
                    url, headers=self._headers(), json=payload, timeout=self.timeout
                )
            except requests.exceptions.RequestException as exc:
                last_exc = LLMError(
                    f"Could not reach HuggingFace: {exc}", kind="network", retryable=True
                )
                if attempt < self.max_retries - 1:
                    time.sleep(delay)
                    delay *= 2
                    continue
                raise last_exc

            if resp.status_code == 200:
                return self._parse(resp.json())

            err = self._classify(resp.status_code, resp.text)
            if not err.retryable or attempt == self.max_retries - 1:
                raise err
            last_exc = err
            time.sleep(delay)
            delay *= 2

        raise last_exc or LLMError("HuggingFace request failed.", kind="unknown")

    @staticmethod
    def _parse(data: Dict[str, Any]) -> Tuple[str, LLMUsage]:
        choices = data.get("choices") or []
        if not choices:
            raise LLMError("HuggingFace returned no choices.", kind="unknown")
        content = (choices[0].get("message") or {}).get("content")
        if not content:
            raise LLMError("HuggingFace returned an empty completion.", kind="unknown")
        raw = data.get("usage") or {}
        return str(content), LLMUsage(
            prompt_tokens=int(raw.get("prompt_tokens") or 0),
            completion_tokens=int(raw.get("completion_tokens") or 0),
        )

    def health(self) -> Dict[str, Any]:
        """Report whether the client is configured and which model answers."""
        info: Dict[str, Any] = {
            "configured": self.configured,
            "preferred_model": self._healthy_model or DEFAULT_MODELS[0],
            "models_tried": list(DEFAULT_MODELS),
        }
        if not self.configured:
            info["status"] = "unconfigured"
            return info
        try:
            _, usage, used = self.chat(
                [{"role": "user", "content": "Reply with the single word: ready"}],
                max_tokens=5,
            )
            info["status"] = "ok"
            info["active_model"] = used
            info["probe_tokens"] = usage.completion_tokens
        except LLMError as exc:
            info["status"] = "error"
            info["error_kind"] = exc.kind
            info["error"] = exc.message
        return info


_default_client: Optional[HuggingFaceClient] = None
_default_lock = threading.Lock()


def get_client(api_key: Optional[str] = None) -> HuggingFaceClient:
    """Return the process-wide shared client.

    A caller-supplied ``api_key`` yields a dedicated client rather than
    poisoning the shared instance, so one request cannot reconfigure the key
    for every other thread.
    """
    global _default_client
    if api_key:
        return HuggingFaceClient(api_key=api_key)
    with _default_lock:
        if _default_client is None:
            _default_client = HuggingFaceClient()
    return _default_client

