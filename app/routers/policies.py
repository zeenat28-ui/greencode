"""Enterprise Energy Policy REST API Router."""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.services.policy_service import PolicyService
from app.auth.dependencies import get_current_actor, get_tenant_actor, require_permission
from app.auth.roles import Permission, Role, normalize_role

router = APIRouter(prefix="/api/policies", tags=["Energy Policies & Guardrails"])


def _enforce_tenant(actor: Dict[str, Any], org_id: int) -> None:
    """Refuse cross-tenant access unless the caller is a platform superadmin."""
    role = normalize_role(actor.get("role"))
    if role != Role.SUPERADMIN and actor.get("org_id") != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Tenant isolation violation: token belongs to organization "
                f"{actor.get('org_id')} but requested organization {org_id}"
            ),
        )


class PolicySaveRequest(BaseModel):
    org_id: int = 1
    project_id: Optional[int] = None
    name: str = "Enterprise Standard Policy"
    max_regression_pct: float = Field(25.0, ge=0.0)
    max_energy_per_run_joules: float = Field(1.0, gt=0.0)
    max_sci_score: float = Field(80.0, gt=0.0)
    warning_threshold_pct: float = Field(70.0, ge=0.0)
    critical_threshold_pct: float = Field(90.0, ge=0.0)
    breach_threshold_pct: float = Field(100.0, ge=0.0)
    auto_block_deploy: bool = True
    auto_rollback_k8s: bool = True
    dirty_grid_threshold_gco2e: float = Field(450.0, gt=0.0)


class EvaluateRulesRequest(BaseModel):
    org_id: int = 1
    current_energy: float = Field(..., ge=0.0)
    baseline_energy: float = Field(..., gt=0.0)
    team_budget_consumed: float = 0.0
    team_budget_total: float = 500.0
    grid_intensity: float = 380.0
    project_id: Optional[int] = None


class CustomRuleEvaluationRequest(BaseModel):
    source_code: str = Field(..., min_length=1, max_length=200000, description="Source code to evaluate against custom rules")
    language: str = Field("python", max_length=40, description="Programming language identifier")
    file_path: str = Field("snippet.py", max_length=300, description="Virtual file path")
    rules_yaml: Optional[str] = Field(None, max_length=50000, description="Optional custom .greencode-rules.yaml content override")


@router.get("/custom-rules")
async def list_custom_yaml_rules():
    """Return the active declarative custom energy rules loaded from .greencode-rules.yaml."""
    from app.custom_rules import load_repo_custom_rules

    rules = load_repo_custom_rules()
    return {
        "source": ".greencode-rules.yaml",
        "count": len(rules),
        "rules": rules,
    }


@router.post("/custom-rules/evaluate")
async def evaluate_custom_yaml_rules(payload: CustomRuleEvaluationRequest):
    """Evaluate source code against either the repository .greencode-rules.yaml or a custom YAML rule definition."""
    from app.custom_rules import evaluate_custom_rules, parse_custom_rules_yaml

    active_rules = parse_custom_rules_yaml(payload.rules_yaml) if payload.rules_yaml else None
    violations = evaluate_custom_rules(
        source_code=payload.source_code,
        language=payload.language,
        file_path=payload.file_path,
        custom_rules=active_rules,
    )
    total_deduction = sum(float(v.get("deduction", 0.0)) for v in violations)
    return {
        "file_path": payload.file_path,
        "language": payload.language,
        "violations_count": len(violations),
        "green_score": max(0.0, round(100.0 - total_deduction, 2)),
        "violations": violations,
    }


@router.get("/{org_id}")
async def get_enterprise_policy(
    org_id: int,
    project_id: Optional[int] = Query(None),
    actor: Dict[str, Any] = Depends(get_tenant_actor),
):
    """Fetch active energy guardrail policies for an enterprise organization or project."""
    return PolicyService.get_policy(org_id=org_id, project_id=project_id)


@router.post("", status_code=status.HTTP_200_OK)
@router.post("/", status_code=status.HTTP_200_OK)
async def save_enterprise_policy(
    payload: PolicySaveRequest,
    actor: Dict[str, Any] = Depends(require_permission(Permission.OVERRIDE_POLICIES)),
):
    """Save or update organizational energy policies and threshold rules."""
    _enforce_tenant(actor, payload.org_id)
    return PolicyService.save_policy(
        org_id=payload.org_id,
        policy_data=payload.model_dump(),
        project_id=payload.project_id,
    )


@router.post("/org/{org_id}", status_code=status.HTTP_200_OK)
async def save_enterprise_policy_by_org(
    org_id: int,
    payload: PolicySaveRequest,
    actor: Dict[str, Any] = Depends(require_permission(Permission.OVERRIDE_POLICIES)),
):
    """Save or update organizational energy policies for specific org."""
    _enforce_tenant(actor, org_id)
    return PolicyService.save_policy(
        org_id=org_id,
        policy_data=payload.model_dump(),
        project_id=payload.project_id,
    )


@router.post("/evaluate")
async def evaluate_deployment_rules(
    payload: EvaluateRulesRequest,
    actor: Dict[str, Any] = Depends(get_current_actor),
):
    """Evaluate live candidate metrics against organizational energy rules to determine gate verdict."""
    _enforce_tenant(actor, payload.org_id)
    return PolicyService.evaluate_deployment_rules(
        org_id=payload.org_id,
        current_energy=payload.current_energy,
        baseline_energy=payload.baseline_energy,
        team_budget_consumed=payload.team_budget_consumed,
        team_budget_total=payload.team_budget_total,
        grid_intensity=payload.grid_intensity,
        project_id=payload.project_id,
    )

