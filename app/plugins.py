"""Extensible Plugin & Event Hook Registry for GreenCode Auditor.

Provides a clean extension architecture so external developers and platform
teams can register custom static/IaC analyzers, post-audit lifecycle hooks,
and HMAC-SHA256 signed outbound webhook sinks (Slack, Datadog, PagerDuty,
OpenTelemetry, or custom HTTP receivers) without modifying core engine code.
"""

from datetime import datetime, timezone
import hashlib
import hmac
import json
from typing import Any, Callable, Dict, List, Optional


class PluginRegistry:
    """Central registry for analyzers, lifecycle hooks, and signed webhook sinks."""

    def __init__(self) -> None:
        self._analyzers: Dict[str, Dict[str, Any]] = {}
        self._hooks: Dict[str, Dict[str, Any]] = {}
        self._webhooks: Dict[str, Dict[str, Any]] = {}
        self._register_builtin_plugins()

    def _register_builtin_plugins(self) -> None:
        builtins = [
            {
                "id": "oasis-sarif-v2.1-autofix",
                "name": "OASIS SARIF v2.1.0 Exporter with ArtifactChanges",
                "version": "2.0.0",
                "category": "exporter",
                "languages": ["*"],
                "description": "Exports static findings and deterministic AST replacements in OASIS SARIF v2.1.0 format.",
            },
            {
                "id": "gsf-impact-framework-manifest",
                "name": "GSF Impact Framework (.imp.yaml) Exporter",
                "version": "2.0.0",
                "category": "compliance",
                "languages": ["*"],
                "description": "Generates @grnsft/if-plugins compatible SciE/SciO/SciM/Sci manifests per ISO/IEC 21031:2024.",
            },
            {
                "id": "finops-focus-1.4-reconciler",
                "name": "FinOps Foundation FOCUS 1.4 Billing Reconciler",
                "version": "2.0.0",
                "category": "finops",
                "languages": ["csv", "json"],
                "description": "Reconciles cloud billing rows (BilledCost, EffectiveCost) with regional PUE and gCO2e/kWh.",
            },
            {
                "id": "iac-graviton-k8s-linter",
                "name": "Terraform, Kubernetes & Dockerfile FinOps Linter",
                "version": "2.0.0",
                "category": "analyzer",
                "languages": ["terraform", "kubernetes", "dockerfile"],
                "description": "Detects x86-to-Graviton migrations, gp2-to-gp3 upgrades, and missing K8s resource limits.",
            },
        ]
        for b in builtins:
            self._analyzers[b["id"]] = b

    def register_analyzer(
        self,
        plugin_id: str,
        name: str,
        *,
        version: str = "1.0.0",
        languages: Optional[List[str]] = None,
        description: str = "",
        callback: Optional[Callable[[str, str], List[Dict[str, Any]]]] = None,
    ) -> Dict[str, Any]:
        """Register an external static or IaC analyzer plugin."""
        entry = {
            "id": plugin_id,
            "name": name,
            "version": version,
            "category": "analyzer",
            "languages": languages or ["*"],
            "description": description,
            "has_callable": callback is not None,
            "callback": callback,
        }
        self._analyzers[plugin_id] = entry
        return self._public_analyzer_view(entry)

    @staticmethod
    def _public_analyzer_view(entry: Dict[str, Any]) -> Dict[str, Any]:
        return {k: v for k, v in entry.items() if k != "callback"}

    def register_hook(
        self,
        hook_id: str,
        event_type: str,
        callback: Callable[[Dict[str, Any]], Any],
        *,
        description: str = "",
    ) -> Dict[str, Any]:
        """Register an in-process Python callback for lifecycle events (e.g. 'audit.completed')."""
        entry = {
            "id": hook_id,
            "event_type": event_type,
            "description": description,
            "callback": callback,
        }
        self._hooks[hook_id] = entry
        return {"id": hook_id, "event_type": event_type, "description": description}

    def register_webhook_sink(
        self,
        sink_id: str,
        target_url: str,
        *,
        events: Optional[List[str]] = None,
        secret: str = "greencode-webhook-secret",
    ) -> Dict[str, Any]:
        """Register an outbound webhook endpoint with HMAC-SHA256 payload signing."""
        entry = {
            "id": sink_id,
            "target_url": target_url,
            "events": events or ["audit.completed", "budget.breached", "iac.audited"],
            "secret": secret,
            "registered_at": datetime.now(timezone.utc).isoformat(),
        }
        self._webhooks[sink_id] = entry
        return {
            "id": sink_id,
            "target_url": target_url,
            "events": entry["events"],
            "registered_at": entry["registered_at"],
        }

    @staticmethod
    def sign_payload(payload_bytes: bytes, secret: str) -> str:
        """Compute an HMAC-SHA256 signature (`sha256=<hex>`) for outbound webhook verification."""
        digest = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
        return f"sha256={digest}"

    def _build_webhook_delivery(self, sink: Dict[str, Any], event_type: str, body_bytes: bytes) -> Dict[str, Any]:
        sig = self.sign_payload(body_bytes, str(sink.get("secret") or "greencode-webhook-secret"))
        return {
            "sink_id": sink["id"],
            "target_url": sink["target_url"],
            "headers": {
                "Content-Type": "application/json",
                "X-GreenCode-Event": event_type,
                "X-GreenCode-Signature-256": sig,
            },
            "signature": sig,
        }

    def dispatch_event(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute matching in-process hooks and build signed webhook delivery envelopes."""
        envelope = {
            "event": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": payload,
        }
        body_bytes = json.dumps(envelope, sort_keys=True).encode("utf-8")

        matching_hooks = [
            h for h in self._hooks.values()
            if h["event_type"] in ("*", event_type)
        ]
        hook_results = []
        for h in matching_hooks:
            try:
                res = h["callback"](envelope)
                hook_results.append({"hook_id": h["id"], "status": "ok", "result": res})
            except Exception as exc:
                hook_results.append({"hook_id": h["id"], "status": "error", "error": str(exc)})

        matching_sinks = [
            w for w in self._webhooks.values()
            if "*" in w["events"] or event_type in w["events"]
        ]
        deliveries = [self._build_webhook_delivery(w, event_type, body_bytes) for w in matching_sinks]

        return {
            "event": event_type,
            "hooks_invoked": len(hook_results),
            "hook_results": hook_results,
            "webhook_deliveries_prepared": len(deliveries),
            "webhook_deliveries": deliveries,
        }

    def list_catalog(self) -> Dict[str, Any]:
        """Return all registered analyzer plugins, lifecycle hooks, and webhook sinks."""
        analyzers = [self._public_analyzer_view(a) for a in self._analyzers.values()]
        hooks = [
            {"id": h["id"], "event_type": h["event_type"], "description": h["description"]}
            for h in self._hooks.values()
        ]
        webhooks = [
            {
                "id": w["id"],
                "target_url": w["target_url"],
                "events": w["events"],
                "registered_at": w["registered_at"],
            }
            for w in self._webhooks.values()
        ]
        return {
            "total_plugins": len(analyzers),
            "analyzers": analyzers,
            "hooks": hooks,
            "webhook_sinks": webhooks,
        }


plugin_registry = PluginRegistry()

