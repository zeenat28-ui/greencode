"""Tests for the Infrastructure-as-Code (Terraform, Kubernetes, Dockerfile) FinOps & GreenOps Linter."""

from fastapi.testclient import TestClient

from app.iac_linter import audit_iac_content
from app.main import app

client = TestClient(app)


def test_terraform_graviton_and_gp3_linting():
    tf_code = (
        'resource "aws_instance" "web" {\n'
        '  ami           = "ami-123456"\n'
        '  instance_type = "c5.2xlarge"\n'
        '}\n'
        'resource "aws_ebs_volume" "data" {\n'
        '  type = "gp2"\n'
        '  size = 100\n'
        '}\n'
        'resource "aws_cloudwatch_log_group" "app_logs" {\n'
        '  name = "/aws/app/prod"\n'
        '}\n'
    )
    res = audit_iac_content(tf_code, file_path="infra/main.tf")
    assert res["iac_type"] == "terraform"
    assert res["total_findings"] == 3
    rule_ids = {f["rule_id"] for f in res["findings"]}
    assert "IAC_TF_NON_GRAVITON_EC2" in rule_ids
    assert "IAC_TF_LEGACY_GP2_EBS" in rule_ids
    assert "IAC_TF_UNBOUNDED_LOG_RETENTION" in rule_ids
    assert res["estimated_monthly_usd_savings"] > 100.0
    assert res["estimated_annual_co2_saved_kg"] > 100.0


def test_kubernetes_and_dockerfile_iac_endpoints():
    r_rules = client.get("/api/kubernetes/iac-rules")
    assert r_rules.status_code == 200
    assert r_rules.json()["count"] >= 8

    k8s_yaml = (
        "apiVersion: apps/v1\n"
        "kind: Deployment\n"
        "metadata:\n"
        "  name: payment-worker\n"
        "spec:\n"
        "  template:\n"
        "    spec:\n"
        "      containers:\n"
        "        - name: worker\n"
        "          image: myorg/worker:latest\n"
    )
    r_k8s = client.post(
        "/api/kubernetes/iac-audit",
        json={"content": k8s_yaml, "file_path": "k8s/deployment.yaml"},
    )
    assert r_k8s.status_code == 200
    body = r_k8s.json()
    assert body["iac_type"] == "kubernetes"
    assert body["total_findings"] == 2

    dockerfile = "FROM python:3.11\nRUN apt-get update && apt-get install -y gcc\n"
    r_docker = client.post(
        "/api/kubernetes/iac-audit",
        json={"content": dockerfile, "file_path": "Dockerfile"},
    )
    assert r_docker.status_code == 200
    d_body = r_docker.json()
    assert d_body["iac_type"] == "dockerfile"
    assert d_body["total_findings"] == 2


def test_terraform_variable_and_locals_resolution():
    tf_with_vars = (
        'variable "app_instance_type" {\n'
        '  default = "m5.2xlarge"\n'
        '}\n'
        'locals {\n'
        '  ebs_tier = "gp2"\n'
        '}\n'
        'resource "aws_instance" "api" {\n'
        '  instance_type = var.app_instance_type\n'
        '}\n'
        'resource "aws_ebs_volume" "logs" {\n'
        '  type = local.ebs_tier\n'
        '}\n'
    )
    res = audit_iac_content(tf_with_vars, file_path="infra/vars.tf")
    rule_ids = {f["rule_id"] for f in res["findings"]}
    assert "IAC_TF_NON_GRAVITON_EC2" in rule_ids
    assert "IAC_TF_LEGACY_GP2_EBS" in rule_ids

