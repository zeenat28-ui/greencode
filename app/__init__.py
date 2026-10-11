"""GreenCode Auditor - Software Carbon Intensity, FinOps, and Optimization Platform.

Public Python SDK exports:
    from app import GreenCodeSDK, track_energy, EnergyTracker
    from app import audit_source_code, audit_repository, audit_iac_content
    from app import reconcile_focus_billing, compute_sci
"""

from app.finops_focus import reconcile_focus_billing
from app.iac_linter import audit_iac_content
from app.parser import audit_repository, audit_source_code
from app.sci import compute_sci, export_impact_framework_manifest
from app.sdk import EnergyTracker, GreenCodeSDK, track_energy

__version__ = "2.0.0"

__all__ = [
    "__version__",
    "GreenCodeSDK",
    "EnergyTracker",
    "track_energy",
    "audit_source_code",
    "audit_repository",
    "audit_iac_content",
    "reconcile_focus_billing",
    "compute_sci",
    "export_impact_framework_manifest",
]
