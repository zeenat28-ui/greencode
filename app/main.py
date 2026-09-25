"""FastAPI Application and CI/CD Quality Gatekeeper for GreenCode Auditor.

Handles repository static AST scanning, dynamic container profiling endpoints,
Electricity Maps live grid telemetry, GreenCode AI refactoring orchestration, and
provides a terminal CLI with exit code blockers for GitHub Actions integration.
"""

import argparse
from collections import OrderedDict
from contextlib import asynccontextmanager
import json
import os
import sys
import threading
import time
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta, timezone
import jwt
import logging

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import uvicorn

try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    SLOWAPI_OK = True
except ImportError:
    SLOWAPI_OK = False

from app.database import (
    close_async_db,
    create_refresh_token,
    get_cumulative_carbon_savings,
    get_latest_repositories,
    get_or_create_github_user,
    get_repository_details,
    get_user_by_id,
    get_user_raw_github_token,
    init_db,
    revoke_refresh_tokens,
    rotate_refresh_token,
    save_profile_metric,
    save_refactoring_record,
    update_user_profile,
)
from app.github_client import (
    GitHubAPIError,
    create_refactoring_pull_request,
    get_authenticated_user,
    list_repository_branches,
    list_user_repositories,
    normalize_repo_slug,
    post_pr_carbon_comment,
)
from app.audit_intel import build_remediation_plan
from app.energy_sensors import probe_capabilities
from app.huggingface_client import get_client as get_hf_client
from app.optimizer import (
    get_zone_carbon_intensity,
    list_available_zones,
    refactor_repository_code,
)
from app.parser import audit_repository
from app.profiler import DynamicExecutionProfiler
from app.sarif import generate_sarif_report
from app.scanner import (
    ASYNC_SCAN_MAX_KB,
    SYNC_SCAN_MAX_KB,
    AuditRejected,
    github_error_to_http,
    run_github_audit,
)
from app.tasks import enqueue_github_scan_task, get_task_status

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S%z",
)
logger = logging.getLogger("greencode.api")

REFRESH_TOKEN_EXPIRE = timedelta(days=7)


# Pydantic Schemas for API Requests & Responses
class GitHubAuthRequest(BaseModel):
    github_token: str = Field(
        ..., min_length=10, max_length=200,
        description="GitHub Personal Access Token with 'repo' scope",
    )


class UpdateProfileRequest(BaseModel):
    github_token: Optional[str] = Field(
        None, min_length=10, max_length=200,
        description="Replacement GitHub Personal Access Token",
    )
    github_username: Optional[str] = Field(None, max_length=100)
    full_name: Optional[str] = Field(None, max_length=150)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="Valid refresh token issued during GitHub sign-in")


class GitHubScanRequest(BaseModel):
    repo: str = Field(
        ..., min_length=3, max_length=300,
        description="Repository as 'owner/repo' or a full github.com URL",
    )
    ref: Optional[str] = Field(
        None, max_length=255,
        description="Branch, tag or commit SHA. Defaults to the repository default branch.",
    )
    token: Optional[str] = Field(
        None, min_length=10, max_length=200,
        description="Optional GitHub token override. Falls back to the token stored on your account.",
    )
    name: Optional[str] = Field(None, max_length=255, description="Optional display name override")


class ProfileRequest(BaseModel):
    benchmark: str = Field(
        ..., max_length=100,
        description="Identifier of a bundled benchmark script, e.g. 'heavy_pipeline'",
    )
    timeout_sec: float = Field(20.0, ge=1.0, le=120.0, description="Max execution timeout in seconds")
    zone: str = Field("US-CAL-CISO", description="Electricity Maps grid zone identifier")
    repo_id: Optional[int] = Field(None, description="Optional associated audit record ID")


class RefactorRequest(BaseModel):
    snippet: str = Field(..., max_length=40000, description="Inefficient code snippet to refactor")
    violation_type: str = Field(..., max_length=100, description="Detected violation type identifier")
    language: str = Field("python", max_length=40, description="Programming language identifier")
    violation_id: Optional[int] = Field(None, description="Optional violation DB record ID")
    file_context: Optional[str] = Field("", max_length=8000, description="Optional surrounding file context")


class GitHubPRRequest(BaseModel):
    repo_full_name: str = Field(..., min_length=3, max_length=300, description="Repository as 'owner/repo'")
    file_path: str = Field(..., min_length=1, max_length=1000, description="Repository-relative path of the file")
    refactored_code: str = Field(..., max_length=200000, description="Optimized source code to commit")
    original_snippet: Optional[str] = Field(None, max_length=20000, description="Original snippet to replace")
    violation_title: str = Field("Energy Optimization", max_length=200)
    energy_reduction_pct: float = Field(50.0, ge=0.0, le=100.0, description="Estimated percentage energy saved")
    carbon_saved_10k: float = Field(30.0, ge=0.0, description="Estimated carbon saved per 10k runs")
    token: Optional[str] = Field(None, min_length=10, max_length=200, description="Optional GitHub token override")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database tables on startup and dispose async connections on shutdown."""
    init_db()
    if not os.environ.get("JWT_SECRET") or JWT_SECRET == DEFAULT_INSECURE_JWT_SECRET:
        message = (
            "JWT_SECRET is not configured or still uses the insecure default. "
            "Set a strong JWT_SECRET before deploying to production."
        )
        # Fail loudly in production, warn once in development.
        if os.environ.get("ENV", "development").lower() in ("production", "prod", "staging"):
            logger.critical(message)
        else:
            logger.warning(message)
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

CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:5173,http://localhost:8080",
    ).split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_headers=["Authorization", "Content-Type", "Accept"],
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
)

DEFAULT_INSECURE_JWT_SECRET = "greencode-production-jwt-secret-key-2026"
JWT_SECRET = os.environ.get("JWT_SECRET", DEFAULT_INSECURE_JWT_SECRET)
JWT_ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE = timedelta(minutes=15)

security = HTTPBearer(auto_error=False)

if SLOWAPI_OK:
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
else:
    limiter = None


def maybe_limit(limit_value: str):
    """Conditionally apply a slowapi rate limit if slowapi is available."""
    def decorator(func):
        if SLOWAPI_OK and limiter is not None:
            return limiter.limit(limit_value)(func)
        return func
    return decorator


TOKEN_BLACKLIST_MAX = 10_000


class _BoundedTokenBlacklist:
    """Thread-safe, size-capped set of revoked access-token hashes.

    Kept in-process on purpose: a full 15-minute access-token TTL already bounds
    the exposure window, and persisting every token would be far more expensive
    than the threat it mitigates. The cap prevents unbounded growth.
    """

    def __init__(self, max_entries: int = TOKEN_BLACKLIST_MAX) -> None:
        self._data: "OrderedDict[str, float]" = OrderedDict()
        self._max = max_entries
        self._lock = threading.Lock()

    def add(self, token: str) -> None:
        with self._lock:
            self._data[token] = time.monotonic()
            self._data.move_to_end(token)
            while len(self._data) > self._max:
                self._data.popitem(last=False)

    def __contains__(self, token: str) -> bool:
        with self._lock:
            return token in self._data

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)


TOKEN_BLACKLIST = _BoundedTokenBlacklist()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generate a signed JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or ACCESS_TOKEN_EXPIRE)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and verify signed JWT access token."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except Exception:
        return None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Dict[str, Any]:
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    if token in TOKEN_BLACKLIST:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id_str: Optional[str] = payload.get("sub")
    if user_id_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        user_id = int(user_id_str)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


profiler_engine = DynamicExecutionProfiler()

# Bundled benchmark scripts for the runtime profiler. The profiler executes code,
# so it must NEVER accept an arbitrary caller-supplied path (that would be remote
# code execution on the API host). Only these known-safe, read-only sample files
# are profileable.
BENCHMARK_SCRIPTS: Dict[str, Dict[str, str]] = {
    "heavy_pipeline": {
        "file": "heavy_pipeline.py",
        "label": "Heavy Pipeline (Anti-Pattern Baseline)",
        "description": "Deliberately inefficient pipeline exhibiting all GSF anti-patterns.",
    },
    "eco_pipeline": {
        "file": "eco_pipeline.py",
        "label": "Eco Pipeline (Optimized Reference)",
        "description": "The refactored counterpart used to quantify the energy delta.",
    },
    "heavy_pipeline_refactored": {
        "file": "heavy_pipeline_refactored.py",
        "label": "Heavy Pipeline (GreenCode Refactor)",
        "description": "Auto-synthesized eco-refactor of the heavy pipeline baseline.",
    },
}

SAMPLES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples")


def list_benchmark_scripts() -> List[Dict[str, str]]:
    """Return the profiler's whitelisted benchmark scripts that exist on disk."""
    out: List[Dict[str, str]] = []
    for key, meta in BENCHMARK_SCRIPTS.items():
        abs_path = os.path.join(SAMPLES_DIR, meta["file"])
        if os.path.isfile(abs_path):
            out.append({"id": key, "label": meta["label"], "description": meta["description"]})
    return out


def resolve_benchmark_path(benchmark_id: str) -> str:
    """Map a benchmark id to an on-disk path inside the bundled samples directory.

    Raises HTTP 404 for anything not in the whitelist, which is what keeps this
    endpoint from being an arbitrary-file-execution primitive.
    """
    meta = BENCHMARK_SCRIPTS.get(benchmark_id)
    if not meta:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown benchmark '{benchmark_id}'. Call GET /api/profile/benchmarks for the list.",
        )
    abs_path = os.path.realpath(os.path.join(SAMPLES_DIR, meta["file"]))
    samples_root = os.path.realpath(SAMPLES_DIR)
    # Defence in depth: guarantee the resolved path cannot escape samples/.
    if not abs_path.startswith(samples_root + os.sep):
        raise HTTPException(status_code=400, detail="Invalid benchmark path.")
    if not os.path.isfile(abs_path):
        raise HTTPException(status_code=404, detail=f"Benchmark script '{meta['file']}' is missing on the server.")
    return abs_path


def resolve_github_token(user_id: int, explicit: Optional[str] = None) -> str:
    """Resolve the GitHub token to use for an API call.

    Precedence: explicit override -> the token stored (encrypted) on the user's
    account -> the server-level GITHUB_TOKEN env var.

    Tokens are never accepted as query parameters, so they cannot leak into
    access logs, proxy logs, or browser history.
    """
    if explicit:
        return explicit
    stored = None
    try:
        stored = get_user_raw_github_token(user_id)
    except Exception:
        logger.warning("Could not read stored GitHub token for user %s", user_id)
    if stored:
        return stored
    fallback = os.environ.get("GITHUB_TOKEN", "")
    if not fallback:
        raise HTTPException(
            status_code=400,
            detail=(
                "No GitHub token available. Sign out and reconnect your GitHub account, "
                "or set GITHUB_TOKEN on the server."
            ),
        )
    return fallback


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
    from app.database import SessionLocal
    from sqlalchemy import text

    deps: Dict[str, Any] = {}
    overall = "healthy"

    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            deps["database"] = "ok"
        except Exception as db_exc:
            deps["database"] = f"error: {db_exc}"
            overall = "degraded"
        finally:
            try:
                db.close()
            except Exception:
                pass
    except Exception as exc:
        deps["database"] = f"error: {exc}"
        overall = "degraded"

    redis_url = os.environ.get("REDIS_URL")
    if redis_url:
        try:
            import redis as redis_lib

            r_client = redis_lib.Redis.from_url(redis_url, socket_connect_timeout=2)
            r_client.ping()
            deps["redis"] = "ok"
            r_client.close()
        except Exception as r_exc:
            deps["redis"] = f"error: {r_exc}"
            overall = "degraded"
    else:
        deps["redis"] = "not_configured"

    # Measurement and AI capabilities are part of operational readiness: a
    # host without RAPL reports estimates, and a host without a model key cannot
    # refactor. Operators need to see both at a glance.
    from app.dynamic_analysis import DynamicAnalyzer

    dyn = DynamicAnalyzer.status()
    deps["docker"] = "ok" if dyn["docker"]["reachable"] else "unavailable"
    deps["energy_counter"] = dyn["energy_measurement"]["best_available"]

    hf = get_hf_client()
    deps["huggingface"] = "ok" if hf.configured else "not_configured"

    return {
        "status": overall,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "GreenCode Auditor",
        "version": "1.1.0",
        "deps": deps,
        "capabilities": {
            "dynamic_analysis": dyn["dynamic_analysis_available"],
            "dynamic_analysis_blockers": dyn["blockers"],
            "hardware_energy_measurement": dyn["hardware_measurement_available"],
            "llm_refactoring": hf.configured,
        },
    }


# ---------------------------------------------------------------------------
# DYNAMIC ANALYSIS
#
# Executes a checked-out repository under measurement. Docker is mandatory:
# running third-party code on the host is not offered as a fallback.
# ---------------------------------------------------------------------------
class DynamicAnalysisRequest(BaseModel):
    repo_full_name: str = Field(..., min_length=3, max_length=300,
                                description="Repository as 'owner/repo'")
    ref: Optional[str] = Field(None, max_length=255, description="Branch or tag")
    grid_intensity: float = Field(380.0, ge=0.0, le=1500.0,
                                  description="Grid carbon intensity, gCO2e/kWh")
    functional_unit: float = Field(1.0, gt=0.0, le=1e9,
                                   description="R in the SCI formula: functional units delivered")
    timeout_sec: float = Field(60.0, gt=0.0, le=120.0, description="Hard wall-clock budget")


@app.get("/api/dynamic/status", tags=["Dynamic Analysis"])
def dynamic_analysis_status():
    """Report whether dynamic analysis can run, and how energy will be measured."""
    from app.dynamic_analysis import DynamicAnalyzer

    return DynamicAnalyzer.status()


@app.post("/api/dynamic/analyze", tags=["Dynamic Analysis"])
def dynamic_analysis_endpoint(
    request: DynamicAnalysisRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Run a repository's test/benchmark suite in a sandbox and measure it.

    Energy is read from a hardware counter when the host exposes one (Linux
    RAPL). The response always states which measurement path produced the
    numbers, so a modelled estimate is never presented as a measurement.
    """
    import shutil
    import tempfile

    from app.dynamic_analysis import DynamicAnalyzer
    from app.github_client import GitHubAPIError, download_repository_archive

    analyzer = DynamicAnalyzer()
    if not analyzer.available():
        return analyzer.status()

    token = resolve_github_token(current_user["id"])
    workdir = tempfile.mkdtemp(prefix="greencode-dyn-")
    try:
        try:
            archive = download_repository_archive(
                request.repo_full_name, token=token, ref=request.ref
            )
        except GitHubAPIError as exc:
            raise HTTPException(
                status_code=github_error_to_http(exc), detail=exc.message
            )

        import zipfile

        try:
            with zipfile.ZipFile(archive) as zf:
                _safe_extract(zf, workdir)
        except (zipfile.BadZipFile, ValueError) as exc:
            raise HTTPException(
                status_code=400, detail=f"Repository archive is not readable: {exc}"
            )

        result = analyzer.analyze(
            _repo_root(workdir),
            repo_slug=request.repo_full_name,
            ref=request.ref or "",
            grid_intensity=request.grid_intensity,
            functional_unit=request.functional_unit,
            timeout_sec=request.timeout_sec,
        )
        return result.to_dict()
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _safe_extract(zf, dest: str) -> None:
    """Extract an archive, rejecting path traversal and zip bombs."""
    dest_real = os.path.realpath(dest)
    total = 0
    for member in zf.infolist():
        target = os.path.realpath(os.path.join(dest_real, member.filename))
        if not (target == dest_real or target.startswith(dest_real + os.sep)):
            raise ValueError(f"Archive entry escapes the extraction directory: {member.filename}")
        total += member.file_size
        if total > 500 * 1024 * 1024:
            raise ValueError("Archive expands beyond the 500 MB limit")
    zf.extractall(dest_real)


def _repo_root(workdir: str) -> str:
    """GitHub archives nest everything under a single top-level directory."""
    try:
        entries = [e for e in os.listdir(workdir) if not e.startswith("__MACOSX")]
    except OSError:
        return workdir
    if len(entries) == 1:
        candidate = os.path.join(workdir, entries[0])
        if os.path.isdir(candidate):
            return candidate
    return workdir



@app.post("/api/scan/github", tags=["GitHub Scanning"])
@maybe_limit("30/minute")
def scan_github_repository_endpoint(
    req: GitHubScanRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Audit a GitHub repository synchronously.

    Downloads the repository zipball, audits every supported source file, and
    persists the result against the authenticated user. Repositories larger than
    `SYNC_SCAN_MAX_KB` are rejected with a 413 pointing at the async endpoint so
    the request cannot exceed a gateway timeout.
    """
    try:
        slug = normalize_repo_slug(req.repo)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    token = resolve_github_token(current_user["id"], req.token)

    # Reject oversized repositories before starting a long download.
    from app.github_client import inspect_repository_before_audit
    preflight = inspect_repository_before_audit(slug, token=token)
    size_kb = int(preflight.get("size_kb", 0) or 0)
    if size_kb > SYNC_SCAN_MAX_KB:
        raise HTTPException(
            status_code=413,
            detail=(
                f"'{slug}' is {size_kb / 1024:.1f} MB, above the "
                f"{SYNC_SCAN_MAX_KB // 1024} MB synchronous limit. "
                "Use POST /api/scan/github/async for large repositories."
            ),
        )

    try:
        return run_github_audit(
            repo_ref=slug,
            ref=req.ref,
            token=token,
            user_id=current_user["id"],
            display_name=req.name,
            max_mb=ASYNC_SCAN_MAX_KB // 1024,
        )
    except AuditRejected as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except GitHubAPIError as exc:
        raise HTTPException(status_code=github_error_to_http(exc), detail=exc.message)
    except Exception as exc:
        logger.exception("GitHub audit failed for %s", slug)
        raise HTTPException(status_code=500, detail=f"Audit failed: {exc}")


@app.post("/api/scan/github/async", tags=["GitHub Scanning"])
@maybe_limit("30/minute")
def scan_github_repository_async_endpoint(
    req: GitHubScanRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Enqueue a GitHub repository audit and return a task id for polling.

    Use this for large repositories. The authenticated user's id is bound to the
    task so `/api/task/{id}` can enforce ownership.
    """
    try:
        slug = normalize_repo_slug(req.repo)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    token = resolve_github_token(current_user["id"], req.token)

    from app.github_client import inspect_repository_before_audit
    preflight = inspect_repository_before_audit(slug, token=token)
    if not preflight.get("can_audit", True):
        raise HTTPException(status_code=400, detail=preflight.get("message", "Repository cannot be audited."))
    size_kb = int(preflight.get("size_kb", 0) or 0)
    if size_kb > ASYNC_SCAN_MAX_KB:
        raise HTTPException(
            status_code=413,
            detail=f"'{slug}' is {size_kb / 1024:.1f} MB, above the {ASYNC_SCAN_MAX_KB // 1024} MB async limit.",
        )

    return enqueue_github_scan_task(
        repo_full_name=slug,
        ref=req.ref,
        token=token,
        user_id=current_user["id"],
    )


@app.get("/api/task/{task_id}")
def get_task_status_endpoint(
    task_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Poll the status and results of an asynchronous background audit.

    Authenticated and ownership-scoped: a task belonging to another user is
    reported as 404 so task ids cannot be probed across tenants.
    """
    status_payload = get_task_status(task_id, user_id=current_user["id"])
    if status_payload.get("status") == "NotFound":
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")
    return status_payload


@app.get("/api/profile/benchmarks", tags=["Runtime Profiler"])
def list_profile_benchmarks_endpoint(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """List the bundled benchmark scripts the runtime profiler is allowed to execute.

    In GitHub-only mode there is no local folder to point the profiler at, so the
    profiler runs against these fixed, audited reference scripts instead. Keeping
    this a closed list is also what prevents `/api/profile` from being an
    arbitrary-file-execution primitive.
    """
    return {"benchmarks": list_benchmark_scripts()}


@app.post("/api/profile", tags=["Runtime Profiler"])
@maybe_limit("20/minute")
def profile_code_endpoint(
    req: ProfileRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Execute a bundled benchmark script in a Docker sandbox and capture SCI telemetry."""
    benchmark_path = resolve_benchmark_path(req.benchmark)

    zone_data = get_zone_carbon_intensity(req.zone)
    grid_intensity = zone_data["carbon_intensity"]

    result = profiler_engine.profile_file(
        file_path=benchmark_path,
        timeout_sec=req.timeout_sec,
        grid_intensity=grid_intensity,
    )

    save_profile_metric(
        file_path=req.benchmark,
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
    resp_dict["benchmark"] = req.benchmark
    return resp_dict


@app.post("/api/refactor", tags=["Refactoring"])
@maybe_limit("20/minute")
def refactor_code_endpoint(
    req: RefactorRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Refactor inefficient code using the GreenCode AI Synthesizer directives."""
    refactor_result = refactor_repository_code(
        bad_snippet=req.snippet,
        violation_type=req.violation_type,
        language_id=req.language,
        file_context=req.file_context or "",
    )

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


@app.get("/api/history", tags=["Audit History"])
def get_audit_history_endpoint(
    limit: int = 20,
    offset: int = 0,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Return a page of the caller's audit history plus their cumulative savings.

    Both the repository list and the savings aggregate are scoped to the
    authenticated user. The previous implementation filtered repositories in
    Python after fetching everyone else's rows, and computed savings globally -
    so every user saw other tenants' audit volume and carbon totals.
    """
    page = get_latest_repositories(limit=limit, user_id=current_user["id"], offset=offset)
    cumulative = get_cumulative_carbon_savings(user_id=current_user["id"])
    return {
        "repositories": page["items"],
        "cumulative_savings": cumulative,
        "total": page["total"],
        "limit": page["limit"],
        "offset": page["offset"],
        "has_more": page["has_more"],
    }


@app.get("/api/repository/{repo_id}")
def get_repository_details_endpoint(
    repo_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Retrieve full audit details for a given repository ID if owned by the current user."""
    details = get_repository_details(repo_id)
    if not details:
        raise HTTPException(status_code=404, detail="Repository record not found.")
    if details.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="You do not have permission to access this repository.")
    return details


def generate_svg_badge(label: str = "GreenCode", score: float = 100.0) -> str:
    """Generate a dynamic vector SVG badge suitable for embedding in a GitHub README."""
    if score >= 90:
        color, grade = "#10b981", "A+"
    elif score >= 80:
        color, grade = "#059669", "A"
    elif score >= 70:
        color, grade = "#d97706", "B"
    elif score >= 60:
        color, grade = "#ea580c", "C"
    else:
        color, grade = "#dc2626", "F"

    value_text = f"{score:.1f}/100 ({grade})"
    # Widths are approximated from the glyph count so long labels stay centred.
    left_width = 22 + 7 * len(label)
    right_width = 22 + 7 * len(value_text)
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
    <text aria-hidden="true" x="{left_width * 5}" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)">{label}</text>
    <text x="{left_width * 5}" y="140" transform="scale(.1)">{label}</text>
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
#
# GitHub is the sole identity provider. Email/password, email-verification and
# password-reset flows are intentionally absent: they added attack surface and UI
# with no product value in a tool that already requires a GitHub token to work.
# ---------------------------------------------------------------------------

@app.get("/api/auth/me", tags=["Authentication"])
def get_me_endpoint(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Return the authenticated user's profile (used by AuthContext on mount)."""
    return {
        "authenticated": True,
        "user": current_user,
    }


@app.post("/api/auth/refresh", tags=["Authentication"])
def refresh_token_endpoint(req: RefreshRequest):
    """Rotate a valid refresh token, returning a new access token and refresh token pair."""
    result = rotate_refresh_token(req.refresh_token)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    new_refresh_token = result if isinstance(result, str) else result.get("refresh_token")
    user_id = result.get("user_id") if isinstance(result, dict) else None
    if not new_refresh_token or user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists",
        )
    new_access_token = create_access_token(
        {"sub": str(user["id"]), "username": user.get("username", "")},
        expires_delta=ACCESS_TOKEN_EXPIRE,
    )
    return {
        "success": True,
        "message": "Token refreshed successfully.",
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": int(ACCESS_TOKEN_EXPIRE.total_seconds()),
        "user": user,
    }


@app.post("/api/auth/logout", tags=["Authentication"])
def logout_endpoint(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Revoke all refresh tokens for the current user and invalidate the current access token."""
    if credentials and credentials.credentials:
        TOKEN_BLACKLIST.add(credentials.credentials)
    revoke_refresh_tokens(current_user["id"])
    return {
        "success": True,
        "message": "Logged out successfully. All sessions have been invalidated.",
    }


@app.post("/api/auth/github", tags=["Authentication"])
@maybe_limit("10/minute")
def github_auth_endpoint(req: GitHubAuthRequest):
    """Sign in (or auto-provision) using a GitHub Personal Access Token.

    This is the only authentication method. The token is verified against
    GitHub, stored Fernet-encrypted, and never returned to the client again.
    """
    gh_user_data = get_authenticated_user(req.github_token)
    if not gh_user_data:
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid or expired GitHub token. Generate a PAT with the 'repo' "
                "scope at https://github.com/settings/tokens"
            ),
        )
    user = get_or_create_github_user(github_token=req.github_token, gh_user_data=gh_user_data)
    access_token = create_access_token(
        {"sub": str(user["id"]), "username": user["username"]},
        expires_delta=ACCESS_TOKEN_EXPIRE,
    )
    refresh_result = create_refresh_token(user["id"])
    refresh_token = refresh_result if isinstance(refresh_result, str) else refresh_result["refresh_token"]
    return {
        "success": True,
        "message": f"Connected as {gh_user_data.get('login', user['username'])}.",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": int(ACCESS_TOKEN_EXPIRE.total_seconds()),
        "user": user,
        "github_login": gh_user_data.get("login"),
    }


@app.get("/api/auth/user/{user_id}", tags=["Authentication"])
def get_user_endpoint(
    user_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Retrieve developer profile by user ID (own profile or admin-only)."""
    if user_id != current_user["id"] and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="You do not have permission to access this user profile.")
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


@app.put("/api/auth/user/{user_id}", tags=["Authentication"])
def update_profile_endpoint(
    user_id: int,
    req: UpdateProfileRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Update the caller's profile or rotate their stored GitHub token. IDOR-protected."""
    if user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="You cannot update another user's profile.")

    if req.github_token:
        # Never persist a token we cannot verify - it would silently break every
        # subsequent scan with a confusing 401.
        if not get_authenticated_user(req.github_token):
            raise HTTPException(
                status_code=400,
                detail="That GitHub token was rejected by GitHub. Check it and try again.",
            )

    user = update_user_profile(
        user_id=user_id,
        github_token=req.github_token,
        github_username=req.github_username,
        full_name=req.full_name,
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return {"success": True, "message": "Profile updated successfully.", "user": user}


@app.get("/api/repository/{repo_id}/sarif", tags=["SARIF Integration"])
def get_repository_sarif_endpoint(
    repo_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Convert a stored audit into an OASIS SARIF v2.1.0 report for code-scanning upload."""
    details = get_repository_details(repo_id)
    if not details:
        raise HTTPException(status_code=404, detail="Repository record not found.")
    if details.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="You cannot access this repository's report.")
    return generate_sarif_report(details, base_dir=details.get("full_name") or "")


def _build_audit_context(details: Dict[str, Any]) -> Dict[str, Any]:
    """Assemble the scan-result shape shared by the analysis endpoints."""
    violations = details.get("violations", [])
    return {
        "repo_path": details.get("full_name") or details.get("path_or_url") or "",
        "total_files": details.get("total_files", 0),
        "total_lines": details.get("total_lines", 0),
        "green_score": details.get("green_score", 100.0),
        "total_violations": len(violations),
        "violation_breakdown": _violation_breakdown(violations),
        "violations": violations,
    }


@app.get("/api/audit/context", tags=["Audit Intelligence"])
def get_audit_context_endpoint(
    repo_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Return the prioritised remediation plan for a stored audit.

    Keyed on `repo_id` rather than a filesystem path, because in GitHub-only mode
    there is no server-side directory to point at. Replaces the previous
    vendor-specific report endpoint with an open, provider-neutral payload.
    """
    details = get_repository_details(repo_id)
    if not details:
        raise HTTPException(status_code=404, detail="Repository record not found.")
    if details.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="You cannot access this repository's report.")

    return build_remediation_plan(_build_audit_context(details))



def _violation_breakdown(violations: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for v in violations:
        key = v.get("violation_type", "UNKNOWN")
        counts[key] = counts.get(key, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# GITHUB INTEGRATION
#
# The GitHub token is always resolved server-side from the caller's encrypted
# record. It is never accepted as a query parameter, which previously leaked it
# into access logs, proxy logs and browser history.
# ---------------------------------------------------------------------------

@app.get("/github/user", tags=["GitHub Integration"])
def get_github_user_endpoint(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Retrieve the connected GitHub account profile."""
    token = resolve_github_token(current_user["id"])
    user = get_authenticated_user(token=token)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Your stored GitHub token is no longer valid. Reconnect it in Settings.",
        )
    return {"authenticated": True, "user": user}


@app.get("/github/repos", tags=["GitHub Integration"])
def list_github_repositories_endpoint(
    limit: int = 50,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """List repositories accessible to the connected GitHub account."""
    token = resolve_github_token(current_user["id"])
    try:
        repos = list_user_repositories(token=token, limit=limit)
    except GitHubAPIError as exc:
        raise HTTPException(status_code=github_error_to_http(exc), detail=exc.message)
    if not repos:
        return {
            "count": 0,
            "repositories": [],
            "message": "No repositories returned. Check that your token has the 'repo' scope.",
        }
    return {"count": len(repos), "repositories": repos}


@app.get("/github/repos/{owner}/{name}/branches", tags=["GitHub Integration"])
def list_github_branches_endpoint(
    owner: str,
    name: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """List branches for a repository so a specific ref can be audited."""
    try:
        slug = normalize_repo_slug(f"{owner}/{name}")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    token = resolve_github_token(current_user["id"])
    branches = list_repository_branches(slug, token=token)
    return {"count": len(branches), "branches": branches}


@app.get("/github/repos/{owner}/{name}/inspect", tags=["GitHub Integration"])
def inspect_github_repository_endpoint(
    owner: str,
    name: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Pre-flight check: is this repository auditable, and how large is it?"""
    try:
        slug = normalize_repo_slug(f"{owner}/{name}")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    token = resolve_github_token(current_user["id"])
    from app.github_client import inspect_repository_before_audit
    try:
        return inspect_repository_before_audit(slug, token=token)
    except GitHubAPIError as exc:
        raise HTTPException(status_code=github_error_to_http(exc), detail=exc.message)


@app.post("/github/pull-request", tags=["GitHub Integration"])
@maybe_limit("10/minute")
def create_github_pull_request_endpoint(
    req: GitHubPRRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Create a branch, commit the eco-refactored code, and open a Pull Request."""
    token = resolve_github_token(current_user["id"], req.token)
    res = create_refactoring_pull_request(
        repo_full_name=req.repo_full_name,
        file_path=req.file_path,
        refactored_code=req.refactored_code,
        violation_title=req.violation_title,
        energy_reduction_pct=req.energy_reduction_pct,
        carbon_saved_10k=req.carbon_saved_10k,
        token=token,
        original_snippet=req.original_snippet,
    )
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to create PR"))
    return res
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
            # Violations already carry repository-relative paths.
            rel = v.get("relative_path") or v.get("file_path", "unknown")
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
