"""Runtime configuration for the GreenCode Reality Verification Pipeline.

A pipeline that decides whether a carbon claim is real is only as trustworthy as
its configuration, so every value is resolved from the environment at *call time*
rather than import time. That gives three things for free: a deployment can rotate
the webhook secret without touching code, a test can drive the whole pipeline with
a temporary environment, and a misconfigured production host is detectable
(`production_blockers`) instead of silently accepting unsigned traffic.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List

TRUE_VALUES = {"1", "true", "yes", "on"}
PRODUCTION_ENVS = {"production", "prod", "staging"}


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in TRUE_VALUES


def _env_int(name: str, default: int) -> int:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return int(float(raw))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_list(name: str) -> List[str]:
    raw = os.environ.get(name) or ""
    return [item.strip() for item in raw.split(",") if item.strip()]



@dataclass
class PipelineConfig:
    """Every knob the pipeline reads, resolved once per operation."""

    # --- intake security -------------------------------------------------
    webhook_secret: str = ""
    allow_unsigned: bool = True
    max_skew_seconds: int = 300

    # --- verification policy --------------------------------------------
    default_tolerance_pct: float = 15.0
    default_min_samples: int = 3
    max_spread_pct: float = 20.0
    auto_claim: bool = False

    # --- egress ---------------------------------------------------------
    slack_webhook_url: str = ""
    teams_webhook_url: str = ""
    n8n_webhook_url: str = ""
    notify_email_to: List[str] = field(default_factory=list)
    http_timeout_seconds: float = 8.0
    max_retries: int = 2

    # --- runtime --------------------------------------------------------
    environment: str = "development"

    @classmethod
    def from_env(cls) -> "PipelineConfig":
        return cls(
            webhook_secret=_env_str("GREENCODE_PIPELINE_WEBHOOK_SECRET"),
            # Unsigned intake is a development convenience only; production
            # refuses it outright (see `production_blockers`).
            allow_unsigned=_env_bool("GREENCODE_PIPELINE_ALLOW_UNSIGNED", True),
            max_skew_seconds=_env_int("GREENCODE_PIPELINE_MAX_SKEW_SECONDS", 300),
            default_tolerance_pct=_env_float("GREENCODE_PIPELINE_TOLERANCE_PCT", 15.0),
            default_min_samples=_env_int("GREENCODE_PIPELINE_MIN_SAMPLES", 3),
            max_spread_pct=_env_float("GREENCODE_PIPELINE_MAX_SPREAD_PCT", 20.0),
            auto_claim=_env_bool("GREENCODE_PIPELINE_AUTO_CLAIM", False),
            slack_webhook_url=_env_str("GREENCODE_PIPELINE_SLACK_WEBHOOK"),
            teams_webhook_url=_env_str("GREENCODE_PIPELINE_TEAMS_WEBHOOK"),
            n8n_webhook_url=_env_str("GREENCODE_PIPELINE_N8N_WEBHOOK_URL"),
            notify_email_to=_env_list("GREENCODE_PIPELINE_NOTIFY_EMAIL"),
            http_timeout_seconds=_env_float("GREENCODE_PIPELINE_HTTP_TIMEOUT_SECONDS", 8.0),
            max_retries=_env_int("GREENCODE_PIPELINE_MAX_RETRIES", 2),
            environment=_env_str("ENV", "development").lower(),
        )

    @property
    def is_production(self) -> bool:
        return self.environment in PRODUCTION_ENVS

    @property
    def signature_enforced(self) -> bool:
        """Whether inbound events must carry a valid HMAC signature."""
        return bool(self.webhook_secret) and not self.allow_unsigned

    def production_blockers(self) -> List[str]:
        """Configuration faults that must block a production deployment."""
        blockers: List[str] = []
        if self.is_production:
            if not self.webhook_secret:
                blockers.append(
                    "GREENCODE_PIPELINE_WEBHOOK_SECRET is not set. Anyone who can "
                    "reach the pipeline could file verification evidence for any "
                    "repository."
                )
            elif self.allow_unsigned:
                blockers.append(
                    "GREENCODE_PIPELINE_ALLOW_UNSIGNED is enabled in production. "
                    "Evidence intake is unauthenticated, so the ledger is forgeable."
                )
            if not self.slack_webhook_url and not self.teams_webhook_url and not self.notify_email_to:
                blockers.append(
                    "No notification channel configured. Verdicts would be recorded "
                    "but never reach an operator, which is a silent failure."
                )
        return blockers

    def public_status(self) -> Dict[str, Any]:
        """Configuration view safe to expose over HTTP (no secret material)."""
        return {
            "signature_enforced": self.signature_enforced,
            "allow_unsigned": self.allow_unsigned,
            "webhook_secret_configured": bool(self.webhook_secret),
            "max_skew_seconds": self.max_skew_seconds,
            "policy": {
                "default_tolerance_pct": self.default_tolerance_pct,
                "default_min_samples": self.default_min_samples,
                "max_spread_pct": self.max_spread_pct,
            },
            "channels": {
                "slack": bool(self.slack_webhook_url),
                "teams": bool(self.teams_webhook_url),
                "email": bool(self.notify_email_to),
                "n8n_forward": bool(self.n8n_webhook_url),
            },
            "auto_claim": self.auto_claim,
            "environment": self.environment,
            "blockers": self.production_blockers(),
        }


def _env_str(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()
