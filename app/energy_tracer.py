"""Per-function energy attribution via CPython tracing hooks.

This is the dynamic-analysis half of the tool: rather than only reporting one
total for a whole process, it attributes measured energy to the individual
functions that consumed it.

The technique follows CodeGreen: a background sampler reads the hardware energy
counter on a fixed interval, while ``sys.settrace`` emits cheap (~100-200 ns)
call/return events. The two timelines are correlated - energy read between a
function's call and return is attributed to that function.

Why a tracer instead of per-function counters:
- Hardware energy counters are per-socket, not per-thread or per-function. There
  is no way to ask the CPU "how many joules did this function cost".
- A sampler thread polling the counter *is* the standard way to get a time
  series, and call/return events are the standard way to slice it.

Caveats handled explicitly rather than hidden:
- Sampling resolution bounds attribution granularity. A function running
  between two samples inherits whatever energy was read across that window.
- Self time (excluding callees) is computed by subtracting child time, so both
  self and total are reported.
"""

from __future__ import annotations

import os
import sys
import sysconfig
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.energy_sensors import is_hardware_method

# Path fragments whose frames must never be billed to the user's code.
_EXCLUDED_PATH_PARTS = (
    "site-packages",
    "dist-packages",
    "__pycache__",
    "importlib",
    "encodings",
)


def _stdlib_roots() -> Tuple[str, ...]:
    """Directories holding the standard library for this interpreter."""
    roots = []
    for key in ("stdlib", "platstdlib"):
        try:
            path = sysconfig.get_path(key)
            if path:
                roots.append(os.path.realpath(path))
        except Exception:
            pass
    try:
        roots.append(os.path.realpath(os.path.dirname(os.__file__)))
    except Exception:
        pass
    return tuple(r for r in roots if r)


_STDLIB_ROOTS = _stdlib_roots()
_TRACER_DIR = os.path.dirname(os.path.realpath(__file__))


def _is_user_frame(filename: str, include_paths: Optional[Tuple[str, ...]]) -> bool:
    """True when a frame belongs to code the caller asked us to measure.

    Frames from the standard library, installed packages and the import system
    are excluded by default: attributing their energy to the user's functions
    would be actively misleading. Passing ``include_paths`` narrows measurement
    further, to an explicit set of project roots.

    The tracer's own module is also excluded, because ``_stop_sampler`` and
    ``_report`` run while tracing is still active - otherwise the measurement
    bills its own bookkeeping to the workload and pollutes the ranking.
    """
    if not filename or filename.startswith("<"):
        return False
    norm = os.path.realpath(filename).replace("\\", "/")
    if any(part in norm for part in _EXCLUDED_PATH_PARTS):
        return False
    if norm.startswith(_TRACER_DIR.replace("\\", "/")):
        return False
    for root in _STDLIB_ROOTS:
        if norm.startswith(root.replace("\\", "/")):
            return False
    if include_paths:
        return any(norm.startswith(p.replace("\\", "/")) for p in include_paths)
    return True



@dataclass
class FrameKey:
    """Identifies a function by qualified name and location."""

    qualified_name: str
    filename: str
    lineno: int

    @property
    def key(self) -> str:
        return f"{self.filename}:{self.lineno}:{self.qualified_name}"


@dataclass
class FunctionEnergy:
    """Accumulated dynamic statistics for one function."""

    qualified_name: str
    filename: str
    lineno: int
    calls: int = 0
    total_seconds: float = 0.0
    self_seconds: float = 0.0
    joules: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "qualified_name": self.qualified_name,
            "file": self.filename,
            "line": self.lineno,
            "calls": self.calls,
            "total_ms": round(self.total_seconds * 1000.0, 3),
            "self_ms": round(self.self_seconds * 1000.0, 3),
            "joules": round(self.joules, 6),
        }


class EnergyTracer:
    """Correlate a hardware energy sampler with CPython call/return events.

    Usage::

        tracer = EnergyTracer()
        result, report = tracer.run(fn, *args)

    The tracer is safe to use repeatedly; each ``run`` resets the accumulators.
    """

    def __init__(
        self,
        interval: float = 0.005,
        include_paths: Optional[Tuple[str, ...]] = None,
        max_functions: int = 500,
    ):
        self.interval = max(0.001, interval)
        self.include_paths = include_paths
        self.max_functions = max_functions

        self._lock = threading.Lock()
        self._functions: Dict[str, FunctionEnergy] = {}
        # Each entry: (FrameKey | None, start_time, child_seconds)
        self._stack: List[Tuple[Optional[FrameKey], float, float]] = []
        self._energy_timeline: List[Tuple[float, float]] = []
        self._sampler: Optional[threading.Thread] = None
        self._sampling = False
        self._total_joules: float = 0.0
        self._stop = threading.Event()
        self._meter: Any = None

    # -- energy sampling ---------------------------------------------------
    def _start_sampler(self) -> None:
        self._sampling = True
        self._stop.clear()
        self._energy_timeline = [(time.perf_counter(), 0.0)]

        def _pump() -> None:
            while not self._stop.wait(self.interval):
                if self._meter is None:
                    continue
                try:
                    _, _, joules = self._meter.measure(lambda: None)
                    self._energy_timeline.append((time.perf_counter(), joules["total_joules"]))
                    self._total_joules += joules["total_joules"]
                except Exception:
                    # A failed counter read must never abort the workload.
                    continue

        self._sampler = threading.Thread(target=_pump, name="greencode-energy", daemon=True)
        self._sampler.start()

    def _stop_sampler(self) -> None:
        self._stop.set()
        if self._sampler is not None:
            self._sampler.join(timeout=2.0)
            self._sampler = None
        self._sampling = False

    def _energy_between(self, t_start: float, t_end: float) -> float:
        """Linearly interpolate the sampler timeline across [t_start, t_end].

        With a single sample there is no rate to infer, so nothing is charged.
        Otherwise the piecewise-linear curve is integrated, which is an honest
        interpolation of what was actually measured.
        """
        if len(self._energy_timeline) < 2:
            return 0.0

        t0, e0 = self._energy_timeline[0]
        t1, e1 = self._energy_timeline[-1]
        if t1 <= t0:
            return 0.0
        if t_end <= t0:
            return 0.0
        if t_start >= t1:
            return e1 - e0

        acc = 0.0
        timeline = self._energy_timeline
        for (ta, ea), (tb, eb) in zip(timeline, timeline[1:]):
            seg_start, seg_end = max(ta, t_start), min(tb, t_end)
            if seg_end <= seg_start:
                continue
            span = tb - ta
            if span <= 0:
                continue
            acc += ((eb - ea) / span) * (seg_end - seg_start)
        return acc

    # -- tracing hooks -----------------------------------------------------
    def _global_trace(self, frame, event, arg):  # noqa: ANN001
        if not self._sampling:
            return None
        if event != "call":
            return self._local_trace

        filename = frame.f_code.co_filename
        if _is_user_frame(filename, self.include_paths):
            fk: Optional[FrameKey] = FrameKey(
                frame.f_code.co_qualname, filename, frame.f_lineno
            )
        else:
            # Still push a frame so returns stay balanced, but do not bill it.
            fk = None
        self._stack.append((fk, time.perf_counter(), 0.0))
        return self._local_trace

    def _local_trace(self, frame, event, arg):  # noqa: ANN001
        if event == "return":
            self._on_return()
        return self._local_trace

    def _on_return(self) -> None:
        if not self._stack:
            return
        fk, start, child_seconds = self._stack.pop()
        elapsed = time.perf_counter() - start

        if self._stack:
            # Credit elapsed time to the parent's child-time accumulator so that
            # self time can be derived as total minus children.
            pfk, pstart, pchild = self._stack[-1]
            self._stack[-1] = (pfk, pstart, pchild + elapsed)

        if fk is None:
            return

        joules = self._energy_between(start, start + elapsed)
        with self._lock:
            rec = self._functions.get(fk.key)
            if rec is None:
                if len(self._functions) >= self.max_functions:
                    return
                rec = FunctionEnergy(fk.qualified_name, fk.filename, fk.lineno)
                self._functions[fk.key] = rec
            rec.calls += 1
            rec.total_seconds += elapsed
            rec.self_seconds += max(0.0, elapsed - child_seconds)
            rec.joules += joules

    # -- public API --------------------------------------------------------
    def run(self, fn: Callable, *args, **kwargs) -> Tuple[Any, Dict[str, Any]]:
        """Execute ``fn`` with tracing and energy sampling enabled."""
        from app.energy_sensors import select_meter

        self._meter = select_meter()
        self._start_sampler()

        prev_trace = sys.gettrace()
        prev_profile = sys.getprofile()
        try:
            sys.settrace(self._global_trace)
        except Exception:
            prev_trace = None

        t0 = time.perf_counter()
        error: Optional[str] = None
        result: Any = None
        try:
            result = fn(*args, **kwargs)
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
        wall = time.perf_counter() - t0

        self._stop_sampler()
        try:
            sys.settrace(prev_trace)
            sys.setprofile(prev_profile)
        except Exception:
            pass
        finally:
            self._stack.clear()

        return result, self._report(wall, error)

    def _report(self, wall: float, error: Optional[str]) -> Dict[str, Any]:
        with self._lock:
            all_functions = list(self._functions.values())

        backend = self._meter.describe().get("backend", "model") if self._meter else "model"
        is_hardware = is_hardware_method(backend)

        # With a hardware counter, energy is the meaningful ranking key. Without
        # one every joules figure is 0.0 and ranking by it would return an
        # arbitrary order, so fall back to self time.
        if is_hardware and self._total_joules > 0:
            ordered = sorted(all_functions, key=lambda f: f.joules, reverse=True)
            rank_by = "energy"
        else:
            ordered = sorted(all_functions, key=lambda f: f.self_seconds, reverse=True)
            rank_by = "self_time"

        return {
            "wall_seconds": round(wall, 6),
            "sampler_interval_ms": round(self.interval * 1000.0, 3),
            "samples": len(self._energy_timeline),
            "measurement_method": backend,
            "measurement_is_hardware": is_hardware,
            "ranked_by": rank_by,
            "total_joules": round(self._total_joules, 6),
            "error": error,
            "hotspots": [f.to_dict() for f in ordered[:50]],
            "unique_functions": len(ordered),
        }

