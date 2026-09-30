"""Dynamic analysis of arbitrary repository code, safely and with real measurement.

This is the "run it and see" half of the tool. Static analysis tells you a
pattern is expensive; dynamic analysis tells you what the program actually
costs. That distinction matters: a 4-deep loop over a 3-element list is
pathological in theory and free in practice, and no amount of AST inspection
can tell you which one you are looking at.

Security model
--------------
Executing code from an arbitrary GitHub repository is remote code execution by
definition, so the sandbox is not a convenience - it is the only thing standing
between a user's browser and someone else's payload.

The default posture is **deny unless Docker is available**. Host-level
execution of untrusted code is deliberately not offered as a fallback, because
a static denylist of dangerous calls is trivially bypassed via ``__import__``,
``getattr``, ``compile``, codecs or ``ctypes`` - or simply by reading the
operator's SSH key.

Container guardrails: network disabled, read-only rootfs with a small writable
tmpfs, all capabilities dropped, no privilege escalation, non-root user, CPU /
memory / PID limits so a fork bomb cannot take down the host, and a hard
wall-clock timeout enforced both in-container and by the runner.

Without Docker the endpoint reports ``sandbox_unavailable`` and returns no
numbers, rather than silently measuring something that is not the repository.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from fnmatch import fnmatch
from typing import Any, Dict, List, Optional, Tuple

from app.energy_sensors import probe_capabilities, select_meter
from app.sci import carbon_equivalents, compute_sci, sci_grade

# Marks containers this module created, so crash cleanup can reap exactly its
# own leftovers and never touch an operator's containers.
OWNER_LABEL = "com.greencode.analysis"

try:
    import docker

    DOCKER_AVAILABLE = True
except ImportError:  # pragma: no cover - depends on the host
    docker = None
    DOCKER_AVAILABLE = False


# Hard ceilings. A runaway repository must not be able to exhaust the host.
MAX_WALL_SECONDS = 120
MAX_MEMORY_BYTES = 512 * 1024 * 1024
MAX_CPUS = 1.0
MAX_PIDS = 128
MAX_OUTPUT_BYTES = 64 * 1024

_SAFE_FILENAME = re.compile(r"^[A-Za-z0-9_.-]+$")

# Entry-point filenames recognised as runnable, per language, in preference
# order. A test suite is preferred over a main script because it is the most
# representative workload a repository actually runs.
_ENTRY_CANDIDATES: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("python", ("test_*.py", "*_test.py", "tests.py",
                "benchmark*.py", "bench*.py", "main.py", "__main__.py")),
    ("node", ("test.js", "test.mjs", "index.js", "main.js", "index.mjs", "main.mjs")),
    ("java", ("Main.java", "main.java")),
    ("go", ("main.go",)),
)

_IMAGE_FOR = {
    "python": "python:3.12-slim",
    "node": "node:20-slim",
    "java": "eclipse-temurin:17-jdk",
    "go": "golang:1.22-alpine",
}

# Directories never descended into: a "test" inside these is not the repo's test.
_SKIP_DIRS = frozenset({
    ".git", "node_modules", "vendor", ".venv", "venv",
    "__pycache__", "dist", "build", "site-packages", "target", ".next",
})


def _matches(name: str, pattern: str) -> bool:
    return fnmatch(name, pattern)


def _command_for(language: str, entry: str) -> Optional[List[str]]:
    """Build the container command. Arguments are positional, never shell-interpreted."""
    if language == "python":
        return ["python", "-u", f"/workspace/{entry}"]
    if language == "node":
        return ["node", f"/workspace/{entry}"]
    if language == "java":
        cls = os.path.splitext(entry)[0]
        if not re.match(r"^[A-Za-z0-9_]+$", cls):
            return None
        # Compiled into a writable tmpfs, never back onto the host filesystem.
        return ["sh", "-c", 'javac "$1" -d /tmp/classes && java -cp /tmp/classes "$2"',
                "sh", f"/workspace/{entry}", cls]
    if language == "go":
        return ["go", "run", f"/workspace/{entry}"]
    return None


# Injected before the target script. Samples peak RSS from VmHWM on a timer and
# emits it on exit, so peak memory is measured *inside* the container rather
# than inferred from the Docker daemon's own footprint.
_MEM_PROBE = """import atexit, json, os, sys, threading, time
_peak = {"rss_kb": 0}
def _probe():
    try:
        with open("/proc/self/status") as _fh:
            for _line in _fh:
                if _line.startswith("VmHWM:"):
                    _peak["rss_kb"] = int(_line.split()[1])
    except Exception:
        pass
def _loop():
    while True:
        _probe()
        time.sleep(0.05)
threading.Thread(target=_loop, daemon=True).start()
atexit.register(lambda: sys.stderr.write(
    "@@GREENCODE_META@@" + json.dumps(_peak) + "\\n"))
"""

_META_RE = re.compile(r"@@GREENCODE_META@@(\{.*?\})", re.DOTALL)


@dataclass
class DynamicAnalysisResult:
    """Outcome of running a repository entry point under measurement."""

    ok: bool
    reason: str
    repo_slug: str = ""
    ref: str = ""
    entry_point: str = ""
    language: str = ""
    sandbox: str = ""
    measurement_method: str = ""
    measurement_is_hardware: bool = False
    exit_code: int = 0
    duration_seconds: float = 0.0
    peak_memory_mb: float = 0.0
    it_energy_joules: float = 0.0
    cpu_joules: float = 0.0
    memory_joules: float = 0.0
    sci: Dict[str, Any] = field(default_factory=dict)
    grade: Dict[str, Any] = field(default_factory=dict)
    equivalents: Dict[str, float] = field(default_factory=dict)
    stdout_tail: str = ""
    stderr_tail: str = ""
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DynamicAnalyzer:
    """Runs repository code in an isolated container while measuring energy."""

    def __init__(self, docker_client: Optional[Any] = None):
        self._client = docker_client

    # -- availability ------------------------------------------------------
    def _get_client(self):
        if self._client is not None:
            return self._client
        if not DOCKER_AVAILABLE:
            return None
        try:
            self._client = docker.from_env()
            self._client.ping()
            return self._client
        except Exception:
            return None

    def available(self) -> bool:
        return self._get_client() is not None

    @staticmethod
    def status() -> Dict[str, Any]:
        """Report why dynamic analysis can or cannot run, for the UI to display."""
        caps = probe_capabilities()
        docker_ok = False
        docker_error: Optional[str] = None

        if DOCKER_AVAILABLE:
            try:
                docker.from_env().ping()
                docker_ok = True
            except Exception as exc:
                docker_error = f"{type(exc).__name__}: {exc}"
        else:
            docker_error = "docker SDK not installed (pip install docker)"

        blockers: List[str] = []
        if not docker_ok:
            blockers.append(
                "Docker is required to execute untrusted repository code safely. "
                "Host-level execution of third-party code is deliberately not "
                "offered as a fallback."
            )

        return {
            "dynamic_analysis_available": not blockers,
            "blockers": blockers,
            "docker": {
                "sdk_installed": DOCKER_AVAILABLE,
                "reachable": docker_ok,
                "error": docker_error,
            },
            "energy_measurement": caps,
            "hardware_measurement_available": bool(caps["rapl"]["supported"]),
        }

    # -- entry point discovery --------------------------------------------
    @staticmethod
    def discover_entry_points(workdir: str) -> List[Tuple[str, str, str]]:
        """Find runnable entry points in a checked-out tree.

        Returns (language, relative_path, image) in preference order. Only the
        repository root is considered: running a test buried in a subpackage
        usually fails on imports, and a failing measurement is worse than none.
        """
        results: List[Tuple[str, str, str]] = []
        try:
            entries = sorted(os.listdir(workdir))
        except OSError:
            return results

        files = {n for n in entries if os.path.isfile(os.path.join(workdir, n))}

        for language, patterns in _ENTRY_CANDIDATES:
            image = _IMAGE_FOR[language]
            for pattern in patterns:
                hit = next((n for n in entries if n in files and _matches(n, pattern)), None)
                if hit:
                    results.append((language, hit, image))
                    break
        return results

    # -- execution ---------------------------------------------------------
    def analyze(
        self,
        workdir: str,
        *,
        repo_slug: str = "",
        ref: str = "",
        grid_intensity: float = 380.0,
        functional_unit: float = 1.0,
        timeout_sec: float = 60.0,
    ) -> DynamicAnalysisResult:
        """Run the most appropriate entry point and measure what it costs."""
        timeout_sec = max(1.0, min(float(timeout_sec), MAX_WALL_SECONDS))

        client = self._get_client()
        if client is None:
            return DynamicAnalysisResult(
                ok=False, reason="sandbox_unavailable", repo_slug=repo_slug, ref=ref,
                sandbox="none",
                warnings=[
                    "Dynamic analysis requires Docker. Host-level execution of "
                    "third-party code is not offered as a fallback."
                ],
            )

        # A previous process killed between create() and cleanup can strand a
        # container. Reap those before adding more, so repeated crashes degrade
        # instead of accumulating dead containers on the host.
        self.reap_stale_containers(client)

        entries = self.discover_entry_points(workdir)
        if not entries:
            return DynamicAnalysisResult(
                ok=False, reason="no_entry_point", repo_slug=repo_slug, ref=ref,
                sandbox="docker",
                warnings=[
                    "No runnable entry point was found at the repository root "
                    "(no test suite, benchmark or main script)."
                ],
            )

        language, entry, image = entries[0]
        if not _SAFE_FILENAME.match(entry):
            return DynamicAnalysisResult(
                ok=False, reason="unsafe_entry_point", repo_slug=repo_slug, ref=ref,
                entry_point=entry, language=language, sandbox="docker",
                warnings=[f"Refusing to execute '{entry}': unsafe filename."],
            )

        command = _command_for(language, entry)
        if command is None:
            return DynamicAnalysisResult(
                ok=False, reason="unsupported_language", repo_slug=repo_slug, ref=ref,
                entry_point=entry, language=language, sandbox="docker",
                warnings=[f"No execution command for language '{language}'."],
            )

        return self._run_in_container(
            client, os.path.realpath(workdir), entry, language, image, command,
            timeout_sec, repo_slug, ref, grid_intensity, functional_unit,
        )

    # -- container execution ----------------------------------------------
    def _run_in_container(
        self,
        client: Any,
        workdir: str,
        entry: str,
        language: str,
        image: str,
        command: List[str],
        timeout_sec: float,
        repo_slug: str,
        ref: str,
        grid_intensity: float,
        functional_unit: float,
    ) -> DynamicAnalysisResult:
        """Launch the workload under measurement and collect every figure.

        Energy is read from a host-side hardware counter spanning the whole
        container run, so the measurement covers the runtime image's own work
        (interpreter startup included), which is exactly the cost a user cares
        about when asking "what does running this cost me".
        """
        import time

        try:
            client.images.get(image)
        except Exception:
            try:
                client.images.pull(image)
            except Exception as exc:
                return DynamicAnalysisResult(
                    ok=False, reason="image_pull_failed", repo_slug=repo_slug, ref=ref,
                    entry_point=entry, language=language, sandbox="docker",
                    warnings=[f"Could not obtain {image}: {type(exc).__name__}"],
                )

        # The memory probe is prepended only for Python, where prepending source
        # is safe. Other languages get the plain command.
        if language == "python":
            probe_path = os.path.join(workdir, ".greencode_probe.py")
            try:
                with open(probe_path, "w", encoding="utf-8") as fh:
                    fh.write(_MEM_PROBE)
            except OSError as exc:
                return DynamicAnalysisResult(
                    ok=False, reason="probe_write_failed", repo_slug=repo_slug, ref=ref,
                    entry_point=entry, language=language, sandbox="docker",
                    warnings=[f"Could not stage the measurement probe: {exc}"],
                )
            # Prepending source is only safe for Python, where there is no
            # shebang or BOM to disturb. Other languages get the plain command.
            command = [
                "python", "-u", "-c",
                "exec(open('/workspace/.greencode_probe.py').read());"
                f"exec(open('/workspace/{entry}').read())",
            ]

        container = None
        meter = select_meter()
        before = meter.read() if meter is not None and hasattr(meter, "read") else None

        try:
            container = client.containers.create(
                image=image,
                command=command,
                working_dir="/workspace",
                volumes={workdir: {"bind": "/workspace", "mode": "ro"}},
                network_disabled=True,
                read_only=True,
                mem_limit=MAX_MEMORY_BYTES,
                memswap_limit=MAX_MEMORY_BYTES,   # no swap escape hatch
                cpu_quota=int(MAX_CPUS * 1_000_000),
                cpu_period=1_000_000,
                pids_limit=MAX_PIDS,
                security_opt=["no-new-privileges:true"],
                cap_drop=["ALL"],
                user="65534:65534",                # nobody:nogroup
                tmpfs={"/tmp": "rw,size=64m,noexec,nosuid"},
                environment={"PYTHONDONTWRITEBYTECODE": "1", "HOME": "/tmp"},
                labels={OWNER_LABEL: "1"},
                detach=True,
                stdin_open=False,
                tty=False,
            )
        except Exception as exc:
            self._cleanup_probe(workdir, language)
            return DynamicAnalysisResult(
                ok=False, reason="container_create_failed", repo_slug=repo_slug, ref=ref,
                entry_point=entry, language=language, sandbox="docker",
                warnings=[f"{type(exc).__name__}: {exc}"],
            )

        t0 = time.perf_counter()
        stdout_bytes = b""
        stderr_bytes = b""
        timed_out = False
        exit_code = -1
        container_warnings: List[str] = []

        try:
            container.start()
            try:
                # `Container.wait()` returns a single mapping
                # ``{"StatusCode": int, "Error": str|None}``, not a
                # ``(stdout, stderr)`` pair. Unpacking it as a pair yielded the
                # *keys* as strings, so the exit-code conversion raised and
                # every successful run was reported as a timeout.
                wait_result = container.wait(timeout=timeout_sec)
            except Exception:
                # wait() raises on timeout; the container is still running.
                timed_out = True
                try:
                    container.kill()
                except Exception:
                    pass
                wait_result = {"StatusCode": -1, "Error": "timeout"}

            duration = time.perf_counter() - t0

            if isinstance(wait_result, dict):
                exit_code = int(wait_result.get("StatusCode", -1) or 0)
                wait_error = wait_result.get("Error")
            elif isinstance(wait_result, (tuple, list)) and wait_result:
                # Older SDKs returned a (status, error) pair.
                exit_code = int(wait_result[0] or 0)
                wait_error = wait_result[1] if len(wait_result) > 1 else None
            else:
                exit_code = int(wait_result or 0)
                wait_error = None
            if wait_error and not timed_out:
                container_warnings.append(f"container error: {wait_error}")

            # Truncated deliberately: a malicious repo can print unbounded output.
            try:
                logs = container.logs(stdout=False, stderr=False, tail=2000)
                stdout_bytes = logs if isinstance(logs, bytes) else str(logs).encode()
            except Exception:
                pass
            try:
                err_logs = container.logs(stdout=True, stderr=True, tail=2000)
                stderr_bytes = err_logs if isinstance(err_logs, bytes) else str(err_logs).encode()
            except Exception:
                pass

        finally:
            # BaseException, not Exception: an interrupt or a hard exit between
            # create() and here would otherwise strand a container holding
            # memory and pids for as long as the daemon lives.
            try:
                container.remove(force=True)
            except BaseException:
                pass
            self._cleanup_probe(workdir, language)

        result = self._finalise(
            workdir=workdir,
            before=before,
            meter=meter,
            duration=duration,
            exit_code=exit_code,
            timed_out=timed_out,
            stdout_bytes=stdout_bytes,
            stderr_bytes=stderr_bytes,
            repo_slug=repo_slug,
            ref=ref,
            entry=entry,
            language=language,
            grid_intensity=grid_intensity,
            functional_unit=functional_unit,
        )
        result.warnings.extend(container_warnings)
        return result

    @staticmethod
    def _created_epoch(container: Any) -> Optional[float]:
        """Seconds-since-epoch for a container's creation time.

        The Docker API returns ``Created`` as an RFC3339 string with up to
        nanosecond precision (``2026-09-27T10:11:12.123456789Z``). Comparing
        that against a float raises, so it is parsed rather than cast. Returns
        ``None`` when the value is missing or unparseable, which makes the
        caller skip the container instead of guessing its age.
        """
        raw = getattr(container, "attrs", {}).get("Created")
        if raw is None:
            return None
        if isinstance(raw, (int, float)):
            return float(raw)
        text = str(raw).strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        # Trim sub-microsecond digits, which fromisoformat rejects on 3.10.
        if "." in text:
            head, _, tail = text.partition(".")
            digits = "".join(ch for ch in tail if ch.isdigit())[:6]
            offset = tail[len(digits):]
            text = f"{head}.{digits}{offset}" if digits else head
        try:
            return datetime.fromisoformat(text).timestamp()
        except ValueError:
            return None

    @staticmethod
    def reap_stale_containers(client: Any, max_age_seconds: int = 900) -> int:
        """Remove leftover analysis containers older than ``max_age_seconds``.

        Only containers carrying :data:`OWNER_LABEL` are touched, so an
        operator's own `docker run` containers are never at risk. The age guard
        exists so a concurrently running analysis is never reaped out from under
        itself.
        """
        try:
            cutoff = time.time() - max_age_seconds
            stale = client.containers.list(
                all=True, filters={"label": OWNER_LABEL}
            )
            removed = 0
            for container in stale:
                created = DynamicAnalyzer._created_epoch(container)
                if created is None or created >= cutoff:
                    # Unknown age, or young enough to still be in use.
                    continue
                try:
                    container.remove(force=True)
                    removed += 1
                except Exception:
                    pass
            return removed
        except Exception:
            # Reaping is housekeeping; never let it fail an analysis.
            return 0

    @staticmethod
    def _cleanup_probe(workdir: str, language: str) -> None:
        if language != "python":
            return
        try:
            os.remove(os.path.join(workdir, ".greencode_probe.py"))
        except OSError:
            pass

    def _finalise(
        self,
        *,
        workdir: str,
        before: Any,
        meter: Any,
        duration: float,
        exit_code: int,
        timed_out: bool,
        stdout_bytes: bytes,
        stderr_bytes: bytes,
        repo_slug: str,
        ref: str,
        entry: str,
        language: str,
        grid_intensity: float,
        functional_unit: float,
    ) -> DynamicAnalysisResult:
        """Read the energy counter delta, parse the probe, and compute SCI."""
        after = meter.read() if meter is not None else None

        cpu_j = mem_j = 0.0
        method = "model"
        warnings: List[str] = []

        # Only a domain-differencing meter (RAPL) yields a real measurement.
        # A battery meter reports a whole-system average and returns None from
        # read(), so it correctly falls through to the model rather than
        # presenting an average as a measurement of this container.
        backend = meter.describe().get("backend") if meter is not None else None
        can_measure = (
            meter is not None
            and before is not None
            and after is not None
            and hasattr(meter, "joules_between")
        )

        if can_measure:
            joules = meter.joules_between(before, after)
            cpu_j = float(joules.get("cpu_joules", 0.0))
            mem_j = float(joules.get("memory_joules", 0.0))
            if cpu_j + mem_j > 0:
                method = backend or "rapl"
            else:
                can_measure = False
        else:
            warnings.append(
                "No hardware energy counter is reachable on this host. Energy was "
                "estimated from a TDP/load model, not measured."
            )

        stderr_text = (stderr_bytes or b"").decode("utf-8", "replace")
        peak_mb = 0.0
        match = _META_RE.search(stderr_text)
        if match:
            try:
                peak_mb = json.loads(match.group(1)).get("rss_kb", 0) / 1024.0
            except (ValueError, TypeError):
                peak_mb = 0.0

        # When no counter exists, fall back to the model, but say so loudly.
        it_joules = cpu_j + mem_j
        if it_joules <= 0 and duration > 0:
            from app.energy_sensors import model_power_watts

            it_joules = model_power_watts(60.0, peak_mb) * duration
            method = "model"

        sci_result = compute_sci(
            energy_joules=it_joules,
            duration_seconds=duration,
            carbon_intensity_gco2_per_kwh=grid_intensity,
            functional_unit=functional_unit,
            cpu_joules=cpu_j,
            memory_joules=mem_j,
            measurement_method=method,
        )
        warnings.extend(sci_result.warnings)

        reason = "ok"
        if timed_out:
            reason = "timeout"
            warnings.append(
                f"Execution exceeded the {int(duration)}s budget and was killed. "
                "Energy figures are a lower bound, not a complete measurement."
            )
        elif exit_code != 0:
            reason = "nonzero_exit"
            warnings.append(
                f"The workload exited with code {exit_code}. Energy still reflects "
                "the work that was done before it stopped."
            )

        return DynamicAnalysisResult(
            ok=(not timed_out and exit_code == 0),
            reason=reason,
            repo_slug=repo_slug,
            ref=ref,
            entry_point=entry,
            language=language,
            sandbox="docker-isolated",
            measurement_method=method,
            measurement_is_hardware=method in ("rapl", "scaphandre", "perf", "battery"),
            exit_code=exit_code,
            duration_seconds=round(duration, 4),
            peak_memory_mb=round(peak_mb, 2),
            it_energy_joules=round(it_joules, 4),
            cpu_joules=round(cpu_j, 4),
            memory_joules=round(mem_j, 4),
            sci=sci_result.to_dict(),
            grade=sci_grade(sci_result.sci_gco2_per_functional_unit),
            equivalents=carbon_equivalents(sci_result.operational_gco2),
            stdout_tail=(stdout_bytes or b"")[-MAX_OUTPUT_BYTES:].decode("utf-8", "replace"),
            stderr_tail=_META_RE.sub("", stderr_text)[-MAX_OUTPUT_BYTES:],
            warnings=warnings,
        )




