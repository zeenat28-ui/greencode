"""Backend actions that back the GreenCode Alexa voice surface.

These five actions close the gap between the voice layer and the dashboard:

- ``audit_diff``        - audit only the lines a pull request touches
- ``evaluate_sla``      - check a deployment against the energy SLA
- ``scope_inventory``   - Scope 1/2/3 GHG inventory for a workload
- ``audit_history``     - recent audits and cumulative carbon savings
- ``dynamic_analyze``   - sandboxed run of a repository with real measurements

Every function returns the same envelope the MCP tools use::

    {"status": "ok" | "error", "data": {...}, "warnings": [...]}

so ``app.alexa_skill`` can dispatch them exactly like the MCP tools and the
response builders never have to guess the shape of a result.
"""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
import zipfile
from typing import Any, Dict, List, Optional

logger = logging.getLogger("greencode.alexa.actions")


def _envelope(
    status: str,
    *,
    data: Optional[Dict[str, Any]] = None,
    warnings: Optional[List[str]] = None,
) -> Dict[str, Any]:
    return {
        "status": status,
        "data": data or {},
        "warnings": list(warnings or []),
    }


def _error(reason: str) -> Dict[str, Any]:
    return _envelope("error", data={"reason": reason})


# --------------------------------------------------------------------- diff --


def audit_diff(
    diff_text: str = "",
    repo: str = "",
    pr_number: Optional[int] = None,
    github_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Audit the modified lines of a unified diff.

    When ``diff_text`` is not supplied the diff is fetched from GitHub for
    ``repo`` / ``pr_number``. Only violations that intersect a changed hunk
    are reported, which is what a reviewer actually wants to hear.
    """
    from app.parser import audit_git_diff

    if not diff_text:
        if not repo or pr_number is None:
            return _error(
                "I need either a diff or a repository and pull request number "
                "to audit a diff."
            )
        from app.github_client import get_pull_request_diff

        fetched = get_pull_request_diff(
            repo=repo, pr_number=int(pr_number), token=github_token
        )
        if not fetched.get("success"):
            return _error(str(fetched.get("error", "Could not fetch the diff.")))
        diff_text = str(fetched.get("diff_text", ""))
        repo = str(fetched.get("repo", repo))

    if not diff_text.strip():
        return _error("That diff was empty, so there was nothing to audit.")

    try:
        result = audit_git_diff(diff_text=diff_text)
    except Exception as exc:  # noqa: BLE001 - reported to the speaker
        logger.exception("Diff audit failed")
        return _error(f"{type(exc).__name__}: {exc}")

    return _envelope(
        "ok",
        data={
            "repo": repo,
            "pr_number": pr_number,
            "modified_files_count": result.get("modified_files_count", 0),
            "hunks_analyzed": result.get("hunks_analyzed", 0),
            "total_diff_violations": result.get("total_diff_violations", 0),
            "diff_green_score": result.get("diff_green_score", 0.0),
            "violations": result.get("violations", []) or [],
            "per_file_results": result.get("per_file_results", []) or [],
        },
    )


# ---------------------------------------------------------------------- SLA --


def evaluate_sla(
    total_joules: float = 0.0,
    green_score: float = 0.0,
    sci_gco2e: float = 0.0,
    config_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Evaluate a deployment against the configured energy SLA."""
    from app.sla import EnergySLAEngine

    try:
        engine = EnergySLAEngine(config_path=config_path)
        verdict = engine.evaluate_deployment(
            total_joules=float(total_joules),
            green_score=float(green_score),
            sci_gco2e=float(sci_gco2e),
        )
    except Exception as exc:  # noqa: BLE001 - reported to the speaker
        logger.exception("SLA evaluation failed")
        return _error(f"{type(exc).__name__}: {exc}")

    return _envelope("ok", data=verdict.to_dict())


# ------------------------------------------------------------------- scope --


def scope_inventory(
    energy_joules: float = 3600.0,
    duration_seconds: float = 1.0,
    grid_intensity_gco2_per_kwh: float = 200.0,
    runs_per_year: int = 10000,
    team_size: int = 5,
    dev_hours: float = 160.0,
    cloud_provider: str = "aws",
    vcpu_count: int = 2,
    memory_gb: float = 4.0,
    data_transfer_gb: float = 0.05,
    grid_zone: str = "US-CAL-CISO",
    renewable_rec_pct: float = 0.0,
) -> Dict[str, Any]:
    """Generate a Scope 1, 2 and 3 GHG Protocol emissions inventory."""
    from app.scope import ScopeCalculator

    try:
        report = ScopeCalculator.generate_inventory(
            energy_joules=float(energy_joules),
            duration_seconds=float(duration_seconds),
            grid_intensity_gco2_per_kwh=float(grid_intensity_gco2_per_kwh),
            runs_per_year=int(runs_per_year),
            team_size=int(team_size),
            dev_hours=float(dev_hours),
            cloud_provider=str(cloud_provider),
            vcpu_count=int(vcpu_count),
            memory_gb=float(memory_gb),
            data_transfer_gb=float(data_transfer_gb),
            grid_zone=str(grid_zone),
            renewable_rec_pct=float(renewable_rec_pct),
        )
    except Exception as exc:  # noqa: BLE001 - reported to the speaker
        logger.exception("Scope inventory failed")
        return _error(f"{type(exc).__name__}: {exc}")

    return _envelope("ok", data=report.to_dict())


# ------------------------------------------------------------------ history --


def audit_history(
    limit: int = 5,
    offset: int = 0,
    user_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Return the caller's recent audits plus their cumulative savings."""
    from app.database import get_cumulative_carbon_savings, get_latest_repositories

    try:
        page = get_latest_repositories(
            limit=limit, user_id=user_id, offset=offset
        )
        cumulative = get_cumulative_carbon_savings(user_id=user_id)
    except Exception as exc:  # noqa: BLE001 - reported to the speaker
        logger.exception("Audit history lookup failed")
        return _error(f"{type(exc).__name__}: {exc}")

    return _envelope(
        "ok",
        data={
            "repositories": page.get("items", []) or [],
            "cumulative_savings": cumulative or {},
            "total": page.get("total", 0),
            "limit": page.get("limit", limit),
            "offset": page.get("offset", offset),
            "has_more": page.get("has_more", False),
        },
    )


# ------------------------------------------------------------- dynamic run --


def dynamic_analyze(
    repo: str = "",
    ref: str = "",
    grid_intensity: float = 380.0,
    functional_unit: float = 1.0,
    timeout_sec: float = 60.0,
    github_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Run a repository entry point in a sandbox and measure its energy.

    Dynamic analysis needs Docker and a self-hosted deployment. On a
    serverless host it reports ``sandbox_unavailable`` rather than
    returning numbers that were never measured.
    """
    if not repo:
        return _error("I need a repository to run, for example 'owner/repo'.")

    if os.environ.get("VERCEL", "").strip().lower() in {"1", "true", "yes"}:
        return _error(
            "Dynamic analysis needs Docker, which is not available on the "
            "serverless deployment. Use the dashboard on a self-hosted "
            "instance for that."
        )

    from app.dynamic_analysis import DynamicAnalyzer
    from app.github_client import GitHubAPIError, download_repository_archive

    analyzer = DynamicAnalyzer()
    if not analyzer.available():
        status = analyzer.status()
        reason = str(status.get("reason") or "sandbox_unavailable")
        return _error(
            f"Dynamic analysis is unavailable right now ({reason}). "
            "It needs a Docker sandbox."
        )

    workdir = tempfile.mkdtemp(prefix="greencode-alexa-dyn-")
    try:
        try:
            archive = download_repository_archive(
                repo, token=github_token, ref=ref or None
            )
        except GitHubAPIError as exc:
            return _error(exc.message)

        try:
            with zipfile.ZipFile(archive) as zf:
                zf.extractall(workdir)
        except (zipfile.BadZipFile, ValueError) as exc:
            return _error(f"Repository archive is not readable: {exc}")

        root = workdir
        entries = [e for e in os.listdir(workdir) if not e.startswith("__MACOSX")]
        if len(entries) == 1:
            candidate = os.path.join(workdir, entries[0])
            if os.path.isdir(candidate):
                root = candidate

        result = analyzer.analyze(
            root,
            repo_slug=repo,
            ref=ref,
            grid_intensity=float(grid_intensity),
            functional_unit=float(functional_unit),
            timeout_sec=float(timeout_sec),
        )
    except Exception as exc:  # noqa: BLE001 - reported to the speaker
        logger.exception("Dynamic analysis failed")
        return _error(f"{type(exc).__name__}: {exc}")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    return _envelope(
        "ok",
        data=result.to_dict(),
        warnings=list(result.warnings or []),
    )
