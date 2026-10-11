"""Enterprise Audit Lifecycle & Persistence Service."""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from app.audit.analyzer import CodeAnalyzer
from app.database import SessionLocal, Repository, ScanViolation, Project


class AuditService:
    """Orchestrates code audit runs, persistence, and compliance scoring."""

    @classmethod
    def execute_audit(cls, path: str, project_id: Optional[int] = None, commit_sha: str = "HEAD") -> Dict[str, Any]:
        """Runs the static AST scanner and records results."""
        analysis_result = CodeAnalyzer.scan_path(path)
        violations = analysis_result.get("violations", [])
        green_score = float(analysis_result.get("green_score", 100.0))
        total_energy = float(analysis_result.get("total_energy_joules", 0.05))

        db = SessionLocal()
        try:
            repo_record = None
            if project_id:
                proj = db.query(Project).filter(Project.id == project_id).first()
                if proj:
                    repo_record = (
                        db.query(Repository)
                        .filter(Repository.org_id == proj.org_id, Repository.name == proj.name)
                        .first()
                    )
                    if not repo_record:
                        repo_record = Repository(
                            name=proj.name,
                            path_or_url=proj.repo_url or f"https://internal/{proj.slug}",
                            default_branch=proj.default_branch or "main",
                            green_score=green_score,
                            total_files=int(analysis_result.get("total_files", 0)),
                            total_lines=int(analysis_result.get("total_lines", 0)),
                            org_id=proj.org_id,
                            status="completed",
                        )
                        db.add(repo_record)
                        db.flush()

            if repo_record:
                repo_record.green_score = green_score
                repo_record.total_files = int(analysis_result.get("total_files", 0))
                repo_record.total_lines = int(analysis_result.get("total_lines", 0))
                repo_record.created_at = datetime.now(timezone.utc)
                db.commit()

            return {
                "project_id": project_id,
                "commit_sha": commit_sha,
                "path_scanned": path,
                "green_score": green_score,
                "total_energy_joules": total_energy,
                "total_files": analysis_result.get("total_files", 0),
                "total_lines": analysis_result.get("total_lines", 0),
                "violations_count": len(violations),
                "violations": violations[:50],  # Return top violations
                "passed": green_score >= 80.0,
            }
        finally:
            db.close()

    @classmethod
    def get_project_audits(cls, project_id: int) -> List[Dict[str, Any]]:
        """Retrieve historical audits for a project."""
        db = SessionLocal()
        try:
            proj = db.query(Project).filter(Project.id == project_id).first()
            if proj:
                repos = (
                    db.query(Repository)
                    .filter(Repository.org_id == proj.org_id, Repository.name == proj.name)
                    .order_by(Repository.created_at.desc())
                    .all()
                )
            else:
                repos = db.query(Repository).filter(Repository.id == project_id).all()
            return [
                {
                    "id": repo.id,
                    "name": repo.name,
                    "green_score": repo.green_score,
                    "carbon_intensity_tier": "LOW" if (repo.green_score or 100.0) >= 80.0 else "MEDIUM",
                    "last_scanned": repo.created_at.isoformat() if repo.created_at else None,
                }
                for repo in repos
            ]
        finally:
            db.close()

