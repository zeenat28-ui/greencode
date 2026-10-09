"""Enterprise Settings and Feature Flags Manager."""

from typing import Any, Dict

_ENTERPRISE_SETTINGS = {
    "enforce_policies": True,
    "enable_k8s_rollback": True,
    "default_monthly_budget_kg": 500.0,
    "alert_channel": "console",
    "retention_days": 365,
    "soc2_compliance_mode": True,
}


class AdminSettings:
    """Manages dynamic enterprise configuration and guardrail settings."""

    @classmethod
    def get_settings(cls) -> Dict[str, Any]:
        return dict(_ENTERPRISE_SETTINGS)

    @classmethod
    def update_settings(cls, updates: Dict[str, Any]) -> Dict[str, Any]:
        for k, v in updates.items():
            if v is not None and k in _ENTERPRISE_SETTINGS:
                _ENTERPRISE_SETTINGS[k] = v
        return dict(_ENTERPRISE_SETTINGS)

