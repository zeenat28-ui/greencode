"""Shared GitHub audit orchestration.

Single source of truth for the "download a GitHub repo and audit it" pipeline.
Both the synchronous FastAPI endpoint and the asynchronous background worker call
`run_github_audit`, so the two paths can never drift apart.
"""

import json
import logging
import os
from typing import Any, Callable, Dict, Optional

from app.database import save_scan_results
from app.github_client import (
    GitHubAPIError,
    RepositoryTooLargeError,
    download_repository_archive,
    inspect_repository_before_audit,
    normalize_repo_slug,
)
from app.parser import audit_zip_archive, cleanup_workspace

logger = logging.getLogger("greencode.scanner")

# Repositories above this size are streamed to the background worker instead of
# blocking a synchronous HTTP request (and would time out behind a load balancer).
SYNC_SCAN_MAX_KB = 25 * 1024  # 25 MB
ASYNC_SCAN_MAX_KB = 100 * 1024  # 100 MB


class AuditRejected(Exception):
    """Raised when a repository cannot be audited (unsupported language, too large)."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def run_github_audit(
    repo_ref: str,
    ref: Optional[str] = None,
    token: Optional[str] = None,
    user_id: Optional[int] = None,
    display_name: Optional[str] = None,
    max_mb: int = 100,
    on_progress: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    """Download, extract and audit a GitHub repository end-to-end.

    Guarantees temp-file cleanup on every exit path (success, rejection, error).

    Returns the standard scan payload plus GitHub provenance fields.
    """
    notify = on_progress or (lambda _msg: None)
    slug = normalize_repo_slug(repo_ref)

    notify(f"Verifying {slug}...")
    preflight = inspect_repository_before_audit(slug, token=token)
    if not preflight.get("can_audit", True):
        raise AuditRejected(preflight.get("message", f"'{slug}' cannot be audited."), 400)

    target_ref = ref or preflight.get("default_branch") or "main"
    repo_name = display_name or slug.split("/", 1)[1]

    notify(f"Downloading {slug} @ {target_ref}...")
    zip_path = None
    workspace = None
    try:
        zip_path = download_repository_archive(slug, ref=target_ref, token=token, max_mb=max_mb)

        notify("Extracting source tree...")
        try:
            scan_result = audit_zip_archive(zip_path)
        except ValueError as exc:
            # Zip-bomb / file-count / traversal guards raise ValueError.
            raise AuditRejected(str(exc), 400) from exc

        workspace = scan_result.pop("workspace_dir", None)
        scan_result["repo_path"] = slug
        scan_result["full_name"] = slug
        scan_result["ref"] = target_ref
        scan_result["default_branch"] = preflight.get("default_branch", target_ref)
        scan_result["html_url"] = preflight.get("html_url", f"https://github.com/{slug}")
        scan_result["language"] = preflight.get("language", "Other")
        scan_result["source"] = "github"
        scan_result["is_github"] = True

        notify("Persisting audit record...")
        saved_repo = save_scan_results(
            name=repo_name,
            path_or_url=slug,
            total_files=scan_result["total_files"],
            total_lines=scan_result["total_lines"],
            green_score=scan_result["green_score"],
            violations_data=scan_result["violations"],
            summary_json=json.dumps(scan_result["violation_breakdown"]),
            user_id=user_id,
            source="github",
            full_name=slug,
            default_branch=scan_result["default_branch"],
            html_url=scan_result["html_url"],
        )
        scan_result["repo_id"] = saved_repo.id
        return scan_result
    finally:
        if zip_path and os.path.exists(zip_path):
            try:
                os.remove(zip_path)
            except OSError:
                logger.warning("Failed to remove temp archive %s", zip_path)
        if workspace:
            cleanup_workspace(workspace)


def github_error_to_http(exc: Exception) -> int:
    """Map a GitHub client exception onto an appropriate HTTP status code."""
    if isinstance(exc, RepositoryTooLargeError):
        return 413
    if isinstance(exc, GitHubAPIError):
        return exc.status_code
    if isinstance(exc, ValueError):
        return 400
    return 502
