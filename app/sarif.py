"""OASIS SARIF (Static Analysis Results Interchange Format) v2.1.0 Exporter.

Enables native integration with GitHub Code Scanning alerts, the GitHub Security Tab,
and enterprise CI/CD SAST pipelines complying with OASIS SARIF v2.1.0 specifications.
"""

import json
import os
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from app.parser import VIOLATION_METADATA, ViolationType

SARIF_SCHEMA_URI = (
    "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json"
)
SARIF_VERSION = "2.1.0"
GREENCODE_VERSION = "1.0.0"

# Map GSF severity to SARIF level
SEVERITY_TO_SARIF_LEVEL = {
    "CRITICAL": "error",
    "HIGH": "error",
    "MEDIUM": "warning",
    "LOW": "note",
}


def _build_sarif_rules() -> List[Dict[str, Any]]:
    """Build SARIF rule metadata definitions for all Green Software Foundation anti-patterns."""
    rules = []
    for vtype, meta in VIOLATION_METADATA.items():
        sarif_level = SEVERITY_TO_SARIF_LEVEL.get(meta.get("severity", "MEDIUM"), "warning")
        rule_def = {
            "id": vtype,
            "name": "".join(word.capitalize() for word in vtype.split("_")),
            "shortDescription": {"text": meta.get("title", vtype)},
            "fullDescription": {"text": meta.get("description", "")},
            "help": {
                "text": f"{meta.get('description', '')}\n\nRemediation Guidance:\n{meta.get('fix_guidance', '')}\n\nGSF Pattern: {meta.get('gsf_pattern', 'General Efficiency')}",
                "markdown": f"**GSF Pattern**: `{meta.get('gsf_pattern', 'General Efficiency')}`\n\n{meta.get('description', '')}\n\n### Remediation Guidance\n{meta.get('fix_guidance', '')}\n\n*Energy Impact Deduction*: `-{meta.get('deduction', 0.0)} points`",
            },
            "defaultConfiguration": {"level": sarif_level},
            "properties": {
                "tags": [
                    "green-computing",
                    "energy-efficiency",
                    "sustainability",
                    "gsf-sci-v1.0",
                ],
                "precision": "high",
                "severity": meta.get("severity", "MEDIUM"),
                "deduction": meta.get("deduction", 0.0),
            },
        }
        rules.append(rule_def)
    return rules


def generate_sarif_report(
    scan_result: Dict[str, Any],
    output_path: Optional[str] = None,
    base_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Transform GreenCode Auditor scan results into official OASIS SARIF v2.1.0 format.

    Args:
        scan_result: The dictionary returned by audit_repository or audit_file.
        output_path: Optional file path to persist the generated JSON report.
        base_dir: Optional base directory to make artifact URIs relative for GitHub.

    Returns:
        Dictionary conforming to the SARIF 2.1.0 JSON schema.
    """
    repo_path = base_dir or scan_result.get("repo_path", "")
    violations = scan_result.get("violations", [])
    results: List[Dict[str, Any]] = []

    for v in violations:
        vtype = v.get("violation_type", "UNKNOWN")
        file_path = v.get("file_path", "")
        # Compute relative URI if base directory is available
        if repo_path and os.path.isabs(file_path):
            try:
                uri = os.path.relpath(file_path, repo_path).replace("\\", "/")
            except Exception:
                uri = file_path.replace("\\", "/")
        else:
            uri = file_path.replace("\\", "/")

        line_num = max(1, int(v.get("line_number", 1)))
        end_line = max(line_num, int(v.get("end_line_number", line_num)))
        severity = v.get("severity", "MEDIUM")
        sarif_level = SEVERITY_TO_SARIF_LEVEL.get(severity, "warning")

        message_text = f"[{severity}] {v.get('title', vtype)}: {v.get('description', '')}"

        snippet = v.get("snippet", "")
        region: Dict[str, Any] = {
            "startLine": line_num,
            "endLine": end_line,
            "startColumn": 1,
            "endColumn": 80,
        }
        if snippet:
            region["snippet"] = {"text": snippet[:300]}

        result_item: Dict[str, Any] = {
            "ruleId": vtype,
            "level": sarif_level,
            "message": {
                "text": message_text,
                "markdown": f"**{v.get('title', vtype)}**\n\n{v.get('description', '')}\n\n> **Suggested Fix**: {v.get('suggested_fix', '')}",
            },
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {
                            "uri": uri,
                            "uriBaseId": "%SRCROOT%",
                        },
                        "region": region,
                    }
                }
            ],
            "properties": {
                "deduction": v.get("deduction", 0.0),
                "language": v.get("language", "unknown"),
                "gsf_pattern": v.get("gsf_pattern", ""),
            },
        }

        # If fix guidance is provided, attach a proposed fix
        fix_guidance = v.get("suggested_fix")
        if fix_guidance:
            result_item["fixes"] = [
                {
                    "description": {"text": fix_guidance},
                }
            ]

        results.append(result_item)

    sarif_log: Dict[str, Any] = {
        "$schema": SARIF_SCHEMA_URI,
        "version": SARIF_VERSION,
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "GreenCode Auditor",
                        "version": GREENCODE_VERSION,
                        "informationUri": "https://github.com/zeenat28-ui/greencode",
                        "rules": _build_sarif_rules(),
                    }
                },
                "invocations": [
                    {
                        "executionSuccessful": True,
                        "endTimeUtc": datetime.now(timezone.utc).isoformat(),
                    }
                ],
                "results": results,
                "properties": {
                    "green_score": scan_result.get("green_score", 100.0),
                    "total_files": scan_result.get("total_files", 0),
                    "total_violations": len(violations),
                },
            }
        ],
    }

    if output_path:
        out_dir = os.path.dirname(os.path.abspath(output_path))
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(sarif_log, f, indent=2)

    return sarif_log


def generate_sonarqube_report(
    scan_result: Dict[str, Any],
    output_path: Optional[str] = None,
    base_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Transform GreenCode Auditor scan results into SonarQube Generic Issue Import JSON format.

    Enables native ingestion into SonarQube Community, Developer, and Enterprise editions
    via the standard `sonar.externalIssuesReportPaths=<path>` property.
    """
    repo_path = base_dir or scan_result.get("repo_path", "")
    violations = scan_result.get("violations", [])
    issues: List[Dict[str, Any]] = []

    # Map GSF severity to SonarQube Generic Issue severity
    sonar_severity_map = {
        "CRITICAL": "BLOCKER",
        "HIGH": "CRITICAL",
        "MEDIUM": "MAJOR",
        "LOW": "MINOR",
    }

    for v in violations:
        vtype = v.get("violation_type", "UNKNOWN")
        file_path = v.get("file_path", "")
        if repo_path and os.path.isabs(file_path):
            try:
                rel_file = os.path.relpath(file_path, repo_path).replace("\\", "/")
            except Exception:
                rel_file = file_path.replace("\\", "/")
        else:
            rel_file = file_path.replace("\\", "/")

        line_num = max(1, int(v.get("line_number", 1)))
        end_line = max(line_num, int(v.get("end_line_number", line_num)))
        severity = sonar_severity_map.get(v.get("severity", "MEDIUM"), "MAJOR")

        issue_entry = {
            "engineId": "greencode-auditor",
            "ruleId": vtype,
            "severity": severity,
            "type": "CODE_SMELL",
            "primaryLocation": {
                "message": f"[{v.get('severity', 'MEDIUM')}] {v.get('title', vtype)}: {v.get('description', '')} (Remediation: {v.get('suggested_fix', '')})",
                "filePath": rel_file,
                "textRange": {
                    "startLine": line_num,
                    "endLine": end_line,
                },
            },
            "effortMinutes": int(max(5, v.get("deduction", 5.0) * 3)),
        }
        issues.append(issue_entry)

    sonar_log = {"issues": issues}

    if output_path:
        out_dir = os.path.dirname(os.path.abspath(output_path))
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(sonar_log, f, indent=2)

    return sonar_log

