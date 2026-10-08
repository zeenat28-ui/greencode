"""Amazon Bedrock client - the AWS runtime path for LLM-assisted refactoring.

GreenCode had exactly one model backend (HuggingFace), which made the product
impossible to run inside an AWS account and left the carbon figures with no AWS
footprint to audit. This module adds Bedrock as a first-class backend so the
refactoring agent can be served by Claude via Amazon Bedrock.

WHY IT MIRRORS THE HUGGINGFACE INTERFACE EXACTLY
-----------------------------------------------
``app.llm_refactor`` and ``app.optimizer`` call a client through one small
surface: ``chat() -> (content, usage, model_used)``, plus ``configured``,
``health()`` and ``list_models()``. Implementing that surface identically -
rather than adding ``if bedrock:`` branches through the refactoring engine,
which is how provider lock-in creeps into a codebase - keeps provider selection
a single decision, and means the verification gate that decides whether a
proposed refactor is safe never learns which provider produced it. That is the
property that matters: a Claude-proposed refactor passes precisely the same
behaviour-preservation checks as a Qwen-proposed one.

NO CREDENTIALS ARE INVENTED
---------------------------
With no credentials configured, ``chat()`` raises a classified
:class:`BedrockError` of kind ``auth`` rather than attempting a request or
silently degrading. GreenCode's premise is that a number is never presented as
better than its provenance allows; the same rule applies here.
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Any, Dict, List, Optional, Tuple

from app.huggingface_client import LLMError as LLMError  # re-exported for callers
from app.huggingface_client import LLMUsage as LLMUsage  # re-exported for callers

logger = logging.getLogger("greencode.bedrock")

# Claude first: these are the strongest behaviour-preserving code editors on
# Bedrock today, which is the one property this app cares about. A rewrite that
# changes what the code does is worse than no rewrite at all.
DEFAULT_MODELS: Tuple[str, ...] = (
    "anthropic.claude-sonnet-4-5-20250929-v1:0",
    "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "anthropic.claude-3-5-haiku-20241022-v1:0",
)

DEFAULT_REGION = "us-east-1"
BEDROCK_RUNTIME = "bedrock-runtime"

# Bedrock's Converse API takes a role/content shape rather than the OpenAI
# chat-completions shape, so each provider needs its own mapping. Keeping the
# mapping here is what lets the refactor engine stay provider-agnostic.
_PROVIDER_ROLES: Dict[str, Dict[str, str]] = {
    "anthropic": {"human": "user", "assistant": "assistant"},
    "amazon": {"human": "user", "assistant": "assistant"},
    "meta": {"human": "user", "assistant": "assistant"},
    "mistral": {"human": "user", "assistant": "assistant"},
    "cohere": {"human": "user", "assistant": "assistant"},
}
_DEFAULT_ROLES = {"human": "user", "assistant": "assistant"}


class BedrockError(LLMError):
    """A classified failure from Amazon Bedrock."""


def _provider_of(model_id: str) -> str:
    return (model_id or "").split(".", 1)[0].lower()
class BedrockClient:
    """Thin boto3 wrapper over the Bedrock Runtime Converse API."""

    def __init__(
        self,
        *,
        region_name: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 1024,
    ):
        self.region_name = (
            region_name
            or os.environ.get("AWS_REGION")
            or os.environ.get("AWS_DEFAULT_REGION")
            or DEFAULT_REGION
        )
        self.model = model or os.environ.get("BEDROCK_MODEL_ID") or ""
        self.max_tokens = max_tokens
        self._client = None
        self._lock = threading.Lock()
        self._healthy_model: Optional[str] = None

    def _runtime(self):
        """Build the Bedrock Runtime client lazily.

        Lazy because importing this module must never require credentials: the
        rest of GreenCode (static analysis, SCI maths, carbon intensity) has to
        import cleanly on a machine with no AWS account at all.
        """
        if self._client is None:
            with self._lock:
                if self._client is None:
                    try:
                        import boto3
                    except ImportError as exc:  # pragma: no cover
                        raise BedrockError(
                            "boto3 is not installed. Run: pip install boto3",
                            kind="unavailable",
                        ) from exc
                    self._client = boto3.client(BEDROCK_RUNTIME, region_name=self.region_name)
        return self._client

    @property
    def configured(self) -> bool:
        """True when Bedrock can plausibly be reached.

        boto3 can sign requests from any credential source - env vars, the
        shared config file, an instance role, an SSO cache - so key material is
        deliberately not required here. A false positive costs one failed call;
        a false negative would silently disable a working path.
        """
        return bool(self.model) or bool(
            os.environ.get("AWS_ACCESS_KEY_ID")
            or os.environ.get("AWS_PROFILE")
            or os.environ.get("AWS_WEB_IDENTITY_TOKEN_FILE")
            or os.environ.get("AWS_CONTAINER_CREDENTIALS_RELATIVE_URI")
        )

    @staticmethod
    def list_models() -> Tuple[str, ...]:
        return DEFAULT_MODELS
    def health(self) -> Dict[str, Any]:
        """Report reachability without raising, for /api/health."""
        report: Dict[str, Any] = {
            "provider": "aws_bedrock",
            "region": self.region_name,
            "configured_model": self.model or None,
            "candidate_models": list(DEFAULT_MODELS),
            "reachable": False,
            "detail": None,
        }
        if not self.configured:
            report["detail"] = (
                "No AWS credentials and no BEDROCK_MODEL_ID found. Set AWS_PROFILE, "
                "AWS_ACCESS_KEY_ID, or BEDROCK_MODEL_ID to enable the Bedrock backend."
            )
            return report
        try:
            self._runtime()
            report["reachable"] = True
            report["detail"] = "boto3 bedrock-runtime client constructed successfully."
        except Exception as exc:  # pragma: no cover - defensive
            report["detail"] = f"{type(exc).__name__}: {exc}"
        return report

    @staticmethod
    def _classify(exc: Exception) -> BedrockError:
        """Map a botocore exception onto a classified, actionable error."""
        name = type(exc).__name__
        code = ""
        response = getattr(exc, "response", None)
        if isinstance(response, dict):
            code = str(response.get("Error", {}).get("Code", ""))

        if name in ("NoCredentialsError", "PartialCredentialsError") or code in (
            "UnrecognizedClientException",
            "InvalidSignatureException",
        ):
            return BedrockError(
                "Bedrock rejected the AWS credentials. Configure a profile, "
                "instance role, or AWS_ACCESS_KEY_ID.",
                kind="auth",
            )
        if code == "AccessDeniedException":
            return BedrockError(
                "AWS credentials are valid but lack permission for "
                "bedrock:InvokeModel. Attach a Bedrock model access policy.",
                kind="auth",
            )
        if code in ("ThrottlingException", "TooManyRequestsException"):
            return BedrockError(
                "Bedrock throttled the request. Retry shortly.",
                kind="rate_limit",
                retryable=True,
            )
        if code == "ValidationException" or name == "ValidationException":
            return BedrockError(
                f"Bedrock rejected the request: {str(exc)[:300]}", kind="bad_request"
            )
        if code in ("ModelNotReadyException", "ServiceUnavailableException"):
            return BedrockError(
                f"Bedrock is temporarily unavailable: {str(exc)[:200]}",
                kind="unavailable",
                retryable=True,
            )
        return BedrockError(
            f"Bedrock call failed ({name}): {str(exc)[:300]}", kind="network", retryable=True
        )
    def _to_converse(
        self, messages: List[Dict[str, str]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Split a system prompt out and map the rest onto provider roles."""
        system_parts: List[str] = []
        mapped: List[Dict[str, Any]] = []
        active = self._healthy_model or self.model or DEFAULT_MODELS[0]
        roles = _PROVIDER_ROLES.get(_provider_of(active), _DEFAULT_ROLES)

        for message in messages:
            raw_role = message.get("role", "human")
            text = message.get("content", "")
            if raw_role == "system":
                system_parts.append(text)
                continue
            mapped.append(
                {"role": roles.get(raw_role, raw_role), "content": [{"text": text}]}
            )

        system_block = [{"text": part} for part in system_parts]
        if not mapped:
            # Converse rejects an empty message list outright, so a
            # system-only request still needs one placeholder turn.
            mapped = [
                {"role": roles["human"], "content": [{"text": "Return the code."}]}
            ]
        return system_block, mapped

    def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
        stop: Optional[List[str]] = None,
    ) -> Tuple[str, LLMUsage, str]:
        """Run one Converse call. Returns ``(content, usage, model_used)``."""
        candidates: List[str] = []
        if model:
            candidates.append(model)
        if self.model and self.model not in candidates:
            candidates.append(self.model)
        if self._healthy_model and self._healthy_model not in candidates:
            candidates.insert(0, self._healthy_model)
        for fallback in DEFAULT_MODELS:
            if fallback not in candidates:
                candidates.append(fallback)

        if not self.configured:
            raise BedrockError(
                "Amazon Bedrock is not configured. Set AWS credentials and "
                "BEDROCK_MODEL_ID, or set GREENCODE_LLM_PROVIDER=huggingface.",
                kind="auth",
            )

        last_error: Optional[BedrockError] = None
        for candidate in candidates:
            self._healthy_model = candidate
            try:
                runtime = self._runtime()
                system_block, mapped = self._to_converse(messages)
                inference: Dict[str, Any] = {
                    "maxTokens": max_tokens,
                    "temperature": temperature,
                }
                if stop:
                    inference["stopSequences"] = list(stop)
                request: Dict[str, Any] = {
                    "modelId": candidate,
                    "messages": mapped,
                    "inferenceConfig": inference,
                }
                if system_block:
                    request["system"] = system_block
                response = runtime.converse(**request)
            except Exception as exc:  # noqa: BLE001 - re-raised as classified error
                last_error = self._classify(exc)
                logger.warning("Bedrock call failed for %s: %s", candidate, last_error.message)
                continue

            content = ""
            for block in response.get("output", {}).get("message", {}).get("content", []):
                text = block.get("text")
                if text:
                    content += text
            if not content:
                last_error = BedrockError(
                    f"Bedrock returned no text content for {candidate}.", kind="unknown"
                )
                continue

            usage_raw = response.get("usage", {}) or {}
            usage = LLMUsage(
                prompt_tokens=int(usage_raw.get("inputTokens", 0) or 0),
                completion_tokens=int(usage_raw.get("outputTokens", 0) or 0),
            )
            self._healthy_model = candidate
            return content, usage, candidate

        raise last_error or BedrockError(
            "No Bedrock model produced a completion.", kind="unknown"
        )


_client_singleton: Optional[BedrockClient] = None
_singleton_lock = threading.Lock()


def get_client() -> BedrockClient:
    """Return the process-wide Bedrock client."""
    global _client_singleton
    if _client_singleton is None:
        with _singleton_lock:
            if _client_singleton is None:
                _client_singleton = BedrockClient()
    return _client_singleton

