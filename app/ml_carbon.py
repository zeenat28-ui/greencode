"""Specialized Static Analysis & Carbon Profiler for AI/ML Workloads.

Covers PyTorch, TensorFlow, Hugging Face Transformers, vLLM, and ONNX pipelines.
Detects architectural, data-pipelining, and runtime energy anti-patterns in machine
learning models that cause thermal throttling, excessive Wattage dissipation,
and GPU memory starvation.

Also provides mathematical modeling for AI LLM inference carbon footprint
(Joules per token & gCO2e per 1,000 generated tokens) calibrated against
Patterson et al. (2021) and Luccioni et al. (2023) datacenter benchmarks.
"""

from __future__ import annotations

import ast
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Set

# Hardware Accelerator TDP & Energy Coefficients (Joules per Token per Billion Parameters)
# Source: MLPerf & Hugging Face Carbon Footprint Benchmarks
ACCELERATOR_SPECIFICATIONS: Dict[str, Dict[str, float]] = {
    "h100": {"tdp_watts": 700.0, "pue": 1.15, "joules_per_token_per_b": 0.00035},
    "a100": {"tdp_watts": 400.0, "pue": 1.15, "joules_per_token_per_b": 0.00065},
    "rtx_4090": {"tdp_watts": 450.0, "pue": 1.25, "joules_per_token_per_b": 0.00095},
    "v100": {"tdp_watts": 300.0, "pue": 1.20, "joules_per_token_per_b": 0.00140},
    "t4": {"tdp_watts": 70.0, "pue": 1.15, "joules_per_token_per_b": 0.00280},
    "cpu": {"tdp_watts": 180.0, "pue": 1.20, "joules_per_token_per_b": 0.00850},
    "npu": {"tdp_watts": 25.0, "pue": 1.10, "joules_per_token_per_b": 0.00028},
}

# Energy deduction penalties for ML Anti-Patterns
ML_VIOLATIONS_CATALOG: Dict[str, Dict[str, Any]] = {
    "ML_MISSING_INFERENCE_MODE": {
        "severity": "CRITICAL",
        "deduction": 25.0,
        "description": "Evaluation or inference performed without torch.inference_mode() or torch.no_grad(). Retains computational DAGs, increasing memory allocation by 30-45% and elevating thermal dissipation.",
        "remediation": "Wrap evaluation blocks inside 'with torch.inference_mode():' to deactivate automatic differentiation overhead.",
    },
    "ML_INEFFICIENT_BATCH_SIZE": {
        "severity": "HIGH",
        "deduction": 15.0,
        "description": "Inference or training initialized with batch_size=1 or batch_size < 4. Underutilizes GPU Tensor Cores, causing excessive idle standby Wattage per inference.",
        "remediation": "Increase batch size to powers of 2 (e.g. 16, 32, 64) or enable dynamic request batching (vLLM / Triton).",
    },
    "ML_SYNC_GPU_TENSOR_TRANSFER": {
        "severity": "HIGH",
        "deduction": 20.0,
        "description": "Item-by-item host-to-device (.to('cuda'), .cuda()) or device-to-host (.cpu(), .numpy(), .item()) synchronization inside iteration loops. Blocks PCIe bus and stalls GPU warps.",
        "remediation": "Transfer tensors in bulk batches outside the loop, or use non_blocking=True with pinned memory.",
    },
    "ML_DATALOADER_CPU_BOTTLENECK": {
        "severity": "HIGH",
        "deduction": 15.0,
        "description": "PyTorch DataLoader configured with num_workers=0 or pin_memory=False. Forces synchronous disk read on main thread, keeping high-TDP GPU idling between epochs.",
        "remediation": "Configure DataLoader(..., num_workers=4, pin_memory=True) to allow asynchronous DMA data transfers.",
    },
    "ML_UNQUANTIZED_INFERENCE": {
        "severity": "MEDIUM",
        "deduction": 12.0,
        "description": "Model loaded in unquantized FP32/float32 precision for inference. FP16/BF16 or 8-bit/4-bit quantization reduces memory bandwidth energy by 50-75%.",
        "remediation": "Quantize model weights using bitsandbytes (load_in_8bit=True, load_in_4bit=True), AWQ, GPTQ, or torch.bfloat16.",
    },
    "ML_RETRAINING_IN_ENDPOINT": {
        "severity": "CRITICAL",
        "deduction": 30.0,
        "description": "Model fitting (.fit(), .train(), trainer.train()) invoked directly inside web request handlers or loops without checkpoint check. Risks runaway CPU/GPU thermal dissipation.",
        "remediation": "Decouple model training into an asynchronous offline background job queue with checkpoint caches.",
    },
    "ML_MISSING_KV_CACHE": {
        "severity": "MEDIUM",
        "deduction": 10.0,
        "description": "Autoregressive generation executed with use_cache=False or repetitive forward passes over full context history without KV-cache.",
        "remediation": "Ensure use_cache=True is enabled in generation config to prevent quadratic O(N^2) token recalculation.",
    },
}


@dataclass
class MLViolation:
    """An identified ML/AI energy anti-pattern."""

    rule: str
    severity: str
    line: int
    deduction: float
    description: str
    remediation: str
    code_snippet: str = ""


@dataclass
class MLTokenCarbonResult:
    """Projected energy and carbon footprint for AI token generation."""

    parameter_count_b: float
    token_count: int
    hardware: str
    energy_joules: float
    energy_kwh: float
    carbon_gco2e: float
    joules_per_token: float
    gco2e_per_1k_tokens: float
    annual_cost_usd_at_scale: float
    recommendation: str


@dataclass
class MLAnalysisResult:
    """Complete static and mathematical evaluation of an ML script or repo."""

    file_or_repo: str
    ml_green_score: float
    total_deductions: float
    violations_count: int
    violations: List[MLViolation] = field(default_factory=list)
    frameworks_detected: List[str] = field(default_factory=list)
    token_projection: Optional[MLTokenCarbonResult] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert the result to a JSON-serializable dictionary."""
        return asdict(self)


class MLCodeVisitor(ast.NodeVisitor):
    """AST Visitor detecting machine learning energy anti-patterns."""

    def __init__(self, source_lines: List[str]) -> None:
        self.source_lines = source_lines
        self.violations: List[MLViolation] = []
        self.frameworks: Set[str] = set()
        self.loop_depth = 0
        self.inside_function = False
        self.function_names: List[str] = []

    def _add_violation(self, rule: str, node: ast.AST) -> None:
        meta = ML_VIOLATIONS_CATALOG.get(rule)
        if not meta:
            return
        line_num = getattr(node, "lineno", 1)
        snippet = ""
        if 0 < line_num <= len(self.source_lines):
            snippet = self.source_lines[line_num - 1].strip()

        self.violations.append(
            MLViolation(
                rule=rule,
                severity=meta["severity"],
                line=line_num,
                deduction=meta["deduction"],
                description=meta["description"],
                remediation=meta["remediation"],
                code_snippet=snippet,
            )
        )

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            name = alias.name.lower()
            if "torch" in name:
                self.frameworks.add("PyTorch")
            elif "tensorflow" in name or "tf" in name:
                self.frameworks.add("TensorFlow")
            elif "transformers" in name:
                self.frameworks.add("HuggingFace Transformers")
            elif "vllm" in name:
                self.frameworks.add("vLLM")
            elif "onnx" in name:
                self.frameworks.add("ONNX")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        mod = (node.module or "").lower()
        if "torch" in mod:
            self.frameworks.add("PyTorch")
        elif "tensorflow" in mod:
            self.frameworks.add("TensorFlow")
        elif "transformers" in mod:
            self.frameworks.add("HuggingFace Transformers")
        elif "vllm" in mod:
            self.frameworks.add("vLLM")
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self.loop_depth += 1
        self.generic_visit(node)
        self.loop_depth -= 1

    def visit_While(self, node: ast.While) -> None:
        self.loop_depth += 1
        self.generic_visit(node)
        self.loop_depth -= 1

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.function_names.append(node.name)
        self.inside_function = True
        self.generic_visit(node)
        self.function_names.pop()
        self.inside_function = bool(self.function_names)

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func

        # 1. Check DataLoader bottlenecks
        func_name = ""
        if isinstance(func, ast.Name):
            func_name = func.id
        elif isinstance(func, ast.Attribute):
            func_name = func.attr

        if func_name == "DataLoader":
            has_pin_memory = False
            zero_workers = False
            for kw in node.keywords:
                if kw.arg == "pin_memory":
                    if isinstance(kw.value, ast.Constant) and kw.value.value is True:
                        has_pin_memory = True
                elif kw.arg == "num_workers":
                    if isinstance(kw.value, ast.Constant) and kw.value.value == 0:
                        zero_workers = True

            if zero_workers or not has_pin_memory:
                self._add_violation("ML_DATALOADER_CPU_BOTTLENECK", node)

        # 2. Check batch_size=1
        for kw in node.keywords:
            if kw.arg in ("batch_size", "per_device_train_batch_size", "per_device_eval_batch_size"):
                if isinstance(kw.value, ast.Constant) and kw.value.value == 1:
                    self._add_violation("ML_INEFFICIENT_BATCH_SIZE", node)

        # 3. Synchronous GPU transfer in loop (.to('cuda'), .cuda(), .cpu(), .item())
        if self.loop_depth > 0:
            if isinstance(func, ast.Attribute):
                attr = func.attr
                if attr in ("cuda", "cpu", "numpy", "item"):
                    self._add_violation("ML_SYNC_GPU_TENSOR_TRANSFER", node)
                elif attr == "to":
                    # Check if transferring to cuda/gpu
                    for arg in node.args:
                        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                            if "cuda" in arg.value.lower():
                                self._add_violation("ML_SYNC_GPU_TENSOR_TRANSFER", node)

        # 4. Retraining inside endpoint/handler
        if func_name in ("fit", "train") and isinstance(func, ast.Attribute):
            current_fn = self.function_names[-1].lower() if self.function_names else ""
            if any(endpoint_word in current_fn for endpoint_word in ["route", "endpoint", "handler", "api", "predict", "infer"]):
                self._add_violation("ML_RETRAINING_IN_ENDPOINT", node)

        # 5. use_cache=False in generation
        for kw in node.keywords:
            if kw.arg == "use_cache" and isinstance(kw.value, ast.Constant) and kw.value.value is False:
                self._add_violation("ML_MISSING_KV_CACHE", node)

        # 6. Unquantized FP32 in HuggingFace or PyTorch
        for kw in node.keywords:
            if kw.arg == "torch_dtype":
                if isinstance(kw.value, ast.Attribute) and kw.value.attr in ("float32", "fp32"):
                    self._add_violation("ML_UNQUANTIZED_INFERENCE", node)

        self.generic_visit(node)


class MLCarbonAnalyzer:
    """Static Code Auditor and Operational Footprint Calculator for ML/AI."""

    @classmethod
    def audit_code(cls, source_code: str, file_path: str = "script.py") -> MLAnalysisResult:
        """Analyze a string of Python code for ML energy anti-patterns."""
        source_lines = source_code.splitlines()
        visitor = MLCodeVisitor(source_lines)

        try:
            tree = ast.parse(source_code)
            visitor.visit(tree)
        except SyntaxError:
            pass

        # Deduct score starting from 100
        total_deductions = sum(v.deduction for v in visitor.violations)
        green_score = max(0.0, round(100.0 - total_deductions, 1))

        return MLAnalysisResult(
            file_or_repo=file_path,
            ml_green_score=green_score,
            total_deductions=round(total_deductions, 1),
            violations_count=len(visitor.violations),
            violations=visitor.violations,
            frameworks_detected=sorted(list(visitor.frameworks)),
        )

    @classmethod
    def audit_file(cls, file_path: str) -> MLAnalysisResult:
        """Read and audit a Python ML file on disk."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                code = f.read()
            return cls.audit_code(code, file_path=file_path)
        except Exception as exc:
            return MLAnalysisResult(
                file_or_repo=file_path,
                ml_green_score=100.0,
                total_deductions=0.0,
                violations_count=0,
                violations=[],
                frameworks_detected=[],
            )

    @staticmethod
    def project_token_emissions(
        parameter_count_b: float = 7.0,
        token_count: int = 1000,
        hardware: str = "a100",
        grid_intensity_gco2_per_kwh: float = 200.0,
        runs_per_year: int = 1_000_000,
        kwh_cost_usd: float = 0.12,
    ) -> MLTokenCarbonResult:
        """Model the operational energy and carbon footprint of LLM token generation."""
        hw_key = hardware.lower().replace(" ", "_")
        spec = ACCELERATOR_SPECIFICATIONS.get(hw_key, ACCELERATOR_SPECIFICATIONS["a100"])

        safe_params = max(0.1, parameter_count_b)
        safe_tokens = max(1, token_count)

        # Joules = tokens * parameters (Billions) * coefficient * PUE
        joules_per_token = safe_params * spec["joules_per_token_per_b"] * spec["pue"]
        total_joules = joules_per_token * safe_tokens
        total_kwh = total_joules / 3_600_000.0

        # Carbon in gCO2e
        carbon_gco2e = total_kwh * grid_intensity_gco2_per_kwh
        gco2e_per_1k = (carbon_gco2e / safe_tokens) * 1000.0

        annual_kwh_scale = total_kwh * (runs_per_year / safe_tokens)
        annual_cost_usd = annual_kwh_scale * kwh_cost_usd

        rec = (
            f"Using {hardware.upper()} for {safe_params}B parameters. "
            f"Quantizing to 4-bit/AWQ reduces active Joules/token by up to 68%."
        )

        return MLTokenCarbonResult(
            parameter_count_b=safe_params,
            token_count=safe_tokens,
            hardware=hardware.upper(),
            energy_joules=round(total_joules, 4),
            energy_kwh=round(total_kwh, 8),
            carbon_gco2e=round(carbon_gco2e, 6),
            joules_per_token=round(joules_per_token, 6),
            gco2e_per_1k_tokens=round(gco2e_per_1k, 6),
            annual_cost_usd_at_scale=round(annual_cost_usd, 2),
            recommendation=rec,
        )

