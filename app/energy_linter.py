"""Real-Time Energy Linter & Language Server Protocol (LSP) Engine.

Enables instant, real-time energy feedback in developer IDEs (VS Code, Cursor, IntelliJ)
before code is committed or pushed.

Features:
- Fast AST and CST energy anti-pattern linting.
- Calculates estimated annual kWh and financial waste ($ USD) per anti-pattern.
- Produces LSP-compliant diagnostics and quick-fix automated refactoring proposals.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from typing import Any, Dict, List, Optional

from app.parser import audit_source_code, VIOLATION_METADATA


@dataclass
class EnergyDiagnostic:
    """Diagnostic item formatted for Language Server Protocol (LSP) / IDE consumption."""
    line_number: int
    end_line_number: int
    severity: str  # ERROR, WARNING, INFORMATION
    code: str      # E.g. "GSF-001-QUADRATIC-LOOP"
    title: str
    message: str
    annual_cost_usd: float
    annual_co2_kg: float
    suggested_fix: str
    quick_fix_code: Optional[str] = None


class EnergyLinter:
    """Real-Time IDE Energy Linter backed by CalibratedEnergyModel."""

    @classmethod
    def lint_code(cls, source_code: str, language: str = "python", file_path: str = "snippet.py") -> List[EnergyDiagnostic]:
        """Lint code buffer and return LSP diagnostics with physics-calibrated carbon and dollar impact."""
        from app.energy_debt import EnergyDebtTracker

        raw_audit = audit_source_code(source_code, language=language, file_path=file_path)
        violations = raw_audit.get("violations", [])

        diagnostics: List[EnergyDiagnostic] = []

        for v in violations:
            sev = v.get("severity", "MEDIUM").upper()
            impact = EnergyDebtTracker.estimate_violation_impact(v)

            lsp_severity = "ERROR" if sev in ("CRITICAL", "HIGH") else "WARNING" if sev == "MEDIUM" else "INFORMATION"

            diag = EnergyDiagnostic(
                line_number=v.get("line_number", 1),
                end_line_number=v.get("end_line_number", v.get("line_number", 1)),
                severity=lsp_severity,
                code=v.get("violation_type", "GSF-ENERGY-VIOLATION"),
                title=v.get("title", "Energy Inefficiency"),
                message=(
                    f"{v.get('title')}: {v.get('description')} "
                    f"[Estimated Impact: ~${impact['cost_usd']:.2f}/yr, {impact['co2_kg']:.1f} kg CO2e, "
                    f"{impact['joules_per_1k_calls']:.1f} J/1k calls]"
                ),
                annual_cost_usd=impact["cost_usd"],
                annual_co2_kg=impact["co2_kg"],
                suggested_fix=v.get("suggested_fix", ""),
            )
            diagnostics.append(diag)

        return diagnostics

    @classmethod
    def format_lsp_response(cls, diagnostics: List[EnergyDiagnostic]) -> Dict[str, Any]:
        """Format diagnostics as standard Language Server Protocol publishDiagnostics payload."""
        lsp_diags = []
        for d in diagnostics:
            lsp_diags.append({
                "range": {
                    "start": {"line": max(0, d.line_number - 1), "character": 0},
                    "end": {"line": max(0, d.end_line_number - 1), "character": 80},
                },
                "severity": 1 if d.severity == "ERROR" else 2 if d.severity == "WARNING" else 3,
                "code": d.code,
                "source": "GreenCode Linter",
                "message": d.message,
                "data": {
                    "annual_cost_usd": d.annual_cost_usd,
                    "annual_co2_kg": d.annual_co2_kg,
                    "suggested_fix": d.suggested_fix,
                },
            })
        return {"diagnostics": lsp_diags}

