"""Infrastructure-as-Code (Terraform, Kubernetes, Dockerfile) FinOps & GreenOps Linter.

Analyzes `.tf` (Terraform), `.yaml`/`.yml` (Kubernetes manifests), and `Dockerfile`
specifications to detect overprovisioned x86 instances, legacy storage tiers,
missing Kubernetes scheduler resource limits, and unoptimized container layers,
quantifying monthly USD and annual kg CO2e savings.
"""

import re
from typing import Any, Dict, List, Optional

# Precompiled module-level patterns (avoids regex compilation inside loops)
_RE_TF_EC2_X86 = re.compile(
    r'instance_type\s*=\s*"((?:t2|t3|m4|m5|c4|c5|r4|r5)\.[a-z0-9]+)"'
)
_RE_TF_RDS_X86 = re.compile(
    r'instance_class\s*=\s*"(db\.(?:t2|t3|m4|m5|r4|r5)\.[a-z0-9]+)"'
)
_RE_TF_EBS_GP2 = re.compile(r'type\s*=\s*"gp2"')
_RE_TF_LOG_GROUP = re.compile(r'resource\s+"aws_cloudwatch_log_group"\s+"([^"]+)"\s*\{([^}]*)\}', re.DOTALL)

_RE_K8S_WORKLOAD = re.compile(r"^\s*kind:\s*(Deployment|StatefulSet|DaemonSet|Job)\b", re.MULTILINE)
_RE_K8S_LIMITS = re.compile(r"^\s*limits:\s*$", re.MULTILINE)
_RE_K8S_IMAGE_LATEST = re.compile(r"^\s*image:\s*([^\s:#]+:latest)\b", re.MULTILINE)

_RE_DOCKER_FAT_IMAGE = re.compile(
    r"^\s*FROM\s+((?:python|node|golang|openjdk|ruby|rust):[0-9.]+)\s*$",
    re.MULTILINE | re.IGNORECASE,
)
_RE_DOCKER_APT_INSTALL = re.compile(r"apt-get\s+install(?!\s+[^\n]*--no-install-recommends)", re.IGNORECASE)

_GRAVITON_MAP = {
    "t2": "t4g",
    "t3": "t4g",
    "m4": "m7g",
    "m5": "m7g",
    "c4": "c7g",
    "c5": "c7g",
    "r4": "r7g",
    "r5": "r7g",
}

_SIZE_MONTHLY_USD_DELTA = {
    "nano": 1.80,
    "micro": 3.50,
    "small": 7.20,
    "medium": 14.40,
    "large": 28.50,
    "xlarge": 57.00,
    "2xlarge": 114.00,
    "4xlarge": 228.00,
    "8xlarge": 456.00,
}

IAC_RULES_CATALOG: List[Dict[str, Any]] = [
    {
        "id": "IAC_TF_NON_GRAVITON_EC2",
        "iac_type": "terraform",
        "severity": "HIGH",
        "title": "x86_64 EC2 Instance Instead of AWS Graviton ARM64",
        "gsf_pattern": "GSF-HW-01: High-Efficiency ARM64 Silicon Selection",
    },
    {
        "id": "IAC_TF_NON_GRAVITON_RDS",
        "iac_type": "terraform",
        "severity": "HIGH",
        "title": "x86_64 RDS Database Instance Instead of AWS Graviton",
        "gsf_pattern": "GSF-HW-02: Managed Database Silicon Efficiency",
    },
    {
        "id": "IAC_TF_LEGACY_GP2_EBS",
        "iac_type": "terraform",
        "severity": "MEDIUM",
        "title": "Legacy AWS EBS gp2 Volume Instead of gp3",
        "gsf_pattern": "GSF-STORAGE-01: Storage Tier Power & Cost Optimization",
    },
    {
        "id": "IAC_TF_UNBOUNDED_LOG_RETENTION",
        "iac_type": "terraform",
        "severity": "LOW",
        "title": "CloudWatch Log Group Missing retention_in_days Policy",
        "gsf_pattern": "GSF-STORAGE-02: Data Lifecycle & Retention Expiration",
    },
    {
        "id": "IAC_K8S_MISSING_RESOURCE_LIMITS",
        "iac_type": "kubernetes",
        "severity": "HIGH",
        "title": "Kubernetes Workload Missing CPU/Memory Resource Limits",
        "gsf_pattern": "GSF-K8S-01: Cluster Bin-Packing & Right-Sizing",
    },
    {
        "id": "IAC_K8S_LATEST_IMAGE_TAG",
        "iac_type": "kubernetes",
        "severity": "MEDIUM",
        "title": "Unpinned :latest Container Image Tag in Pod Spec",
        "gsf_pattern": "GSF-NET-02: Immutable Layer Caching",
    },
    {
        "id": "IAC_DOCKER_UNOPTIMIZED_BASE_IMAGE",
        "iac_type": "dockerfile",
        "severity": "MEDIUM",
        "title": "Unoptimized Full OS Container Base Image",
        "gsf_pattern": "GSF-CONTAINER-01: Minimal Base Image Footprint",
    },
    {
        "id": "IAC_DOCKER_APT_NO_RECOMMEND",
        "iac_type": "dockerfile",
        "severity": "LOW",
        "title": "apt-get install Without --no-install-recommends",
        "gsf_pattern": "GSF-CONTAINER-02: Layer Bloat Elimination",
    },
]


def _graviton_equivalent(instance_type: str) -> str:
    parts = instance_type.split(".")
    if len(parts) == 2:
        family, size = parts
        target_family = _GRAVITON_MAP.get(family, "m7g")
        return f"{target_family}.{size}"
    if len(parts) == 3 and parts[0] == "db":
        _, family, size = parts
        target_family = _GRAVITON_MAP.get(family, "m7g")
        return f"db.{target_family}.{size}"
    return "c7g.large"


def _estimate_instance_savings(instance_type: str) -> Dict[str, float]:
    size = instance_type.split(".")[-1]
    monthly_usd = _SIZE_MONTHLY_USD_DELTA.get(size, 32.00)
    annual_co2_kg = round(monthly_usd * 1.85, 2)
    return {"monthly_usd": monthly_usd, "annual_co2_kg": annual_co2_kg}


_RE_TF_VARIABLE_BLOCK = re.compile(
    r'variable\s+"([a-zA-Z0-9_-]+)"\s*\{([^}]*)\}', re.DOTALL
)
_RE_TF_DEFAULT_STR = re.compile(r'default\s*=\s*"([^"]+)"')
_RE_TF_LOCALS_BLOCK = re.compile(r"locals\s*\{([^}]*)\}", re.DOTALL)
_RE_TF_LOCAL_KV = re.compile(r'([a-zA-Z0-9_-]+)\s*=\s*"([^"]+)"')
_RE_TF_REF = re.compile(r"=\s*((?:var|local)\.[a-zA-Z0-9_-]+)\b")


def _extract_locals_into_map(l_body: str, var_map: Dict[str, str]) -> None:
    """Populate `local.<key>` entries into `var_map`."""
    for kv in _RE_TF_LOCAL_KV.finditer(l_body):
        var_map[f"local.{kv.group(1)}"] = kv.group(2)


def _resolve_terraform_symbols(content: str) -> str:
    """Resolve `var.<name>` and `local.<name>` expressions against Terraform defaults/locals."""
    var_map: Dict[str, str] = {}
    for vm in _RE_TF_VARIABLE_BLOCK.finditer(content):
        v_name, v_body = vm.group(1), vm.group(2)
        dm = _RE_TF_DEFAULT_STR.search(v_body)
        if dm:
            var_map[f"var.{v_name}"] = dm.group(1)

    for lm in _RE_TF_LOCALS_BLOCK.finditer(content):
        _extract_locals_into_map(lm.group(1), var_map)

    if not var_map:
        return content

    return _RE_TF_REF.sub(
        lambda m: f'= "{var_map[m.group(1)]}"' if m.group(1) in var_map else m.group(0),
        content,
    )


def _lint_terraform(content: str, file_path: str) -> List[Dict[str, Any]]:
    content = _resolve_terraform_symbols(content)
    findings: List[Dict[str, Any]] = []

    for m in _RE_TF_EC2_X86.finditer(content):
        inst = m.group(1)
        target = _graviton_equivalent(inst)
        sav = _estimate_instance_savings(inst)
        line_no = content.count("\n", 0, m.start()) + 1
        findings.append({
            "rule_id": "IAC_TF_NON_GRAVITON_EC2",
            "iac_type": "terraform",
            "severity": "HIGH",
            "title": f"x86_64 EC2 Instance ({inst}) Instead of AWS Graviton ({target})",
            "description": (
                f"Instance '{inst}' uses legacy x86_64 silicon. Migrating to AWS Graviton ARM64 "
                f"('{target}') reduces power draw per vCPU by up to 60% and lowers EC2 hourly cost by ~20%."
            ),
            "line_number": line_no,
            "file_path": file_path,
            "deduction": 12.0,
            "gsf_pattern": "GSF-HW-01: High-Efficiency ARM64 Silicon Selection",
            "estimated_monthly_usd_savings": sav["monthly_usd"],
            "estimated_annual_co2_saved_kg": sav["annual_co2_kg"],
            "recommended_patch": f'instance_type = "{target}"',
        })

    for m in _RE_TF_RDS_X86.finditer(content):
        inst = m.group(1)
        target = _graviton_equivalent(inst)
        sav = _estimate_instance_savings(inst)
        line_no = content.count("\n", 0, m.start()) + 1
        findings.append({
            "rule_id": "IAC_TF_NON_GRAVITON_RDS",
            "iac_type": "terraform",
            "severity": "HIGH",
            "title": f"x86_64 RDS Instance ({inst}) Instead of AWS Graviton ({target})",
            "description": (
                f"Managed database instance '{inst}' runs on x86_64. Switching to '{target}' "
                "improves price-performance and reduces datacenter Scope 2 operational emissions."
            ),
            "line_number": line_no,
            "file_path": file_path,
            "deduction": 10.0,
            "gsf_pattern": "GSF-HW-02: Managed Database Silicon Efficiency",
            "estimated_monthly_usd_savings": round(sav["monthly_usd"] * 1.25, 2),
            "estimated_annual_co2_saved_kg": round(sav["annual_co2_kg"] * 1.2, 2),
            "recommended_patch": f'instance_class = "{target}"',
        })

    for m in _RE_TF_EBS_GP2.finditer(content):
        line_no = content.count("\n", 0, m.start()) + 1
        findings.append({
            "rule_id": "IAC_TF_LEGACY_GP2_EBS",
            "iac_type": "terraform",
            "severity": "MEDIUM",
            "title": "Legacy AWS EBS gp2 Volume Instead of gp3",
            "description": (
                "EBS gp3 volumes cost 20% less per GB-month than gp2 and deliver 3,000 baseline IOPS "
                "without requiring overprovisioned volume capacity."
            ),
            "line_number": line_no,
            "file_path": file_path,
            "deduction": 6.0,
            "gsf_pattern": "GSF-STORAGE-01: Storage Tier Power & Cost Optimization",
            "estimated_monthly_usd_savings": 8.00,
            "estimated_annual_co2_saved_kg": 9.40,
            "recommended_patch": 'type = "gp3"',
        })

    for m in _RE_TF_LOG_GROUP.finditer(content):
        group_name = m.group(1)
        body = m.group(2)
        if "retention_in_days" not in body:
            line_no = content.count("\n", 0, m.start()) + 1
            findings.append({
                "rule_id": "IAC_TF_UNBOUNDED_LOG_RETENTION",
                "iac_type": "terraform",
                "severity": "LOW",
                "title": f"CloudWatch Log Group '{group_name}' Missing retention_in_days",
                "description": (
                    "CloudWatch log groups without retention_in_days store logs indefinitely, "
                    "accumulating dark data storage cost and continuous storage array power draw."
                ),
                "line_number": line_no,
                "file_path": file_path,
                "deduction": 4.0,
                "gsf_pattern": "GSF-STORAGE-02: Data Lifecycle & Retention Expiration",
                "estimated_monthly_usd_savings": 5.50,
                "estimated_annual_co2_saved_kg": 4.20,
                "recommended_patch": "retention_in_days = 30",
            })

    return findings


def _lint_kubernetes(content: str, file_path: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    workload_match = _RE_K8S_WORKLOAD.search(content)
    if workload_match and not _RE_K8S_LIMITS.search(content):
        kind_name = workload_match.group(1)
        line_no = content.count("\n", 0, workload_match.start()) + 1
        findings.append({
            "rule_id": "IAC_K8S_MISSING_RESOURCE_LIMITS",
            "iac_type": "kubernetes",
            "severity": "HIGH",
            "title": f"Kubernetes {kind_name} Missing CPU/Memory Resource Limits",
            "description": (
                f"Kubernetes {kind_name} manifest does not declare resources.limits. "
                "Unbounded pods prevent tight node bin-packing and force cluster autoscalers to run extra nodes."
            ),
            "line_number": line_no,
            "file_path": file_path,
            "deduction": 10.0,
            "gsf_pattern": "GSF-K8S-01: Cluster Bin-Packing & Right-Sizing",
            "estimated_monthly_usd_savings": 22.00,
            "estimated_annual_co2_saved_kg": 34.50,
            "recommended_patch": (
                "resources:\n"
                "  requests:\n"
                "    cpu: \"250m\"\n"
                "    memory: \"256Mi\"\n"
                "  limits:\n"
                "    cpu: \"500m\"\n"
                "    memory: \"512Mi\""
            ),
        })

    for m in _RE_K8S_IMAGE_LATEST.finditer(content):
        img = m.group(1)
        line_no = content.count("\n", 0, m.start()) + 1
        findings.append({
            "rule_id": "IAC_K8S_LATEST_IMAGE_TAG",
            "iac_type": "kubernetes",
            "severity": "MEDIUM",
            "title": f"Unpinned Container Image Tag ({img})",
            "description": (
                "Using ':latest' forces ImagePullPolicy: Always semantics, causing redundant registry "
                "egress traffic and layer decompression CPU spikes on every pod scheduling event."
            ),
            "line_number": line_no,
            "file_path": file_path,
            "deduction": 5.0,
            "gsf_pattern": "GSF-NET-02: Immutable Layer Caching",
            "estimated_monthly_usd_savings": 4.50,
            "estimated_annual_co2_saved_kg": 6.10,
            "recommended_patch": f"image: {img[:-7]}:v1.0.0",
        })

    return findings


def _lint_dockerfile(content: str, file_path: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    for m in _RE_DOCKER_FAT_IMAGE.finditer(content):
        base_img = m.group(1)
        line_no = content.count("\n", 0, m.start()) + 1
        findings.append({
            "rule_id": "IAC_DOCKER_UNOPTIMIZED_BASE_IMAGE",
            "iac_type": "dockerfile",
            "severity": "MEDIUM",
            "title": f"Full OS Base Image ('{base_img}') Instead of Slim/Alpine Variant",
            "description": (
                f"Base image '{base_img}' bundles full Debian build toolchains (~900MB). "
                f"Switching to '{base_img}-slim' cuts image size by ~75%, reducing network pull and disk I/O energy."
            ),
            "line_number": line_no,
            "file_path": file_path,
            "deduction": 6.0,
            "gsf_pattern": "GSF-CONTAINER-01: Minimal Base Image Footprint",
            "estimated_monthly_usd_savings": 6.00,
            "estimated_annual_co2_saved_kg": 8.80,
            "recommended_patch": f"FROM {base_img}-slim",
        })

    for m in _RE_DOCKER_APT_INSTALL.finditer(content):
        line_no = content.count("\n", 0, m.start()) + 1
        findings.append({
            "rule_id": "IAC_DOCKER_APT_NO_RECOMMEND",
            "iac_type": "dockerfile",
            "severity": "LOW",
            "title": "apt-get install Without --no-install-recommends",
            "description": (
                "Installing optional recommended packages inflates container image layers "
                "and increases pull bandwidth across CI/CD runners and Kubernetes nodes."
            ),
            "line_number": line_no,
            "file_path": file_path,
            "deduction": 3.5,
            "gsf_pattern": "GSF-CONTAINER-02: Layer Bloat Elimination",
            "estimated_monthly_usd_savings": 2.50,
            "estimated_annual_co2_saved_kg": 3.20,
            "recommended_patch": "apt-get install -y --no-install-recommends",
        })

    return findings


def audit_iac_content(
    content: str,
    file_path: str = "main.tf",
    iac_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Audit Terraform (.tf), Kubernetes (.yaml), or Dockerfile content for FinOps & carbon waste."""
    norm_path = (file_path or "").lower()
    detected_type = (iac_type or "").lower()
    if not detected_type:
        if norm_path.endswith(".tf") or "resource " in content:
            detected_type = "terraform"
        elif "dockerfile" in norm_path or content.lstrip().upper().startswith("FROM "):
            detected_type = "dockerfile"
        else:
            detected_type = "kubernetes"

    if detected_type == "terraform":
        findings = _lint_terraform(content, file_path)
    elif detected_type == "dockerfile":
        findings = _lint_dockerfile(content, file_path)
    else:
        findings = _lint_kubernetes(content, file_path)

    total_deduction = sum(float(f.get("deduction", 0.0)) for f in findings)
    monthly_usd = round(sum(float(f.get("estimated_monthly_usd_savings", 0.0)) for f in findings), 2)
    annual_co2_kg = round(sum(float(f.get("estimated_annual_co2_saved_kg", 0.0)) for f in findings), 2)

    return {
        "file_path": file_path,
        "iac_type": detected_type,
        "green_score": max(0.0, round(100.0 - total_deduction, 2)),
        "total_findings": len(findings),
        "estimated_monthly_usd_savings": monthly_usd,
        "estimated_annual_usd_savings": round(monthly_usd * 12.0, 2),
        "estimated_annual_co2_saved_kg": annual_co2_kg,
        "findings": findings,
    }
