"""FastAPI Application and CI/CD Quality Gatekeeper for GreenCode Auditor.

Handles repository static AST scanning, dynamic container profiling endpoints,
Electricity Maps live grid telemetry, GreenCode AI refactoring orchestration, and
provides a terminal CLI with exit code blockers for GitHub Actions integration.
"""

import argparse
from contextlib import asynccontextmanager
import json
import os
import sys
from typing import Any, Dict, List, Optional

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, Query, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from app.database import (
    authenticate_user,
    close_async_db,
    create_password_reset_token,
    create_user,
    get_cumulative_carbon_savings,
    get_latest_repositories,
    get_or_create_github_user,
    get_repository_details,
    get_user_by_email,
    get_user_by_id,
    get_user_by_username,
    init_db,
    reset_password_with_token,
    save_profile_metric,
    save_refactoring_record,
    save_scan_results,
    update_user_profile,
    verify_user_email,
)
from app.github_client import (
    create_refactoring_pull_request,
    get_authenticated_user,
    list_user_repositories,
    post_pr_carbon_comment,
)
from app.mailer import send_password_reset_email, send_verification_email
from app.optimizer import (
    get_zone_carbon_intensity,
    list_available_zones,
    refactor_repository_code,
)
from app.parser import audit_file_content, audit_repository, audit_zip_archive
from app.profiler import DynamicExecutionProfiler
from app.sarif import generate_sarif_report
from app.tasks import enqueue_scan_task, get_task_status




# Pydantic Schemas for API Requests & Responses
class SignUpRequest(BaseModel):
    email: str = Field(..., description="Developer email address")
    username: str = Field(..., description="Unique username")
    password: str = Field(..., description="Account password (min 6 characters)")
    full_name: Optional[str] = Field(None, description="Optional full name")
    github_token: Optional[str] = Field(None, description="Optional GitHub Personal Access Token")


class SignInRequest(BaseModel):
    login: str = Field(..., description="Email address or username")
    password: str = Field(..., description="Account password")


class GitHubAuthRequest(BaseModel):
    github_token: str = Field(..., description="GitHub Personal Access Token")


class UpdateProfileRequest(BaseModel):
    github_token: Optional[str] = Field(None, description="Updated GitHub Personal Access Token")
    github_username: Optional[str] = Field(None, description="Updated GitHub username")
    avatar_url: Optional[str] = Field(None, description="Updated avatar URL")
    full_name: Optional[str] = Field(None, description="Updated full name")


class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., description="Registered account email address")


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., description="Password reset security token")
    new_password: str = Field(..., description="New account password (min 6 characters)")


class ResendVerificationRequest(BaseModel):
    email: str = Field(..., description="Registered account email address")



class ScanRequest(BaseModel):
    repo_path: str = Field(..., description="Local folder directory path to audit")
    name: Optional[str] = Field(None, description="Optional custom repository name")


class ProfileRequest(BaseModel):
    file_path: str = Field(..., description="Path to target source file to profile (.py, .js, .go, .java, .cpp, .rs, .rb, .php, .sh)")
    timeout_sec: float = Field(30.0, description="Max execution timeout in seconds")
    zone: str = Field("US-CAL-CISO", description="Electricity Maps grid zone identifier")
    repo_id: Optional[int] = Field(None, description="Optional associated repository ID")



class RefactorRequest(BaseModel):
    snippet: str = Field(..., description="Inefficient code snippet to refactor")
    violation_type: str = Field(..., description="Detected violation type identifier")
    language: str = Field("python", description="Programming language: python, javascript, cpp, java, go")
    violation_id: Optional[int] = Field(None, description="Optional violation DB record ID")
    file_context: Optional[str] = Field("", description="Optional surrounding file context")
    api_key: Optional[str] = Field(None, description="Optional IBM Bob 2.0 API Key")


class GitHubPRRequest(BaseModel):
    repo_full_name: str = Field(..., description="GitHub repository full name, e.g. 'zeenat28-ui/greencode'")
    file_path: str = Field(..., description="Relative path of file in repo")
    refactored_code: str = Field(..., description="Optimized source code to commit")
    original_snippet: Optional[str] = Field(None, description="Original source code snippet to replace contextually")
    violation_title: str = Field("Energy Optimization", description="Violation type or title")
    energy_reduction_pct: float = Field(50.0, description="Estimated percentage energy saved")
    carbon_saved_10k: float = Field(30.0, description="Estimated carbon saved in gCO2eq per 10k runs")
    token: Optional[str] = Field(None, description="Optional GitHub Personal Access Token override")


class CIEvaluateRequest(BaseModel):
    repo_path: str = Field(".", description="Repository path to audit")
    threshold: float = Field(75.0, description="Minimum acceptable Green Score (0-100)")
    zone: str = Field("US-CAL-CISO", description="Regional grid zone code")



@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database tables upon application startup and dispose connections on shutdown."""
    init_db()
    try:
        yield
    finally:
        await close_async_db()


app = FastAPI(
    title="GreenCode Auditor API",
    description="Green Software Carbon Intensity Audit, Dynamic Profiling, and Automated Refactoring Platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

profiler_engine = DynamicExecutionProfiler()
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB


@app.get("/")
def read_root():
    return {
        "service": "GreenCode Auditor API",
        "version": "1.0.0",
        "status": "online",
        "standards": ["Green Software Foundation Patterns", "SCI Specification v1.0"],
        "docker_engine_ready": profiler_engine.is_docker_ready(),
    }


@app.get("/api/health", tags=["Health"])
def health_check():
    """Production health check probe for Docker, Kubernetes, and load balancers."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "GreenCode Auditor",
        "version": "1.0.0",
    }


@app.post("/api/scan")
def scan_repository_endpoint(req: ScanRequest):
    """Execute static AST analysis across an entire local directory path."""
    clean_path = os.path.abspath(req.repo_path)
    if not os.path.exists(clean_path):
        raise HTTPException(status_code=400, detail=f"Directory path does not exist: {req.repo_path}")

    scan_result = audit_repository(clean_path)
    repo_name = req.name or os.path.basename(clean_path) or "Repository"

    # Persist in SQLite
    saved_repo = save_scan_results(
        name=repo_name,
        path_or_url=clean_path,
        total_files=scan_result["total_files"],
        total_lines=scan_result["total_lines"],
        green_score=scan_result["green_score"],
        violations_data=scan_result["violations"],
        summary_json=json.dumps(scan_result["violation_breakdown"]),
    )

    scan_result["repo_id"] = saved_repo.id
    return scan_result


@app.post("/api/scan/async")
def scan_repository_async_endpoint(req: ScanRequest):
    """Offload repository scan to Celery / background worker to prevent gateway timeouts."""
    clean_path = os.path.abspath(req.repo_path)
    if not os.path.exists(clean_path):
        raise HTTPException(status_code=400, detail=f"Directory path does not exist: {req.repo_path}")
    return enqueue_scan_task(clean_path, req.name)


@app.get("/api/task/{task_id}")
def get_task_status_endpoint(task_id: str):
    """Poll the status and results of an asynchronous background task."""
    status_payload = get_task_status(task_id)
    if status_payload.get("status") == "NotFound":
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")
    return status_payload


@app.post("/api/scan/upload")
async def scan_zip_upload_endpoint(file: UploadFile = File(...)):
    """Upload and audit a ZIP archive containing a codebase with size & path traversal safeguards."""
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip archives are supported.")

    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        downloaded = 0
        while chunk := await file.read(1024 * 1024):
            downloaded += len(chunk)
            if downloaded > MAX_UPLOAD_SIZE:
                tmp.close()
                if os.path.exists(tmp.name):
                    os.remove(tmp.name)
                raise HTTPException(status_code=413, detail=f"Uploaded ZIP archive exceeds limit of {MAX_UPLOAD_SIZE // (1024*1024)}MB.")
            tmp.write(chunk)
        tmp_path = tmp.name

    try:
        scan_result = audit_zip_archive(tmp_path)
        repo_name = file.filename.replace(".zip", "")
        saved_repo = save_scan_results(
            name=repo_name,
            path_or_url=file.filename,
            total_files=scan_result["total_files"],
            total_lines=scan_result["total_lines"],
            green_score=scan_result["green_score"],
            violations_data=scan_result["violations"],
            summary_json=json.dumps(scan_result["violation_breakdown"]),
        )
        scan_result["repo_id"] = saved_repo.id
        return scan_result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


@app.post("/api/profile")
def profile_code_endpoint(req: ProfileRequest):
    """Execute target Python script in Docker sandbox to capture hardware telemetry & SCI score."""
    if not os.path.exists(req.file_path):
        raise HTTPException(status_code=400, detail=f"Target file does not exist: {req.file_path}")

    # Fetch live or verified grid carbon intensity
    zone_data = get_zone_carbon_intensity(req.zone)
    grid_intensity = zone_data["carbon_intensity"]

    # Run dynamic profiler
    result = profiler_engine.profile_file(
        file_path=req.file_path,
        timeout_sec=req.timeout_sec,
        grid_intensity=grid_intensity,
    )

    # Persist in DB
    save_profile_metric(
        file_path=req.file_path,
        duration_sec=result.duration_sec,
        avg_cpu_percent=result.avg_cpu_percent,
        peak_memory_mb=result.peak_memory_mb,
        energy_wh=result.energy_wh,
        operational_carbon_gco2=result.operational_carbon_gco2,
        sci_score=result.sci_score_gco2,
        profiling_mode=result.profiling_mode,
        repo_id=req.repo_id,
    )

    resp_dict = result.to_dict()
    resp_dict["zone_info"] = zone_data
    return resp_dict


@app.post("/api/refactor")
def refactor_code_endpoint(req: RefactorRequest):
    """Refactor inefficient code using GreenCode AI Synthesizer directives."""
    refactor_result = refactor_repository_code(
        bad_snippet=req.snippet,
        violation_type=req.violation_type,
        language_id=req.language,
        file_context=req.file_context or "",
        api_key=req.api_key,
    )

    # Persist refactoring record
    save_refactoring_record(
        original_code=req.snippet,
        refactored_code=refactor_result["refactored_code"],
        energy_reduction_pct=refactor_result["energy_reduction_pct"],
        carbon_saved_gco2_10k_runs=refactor_result["carbon_saved_gco2_10k_runs"],
        violation_id=req.violation_id,
    )

    return refactor_result


@app.get("/api/grid/zones")
def get_grid_zones_endpoint():
    """Retrieve supported global grid zones with carbon intensities."""
    return list_available_zones()


@app.get("/api/grid/zone/{zone_code}")
def get_specific_zone_endpoint(zone_code: str, api_key: Optional[str] = Query(None)):
    """Fetch live or verified carbon intensity for a specific grid zone."""
    return get_zone_carbon_intensity(zone=zone_code, api_key=api_key)


@app.get("/api/history")
def get_audit_history_endpoint():
    """Retrieve recent audits and cumulative carbon savings."""
    repos = get_latest_repositories(limit=15)
    cumulative = get_cumulative_carbon_savings()
    return {"repositories": repos, "cumulative_savings": cumulative}


@app.get("/api/repository/{repo_id}")
def get_repository_details_endpoint(repo_id: int):
    """Retrieve full audit details for a given repository ID."""
    details = get_repository_details(repo_id)
    if not details:
        raise HTTPException(status_code=404, detail="Repository record not found.")
    return details


def generate_svg_badge(label: str = "GreenCode", score: float = 100.0) -> str:
    """Generate dynamic vector SVG badge styled for GitHub README files."""
    if score >= 90:
        color = "#10b981"  # Emerald
        grade = "A+"
    elif score >= 80:
        color = "#059669"  # Green
        grade = "A"
    elif score >= 70:
        color = "#d97706"  # Amber
        grade = "B"
    elif score >= 60:
        color = "#ea580c"  # Orange
        grade = "C"
    else:
        color = "#dc2626"  # Red
        grade = "F"

    value_text = f"{score:.1f}/100 ({grade})"
    left_width = 85
    right_width = 95
    total_width = left_width + right_width

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{total_width}" height="20" role="img" aria-label="{label}: {value_text}">
  <title>{label}: {value_text}</title>
  <linearGradient id="s" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="r">
    <rect width="{total_width}" height="20" rx="3" fill="#fff"/>
  </clipPath>
  <g clip-path="url(#r)">
    <rect width="{left_width}" height="20" fill="#1f2937"/>
    <rect x="{left_width}" width="{right_width}" height="20" fill="{color}"/>
    <rect width="{total_width}" height="20" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" text-rendering="geometricPrecision" font-size="110">
    <text aria-hidden="true" x="{left_width * 5}" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)">🌱 {label}</text>
    <text x="{left_width * 5}" y="140" transform="scale(.1)">🌱 {label}</text>
    <text aria-hidden="true" x="{(left_width + right_width / 2) * 10}" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)">{value_text}</text>
    <text x="{(left_width + right_width / 2) * 10}" y="140" transform="scale(.1)">{value_text}</text>
  </g>
</svg>"""
    return svg


@app.get("/api/badge/score/{score}", tags=["Badges"])
def get_badge_by_score_endpoint(score: float):
    """Generate dynamic vector SVG badge for any Green Score."""
    svg_content = generate_svg_badge(label="GreenCode", score=score)
    return Response(content=svg_content, media_type="image/svg+xml")


@app.get("/api/badge/repo/{repo_id}", tags=["Badges"])
def get_badge_by_repo_endpoint(repo_id: int):
    """Generate dynamic vector SVG badge for an audited repository."""
    details = get_repository_details(repo_id)
    score = float(details["green_score"]) if details else 100.0
    svg_content = generate_svg_badge(label="GreenCode", score=score)
    return Response(content=svg_content, media_type="image/svg+xml")


# ---------------------------------------------------------------------------
# AUTHENTICATION & DEVELOPER PORTAL ENDPOINTS
# ---------------------------------------------------------------------------
from datetime import datetime, timedelta, timezone
import jwt

JWT_SECRET = os.environ.get("JWT_SECRET", "greencode-production-jwt-secret-key-2026")
JWT_ALGORITHM = "HS256"


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generate a signed JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(days=7))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and verify signed JWT access token."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except Exception:
        return None


@app.post("/api/auth/signup", tags=["Authentication"])
def signup_endpoint(req: SignUpRequest, background_tasks: BackgroundTasks):
    """Register a new developer account with hashed password and dispatch verification email asynchronously."""
    try:
        user = create_user(
            email=req.email,
            username=req.username,
            password=req.password,
            full_name=req.full_name,
            github_token=req.github_token,
        )
        token = create_access_token({"sub": str(user["id"]), "username": user["username"]})
        
        email_dispatch = {"queued": True, "recipient": user["email"]}
        if user.get("verification_token"):
            email_dispatch = send_verification_email(
                to_email=user["email"],
                username=user["username"],
                verification_token=user["verification_token"],
            )

        return {
            "success": True,
            "message": "Account created successfully. A verification link has been dispatched to your email.",
            "access_token": token,
            "token_type": "bearer",
            "user": user,
            "email_dispatch": email_dispatch,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


@app.get("/api/auth/verify-email", tags=["Authentication"])
def verify_email_endpoint(token: str):
    """Confirm user email address via unique verification token."""
    res = verify_user_email(token)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Invalid verification token."))
    return res


@app.post("/api/auth/forgot-password", tags=["Authentication"])
def forgot_password_endpoint(req: ForgotPasswordRequest, background_tasks: BackgroundTasks):
    """Generate expiring password reset token and dispatch via email asynchronously."""
    reset_data = create_password_reset_token(req.email)
    if reset_data:
        background_tasks.add_task(
            send_password_reset_email,
            to_email=reset_data["email"],
            username=reset_data["username"],
            reset_token=reset_data["token"],
        )
    return {
        "success": True,
        "message": f"If an account with '{req.email}' exists, a password reset link has been dispatched.",
    }


@app.post("/api/auth/reset-password", tags=["Authentication"])
def reset_password_endpoint(req: ResetPasswordRequest):
    """Reset user password using valid token."""
    res = reset_password_with_token(req.token, req.new_password)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Password reset failed."))
    return res


@app.post("/api/auth/signin", tags=["Authentication"])
def signin_endpoint(req: SignInRequest):
    """Authenticate developer with email or username and password, issuing JWT."""
    user = authenticate_user(login=req.login, password=req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email/username or password.")
    token = create_access_token({"sub": str(user["id"]), "username": user["username"]})
    return {
        "success": True,
        "message": "Authentication successful.",
        "access_token": token,
        "token_type": "bearer",
        "user": user,
    }


@app.post("/api/auth/github", tags=["Authentication"])
def github_auth_endpoint(req: GitHubAuthRequest):
    """Sign in or auto-provision account directly using GitHub Personal Access Token."""
    gh_user_data = get_authenticated_user(req.github_token)
    if not gh_user_data:
        raise HTTPException(status_code=400, detail="Invalid or expired GitHub Personal Access Token.")
    user = get_or_create_github_user(github_token=req.github_token, gh_user_data=gh_user_data)
    token = create_access_token({"sub": str(user["id"]), "username": user["username"]})
    return {
        "success": True,
        "message": "GitHub account connected successfully.",
        "access_token": token,
        "token_type": "bearer",
        "user": user,
    }


@app.get("/api/auth/user/{user_id}", tags=["Authentication"])
def get_user_endpoint(user_id: int):
    """Retrieve public developer profile by user ID."""
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


@app.put("/api/auth/user/{user_id}", tags=["Authentication"])
def update_profile_endpoint(user_id: int, req: UpdateProfileRequest):
    """Update profile information or link new GitHub token."""
    user = update_user_profile(
        user_id=user_id,
        github_token=req.github_token,
        github_username=req.github_username,
        avatar_url=req.avatar_url,
        full_name=req.full_name,
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return {"success": True, "message": "Profile updated successfully.", "user": user}


@app.post("/api/ci/evaluate")
def evaluate_ci_endpoint(req: CIEvaluateRequest):
    """Evaluate repository against Green Score threshold for CI/CD pipelines."""
    if not os.path.exists(req.repo_path):
        raise HTTPException(status_code=400, detail="Repository path does not exist.")

    scan = audit_repository(req.repo_path)
    score = scan["green_score"]
    passed = score >= req.threshold

    return {
        "passed": passed,
        "green_score": score,
        "threshold": req.threshold,
        "total_files": scan["total_files"],
        "total_lines": scan["total_lines"],
        "total_violations": scan["total_violations"],
        "violation_breakdown": scan["violation_breakdown"],
        "exit_code": 0 if passed else 1,
        "message": f"Quality Gate {'PASSED' if passed else 'BLOCKED'}: Score {score:.1f} vs Threshold {req.threshold:.1f}",
    }


@app.post("/api/scan/sarif", tags=["SARIF Integration"])
def scan_sarif_endpoint(req: ScanRequest):
    """Execute static AST analysis across directory and export OASIS SARIF v2.1.0 JSON."""
    if not os.path.exists(req.repo_path):
        raise HTTPException(status_code=400, detail=f"Directory path does not exist: {req.repo_path}")
    scan_result = audit_repository(req.repo_path)
    return generate_sarif_report(scan_result, base_dir=req.repo_path)


@app.get("/api/repository/{repo_id}/sarif", tags=["SARIF Integration"])
def get_repository_sarif_endpoint(repo_id: int):
    """Retrieve full audit details for a given repository ID and convert into SARIF v2.1.0."""
    details = get_repository_details(repo_id)
    if not details:
        raise HTTPException(status_code=404, detail="Repository record not found.")
    return generate_sarif_report(details, base_dir=details.get("path_or_url"))



@app.get("/api/ibm-bob/report", tags=["IBM Bob 2.0 Integration"])
def get_ibm_bob_report_endpoint(repo_path: str = "."):
    """Generate official IBM Bob 2.0 Plan Mode and Repository Context audit report."""
    from app.ibm_bob_engine import get_ibm_bob_report
    clean_path = os.path.abspath(repo_path)
    if not os.path.exists(clean_path):
        raise HTTPException(status_code=400, detail=f"Repository path '{repo_path}' does not exist.")
    scan_result = audit_repository(clean_path)
    return get_ibm_bob_report(scan_result)


@app.get("/github/user", tags=["GitHub Integration"])
async def get_github_user_endpoint(token: Optional[str] = None):
    """Retrieve details of the authenticated GitHub account."""
    user = get_authenticated_user(token=token)
    if not user:
        raise HTTPException(status_code=401, detail="GitHub token not configured or invalid.")
    return {"authenticated": True, "user": user}


@app.get("/github/repos", tags=["GitHub Integration"])
async def list_github_repositories_endpoint(token: Optional[str] = None, limit: int = 30):
    """List accessible GitHub repositories for the authenticated user."""
    repos = list_user_repositories(token=token, limit=limit)
    return {"count": len(repos), "repositories": repos}


@app.post("/github/pull-request", tags=["GitHub Integration"])
async def create_github_pull_request_endpoint(req: GitHubPRRequest):
    """Create a feature branch, commit eco-refactored code, and open a Pull Request."""
    res = create_refactoring_pull_request(
        repo_full_name=req.repo_full_name,
        file_path=req.file_path,
        refactored_code=req.refactored_code,
        violation_title=req.violation_title,
        energy_reduction_pct=req.energy_reduction_pct,
        carbon_saved_10k=req.carbon_saved_10k,
        token=req.token,
        original_snippet=req.original_snippet,
    )
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to create PR"))
    return res


def run_cli():
    """CLI Entrypoint for terminal invocation and GitHub Action CI/CD blocker."""
    parser = argparse.ArgumentParser(
        description="GreenCode Auditor - CI/CD Quality Gate & Static Carbon Analyzer"
    )
    parser.add_argument(
        "--path",
        default=".",
        help="Path to directory or repository to audit (default: current directory)",
    )
    parser.add_argument(

        "--sarif",
        default=None,
        help="Path to write OASIS SARIF v2.1.0 JSON report (e.g. greencode.sarif)",
    )
    parser.add_argument(
        "--pr",
        type=int,
        default=None,
        help="GitHub Pull Request number to publish automated carbon audit comment",
    )
    parser.add_argument(
        "--repo-name",
        default=None,
        help="GitHub repository full name (e.g. 'owner/repo') for PR commenting",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=75.0,
        help="Minimum acceptable Green Score (0-100) before blocking build (default: 75.0)",
    )
    parser.add_argument(
        "--zone",
        default="US-CAL-CISO",
        help="Grid region identifier for operational carbon calculation (default: US-CAL-CISO)",
    )
    parser.add_argument(
        "--ci",
        action="store_true",
        help="Run in CI/CD pipeline blocker mode (exits with code 1 if score < threshold)",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Start the FastAPI backend server daemon",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind server (default: 8000)",
    )

    args = parser.parse_args()


    if sys.platform.startswith("win"):
        try:
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            if hasattr(sys.stderr, "reconfigure"):
                sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    if args.serve:
        print(f"Starting GreenCode Auditor FastAPI server on port {args.port}...")
        uvicorn.run("app.main:app", host="0.0.0.0", port=args.port, reload=True)
        return

    # CLI Audit Mode
    target_path = os.path.abspath(args.path)
    print("\n" + "=" * 70)
    print("  [GREEN] GREENCODE AUDITOR  -  Automated CI/CD Quality Gatekeeper")
    print("=" * 70)
    print(f"Target Path     : {target_path}")
    print(f"Quality Gate    : Minimum Green Score >= {args.threshold}/100")
    print(f"Grid Zone       : {args.zone}")
    print("-" * 70)

    if not os.path.exists(target_path):
        print(f"[ERROR] Target path '{target_path}' does not exist.")
        sys.exit(1)

    result = audit_repository(target_path)
    score = result["green_score"]
    violations = result["violations"]

    print(f"Total Files Audited : {result['total_files']}")
    print(f"Total Lines of Code : {result['total_lines']}")
    print(f"Total Violations    : {result['total_violations']}")
    print(f"Overall Green Score : {score} / 100.0")
    print("-" * 70)

    if violations:
        print("[!] DETECTED GREEN COMPUTING ANOMALIES:")
        for idx, v in enumerate(violations[:10], 1):
            rel = os.path.relpath(v["file_path"], target_path)
            print(f"  {idx}. [{v['severity']}] {v['title']} (Line {v['line_number']} in {rel})")
            print(f"     Deduction: -{v['deduction']} pts | Pattern: {v['gsf_pattern']}")
            print(f"     Guidance : {v['suggested_fix']}")
            print()
        if len(violations) > 10:
            print(f"  ... and {len(violations) - 10} more violations.")
        print("-" * 70)

    # 1. Export SARIF v2.1.0 Report if requested
    if args.sarif:
        try:
            generate_sarif_report(result, output_path=args.sarif, base_dir=target_path)
            print(f"[SARIF] Successfully exported OASIS SARIF v2.1.0 report: {args.sarif}")
        except Exception as exc:
            print(f"[SARIF ERROR] Failed to export SARIF report: {exc}")

    # 2. Automated PR Bot Commenting
    pr_number = args.pr
    github_repo = args.repo_name or os.environ.get("GITHUB_REPOSITORY")
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not pr_number and event_path and os.path.exists(event_path):
        try:
            with open(event_path, "r", encoding="utf-8") as ef:
                event_data = json.load(ef)
                if "pull_request" in event_data and "number" in event_data["pull_request"]:
                    pr_number = int(event_data["pull_request"]["number"])
        except Exception:
            pass

    if pr_number and github_repo:
        print(f"Publishing automated carbon quality audit comment to PR #{pr_number} in '{github_repo}'...")
        pr_res = post_pr_carbon_comment(
            repo_full_name=github_repo,
            pr_number=pr_number,
            scan_result=result,
            gate_threshold=args.threshold,
        )
        if pr_res.get("success"):
            print(f"[PR BOT] {pr_res.get('message', 'Comment published successfully.')}")
        else:
            print(f"[PR BOT WARNING] {pr_res.get('error', 'Could not post PR comment.')}")

    # 3. Export outputs to GitHub Actions if running under GITHUB_OUTPUT
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        try:
            with open(github_output, "a", encoding="utf-8") as gh_out:
                gh_out.write(f"green_score={score}\n")
                gh_out.write(f"total_violations={len(violations)}\n")
                gh_out.write(f"passed={str(score >= args.threshold).lower()}\n")
                if args.sarif:
                    gh_out.write(f"sarif_file={args.sarif}\n")
        except Exception:
            pass


    # Check against threshold
    if score < args.threshold:
        print(f"[BLOCKED] Green Score {score} is BELOW the threshold ({args.threshold}).")
        print("   Refactor flagged code patterns to reduce operational energy consumption before pushing.")
        print("=" * 70 + "\n")
        if args.ci or not args.serve:
            sys.exit(1)
    else:
        print(f"[PASSED] Green Score {score} meets acceptable criteria (>= {args.threshold}).")
        print("   Code complies with Green Software Foundation efficiency guidelines.")
        print("=" * 70 + "\n")
        sys.exit(0)



if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_cli()
    else:
        uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
