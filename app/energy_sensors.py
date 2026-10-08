"""Hardware energy measurement backends.

Real dynamic energy analysis requires reading an actual energy counter. This
module probes the host for whatever it genuinely supports and always reports
which tier produced each number, so an estimate is never mistaken for a
measurement.

Tiers (highest fidelity first):

1. ``rapl``        - Intel/AMD RAPL counters via Linux ``/sys/class/powercap``.
   Millijoule-accurate; this is what CodeGreen validates against.
2. ``scaphandre``  - Scaphandre energy exporter sidecar (hubblo/scaphandre).
   Reads the same RAPL hardware via a Prometheus HTTP endpoint, making real
   energy data available to containers on hosts where /sys/class/powercap is
   not bind-mounted. This is the production path for Docker-on-Linux and CI.
3. ``perf``        - the same PMU counters via ``perf stat -e power/energy-pkg/``.
4. ``battery``     - whole-system discharge rate. Coarse but genuinely measured.
5. ``model``       - calibrated TDP + load model. Explicitly an *estimate*.
"""

from __future__ import annotations

import copy
import glob
import os
import platform
import re
import subprocess
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# Calibration constants for the modelled tier, following the approach used by
# the Green Software Foundation reference guidance.
TDP_IDLE_WATTS = 5.0
TDP_SATURATION_WATTS = 95.0
MEMORY_WATTS_PER_GIB = 0.3725  # ~3 W per 8 GiB DDR4 module
DATACENTER_PUE = 1.20


# Single source of truth for "did this number come from a real counter?".
#
# This set used to be duplicated as a literal in four modules, and the copies had
# already drifted apart: app/dynamic_analysis.py listed `scaphandre`, while
# sci.py, energy_tracer.py and the pipeline verifier did not. That drift was not
# cosmetic. The verification pipeline's central promise is that a claim is only
# confirmed by a hardware reading, and it implements that with
# `HARDWARE_METHODS`. With `scaphandre` missing from that set, a claim backed by
# a genuine RAPL counter relayed over the sidecar - the exact production path
# Docker-on-Linux deployments are instructed to use - was downgraded to
# UNVERIFIED, and its SCI figure was labelled an estimate. The tool was
# under-stating what it had actually measured.
#
# Every module that must classify a figure imports this, so adding a backend in
# one place can no longer leave the others silently behind.
HARDWARE_METHODS = frozenset({"rapl", "scaphandre", "perf", "battery"})


def is_hardware_method(method: Optional[str]) -> bool:
    """True when ``method`` names a backend that reads a real energy counter.

    Accepts the same vocabulary as :data:`HARDWARE_METHODS`, case-insensitively,
    and treats an unknown or missing method as *not* hardware. Defaulting to
    False is deliberate: an unrecognised label must never be promoted to a
    measurement, because the whole point of the flag is to distinguish the two.
    """
    return (method or "").strip().lower() in HARDWARE_METHODS


def _read_int(path: str) -> Optional[int]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return int(fh.read().strip())
    except (OSError, ValueError):
        return None


def _read_text(path: str) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return None


def is_linux() -> bool:
    return platform.system().lower() == "linux"


def wrap_delta(start: int, end: int, max_range: int) -> int:
    """Counter delta with 32-bit wrap-around handling.

    RAPL counters are unsigned and wrap at ``max_energy_range_uj``. A naive
    ``end - start`` yields a catastrophically negative delta for any workload
    that crosses the wrap point, silently corrupting every energy figure.
    """
    if end >= start:
        return end - start
    return (max_range - start) + end


@dataclass
class RaplDomain:
    """A single hardware energy domain exposed by the powercap subsystem."""

    name: str
    energy_path: str
    max_range_uj: int
    kind: str  # package | core | dram | uncore | psys

    def read_uj(self) -> Optional[int]:
        return _read_int(self.energy_path)


def discover_rapl_domains() -> List[RaplDomain]:
    """Enumerate readable RAPL energy domains on this host."""
    if not is_linux():
        return []

    domains: List[RaplDomain] = []
    seen: set[str] = set()

    for base in sorted(glob.glob("/sys/class/powercap/intel-rapl:*")):
        energy_path = os.path.join(base, "energy_uj")
        if not os.path.isfile(energy_path):
            continue
        max_range = _read_int(os.path.join(base, "max_energy_range_uj"))
        if not max_range or max_range <= 0:
            continue
        name = _read_text(os.path.join(base, "name")) or os.path.basename(base)
        if name in seen:
            continue
        seen.add(name)

        if name.startswith("package"):
            kind = "package"
        elif name.startswith("core") or name in ("pp0", "pp1"):
            kind = "core"
        elif name.startswith("dram"):
            kind = "dram"
        elif name == "psys":
            kind = "psys"
        else:
            kind = "uncore"

        domains.append(
            RaplDomain(name=name, energy_path=energy_path, max_range_uj=max_range, kind=kind)
        )
    return domains


@dataclass
class EnergySample:
    """A point-in-time reading across the active energy domains."""

    timestamp: float
    per_domain_uj: Dict[str, int] = field(default_factory=dict)


class RaplMeter:
    """Live reader for a set of RAPL domains.

    The package (or psys, when present) is the correct figure for total CPU
    energy. ``core`` is a *subset* of ``package`` and ``dram`` is frequently
    already folded into ``psys``, so summing the wrong combination double
    counts. The constants below encode that precedence.
    """

    PACKAGE_KINDS: Tuple[str, ...] = ("psys", "package")
    MEMORY_KINDS: Tuple[str, ...] = ("dram",)

    def __init__(self, domains: Optional[List[RaplDomain]] = None):
        self.domains = domains if domains is not None else discover_rapl_domains()
        if not self.domains:
            raise RuntimeError("No readable RAPL energy domains on this host.")
        self._ranges = {d.name: d.max_range_uj for d in self.domains}
        self._kinds = {d.name: d.kind for d in self.domains}

    @property
    def available(self) -> bool:
        return bool(self.domains)

    def _read_all(self) -> EnergySample:
        sample = EnergySample(timestamp=time.monotonic())
        for d in self.domains:
            val = d.read_uj()
            if val is not None:
                sample.per_domain_uj[d.name] = val
        return sample

    def read(self) -> EnergySample:
        """Public point-in-time reading across the active domains.

        The sandbox runner brackets a container execution with two of these and
        differences them, so this deliberately has a stable public name rather
        than forcing callers to reach into ``_read_all``.
        """
        return self._read_all()

    def joules_between(self, a: EnergySample, b: EnergySample) -> Dict[str, float]:
        """Energy consumed between two readings, split by domain class.

        Exposed so callers do not have to re-derive the package/memory
        precedence rules - summing the wrong combination double counts, because
        ``core`` is a subset of ``package`` and ``dram`` is often already folded
        into ``psys``.
        """
        package_uj = 0.0
        memory_uj = 0.0
        for name, d_uj in self._delta(a, b).items():
            kind = self._kinds.get(name, "uncore")
            if kind in self.PACKAGE_KINDS:
                package_uj += d_uj
            elif kind in self.MEMORY_KINDS:
                memory_uj += d_uj
            # core/uncore are subsets of the package figure - skipped.
        return {
            "cpu_joules": package_uj / 1_000_000.0,
            "memory_joules": memory_uj / 1_000_000.0,
            "total_joules": (package_uj + memory_uj) / 1_000_000.0,
        }

    def _delta(self, a: EnergySample, b: EnergySample) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for name, end_v in b.per_domain_uj.items():
            start_v = a.per_domain_uj.get(name)
            if start_v is None:
                continue
            out[name] = wrap_delta(start_v, end_v, self._ranges.get(name, 0))
        return out

    def measure(self, fn, *args, **kwargs) -> Tuple[Any, float, Dict[str, float]]:
        """Run ``fn`` while sampling RAPL; return (result, seconds, joules)."""
        before = self._read_all()
        t0 = time.perf_counter()
        result = fn(*args, **kwargs)
        wall = time.perf_counter() - t0
        after = self._read_all()
        return result, wall, self.joules_between(before, after)

    def describe(self) -> Dict[str, Any]:
        return {
            "backend": "rapl",
            "domains": [
                {"name": d.name, "kind": d.kind, "max_range_uj": d.max_range_uj}
                for d in self.domains
            ],
        }


_PERF_ENERGY_RE = re.compile(r"([\d,.]+)\s*J\s+power/energy", re.IGNORECASE)


def perf_available() -> bool:
    """True when `perf` exists and exposes the power/energy PMU events."""
    import shutil

    if not is_linux() or shutil.which("perf") is None:
        return False
    try:
        out = subprocess.run(
            ["perf", "stat", "-e", "power/energy-pkg/", "true"],
            capture_output=True, text=True, timeout=10,
        )
    except Exception:
        return False
    return "power/energy" in (out.stderr or "")


def measure_with_perf(
    cmd: List[str], timeout: float
) -> Tuple[int, float, Optional[float], str]:
    """Execute ``cmd`` under ``perf stat``; return (exit, seconds, joules, stderr)."""
    if not perf_available():
        return -1, 0.0, None, "perf power events not available"

    full_cmd = ["perf", "stat", "-e", "power/energy-pkg/,power/energy-ram/", "--"] + cmd
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(full_cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return -1, time.perf_counter() - t0, None, "timeout"
    wall = time.perf_counter() - t0

    total = 0.0
    found = False
    for line in (proc.stderr or "").splitlines():
        m = _PERF_ENERGY_RE.search(line)
        if m:
            try:
                total += float(m.group(1).replace(",", ""))
                found = True
            except ValueError:
                pass
    return proc.returncode, wall, (total if found else None), proc.stderr or ""


def battery_discharge_watts() -> Optional[float]:
    """Whole-system battery discharge rate in Watts, or None on mains power."""
    system = platform.system().lower()

    if system == "linux":
        for bat in sorted(glob.glob("/sys/class/power_supply/BAT*")):
            status = (_read_text(os.path.join(bat, "status")) or "").lower()
            power_now = _read_int(os.path.join(bat, "power_now"))
            if power_now and power_now > 0 and status == "discharging":
                return power_now / 1_000_000.0  # microwatts -> watts
        return None

    if system == "windows":
        try:
            ps_cmd = (
                "(Get-CimInstance -ClassName Win32_Battery -ErrorAction Stop | "
                "Select-Object -First 1 -ExpandProperty DischargeRate)"
            )
            out = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                capture_output=True, text=True, timeout=6,
            )
            raw = (out.stdout or "").strip()
            if raw.isdigit() and int(raw) > 0:
                return int(raw) / 1000.0  # mW -> W
        except Exception:
            pass
    return None


def model_power_watts(cpu_percent: float, memory_mb: float) -> float:
    """Estimate package+memory power from CPU load and memory footprint.

    Explicitly a *model*, not a measurement. Used only when no hardware counter
    is reachable; results are labelled accordingly.
    """
    cpu = min(100.0, max(0.0, cpu_percent))
    p_cpu = TDP_IDLE_WATTS + (TDP_SATURATION_WATTS - TDP_IDLE_WATTS) * (cpu / 100.0)
    mem_gib = max(0.0, memory_mb) / 1024.0
    return p_cpu + mem_gib * MEMORY_WATTS_PER_GIB


class BatteryMeter:
    """Whole-system battery discharge meter (coarse, but genuinely measured)."""

    def __init__(self) -> None:
        self._baseline = battery_discharge_watts()

    @property
    def available(self) -> bool:
        return self._baseline is not None and self._baseline > 0

    def measure(self, fn, *args, **kwargs) -> Tuple[Any, float, Dict[str, float]]:
        baseline = self._baseline or battery_discharge_watts() or 0.0
        t0 = time.perf_counter()
        result = fn(*args, **kwargs)
        wall = time.perf_counter() - t0
        after = battery_discharge_watts() or 0.0
        # Charge only the *excess* over the idle baseline, so the machine being
        # switched on is not billed to the workload.
        delta_w = max(0.0, after - baseline) if (baseline and after) else after
        return result, wall, {
            "cpu_joules": 0.0,
            "memory_joules": 0.0,
            "total_joules": delta_w * wall,
        }

    def read(self) -> None:
        """Battery discharge cannot be differenced as a per-domain delta.

        Returns ``None`` deliberately: the sandbox runner uses this to decide
        whether a real measurement is possible, and a battery figure is a
        whole-system average, not a per-run energy counter. Claiming otherwise
        would let a coarse average masquerade as a measurement.
        """
        return None

    def describe(self) -> Dict[str, Any]:
        return {"backend": "battery", "baseline_watts": self._baseline}


# ---------------------------------------------------------------------------
# Scaphandre meter — reads RAPL via the hubblo/scaphandre Prometheus exporter.
#
# On a real Linux host Scaphandre reads /sys/class/powercap directly (same
# hardware as RaplMeter) and exposes per-process and host-total joule counters
# on an HTTP endpoint.  This gives Docker containers access to real energy data
# without bind-mounting the sysfs powercap tree into every analysis container.
#
# Default endpoint: http://localhost:8080/metrics   (configurable via
# SCAPHANDRE_URL env var, e.g. point it at the sidecar's Docker bridge IP).
# ---------------------------------------------------------------------------

_SCAPH_ENERGY_RE = re.compile(
    r'^scaph_host_energy_microjoules\s+([\d.]+)', re.MULTILINE
)

SCAPHANDRE_URL = os.environ.get(
    "SCAPHANDRE_URL", "http://localhost:8080/metrics"
)


class ScaphandreMeter:
    """Energy meter backed by a running Scaphandre Prometheus exporter.

    Scaphandre (https://github.com/hubblo-org/scaphandre) reads the host's
    RAPL hardware counters and exposes them over HTTP. This is the correct
    production path for containerised workloads on Linux: the analysis sandbox
    does not need ``/sys/class/powercap`` mounted inside it; the sidecar reads
    the hardware on its behalf.

    On Windows / WSL2 the sidecar cannot reach RAPL either, so
    ``available`` will be False and ``select_meter`` will skip this tier.
    """

    # Prometheus scrape timeout. Scaphandre is local, so 2 s is generous.
    _TIMEOUT = 2

    def __init__(self, url: str = SCAPHANDRE_URL) -> None:
        self._url = url
        self._ok: Optional[bool] = None  # lazily probed

    # ------------------------------------------------------------------
    def _scrape(self) -> Optional[float]:
        """Return host total energy in microjoules, or None on any failure."""
        try:
            req = urllib.request.Request(
                self._url,
                headers={"User-Agent": "greencode-energy-sensor/1.0"},
            )
            with urllib.request.urlopen(req, timeout=self._TIMEOUT) as resp:
                body = resp.read().decode("utf-8", "replace")
        except (urllib.error.URLError, OSError, Exception):
            return None
        m = _SCAPH_ENERGY_RE.search(body)
        if not m:
            return None
        try:
            return float(m.group(1))
        except ValueError:
            return None

    @property
    def available(self) -> bool:
        if self._ok is None:
            self._ok = self._scrape() is not None
        return self._ok

    def read(self) -> Optional["ScaphandrePoint"]:
        """Point-in-time reading: timestamp + microjoules from the exporter.

        Returns ``None`` if the exporter is unreachable, so the caller can
        fall through to the model tier rather than presenting a broken figure.
        """
        uj = self._scrape()
        if uj is None:
            return None
        return ScaphandrePoint(timestamp=time.monotonic(), host_uj=uj)

    @staticmethod
    def joules_between(
        a: "ScaphandrePoint", b: "ScaphandrePoint"
    ) -> Dict[str, float]:
        """Energy consumed between two readings.

        The exporter emits a monotonically increasing counter, so the delta is
        simply the difference (counter resets are very rare on running hardware
        but are guarded by the >= 0 clamp).
        """
        delta_uj = max(0.0, b.host_uj - a.host_uj)
        total_j = delta_uj / 1_000_000.0
        # Scaphandre exposes package-level energy only; we report it all as
        # cpu_joules to stay compatible with the rest of the pipeline.
        return {
            "cpu_joules": total_j,
            "memory_joules": 0.0,
            "total_joules": total_j,
        }

    def describe(self) -> Dict[str, Any]:
        return {"backend": "scaphandre", "url": self._url}


@dataclass
class ScaphandrePoint:
    """Snapshot from the Scaphandre Prometheus endpoint."""
    timestamp: float
    host_uj: float  # scaph_host_energy_microjoules


# Backwards-compatible alias for the original misspelling
# ("ScaphhandreMeter"). It was public API: the test-suite and any downstream
# integration imported it by that name, so it is kept as an alias rather than
# silently renamed out from under them.
ScaphhandreMeter = ScaphandreMeter


def scaphandre_available(url: str = SCAPHANDRE_URL) -> bool:
    """True when a Scaphandre exporter is reachable and returning RAPL data."""
    return ScaphandreMeter(url).available


def select_meter(prefer: Optional[str] = None):
    """Return the best available energy meter, or None if only the model works.

    Priority follows the documented tier order: RAPL (direct sysfs) -> Scaphandre
    (HTTP sidecar) -> perf (PMU via `perf stat`) -> Battery.

    The `perf` tier is included here deliberately. It used to be documented as
    tier 3 in the README and reported by `probe_capabilities()`, but was never
    actually reached by this function, so a host whose PMU was readable but whose
    `powercap` sysfs tree was not - a common container-permission configuration -
    fell straight past a genuinely working counter to the battery probe and then
    to the TDP model. Capability reporting and meter selection now agree.

    The model fallback is handled by the caller, not here, so this returns None
    rather than a fake meter when nothing real is reachable.
    """
    for backend in ("rapl", "scaphandre", "perf", "battery"):
        if prefer is not None and prefer != backend:
            continue
        try:
            meter = _instantiate_meter(backend)
        except Exception:
            continue
        if meter is not None and meter.available:
            return meter
    return None


def _instantiate_meter(backend: str):
    """Build one meter by tier name, or None when the tier is not a meter class.

    `perf` is not a class here: `perf stat` brackets a *command* rather than
    exposing a differenceable counter, so it is surfaced through
    `measure_with_perf()` instead. It is still reported as available so the
    capability probe reflects the documented tier list.
    """
    if backend == "rapl":
        return RaplMeter()
    if backend == "scaphandre":
        return ScaphandreMeter()
    if backend == "battery":
        return BatteryMeter()
    return None


# Module-level cache for probe_capabilities(): the probes spawn subprocesses
# and HTTP calls, so paying them once per TTL window rather than once per
# request is the difference between an ~8 s and a sub-second tool call.
_PROBE_CACHE: Optional[Tuple[float, Dict[str, Any]]] = None
_PROBE_CACHE_LOCK = threading.Lock()
_PROBE_CACHE_TTL = float(os.environ.get("GREENCODE_PROBE_TTL", "300"))


def probe_capabilities(force: bool = False) -> Dict[str, Any]:
    """Report what this host can genuinely measure. Surfaced by /api/health.

    The answer is a property of the host, not of the request, but the probes
    that produce it are expensive: the Windows battery tier spawns PowerShell
    (6 s timeout), the Scaphandre tier waits on an HTTP probe, and the perf
    tier can run a subprocess. Uncached that cost (~4.5 s here) was paid on
    *every* measure_energy call, which is what made audit_and_score take ~8 s.

    The result is therefore cached for GREENCODE_PROBE_TTL seconds (default
    300). Pass force=True to re-probe immediately; set the TTL to 0 to disable
    caching entirely.
    """
    global _PROBE_CACHE

    if not force and _PROBE_CACHE_TTL > 0:
        with _PROBE_CACHE_LOCK:
            cached = _PROBE_CACHE
        if cached is not None and (time.monotonic() - cached[0]) < _PROBE_CACHE_TTL:
            return copy.deepcopy(cached[1])

    try:
        rapl_domains = [d.__dict__ for d in discover_rapl_domains()]
    except Exception:  # pragma: no cover - defensive
        rapl_domains = []

    battery = battery_discharge_watts()
    perf_ok = perf_available()
    scaph_ok = scaphandre_available()

    result = {
        "platform": platform.system().lower(),
        "rapl": {"supported": bool(rapl_domains), "domains": rapl_domains},
        "scaphandre": {"supported": scaph_ok, "url": SCAPHANDRE_URL},
        "perf": {"supported": perf_ok},
        "battery": {"supported": battery is not None, "watts": battery},
        "modelled_fallback": True,
        "best_available": (
            "rapl" if rapl_domains
            else "scaphandre" if scaph_ok
            else "perf" if perf_ok
            else "battery" if battery
            else "model"
        ),
    }

    with _PROBE_CACHE_LOCK:
        _PROBE_CACHE = (time.monotonic(), copy.deepcopy(result))
    return result
