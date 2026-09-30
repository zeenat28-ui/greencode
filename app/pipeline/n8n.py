"""Generator for the importable n8n workflow.

Kept as code rather than a checked-in JSON blob so the API URL, webhook path and
Slack target can be re-pointed for a new environment by re-running a function
instead of hand-editing three nested JSON strings.

The topology deliberately mirrors the Wazuh + n8n + AI pipeline pattern:

    Webhook -> Code (normalise) -> HTTP Request (file) -> If -> If1 -> Send message

The one deliberate difference: the classification and the verdict are computed by
GreenCode itself, not by JavaScript inside n8n. A decision about whether a carbon
claim is real belongs in the audited, hash-chained ledger - not in a workflow
canvas where nobody can tell what ran six months ago.
"""

from __future__ import annotations

import json
from typing import Any, Dict

WORKFLOW_NAME = "GreenCode Reality Verification Pipeline"

# Runs before the HTTP Request node. Kept as a string constant so the emitted
# workflow is byte-stable across regenerations.
NORMALISE_JS = """// Normalise the incoming payload into a GreenCode evidence record.
// The webhook accepts CI runners, Wazuh alerts and the GitHub Actions gate;
// all of them are mapped onto one evidence shape here so the API never has to
// guess which sender it is talking to.
const crypto = require('crypto');

const out = [];
for (const item of $input.all()) {
  const b = item.json.body ?? item.json;

  // GitHub Actions runners already report kWh; the API speaks joules.
  const rawJoules = b.energy_joules ?? b.energy ?? b.it_energy_joules ?? 0;
  const joules = b.energy_kwh !== undefined
    ? Number(b.energy_kwh) * 3.6e9
    : Number(rawJoules);

  out.push({
    json: {
      event_id: b.event_id || ('n8n_' + crypto.randomUUID()),
      claim_id: b.claim_id || 'unlinked',
      evidence_id: b.evidence_id || b.run_id || ('run_' + Date.now()),
      energy_joules: joules,
      duration_seconds: Number(b.duration_seconds ?? b.duration ?? 1),
      functional_unit: Number(b.functional_unit ?? b.requests ?? b.R ?? 1),
      measurement_method: b.measurement_method || b.method || 'model',
      carbon_intensity: Number(b.carbon_intensity ?? b.grid_intensity ?? 380),
      source: b.source || 'n8n',
      metadata: {
        received_from: 'n8n',
        repository: b.repository ?? b.repo ?? null,
        alert_level: b.alert_level ?? b.severity ?? null,
      },
    },
  });
}

return out;
"""


def _node(node_id: str, name: str, ntype: str, type_version: int, position, parameters) -> Dict[str, Any]:
    return {
        "parameters": parameters,
        "id": node_id,
        "name": name,
        "type": ntype,
        "typeVersion": type_version,
        "position": position,
    }


def _slack_message(node_id: str, name: str, position, text_expression: str) -> Dict[str, Any]:
    node = _node(
        node_id, name, "n8n-nodes-base.slack", 2.2, position,
        {
            "method": "POST",
            "url": "={{ $env.GREENCODE_SLACK_WEBHOOK }}",
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": text_expression,
            "options": {},
        },
    )
    node["webhookId"] = node_id.replace("a1000000", "b6a1b1a1")
    return node


def _if_node(node_id: str, name: str, position, right_value: str) -> Dict[str, Any]:
    return _node(
        node_id, name, "n8n-nodes-base.if", 2.2, position,
        {
            "conditions": {
                "options": {
                    "caseSensitive": True,
                    "leftValue": "",
                    "typeValidation": "strict",
                    "version": 2,
                },
                "conditions": [
                    {
                        "id": f"cond-{right_value.lower()}",
                        "leftValue": "={{ $json.verdict }}",
                        "rightValue": right_value,
                        "operator": {"type": "string", "operation": "equals"},
                    }
                ],
                "combinator": "and",
            },
            "options": {},
        },
    )


def _slack_text(prefix: str, emoji: str) -> str:
    return (
        "={{ JSON.stringify({ text: '"
        + emoji + " *GreenCode: claim " + prefix + "*\\\\nClaim: ' + "
        + "($json.ledger_entry?.claim_id || 'n/a') + '\\\\n' + "
        + "($json.ledger_entry?.summary || '') }) }}"
    )


def build_workflow(
    api_url: str = "http://localhost:8000",
    webhook_path: str = "greencode-evidence",
) -> Dict[str, Any]:
    """Build the importable n8n workflow definition.

    Args:
        api_url: Base URL of the GreenCode API the evidence node posts to.
        webhook_path: Path segment the intake webhook is exposed on.
    """
    nodes = [
        _node(
            "a1000000-0000-4000-8000-000000000001",
            "Webhook (CI / Wazuh / Runner)",
            "n8n-nodes-base.webhook",
            2,
            [-220, 300],
            {
                "httpMethod": "POST",
                "path": webhook_path,
                "responseMode": "responseNode",
                "options": {},
            },
        ),
        _node(
            "a1000000-0000-4000-8000-000000000002",
            "Code: Normalise Evidence",
            "n8n-nodes-base.code",
            2,
            [0, 300],
            {"jsCode": NORMALISE_JS},
        ),
        _node(
            "a1000000-0000-4000-8000-000000000003",
            "HTTP Request: File Evidence",
            "n8n-nodes-base.httpRequest",
            4.2,
            [220, 300],
            {
                "method": "POST",
                "url": f"{api_url.rstrip('/')}/api/pipeline/evidence",
                "sendBody": True,
                "specifyBody": "json",
                "jsonBody": "={{ JSON.stringify($json) }}",
                "options": {"timeout": 15000},
            },
        ),
        _if_node(
            "a1000000-0000-4000-8000-000000000004",
            "If: Claim Contradicted?",
            [440, 300],
            "CONTRADICTED",
        ),
        _if_node(
            "a1000000-0000-4000-8000-000000000005",
            "If1: Verified?",
            [660, 180],
            "VERIFIED",
        ),
        _slack_message(
            "a1000000-0000-4000-8000-000000000006",
            "Send a message (alert)",
            [880, 60],
            _slack_text("CONTRADICTED", "\U0001F6A8"),
        ),
        _slack_message(
            "a1000000-0000-4000-8000-000000000007",
            "Send a message1 (confirmed)",
            [880, 300],
            _slack_text("VERIFIED", "✅"),
        ),
        _slack_message(
            "a1000000-0000-4000-8000-000000000008",
            "Send a message2 (pending)",
            [880, 500],
            _slack_text("needs more evidence", "\U0001F7E1"),
        ),
    ]

    def link(src: str, targets):
        return {"main": [[{"node": t, "type": "main", "index": 0}] for t in targets]}

    return {
        "name": WORKFLOW_NAME,
        "nodes": nodes,
        "connections": {
            "Webhook (CI / Wazuh / Runner)": link(
                "Webhook (CI / Wazuh / Runner)", ["Code: Normalise Evidence"]
            ),
            "Code: Normalise Evidence": link(
                "Code: Normalise Evidence", ["HTTP Request: File Evidence"]
            ),
            "HTTP Request: File Evidence": link(
                "HTTP Request: File Evidence", ["If: Claim Contradicted?"]
            ),
            "If: Claim Contradicted?": {
                "main": [
                    [{"node": "Send a message (alert)", "type": "main", "index": 0}],
                    [{"node": "If1: Verified?", "type": "main", "index": 0}],
                ]
            },
            "If1: Verified?": {
                "main": [
                    [{"node": "Send a message1 (confirmed)", "type": "main", "index": 0}],
                    [{"node": "Send a message2 (pending)", "type": "main", "index": 0}],
                ]
            },
        },
        "settings": {"executionOrder": "v1"},
        "active": False,
        "meta": {"instanceId": "greencode-reality-pipeline"},
        "tags": [
            {"name": "greencode"},
            {"name": "carbon"},
            {"name": "verification"},
        ],
        "pinData": {},
    }


def export(path: str, api_url: str = "http://localhost:8000") -> str:
    """Write the workflow JSON to `path` and return the path."""
    workflow = build_workflow(api_url=api_url)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(workflow, fh, indent=2)
    return path

