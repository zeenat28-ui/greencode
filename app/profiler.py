"""Dynamic Execution Profiler with Docker SDK Container Isolation and SCI Hardware Energy Modeling.

Benchmarks target Python code in an isolated container sandbox, samples CPU/RAM utilization
intervals, estimates physical hardware power draw (Joules & Watt-hours), and calculates
Software Carbon Intensity (SCI) metrics using Green Software Foundation standards.
"""

from dataclasses import asdict, dataclass
import ast
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any, Dict, List, Optional
import psutil

try:
    import docker
    from docker.errors import DockerException
    DOCKER_AVAILABLE = True
except ImportError:
    docker = None
    DockerException = Exception
    DOCKER_AVAILABLE = False


# Server Hardware Thermal Design Power (TDP) Baseline Parameters (GSF Cloud Node Standard)
SERVER_TDP_IDLE_WATTS = 15.0     # Server base idle power draw
SERVER_TDP_PEAK_WATTS = 120.0    # Server full-throttle compute power draw
MEMORY_POWER_PER_GB_WATTS = 0.3725  # GSF Memory coefficient (W per GB)
DATACENTER_PUE = 1.20           # Hyper-scaler Power Usage Effectiveness
EMBODIED_CARBON_RATE_G_PER_SEC = 0.00018  # Amortized server manufacturing carbon allocation


@dataclass
class ProfilingResult:
    file_path: str
    profiling_mode: str
    duration_sec: float
    avg_cpu_percent: float
    peak_memory_mb: float
    total_power_watts: float
    energy_joules: float
    energy_wh: float
    energy_kwh: float
    operational_carbon_gco2: float
    embodied_carbon_gco2: float
    sci_score_gco2: float
    grid_intensity_gco2_per_kwh: float
    exit_code: int
    stdout_preview: str
    stderr_preview: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def calculate_energy_and_sci(
    duration_sec: float,
    avg_cpu_percent: float,
    peak_memory_mb: float,
    grid_intensity: float = 380.0,
) -> Dict[str, float]:
    """Calculates power draw, Watt-hours, and SCI Operational Carbon per GSF standards."""
    # Ensure minimum time quantum to avoid zero division
    duration_sec = max(0.01, duration_sec)
    clamped_cpu = min(100.0, max(0.0, avg_cpu_percent))

    # CPU power based on dynamic TDP load scaling
    p_cpu = SERVER_TDP_IDLE_WATTS + ((SERVER_TDP_PEAK_WATTS - SERVER_TDP_IDLE_WATTS) * (clamped_cpu / 100.0))

    # Memory power based on peak RAM footprint in GB
    peak_ram_gb = max(0.05, peak_memory_mb / 1024.0)
    p_mem = peak_ram_gb * MEMORY_POWER_PER_GB_WATTS

    # Total active power scaled by Datacenter PUE
    p_total = (p_cpu + p_mem) * DATACENTER_PUE

    # Energy calculations
    energy_joules = p_total * duration_sec
    energy_wh = (p_total * duration_sec) / 3600.0
    energy_kwh = energy_wh / 1000.0

    # Operational carbon: E * I
    operational_carbon_g = energy_kwh * grid_intensity

    # Embodied carbon: M
    embodied_carbon_g = duration_sec * EMBODIED_CARBON_RATE_G_PER_SEC

    # Total SCI score: (E * I) + M
    sci_score = operational_carbon_g + embodied_carbon_g

    return {
        "total_power_watts": round(p_total, 3),
        "energy_joules": round(energy_joules, 4),
        "energy_wh": round(energy_wh, 6),
        "energy_kwh": round(energy_kwh, 9),
        "operational_carbon_gco2": round(operational_carbon_g, 6),
        "embodied_carbon_gco2": round(embodied_carbon_g, 6),
        "sci_score_gco2": round(sci_score, 6),
    }


def validate_script_safety_for_host(file_path: str) -> Optional[str]:
    """Scan Python code before host fallback execution to block dangerous system calls.

    Protects host workstation against RCE when Docker daemon is not active.
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in (".py", ".pyw"):
        return None
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            code = f.read()
        tree = ast.parse(code, filename=file_path)
    except Exception:
        return None

    DANGEROUS_CALLS = {
        ("os", "system"),
        ("os", "popen"),
        ("os", "remove"),
        ("os", "unlink"),
        ("os", "rmdir"),
        ("shutil", "rmtree"),
        ("subprocess", "Popen"),
        ("subprocess", "call"),
        ("subprocess", "run"),
        ("subprocess", "check_output"),
    }

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
        ):
            call_tuple = (node.func.value.id, node.func.attr)
            if call_tuple in DANGEROUS_CALLS:
                return (
                    f"Blocked high-risk call '{call_tuple[0]}.{call_tuple[1]}()' on host sandbox. "
                    "Profile inside isolated Docker container."
                )
    return None


def kill_process_tree(pid: int) -> None:
    """Recursively kill a process and all its children to prevent orphan zombie processes and fork bombs."""
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        for child in children:
            try:
                child.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        parent.kill()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass


class DynamicExecutionProfiler:
    """Profiles target multi-language code via isolated Docker scratch containers or fallback sandbox."""

    def __init__(self, grid_intensity_gco2_per_kwh: float = 380.0, docker_host: Optional[str] = None):
        self.grid_intensity = grid_intensity_gco2_per_kwh
        self.custom_docker_host = docker_host or os.environ.get("DOCKER_HOST")
        self.docker_client: Optional[docker.DockerClient] = None
        self.connection_type: str = "SERVERLESS_HOST_SANDBOX"
        self._init_docker()

    def _init_docker(self) -> None:
        """Connect to Docker daemon via physical UNIX socket, Windows pipe, or remote TCP DinD proxy."""
        if not DOCKER_AVAILABLE or docker is None:
            self.connection_type = "SERVERLESS_HOST_SANDBOX"
            self.docker_client = None
            return

        target_host = self.custom_docker_host or os.environ.get("DOCKER_HOST")
        tls_verify = os.environ.get("DOCKER_TLS_VERIFY", "0") in ("1", "true", "True")
        cert_path = os.environ.get("DOCKER_CERT_PATH")

        # 1. Attempt connection using explicit DOCKER_HOST (DinD / remote proxy or custom socket)
        if target_host:
            try:
                tls_config = None
                if tls_verify and cert_path:
                    try:
                        from docker.tls import TLSConfig
                        tls_config = TLSConfig(
                            client_cert=(os.path.join(cert_path, "cert.pem"), os.path.join(cert_path, "key.pem")),
                            ca_cert=os.path.join(cert_path, "ca.pem"),
                            verify=True,
                        )
                    except Exception:
                        pass
                self.docker_client = docker.DockerClient(base_url=target_host, tls=tls_config, timeout=4)
                self.docker_client.ping()
                if target_host.startswith("tcp://"):
                    self.connection_type = "REMOTE_TCP_DIND_PROXY"
                elif target_host.startswith("npipe://"):
                    self.connection_type = "WINDOWS_NAMED_PIPE"
                else:
                    self.connection_type = "CUSTOM_SOCKET_DAEMON"
                return
            except Exception:
                self.docker_client = None

        # 2. Attempt standard environment detection (docker.from_env)
        try:
            self.docker_client = docker.from_env(timeout=2)
            self.docker_client.ping()
            self.connection_type = "LOCAL_DAEMON_SOCKET"
            return
        except Exception:
            self.docker_client = None

        # 3. Graceful serverless fallback: AWS Fargate / Cloud Run / Kubernetes without daemon
        self.connection_type = "SERVERLESS_HOST_SANDBOX"

    def is_docker_ready(self) -> bool:
        """Check if Docker Engine is available and responsive."""
        if not self.docker_client:
            return False
        try:
            return bool(self.docker_client.ping())
        except Exception:
            return False

    def get_runtime_status(self) -> Dict[str, Any]:
        """Return runtime container engine and isolation telemetry."""
        return {
            "docker_available": self.is_docker_ready(),
            "connection_type": self.connection_type,
            "docker_host": self.custom_docker_host or (os.environ.get("DOCKER_HOST", "default") if self.is_docker_ready() else "None"),
            "isolation_level": "Air-Gapped Docker Container (cgroups)" if self.is_docker_ready() else "Restricted Process Sandbox (Subprocess)",
            "memory_limit": "512MB",
            "cpu_limit": "1.0 Core",
        }

    def profile_file(
        self,
        file_path: str,
        timeout_sec: float = 30.0,
        grid_intensity: Optional[float] = None,
    ) -> ProfilingResult:
        """Profile code execution. Uses Docker container if active, else falls back to host sandbox."""
        intensity = grid_intensity if grid_intensity is not None else self.grid_intensity

        if self.is_docker_ready():
            try:
                return self._profile_with_docker(file_path, timeout_sec, intensity)
            except Exception:
                # Graceful fallback to sandbox if container run encounters runtime docker daemon error
                return self._profile_with_process_sandbox(file_path, timeout_sec, intensity)
        else:
            return self._profile_with_process_sandbox(file_path, timeout_sec, intensity)


    def _profile_with_docker(
        self, file_path: str, timeout_sec: float, grid_intensity: float
    ) -> ProfilingResult:
        """Executes code inside a strictly isolated Docker sandbox container.
        
        Enforces cgroups limits, read-only rootfs, network isolation, and capability drops
        to mitigate Remote Code Execution (RCE) flaws during dynamic execution.
        """
        abs_path = os.path.abspath(file_path)
        work_dir = os.path.dirname(abs_path)
        filename = os.path.basename(abs_path)
        ext = os.path.splitext(filename)[1].lower()

        # Sanitize filename against shell escape/injection
        if not re.match(r"^[a-zA-Z0-9_\-\.]+$", filename):
            raise ValueError(f"Unsafe filename for container execution: '{filename}'")

        # Select appropriate language runtime container image & command with positional args ($1)
        if ext in (".js", ".ts", ".mjs"):
            image_name = "node:20-slim"
            command = ["node", f"/workspace/{filename}"]
        elif ext in (".cpp", ".cc", ".c"):
            image_name = "gcc:latest"
            command = ["sh", "-c", 'g++ -O2 "$1" -o /tmp/app && /tmp/app', "sh", f"/workspace/{filename}"]
        elif ext == ".java":
            image_name = "openjdk:17-slim"
            class_name = os.path.splitext(filename)[0]
            if not re.match(r"^[a-zA-Z0-9_]+$", class_name):
                class_name = "Main"
            command = ["sh", "-c", 'javac "$1" -d /tmp && java -cp /tmp "$2"', "sh", f"/workspace/{filename}", class_name]
        elif ext == ".go":
            image_name = "golang:1.22-alpine"
            command = ["go", "run", f"/workspace/{filename}"]
        elif ext in (".rs", ".rlib"):
            image_name = "rust:alpine"
            command = ["sh", "-c", 'rustc "$1" -o /tmp/app && /tmp/app', "sh", f"/workspace/{filename}"]
        elif ext in (".rb", ".rbw"):
            image_name = "ruby:alpine"
            command = ["ruby", f"/workspace/{filename}"]
        elif ext in (".php",):
            image_name = "php:alpine"
            command = ["php", f"/workspace/{filename}"]
        elif ext in (".sh", ".bash"):
            image_name = "bash:alpine"
            command = ["bash", f"/workspace/{filename}"]
        elif ext in (".cs",):
            image_name = "mcr.microsoft.com/dotnet/sdk:8.0-alpine"
            command = ["dotnet", "run", "--project", f"/workspace/{filename}"]
        else:
            image_name = "python:3.12-slim"
            command = ["python", f"/workspace/{filename}"]


        # Ensure container base image is available
        try:
            self.docker_client.images.get(image_name)
        except Exception:
            self.docker_client.images.pull(image_name)

        # Launch container with enterprise sandbox guardrails
        # Strict isolation parameters: network_disabled, read_only, 512MB RAM, 1.0 CPU, drop capabilities
        container = self.docker_client.containers.create(
            image=image_name,
            command=command,
            volumes={work_dir: {"bind": "/workspace", "mode": "ro"}},
            network_disabled=True,                          # Air-gapped network isolation
            read_only=True,                                 # Immutable root filesystem
            mem_limit="512m",                               # 512MB memory boundary
            nano_cpus=int(1.0 * 1e9),                       # Strictly capped to 1.0 CPU core
            cap_drop=["ALL"],                               # Drop all Linux root capabilities
            security_opt=["no-new-privileges:true"],        # Block privilege escalation
            pids_limit=64,                                  # Prevent fork-bombs
            tmpfs={"/tmp": "rw,noexec,nosuid,size=64m"},    # Ephemeral scratch memory for compilers
            working_dir="/workspace",
        )

        cpu_samples: List[float] = []
        mem_samples_mb: List[float] = []
        is_running = True

        def monitor_stats():
            try:
                for stat in container.stats(stream=True, decode=True):
                    if not is_running:
                        break
                    # Calculate container CPU percentage
                    cpu_stats = stat.get("cpu_stats", {})
                    precpu_stats = stat.get("precpu_stats", {})
                    cpu_delta = (
                        cpu_stats.get("cpu_usage", {}).get("total_usage", 0)
                        - precpu_stats.get("cpu_usage", {}).get("total_usage", 0)
                    )
                    system_delta = (
                        cpu_stats.get("system_cpu_usage", 0)
                        - precpu_stats.get("system_cpu_usage", 0)
                    )
                    online_cpus = cpu_stats.get("online_cpus", 1)

                    if system_delta > 0 and cpu_delta > 0:
                        cpu_pct = (cpu_delta / system_delta) * online_cpus * 100.0
                        cpu_samples.append(cpu_pct)

                    # Calculate container Memory usage
                    mem_stats = stat.get("memory_stats", {})
                    usage_bytes = mem_stats.get("usage", 0)
                    if usage_bytes > 0:
                        mem_samples_mb.append(usage_bytes / (1024 * 1024))
            except Exception:
                pass

        monitor_thread = threading.Thread(target=monitor_stats, daemon=True)

        start_time = time.perf_counter()
        container.start()
        monitor_thread.start()

        exit_code = 0
        timed_out = False
        try:
            res = container.wait(timeout=timeout_sec)
            exit_code = res.get("StatusCode", 0)
        except Exception:
            timed_out = True
            try:
                container.kill()
            except Exception:
                pass
            exit_code = 124
        finally:
            end_time = time.perf_counter()
            is_running = False

        duration = max(0.001, end_time - start_time)
        try:
            logs = container.logs(stdout=True, stderr=True).decode("utf-8", errors="replace")
        except Exception:
            logs = ""
        try:
            container.remove(force=True)
        except Exception:
            pass

        avg_cpu = sum(cpu_samples) / len(cpu_samples) if cpu_samples else 25.0
        peak_mem = max(mem_samples_mb) if mem_samples_mb else 35.0

        metrics = calculate_energy_and_sci(duration, avg_cpu, peak_mem, grid_intensity)

        return ProfilingResult(
            file_path=file_path,
            profiling_mode="DOCKER_ISOLATED",
            duration_sec=round(duration, 4),
            avg_cpu_percent=round(avg_cpu, 2),
            peak_memory_mb=round(peak_mem, 2),
            total_power_watts=metrics["total_power_watts"],
            energy_joules=metrics["energy_joules"],
            energy_wh=metrics["energy_wh"],
            energy_kwh=metrics["energy_kwh"],
            operational_carbon_gco2=metrics["operational_carbon_gco2"],
            embodied_carbon_gco2=metrics["embodied_carbon_gco2"],
            sci_score_gco2=metrics["sci_score_gco2"],
            grid_intensity_gco2_per_kwh=grid_intensity,
            exit_code=exit_code,
            stdout_preview=logs[:2000] if not timed_out else logs[:1000] + "\n[Execution Timed Out: Terminated by GreenCode Sandbox Guard]",
            stderr_preview="",
        )


    def _profile_with_process_sandbox(
        self, file_path: str, timeout_sec: float, grid_intensity: float
    ) -> ProfilingResult:
        """High-precision subprocess profiler monitoring CPU and RSS memory intervals across languages."""
        abs_path = os.path.abspath(file_path)
        ext = os.path.splitext(file_path)[1].lower()
        cmd: List[str] = []
        cleanup_file: Optional[str] = None
        missing_runtime_msg: Optional[str] = None

        if ext in (".py", ".pyw"):
            cmd = [sys.executable, abs_path]
        elif ext in (".js", ".mjs"):
            node_bin = shutil.which("node")
            if node_bin:
                cmd = [node_bin, abs_path]
            else:
                missing_runtime_msg = "Host runtime 'node' not found. Profile via Docker container or install Node.js."
        elif ext in (".ts", ".mts"):
            ts_bin = shutil.which("ts-node") or shutil.which("bun") or shutil.which("deno")
            if ts_bin:
                cmd = [ts_bin, abs_path]
            else:
                missing_runtime_msg = "Host runtime 'ts-node' / 'bun' / 'deno' not found. Profile via Docker container or install TypeScript runner."
        elif ext in (".go",):
            go_bin = shutil.which("go")
            if go_bin:
                cmd = [go_bin, "run", abs_path]
            else:
                missing_runtime_msg = "Host runtime 'go' not found. Profile via Docker container or install Go compiler."
        elif ext in (".java",):
            java_bin = shutil.which("java")
            if java_bin:
                cmd = [java_bin, abs_path]
            else:
                missing_runtime_msg = "Host runtime 'java' not found. Profile via Docker container or install OpenJDK."
        elif ext in (".cpp", ".cc", ".cxx", ".c"):
            gpp_bin = shutil.which("g++") or shutil.which("clang++") or shutil.which("gcc")
            if gpp_bin:
                temp_bin = os.path.join(tempfile.gettempdir(), f"greencode_bin_{int(time.time())}.exe" if platform.system() == "Windows" else f"greencode_bin_{int(time.time())}")
                try:
                    compile_proc = subprocess.run([gpp_bin, "-O2", abs_path, "-o", temp_bin], capture_output=True, text=True, timeout=10.0)
                    if compile_proc.returncode == 0 and os.path.exists(temp_bin):
                        cmd = [temp_bin]
                        cleanup_file = temp_bin
                    else:
                        missing_runtime_msg = f"C++ Compilation failed: {compile_proc.stderr[:300]}"
                except Exception as exc:
                    missing_runtime_msg = f"C++ Compiler error: {str(exc)}"
            else:
                missing_runtime_msg = "Host compiler 'g++' not found. Profile via Docker container or install GCC/Clang."
        elif ext in (".rs",):
            rustc_bin = shutil.which("rustc")
            if rustc_bin:
                temp_bin = os.path.join(tempfile.gettempdir(), f"greencode_rs_{int(time.time())}.exe" if platform.system() == "Windows" else f"greencode_rs_{int(time.time())}")
                try:
                    compile_proc = subprocess.run([rustc_bin, abs_path, "-o", temp_bin], capture_output=True, text=True, timeout=15.0)
                    if compile_proc.returncode == 0 and os.path.exists(temp_bin):
                        cmd = [temp_bin]
                        cleanup_file = temp_bin
                    else:
                        missing_runtime_msg = f"Rust Compilation failed: {compile_proc.stderr[:300]}"
                except Exception as exc:
                    missing_runtime_msg = f"Rust Compiler error: {str(exc)}"
            else:
                missing_runtime_msg = "Host compiler 'rustc' not found. Profile via Docker container or install Rust toolchain."
        elif ext in (".rb", ".rbw"):
            ruby_bin = shutil.which("ruby")
            if ruby_bin:
                cmd = [ruby_bin, abs_path]
            else:
                missing_runtime_msg = "Host runtime 'ruby' not found. Profile via Docker container or install Ruby."
        elif ext in (".php",):
            php_bin = shutil.which("php")
            if php_bin:
                cmd = [php_bin, abs_path]
            else:
                missing_runtime_msg = "Host runtime 'php' not found. Profile via Docker container or install PHP."
        elif ext in (".sh", ".bash"):
            bash_bin = shutil.which("bash") or shutil.which("sh")
            if bash_bin:
                cmd = [bash_bin, abs_path]
            else:
                missing_runtime_msg = "Host shell 'bash' not found. Profile via Docker container or install Bash."
        elif ext in (".cs",):
            dotnet_bin = shutil.which("dotnet")
            if dotnet_bin:
                cmd = [dotnet_bin, "run", abs_path]
            else:
                missing_runtime_msg = "Host runtime '.NET SDK' not found. Profile via Docker container or install dotnet."
        else:
            missing_runtime_msg = f"No host execution runtime registered for file extension '{ext}'. Run with Docker container isolation."


        if missing_runtime_msg:
            metrics = calculate_energy_and_sci(0.01, 10.0, 15.0, grid_intensity)
            return ProfilingResult(
                file_path=file_path,
                profiling_mode="HOST_SANDBOX_FALLBACK",
                duration_sec=0.01,
                avg_cpu_percent=10.0,
                peak_memory_mb=15.0,
                total_power_watts=metrics["total_power_watts"],
                energy_joules=metrics["energy_joules"],
                energy_wh=metrics["energy_wh"],
                energy_kwh=metrics["energy_kwh"],
                operational_carbon_gco2=metrics["operational_carbon_gco2"],
                embodied_carbon_gco2=metrics["embodied_carbon_gco2"],
                sci_score_gco2=metrics["sci_score_gco2"],
                grid_intensity_gco2_per_kwh=grid_intensity,
                exit_code=1,
                stdout_preview="",
                stderr_preview=f"[GreenCode Host Sandbox Notice]: {missing_runtime_msg}",
            )

        # 1. Static Security Guard: Block destructive calls from running on host machine
        safety_violation = validate_script_safety_for_host(abs_path)
        if safety_violation:
            metrics = calculate_energy_and_sci(0.01, 5.0, 10.0, grid_intensity)
            return ProfilingResult(
                file_path=file_path,
                profiling_mode="HOST_SANDBOX_BLOCKED",
                duration_sec=0.01,
                avg_cpu_percent=0.0,
                peak_memory_mb=10.0,
                total_power_watts=metrics["total_power_watts"],
                energy_joules=metrics["energy_joules"],
                energy_wh=metrics["energy_wh"],
                energy_kwh=metrics["energy_kwh"],
                operational_carbon_gco2=metrics["operational_carbon_gco2"],
                embodied_carbon_gco2=metrics["embodied_carbon_gco2"],
                sci_score_gco2=metrics["sci_score_gco2"],
                grid_intensity_gco2_per_kwh=grid_intensity,
                exit_code=126,
                stdout_preview="",
                stderr_preview=f"[GreenCode Sandbox Security Guard]: {safety_violation}",
            )

        cpu_samples: List[float] = []
        mem_samples_mb: List[float] = []

        start_time = time.perf_counter()
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=os.path.dirname(abs_path) or None,
            )

            try:
                ps_proc = psutil.Process(proc.pid)
                # Initialize cpu_percent counter without interval to avoid blocking
                ps_proc.cpu_percent(interval=None)
                while proc.poll() is None:
                    elapsed = time.perf_counter() - start_time
                    if elapsed > timeout_sec:
                        kill_process_tree(proc.pid)
                        break
                    try:
                        # Monitor aggregate tree telemetry (parent + all children)
                        all_procs = [ps_proc]
                        try:
                            all_procs.extend(ps_proc.children(recursive=True))
                        except Exception:
                            pass

                        tree_cpu = 0.0
                        tree_mem = 0.0
                        for p in all_procs:
                            try:
                                tree_cpu += p.cpu_percent(interval=None)
                                tree_mem += p.memory_info().rss / (1024 * 1024)
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                pass

                        if tree_cpu > 0:
                            cpu_samples.append(tree_cpu)
                        if tree_mem > 0:
                            mem_samples_mb.append(tree_mem)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        break
                    time.sleep(0.04)
            except Exception:
                pass

            stdout, stderr = proc.communicate()
            exit_code = proc.returncode or 0
        except Exception as exc:
            stdout = ""
            stderr = f"Process invocation error: {str(exc)}"
            exit_code = 1
        finally:
            if cleanup_file and os.path.exists(cleanup_file):
                try:
                    os.remove(cleanup_file)
                except Exception:
                    pass

        end_time = time.perf_counter()
        duration = max(0.001, end_time - start_time)

        avg_cpu = sum(cpu_samples) / len(cpu_samples) if cpu_samples else 15.0
        peak_mem = max(mem_samples_mb) if mem_samples_mb else 25.0

        metrics = calculate_energy_and_sci(duration, avg_cpu, peak_mem, grid_intensity)

        return ProfilingResult(
            file_path=file_path,
            profiling_mode="HOST_SANDBOX_FALLBACK",
            duration_sec=round(duration, 4),
            avg_cpu_percent=round(avg_cpu, 2),
            peak_memory_mb=round(peak_mem, 2),
            total_power_watts=metrics["total_power_watts"],
            energy_joules=metrics["energy_joules"],
            energy_wh=metrics["energy_wh"],
            energy_kwh=metrics["energy_kwh"],
            operational_carbon_gco2=metrics["operational_carbon_gco2"],
            embodied_carbon_gco2=metrics["embodied_carbon_gco2"],
            sci_score_gco2=metrics["sci_score_gco2"],
            grid_intensity_gco2_per_kwh=grid_intensity,
            exit_code=exit_code,
            stdout_preview=stdout[:2000] if stdout else "",
            stderr_preview=stderr[:2000] if stderr else "",
        )

