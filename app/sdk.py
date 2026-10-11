"""Public Python SDK and `@track_energy` Context Manager / Decorator for GreenCode.

Enables external developers, data scientists, and platform engineers to embed
GreenCode static analysis, IaC FinOps linting, FOCUS 1.4 billing reconciliation,
and live ISO/IEC 21031 (GSF SCI) runtime energy tracking directly into their own
Python applications and test suites with a single import:

    from app import GreenCodeSDK, track_energy
"""

from __future__ import annotations

from functools import wraps
import time
from typing import Any, Callable, Dict, List, Optional, TypeVar

import psutil

from app.energy_sensors import MEMORY_WATTS_PER_GIB, TDP_IDLE_WATTS, TDP_SATURATION_WATTS
from app.finops_focus import reconcile_focus_billing
from app.iac_linter import audit_iac_content
from app.optimizer import get_zone_carbon_intensity
from app.parser import audit_git_diff, audit_repository, audit_source_code
from app.sarif import generate_sarif_report, generate_sonarqube_report
from app.sci import compute_sci, export_impact_framework_manifest, sci_grade

F = TypeVar("F", bound=Callable[..., Any])


class EnergyTracker:
    """Dual context-manager and function decorator for ISO/IEC 21031 SCI energy tracking."""

    def __init__(
        self,
        label: str = "workload",
        *,
        zone: str = "US-CAL-CISO",
        functional_unit: float = 1.0,
        vcpu_count: int = 1,
    ) -> None:
        self.label = label
        self.zone = zone
        self.functional_unit = max(1e-9, float(functional_unit))
        self.vcpu_count = max(1, int(vcpu_count))
        self._start_wall: float = 0.0
        self._start_cpu: float = 0.0
        self._proc = psutil.Process()
        self.result: Optional[Dict[str, Any]] = None

    def __enter__(self) -> "EnergyTracker":
        self._start_wall = time.perf_counter()
        cpu_times = self._proc.cpu_times()
        self._start_cpu = float(cpu_times.user + cpu_times.system)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        duration = max(1e-6, time.perf_counter() - self._start_wall)
        cpu_times = self._proc.cpu_times()
        cpu_delta = max(0.0, float(cpu_times.user + cpu_times.system) - self._start_cpu)
        cpu_util = min(1.0, cpu_delta / duration)

        rss_gib = float(self._proc.memory_info().rss) / (1024.0 ** 3)
        cpu_watts = TDP_IDLE_WATTS + (TDP_SATURATION_WATTS - TDP_IDLE_WATTS) * cpu_util
        mem_watts = rss_gib * MEMORY_WATTS_PER_GIB
        cpu_joules = cpu_watts * duration
        mem_joules = mem_watts * duration
        it_joules = cpu_joules + mem_joules

        zone_info = get_zone_carbon_intensity(self.zone)
        grid_intensity = float(zone_info.get("carbon_intensity", 380.0))

        sci_res = compute_sci(
            energy_joules=it_joules,
            duration_seconds=duration,
            carbon_intensity_gco2_per_kwh=grid_intensity,
            functional_unit=self.functional_unit,
            cpu_joules=cpu_joules,
            memory_joules=mem_joules,
            measurement_method="model",
            vcpu_count=self.vcpu_count,
        )
        grade_info = sci_grade(sci_res.sci_gco2_per_functional_unit)
        self.result = {
            "label": self.label,
            "zone": self.zone,
            "duration_seconds": round(duration, 6),
            "cpu_utilization_ratio": round(cpu_util, 4),
            "energy_joules": round(sci_res.energy_joules, 9),
            "energy_kwh": round(sci_res.energy_kwh, 12),
            "operational_gco2": round(sci_res.operational_gco2, 12),
            "embodied_gco2": round(sci_res.embodied_gco2, 12),
            "sci_gco2_per_functional_unit": round(sci_res.sci_gco2_per_functional_unit, 12),
            "carbon_intensity_gco2_per_kwh": grid_intensity,
            "grade": grade_info["grade"],
        }

    def __call__(self, func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with self:
                return func(*args, **kwargs)

        setattr(wrapper, "energy_tracker", self)
        return wrapper  # type: ignore[return-value]


def track_energy(
    label: str = "workload",
    *,
    zone: str = "US-CAL-CISO",
    functional_unit: float = 1.0,
    vcpu_count: int = 1,
) -> EnergyTracker:
    """Create a context manager or decorator that tracks execution energy and GSF SCI."""
    return EnergyTracker(
        label=label,
        zone=zone,
        functional_unit=functional_unit,
        vcpu_count=vcpu_count,
    )


class GreenCodeSDK:
    """High-level programmatic facade for embedding GreenCode into external Python projects."""

    def __init__(self, default_zone: str = "US-CAL-CISO") -> None:
        self.default_zone = default_zone

    def audit_code(
        self,
        source_code: str,
        *,
        language: str = "python",
        file_path: str = "snippet.py",
    ) -> Dict[str, Any]:
        """Run multi-language static carbon and complexity analysis on a source string."""
        return audit_source_code(source_code, language=language, file_path=file_path)

    def audit_path(self, path: str = ".") -> Dict[str, Any]:
        """Recursively audit a file or repository directory."""
        return audit_repository(path)

    def audit_diff(
        self,
        diff_text: str,
        *,
        repo_root: Optional[str] = None,
        source_files: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Audit only the modified lines in a unified git diff."""
        return audit_git_diff(diff_text, repo_root=repo_root, source_files=source_files)

    def audit_iac(
        self,
        content: str,
        *,
        file_path: str = "main.tf",
        iac_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Audit Terraform (.tf), Kubernetes (.yaml), or Dockerfile manifests."""
        return audit_iac_content(content=content, file_path=file_path, iac_type=iac_type)

    def reconcile_focus(
        self,
        *,
        rows: Optional[List[Dict[str, Any]]] = None,
        csv_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Reconcile FinOps Foundation FOCUS 1.4 billing data with energy and carbon."""
        return reconcile_focus_billing(rows=rows, csv_text=csv_text)

    def export_sarif(
        self,
        scan_result: Dict[str, Any],
        *,
        output_path: Optional[str] = None,
        base_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Export an OASIS SARIF v2.1.0 report with embedded autofix replacements."""
        return generate_sarif_report(scan_result, output_path=output_path, base_dir=base_dir)

    def export_sonarqube(
        self,
        scan_result: Dict[str, Any],
        *,
        output_path: Optional[str] = None,
        base_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Export a SonarQube Generic Issue Import JSON report."""
        return generate_sonarqube_report(scan_result, output_path=output_path, base_dir=base_dir)

    def export_if_manifest(self, **kwargs: Any) -> Dict[str, Any]:
        """Export a Green Software Foundation Impact Framework (.imp.yaml) manifest."""
        return export_impact_framework_manifest(**kwargs)
