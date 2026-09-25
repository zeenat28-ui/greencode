"""SQLAlchemy Asynchronous Database Layer and Connection Pool for GreenCode Auditor.

Implements high-concurrency async connection pooling via SQLAlchemy 2.0 and asyncpg / aiosqlite,
providing robust transaction contextual managers, automatic retry policies to eliminate database
concurrency locks, and clean relational schemas for repositories, multi-language violations, and
Software Carbon Intensity (SCI) telemetry metrics.
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import os
import secrets
import sys
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

import bcrypt

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    desc,
    select,
    text,
)
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base, relationship, scoped_session, sessionmaker

# ---------------------------------------------------------------------------
# DATABASE URL & ASYNC ENGINE CONFIGURATION
# ---------------------------------------------------------------------------
RAW_DB_URL = os.environ.get("DATABASE_URL", "sqlite:///greencode.db")

# Automatically adapt URL for async drivers (asyncpg for PostgreSQL, aiosqlite for SQLite)
if RAW_DB_URL.startswith("postgresql://"):
    ASYNC_DB_URL = RAW_DB_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    SYNC_DB_URL = RAW_DB_URL
elif RAW_DB_URL.startswith("postgres://"):
    ASYNC_DB_URL = RAW_DB_URL.replace("postgres://", "postgresql+asyncpg://", 1)
    SYNC_DB_URL = RAW_DB_URL.replace("postgres://", "postgresql://", 1)
elif RAW_DB_URL.startswith("sqlite:///"):
    ASYNC_DB_URL = RAW_DB_URL.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    SYNC_DB_URL = RAW_DB_URL
elif "asyncpg" in RAW_DB_URL or "aiosqlite" in RAW_DB_URL:
    ASYNC_DB_URL = RAW_DB_URL
    SYNC_DB_URL = RAW_DB_URL.replace("+asyncpg", "").replace("+aiosqlite", "")
else:
    ASYNC_DB_URL = f"sqlite+aiosqlite:///{RAW_DB_URL}"
    SYNC_DB_URL = f"sqlite:///{RAW_DB_URL}"

# Build Async Engine with Enterprise Connection Pooling parameters
async_engine_kwargs: Dict[str, Any] = {
    "echo": False,
    "pool_pre_ping": True,  # Detect disconnected pool sockets before checkout
}

if "postgresql" in ASYNC_DB_URL:
    async_engine_kwargs.update({
        "pool_size": int(os.environ.get("DB_POOL_SIZE", "20")),
        "max_overflow": int(os.environ.get("DB_MAX_OVERFLOW", "10")),
        "pool_timeout": 30.0,
        "pool_recycle": 1800,  # Recycle connection after 30 minutes
    })
else:
    # SQLite async connection args
    async_engine_kwargs.update({
        "connect_args": {"check_same_thread": False, "timeout": 30.0},
    })

try:
    async_engine: AsyncEngine = create_async_engine(ASYNC_DB_URL, **async_engine_kwargs)
except Exception:
    # Fallback to local SQLite async engine if connection string fails
    ASYNC_DB_URL = "sqlite+aiosqlite:///greencode.db"
    SYNC_DB_URL = "sqlite:///greencode.db"
    async_engine = create_async_engine(ASYNC_DB_URL, connect_args={"check_same_thread": False, "timeout": 30.0})

# Async Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Synchronous Fallback Engine for Synchronous callers (Streamlit / CLI)
try:
    sync_engine = create_engine(
        SYNC_DB_URL,
        connect_args={"check_same_thread": False, "timeout": 30.0} if "sqlite" in SYNC_DB_URL else {},
        echo=False,
        pool_pre_ping=True,
    )
except Exception:
    # Fallback to local SQLite if remote driver or connection is unavailable
    SYNC_DB_URL = "sqlite:///greencode.db"
    sync_engine = create_engine(
        SYNC_DB_URL,
        connect_args={"check_same_thread": False, "timeout": 30.0},
        echo=False,
        pool_pre_ping=True,
    )
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=sync_engine))

Base = declarative_base()


# ---------------------------------------------------------------------------
# RELATIONAL MODELS
# ---------------------------------------------------------------------------
class User(Base):
    """Registered platform user for GreenCode Developer Portal."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    github_username = Column(String(100), nullable=True)
    github_token = Column(Text, nullable=True)
    avatar_url = Column(String(1024), nullable=True)
    role = Column(String(50), default="developer")
    is_verified = Column(Boolean, default=False, nullable=False)
    verification_token = Column(String(255), nullable=True, index=True)
    reset_token = Column(String(255), nullable=True, index=True)
    reset_token_expires = Column(DateTime, nullable=True)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    last_login_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    repositories = relationship(
        "Repository", back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )


class Repository(Base):
    """Tracks repositories or project workspaces audited for carbon efficiency."""

    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    path_or_url = Column(String(1024), nullable=False)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    total_files = Column(Integer, default=0)
    total_lines = Column(Integer, default=0)
    green_score = Column(Float, default=100.0)
    status = Column(String(50), default="completed")
    summary_json = Column(Text, nullable=True)

    user = relationship("User", back_populates="repositories")
    violations = relationship(
        "ScanViolation", back_populates="repository", cascade="all, delete-orphan", lazy="selectin"
    )
    profiles = relationship(
        "ProfileMetric", back_populates="repository", cascade="all, delete-orphan", lazy="selectin"
    )


class ScanViolation(Base):
    """Individual anti-pattern violation detected during multi-language AST/CST audit."""

    __tablename__ = "scan_violations"

    id = Column(Integer, primary_key=True, index=True)
    repo_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    file_path = Column(String(1024), nullable=False)
    line_number = Column(Integer, nullable=False)
    end_line_number = Column(Integer, nullable=True)
    violation_type = Column(String(100), nullable=False)
    severity = Column(String(20), default="MEDIUM")
    deduction = Column(Float, default=5.0)
    snippet = Column(Text, nullable=True)
    context_code = Column(Text, nullable=True)
    suggested_fix = Column(Text, nullable=True)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    repository = relationship("Repository", back_populates="violations")
    refactorings = relationship("RefactoringRecord", back_populates="violation", lazy="selectin")


class ProfileMetric(Base):
    """Real-time dynamic execution profiling telemetry."""

    __tablename__ = "profile_metrics"

    id = Column(Integer, primary_key=True, index=True)
    repo_id = Column(Integer, ForeignKey("repositories.id"), nullable=True)
    file_path = Column(String(1024), nullable=False)
    duration_sec = Column(Float, nullable=False)
    avg_cpu_percent = Column(Float, nullable=False)
    peak_memory_mb = Column(Float, nullable=False)
    energy_wh = Column(Float, nullable=False)
    operational_carbon_gco2 = Column(Float, nullable=False)
    sci_score = Column(Float, nullable=False)
    profiling_mode = Column(String(50), default="DOCKER_ISOLATED")
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    repository = relationship("Repository", back_populates="profiles")


class RefactoringRecord(Base):
    """Historical records of code transformed via GreenCode AI Synthesizer."""

    __tablename__ = "refactoring_records"

    id = Column(Integer, primary_key=True, index=True)
    violation_id = Column(Integer, ForeignKey("scan_violations.id"), nullable=True)
    original_code = Column(Text, nullable=False)
    refactored_code = Column(Text, nullable=False)
    energy_reduction_pct = Column(Float, default=0.0)
    carbon_saved_gco2_10k_runs = Column(Float, default=0.0)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    violation = relationship("ScanViolation", back_populates="refactorings")


# ---------------------------------------------------------------------------
# INITIALIZATION & CONTEXT MANAGERS WITH RETRY LOGIC
# ---------------------------------------------------------------------------
def init_db() -> None:
    """Initialize relational database tables across sync and async engines."""
    Base.metadata.create_all(bind=sync_engine)
    if "sqlite" in SYNC_DB_URL:
        try:
            with sync_engine.connect() as conn:
                conn.execute(text("PRAGMA journal_mode = WAL;"))
                conn.execute(text("PRAGMA synchronous = NORMAL;"))
                # Migrate user_id column to repositories if not yet present
                res = conn.execute(text("PRAGMA table_info(repositories);")).fetchall()
                col_names = [r[1] for r in res]
                if "user_id" not in col_names:
                    conn.execute(text("ALTER TABLE repositories ADD COLUMN user_id INTEGER REFERENCES users(id);"))
                # Migrate verification and reset columns to users if not yet present
                u_res = conn.execute(text("PRAGMA table_info(users);")).fetchall()
                u_cols = [r[1] for r in u_res]
                if "is_verified" not in u_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT 0;"))
                if "verification_token" not in u_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN verification_token VARCHAR(255);"))
                if "reset_token" not in u_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN reset_token VARCHAR(255);"))
                if "reset_token_expires" not in u_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN reset_token_expires DATETIME;"))
                conn.commit()
        except Exception:
            pass


async def init_async_db() -> None:
    """Initialize schema asynchronously."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if "sqlite" in ASYNC_DB_URL:
            try:
                await conn.execute(text("PRAGMA journal_mode = WAL;"))
                await conn.execute(text("PRAGMA synchronous = NORMAL;"))
                res = await conn.execute(text("PRAGMA table_info(repositories);"))
                col_names = [r[1] for r in res.fetchall()]
                if "user_id" not in col_names:
                    await conn.execute(text("ALTER TABLE repositories ADD COLUMN user_id INTEGER REFERENCES users(id);"))
                u_res = await conn.execute(text("PRAGMA table_info(users);"))
                u_cols = [r[1] for r in u_res.fetchall()]
                if "is_verified" not in u_cols:
                    await conn.execute(text("ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT 0;"))
                if "verification_token" not in u_cols:
                    await conn.execute(text("ALTER TABLE users ADD COLUMN verification_token VARCHAR(255);"))
                if "reset_token" not in u_cols:
                    await conn.execute(text("ALTER TABLE users ADD COLUMN reset_token VARCHAR(255);"))
                if "reset_token_expires" not in u_cols:
                    await conn.execute(text("ALTER TABLE users ADD COLUMN reset_token_expires DATETIME;"))
            except Exception:
                pass


async def close_async_db() -> None:
    """Gracefully dispose and close the asynchronous engine connection pool."""
    if async_engine is not None:
        try:
            await async_engine.dispose()
        except Exception:
            pass


@asynccontextmanager
async def get_async_session(max_retries: int = 3, retry_delay: float = 0.1) -> AsyncGenerator[AsyncSession, None]:
    """Asynchronous transaction session contextual manager with automatic commit/rollback."""
    session = AsyncSessionLocal()
    try:
        yield session
        # Attempt commit with retry if database is temporarily locked
        committed = False
        retries = 0
        while not committed and retries <= max_retries:
            try:
                await session.commit()
                committed = True
            except (OperationalError, DBAPIError) as exc:
                if retries < max_retries and "locked" in str(exc).lower():
                    retries += 1
                    await asyncio.sleep(retry_delay * (2 ** (retries - 1)))
                else:
                    raise
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()



def get_db():
    """Sync contextual DB session generator."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# ASYNCHRONOUS CRUD OPERATIONS (High Concurrency)
# ---------------------------------------------------------------------------
async def save_scan_results_async(
    name: str,
    path_or_url: str,
    total_files: int,
    total_lines: int,
    green_score: float,
    violations_data: List[Dict[str, Any]],
    summary_json: Optional[str] = None,
) -> Dict[str, Any]:
    """Persist repository scan results asynchronously using connection pooling."""
    async with get_async_session() as session:
        repo = Repository(
            name=name,
            path_or_url=path_or_url,
            total_files=total_files,
            total_lines=total_lines,
            green_score=green_score,
            status="completed",
            summary_json=summary_json,
        )
        session.add(repo)
        await session.flush()

        for v in violations_data:
            violation = ScanViolation(
                repo_id=repo.id,
                file_path=v.get("file_path", ""),
                line_number=v.get("line_number", 1),
                end_line_number=v.get("end_line_number"),
                violation_type=v.get("violation_type", "UNKNOWN"),
                severity=v.get("severity", "MEDIUM"),
                deduction=float(v.get("deduction", 0.0)),
                snippet=v.get("snippet", ""),
                context_code=v.get("context_code", ""),
                suggested_fix=v.get("suggested_fix", ""),
            )
            session.add(violation)

        await session.commit()
        return {
            "id": repo.id,
            "name": repo.name,
            "green_score": repo.green_score,
            "total_files": repo.total_files,
        }


async def save_profile_metric_async(
    file_path: str,
    duration_sec: float,
    avg_cpu_percent: float,
    peak_memory_mb: float,
    energy_wh: float,
    operational_carbon_gco2: float,
    sci_score: float,
    profiling_mode: str = "DOCKER_ISOLATED",
    repo_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Persist profiling metrics asynchronously without thread locking."""
    async with get_async_session() as session:
        metric = ProfileMetric(
            repo_id=repo_id,
            file_path=file_path,
            duration_sec=duration_sec,
            avg_cpu_percent=avg_cpu_percent,
            peak_memory_mb=peak_memory_mb,
            energy_wh=energy_wh,
            operational_carbon_gco2=operational_carbon_gco2,
            sci_score=sci_score,
            profiling_mode=profiling_mode,
        )
        session.add(metric)
        await session.commit()
        return {"id": metric.id, "energy_wh": metric.energy_wh, "sci_score": metric.sci_score}


async def save_refactoring_record_async(
    original_code: str,
    refactored_code: str,
    energy_reduction_pct: float,
    carbon_saved_gco2_10k_runs: float,
    violation_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Persist refactoring records asynchronously."""
    async with get_async_session() as session:
        record = RefactoringRecord(
            violation_id=violation_id,
            original_code=original_code,
            refactored_code=refactored_code,
            energy_reduction_pct=energy_reduction_pct,
            carbon_saved_gco2_10k_runs=carbon_saved_gco2_10k_runs,
        )
        session.add(record)
        await session.commit()
        return {"id": record.id, "carbon_saved": record.carbon_saved_gco2_10k_runs}


async def get_latest_repositories_async(limit: int = 10) -> List[Dict[str, Any]]:
    """Query repositories asynchronously."""
    async with get_async_session() as session:
        stmt = select(Repository).order_by(desc(Repository.created_at)).limit(limit)
        result = await session.execute(stmt)
        repos = result.scalars().all()
        return [
            {
                "id": r.id,
                "name": r.name,
                "path_or_url": r.path_or_url,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "total_files": r.total_files,
                "total_lines": r.total_lines,
                "green_score": r.green_score,
                "status": r.status,
            }
            for r in repos
        ]


async def get_cumulative_carbon_savings_async() -> Dict[str, float]:
    """Calculate cumulative carbon savings asynchronously across connection pool."""
    async with get_async_session() as session:
        stmt = select(RefactoringRecord)
        result = await session.execute(stmt)
        records = result.scalars().all()
        total_gco2 = sum(r.carbon_saved_gco2_10k_runs for r in records)
        avg_pct = (
            sum(r.energy_reduction_pct for r in records) / len(records)
            if records
            else 0.0
        )
        return {
            "total_carbon_saved_gco2_10k_runs": round(total_gco2, 4),
            "average_energy_reduction_pct": round(avg_pct, 2),
            "total_refactoring_operations": len(records),
        }


# ---------------------------------------------------------------------------
# SYNCHRONOUS COMPATIBILITY BRIDGES (Streamlit & Test Suites)
# ---------------------------------------------------------------------------
def save_scan_results(
    name: str,
    path_or_url: str,
    total_files: int,
    total_lines: int,
    green_score: float,
    violations_data: List[Dict[str, Any]],
    summary_json: Optional[str] = None,
    user_id: Optional[int] = None,
) -> Repository:
    """Sync wrapper to persist scan results."""
    init_db()
    db = SessionLocal()
    try:
        repo = Repository(
            user_id=user_id,
            name=name,
            path_or_url=path_or_url,
            total_files=total_files,
            total_lines=total_lines,
            green_score=green_score,
            status="completed",
            summary_json=summary_json,
        )
        db.add(repo)
        db.flush()

        for v in violations_data:
            violation = ScanViolation(
                repo_id=repo.id,
                file_path=v.get("file_path", ""),
                line_number=v.get("line_number", 1),
                end_line_number=v.get("end_line_number"),
                violation_type=v.get("violation_type", "UNKNOWN"),
                severity=v.get("severity", "MEDIUM"),
                deduction=float(v.get("deduction", 0.0)),
                snippet=v.get("snippet", ""),
                context_code=v.get("context_code", ""),
                suggested_fix=v.get("suggested_fix", ""),
            )
            db.add(violation)

        db.commit()
        db.refresh(repo)
        return repo
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def save_profile_metric(
    file_path: str,
    duration_sec: float,
    avg_cpu_percent: float,
    peak_memory_mb: float,
    energy_wh: float,
    operational_carbon_gco2: float,
    sci_score: float,
    profiling_mode: str = "DOCKER_ISOLATED",
    repo_id: Optional[int] = None,
) -> ProfileMetric:
    """Sync wrapper to persist profile metric."""
    init_db()
    db = SessionLocal()
    try:
        metric = ProfileMetric(
            repo_id=repo_id,
            file_path=file_path,
            duration_sec=duration_sec,
            avg_cpu_percent=avg_cpu_percent,
            peak_memory_mb=peak_memory_mb,
            energy_wh=energy_wh,
            operational_carbon_gco2=operational_carbon_gco2,
            sci_score=sci_score,
            profiling_mode=profiling_mode,
        )
        db.add(metric)
        db.commit()
        db.refresh(metric)
        return metric
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def save_refactoring_record(
    original_code: str,
    refactored_code: str,
    energy_reduction_pct: float,
    carbon_saved_gco2_10k_runs: float,
    violation_id: Optional[int] = None,
) -> RefactoringRecord:
    """Sync wrapper to persist refactoring record."""
    init_db()
    db = SessionLocal()
    try:
        record = RefactoringRecord(
            violation_id=violation_id,
            original_code=original_code,
            refactored_code=refactored_code,
            energy_reduction_pct=energy_reduction_pct,
            carbon_saved_gco2_10k_runs=carbon_saved_gco2_10k_runs,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_latest_repositories(limit: int = 10) -> List[Dict[str, Any]]:
    """Sync wrapper for repository history."""
    init_db()
    db = SessionLocal()
    try:
        repos = (
            db.query(Repository).order_by(desc(Repository.created_at)).limit(limit).all()
        )
        return [
            {
                "id": r.id,
                "name": r.name,
                "path_or_url": r.path_or_url,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "total_files": r.total_files,
                "total_lines": r.total_lines,
                "green_score": r.green_score,
                "status": r.status,
                "user_id": r.user_id,
            }
            for r in repos
        ]
    finally:
        db.close()


def get_repository_details(repo_id: int) -> Optional[Dict[str, Any]]:
    """Sync wrapper for repository details."""
    init_db()
    db = SessionLocal()
    try:
        repo = db.query(Repository).filter(Repository.id == repo_id).first()
        if not repo:
            return None
        return {
            "id": repo.id,
            "name": repo.name,
            "path_or_url": repo.path_or_url,
            "user_id": repo.user_id,
            "created_at": repo.created_at.isoformat() if repo.created_at else None,
            "total_files": repo.total_files,
            "total_lines": repo.total_lines,
            "green_score": repo.green_score,
            "violations": [
                {
                    "id": v.id,
                    "file_path": v.file_path,
                    "line_number": v.line_number,
                    "end_line_number": v.end_line_number,
                    "violation_type": v.violation_type,
                    "severity": v.severity,
                    "deduction": v.deduction,
                    "snippet": v.snippet,
                    "context_code": v.context_code,
                    "suggested_fix": v.suggested_fix,
                }
                for v in repo.violations
            ],
            "profiles": [
                {
                    "id": p.id,
                    "file_path": p.file_path,
                    "duration_sec": p.duration_sec,
                    "avg_cpu_percent": p.avg_cpu_percent,
                    "peak_memory_mb": p.peak_memory_mb,
                    "energy_wh": p.energy_wh,
                    "operational_carbon_gco2": p.operational_carbon_gco2,
                    "sci_score": p.sci_score,
                    "profiling_mode": p.profiling_mode,
                }
                for p in repo.profiles
            ],
        }
    finally:
        db.close()


def get_cumulative_carbon_savings() -> Dict[str, float]:
    """Sync wrapper for cumulative savings."""
    init_db()
    db = SessionLocal()
    try:
        records = db.query(RefactoringRecord).all()
        total_gco2 = sum(r.carbon_saved_gco2_10k_runs for r in records)
        avg_pct = (
            sum(r.energy_reduction_pct for r in records) / len(records)
            if records
            else 0.0
        )
        return {
            "total_carbon_saved_gco2_10k_runs": round(total_gco2, 4),
            "average_energy_reduction_pct": round(avg_pct, 2),
            "total_refactoring_operations": len(records),
        }
    finally:
        db.close()


# ---------------------------------------------------------------------------
# USER AUTHENTICATION & PROFILE MANAGEMENT
# ---------------------------------------------------------------------------
def hash_password(plain_password: str) -> str:
    """Hash password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against bcrypt hash."""
    if not plain_password or not hashed_password:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def user_to_dict(user: Optional[User], include_sensitive: bool = False) -> Optional[Dict[str, Any]]:
    """Serialize User model to sanitized dictionary (never exposes password_hash; protects tokens by default)."""
    if not user:
        return None
    token = user.github_token
    token_masked = None
    if token:
        token_masked = f"{token[:4]}****{token[-4:]}" if len(token) > 8 else "****"

    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name or user.username,
        "github_username": user.github_username,
        "github_token": token if include_sensitive else None,
        "has_github_token": bool(token),
        "github_token_masked": token_masked,
        "avatar_url": user.avatar_url,
        "role": user.role,
        "is_verified": getattr(user, "is_verified", False),
        "verification_token": user.verification_token if include_sensitive else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
    }


def create_user(
    email: str,
    username: str,
    password: str,
    full_name: Optional[str] = None,
    github_token: Optional[str] = None,
    github_username: Optional[str] = None,
    avatar_url: Optional[str] = None,
    role: str = "developer",
    auto_verify: bool = False,
) -> Dict[str, Any]:
    """Create a new user account with hashed password and verification token."""
    init_db()
    db = SessionLocal()
    try:
        clean_email = email.strip().lower()
        clean_username = username.strip().lower()
        if not clean_email or "@" not in clean_email:
            raise ValueError("A valid email address is required.")
        if not clean_username or len(clean_username) < 3:
            raise ValueError("Username must be at least 3 characters long.")
        if not password or len(password) < 6:
            raise ValueError("Password must be at least 6 characters long.")

        existing = db.query(User).filter(
            (User.email == clean_email) | (User.username == clean_username)
        ).first()
        if existing:
            if existing.email == clean_email:
                raise ValueError("An account with this email address already exists.")
            else:
                raise ValueError("This username is already taken. Please choose another.")

        hashed_pwd = hash_password(password)
        now_utc = datetime.now(timezone.utc)
        v_token = None if auto_verify else secrets.token_urlsafe(32)
        user = User(
            email=clean_email,
            username=clean_username,
            password_hash=hashed_pwd,
            full_name=full_name.strip() if full_name else clean_username,
            github_username=github_username.strip() if github_username else None,
            github_token=github_token.strip() if github_token else None,
            avatar_url=avatar_url,
            role=role,
            is_verified=auto_verify,
            verification_token=v_token,
            created_at=now_utc,
            last_login_at=now_utc,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user_to_dict(user, include_sensitive=True)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def authenticate_user(login: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticate user with email or username and password."""
    init_db()
    db = SessionLocal()
    try:
        clean_login = login.strip().lower()
        user = db.query(User).filter(
            (User.email == clean_login) | (User.username == clean_login)
        ).first()
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        user.last_login_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(user)
        return user_to_dict(user, include_sensitive=True)
    finally:
        db.close()


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Fetch public user profile by ID (tokens masked for security)."""
    init_db()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        return user_to_dict(user, include_sensitive=False) if user else None
    finally:
        db.close()


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Fetch public user profile by email."""
    init_db()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email.strip().lower()).first()
        return user_to_dict(user, include_sensitive=False) if user else None
    finally:
        db.close()


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Fetch public user profile by username."""
    init_db()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username.strip().lower()).first()
        return user_to_dict(user, include_sensitive=False) if user else None
    finally:
        db.close()


def get_user_raw_github_token(user_id: int) -> Optional[str]:
    """Retrieve raw GitHub token strictly for authenticated internal services."""
    init_db()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        return user.github_token if user else None
    finally:
        db.close()


def update_user_profile(
    user_id: int,
    github_token: Optional[str] = None,
    github_username: Optional[str] = None,
    avatar_url: Optional[str] = None,
    full_name: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Update user GitHub credentials or profile details."""
    init_db()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        if github_token is not None:
            user.github_token = github_token.strip() if github_token else None
        if github_username is not None:
            user.github_username = github_username.strip() if github_username else None
        if avatar_url is not None:
            user.avatar_url = avatar_url
        if full_name is not None:
            user.full_name = full_name.strip() if full_name else None
        db.commit()
        db.refresh(user)
        return user_to_dict(user, include_sensitive=True)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_or_create_github_user(github_token: str, gh_user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Auto-provision or sign in a user via GitHub token authentication."""
    init_db()
    db = SessionLocal()
    try:
        gh_login = gh_user_data.get("login", "").strip()
        gh_email = gh_user_data.get("email") or f"{gh_login.lower()}@users.noreply.github.com"
        avatar_url = gh_user_data.get("avatar_url")
        full_name = gh_user_data.get("name") or gh_login

        user = db.query(User).filter(
            (User.github_username == gh_login) |
            (User.email == gh_email.lower()) |
            (User.username == gh_login.lower())
        ).first()

        now_utc = datetime.now(timezone.utc)
        if user:
            user.github_token = github_token.strip()
            user.github_username = gh_login
            if avatar_url:
                user.avatar_url = avatar_url
            if full_name and not user.full_name:
                user.full_name = full_name
            user.last_login_at = now_utc
            db.commit()
            db.refresh(user)
            return user_to_dict(user, include_sensitive=True)
        else:
            random_pwd = os.urandom(16).hex()
            user = User(
                email=gh_email.lower(),
                username=gh_login.lower(),
                password_hash=hash_password(random_pwd),
                full_name=full_name,
                github_username=gh_login,
                github_token=github_token.strip(),
                avatar_url=avatar_url,
                role="developer",
                is_verified=True,  # GitHub-authenticated emails are pre-verified by GitHub
                created_at=now_utc,
                last_login_at=now_utc,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            return user_to_dict(user, include_sensitive=True)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def verify_user_email(token: str) -> Dict[str, Any]:
    """Verify user's email address via one-time verification token."""
    init_db()
    db = SessionLocal()
    try:
        clean_token = token.strip()
        user = db.query(User).filter(User.verification_token == clean_token).first()
        if not user:
            return {"success": False, "error": "Invalid or expired verification token."}
        user.is_verified = True
        user.verification_token = None
        db.commit()
        db.refresh(user)
        return {
            "success": True,
            "message": "Email address verified successfully.",
            "user": user_to_dict(user, include_sensitive=False),
        }
    finally:
        db.close()


def create_password_reset_token(email: str) -> Optional[Dict[str, Any]]:
    """Generate expiring password reset token for given email (1 hour TTL)."""
    init_db()
    db = SessionLocal()
    try:
        clean_email = email.strip().lower()
        user = db.query(User).filter(User.email == clean_email).first()
        if not user:
            return None
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        user.reset_token = token
        user.reset_token_expires = expires_at
        db.commit()
        return {
            "email": user.email,
            "username": user.username,
            "token": token,
            "expires_at": expires_at.isoformat(),
        }
    finally:
        db.close()


def reset_password_with_token(token: str, new_password: str) -> Dict[str, Any]:
    """Verify reset token and update user password."""
    if not new_password or len(new_password) < 6:
        return {"success": False, "error": "Password must be at least 6 characters long."}

    init_db()
    db = SessionLocal()
    try:
        clean_token = token.strip()
        now_utc = datetime.now(timezone.utc)
        user = db.query(User).filter(User.reset_token == clean_token).first()
        if not user:
            return {"success": False, "error": "Invalid or expired reset token."}
        if user.reset_token_expires and user.reset_token_expires.replace(tzinfo=timezone.utc) < now_utc:
            return {"success": False, "error": "Reset token has expired. Please request a new one."}

        user.password_hash = hash_password(new_password)
        user.reset_token = None
        user.reset_token_expires = None
        db.commit()
        db.refresh(user)
        return {"success": True, "message": "Password updated successfully. You can now sign in with your new password."}
    finally:
        db.close()


