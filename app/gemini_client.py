"""Google Gemini API client for verified code-refactoring proposals."""

from __future__ import annotations

import os
import threading
from typing import Any, Dict, List, Optional, Tuple

import requests

from app.huggingface_client import LLMError, LLMUsage

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass

MODEL = "gemini-3.1-pro-preview"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"


class GeminiError(LLMError):
    """A classified failure from the Gemini API."""


class GeminiClient:
    """Small REST client that always targets the Gemini Pro model."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        timeout: float = 60.0,
    ):
        self.api_key = api_key if api_key is not None else os.environ.get("GEMINI_API_KEY", "")
        self.timeout = timeout
        self._local = threading.local()

    @property
    def configured(self) -> bool:
        return bool(self.api_key.strip())

    def _session(self) -> requests.Session:
        session = getattr(self._local, "session", None)
        if session is None:
            session = requests.Session()
            session.headers.update({"Content-Type": "application/json"})
            session.mount(
                "https://",
                requests.adapters.HTTPAdapter(pool_connections=4, pool_maxsize=8),
            )
            self._local.session = session
        return session

    @staticmethod
    def list_models() -> Tuple[str, ...]:
        return (MODEL,)

    @staticmethod
    def _classify(status: int) -> GeminiError:
        if status in (401, 403):
            return GeminiError(
                "Gemini rejected the API key or its permissions. Check GEMINI_API_KEY.",
                kind="auth",
                status_code=status,
            )
        if status == 429:
            return GeminiError(
                "Gemini rate limit reached. Retry shortly.",
                kind="rate_limit",
                status_code=status,
                retryable=True,
            )
        if status in (500, 502, 503, 504):
            return GeminiError(
                f"Gemini is temporarily unavailable ({status}).",
                kind="unavailable",
                status_code=status,
                retryable=True,
            )
        return GeminiError(
            f"Gemini request failed ({status}). Check the model and API configuration.",
            kind="bad_request",
            status_code=status,
        )

    def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
        stop: Optional[List[str]] = None,
    ) -> Tuple[str, LLMUsage, str]:
        """Generate a completion, returning text, usage, and the Pro model id."""
        if model and model != MODEL:
            raise GeminiError(
                f"Gemini refactoring is pinned to {MODEL}.",
                kind="bad_request",
            )
        if not self.configured:
            raise GeminiError(
                "No Gemini API key configured. Set GEMINI_API_KEY.",
                kind="auth",
            )

        system_parts: List[Dict[str, str]] = []
        contents: List[Dict[str, Any]] = []
        for message in messages:
            role = message.get("role", "")
            text = message.get("content", "")
            if role == "system":
                system_parts.append({"text": text})
            elif role in ("user", "assistant"):
                contents.append({
                    "role": "user" if role == "user" else "model",
                    "parts": [{"text": text}],
                })
            else:
                raise GeminiError(
                    f"Unsupported chat role: {role or '(empty)'}.",
                    kind="bad_request",
                )
        if not contents:
            raise GeminiError("Gemini requires at least one user or assistant message.", kind="bad_request")

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            },
        }
        if system_parts:
            payload["systemInstruction"] = {"parts": system_parts}
        if stop:
            payload["generationConfig"]["stopSequences"] = list(stop)

        try:
            response = self._session().post(
                API_URL,
                headers={"x-goog-api-key": self.api_key},
                json=payload,
                timeout=self.timeout,
            )
        except requests.exceptions.RequestException as exc:
            error = GeminiError(
                f"Could not reach Gemini: {type(exc).__name__}.",
                kind="network",
                retryable=True,
            )
            raise error from exc

        if response.status_code != 200:
            raise self._classify(response.status_code)
        try:
            content, usage = self._parse(response.json())
            return content, usage, MODEL
        except (ValueError, TypeError, KeyError) as exc:
            raise GeminiError("Gemini returned an invalid response.", kind="unknown") from exc

    @staticmethod
    def _parse(data: Dict[str, Any]) -> Tuple[str, LLMUsage]:
        if not isinstance(data, dict):
            raise GeminiError("Gemini returned an invalid response.", kind="unknown")
        candidates = data.get("candidates") or []
        if not isinstance(candidates, list) or not candidates or not isinstance(candidates[0], dict):
            raise GeminiError("Gemini returned no completion candidates.", kind="unknown")
        candidate_content = candidates[0].get("content") or {}
        if not isinstance(candidate_content, dict):
            raise GeminiError("Gemini returned an invalid completion.", kind="unknown")
        parts = candidate_content.get("parts") or []
        if not isinstance(parts, list):
            raise GeminiError("Gemini returned an invalid completion.", kind="unknown")
        content = "".join(
            str(part["text"]) for part in parts
            if isinstance(part, dict) and isinstance(part.get("text"), str)
        )
        if not content.strip():
            raise GeminiError("Gemini returned an empty completion.", kind="unknown")
        raw_usage = data.get("usageMetadata") or {}
        if not isinstance(raw_usage, dict):
            raise GeminiError("Gemini returned invalid usage metadata.", kind="unknown")
        try:
            prompt_tokens = int(raw_usage.get("promptTokenCount") or 0)
            completion_tokens = int(raw_usage.get("candidatesTokenCount") or 0)
        except (TypeError, ValueError) as exc:
            raise GeminiError("Gemini returned invalid usage metadata.", kind="unknown") from exc
        return content, LLMUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )


_client: Optional[GeminiClient] = None
_client_lock = threading.Lock()


def get_client() -> GeminiClient:
    """Return the process-wide Gemini client."""
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = GeminiClient()
    return _client
