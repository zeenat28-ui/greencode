"""Operator notification for verification verdicts.

A verdict nobody reads is the same as no verdict, but a pipeline that blocks or
retries inside the request path is worse: a flaky Slack outage would stall
evidence intake. So dispatch is fire-and-forget with bounded retries, and every
failure is reported back in the response rather than raised - the ledger record
is the source of truth, notification is best-effort delivery of it.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.mailer import dispatch_email
from app.pipeline.config import PipelineConfig
from app.pipeline.verifier import Verdict, VERDICT_CONTRADICTED, VERDICT_INVALID

logger = logging.getLogger("greencode.pipeline.notify")

# Slack/Teams colour hints per verdict, so an operator can triage by colour
# alone in a channel scroll.
_COLOURS = {
    VERDICT_CONTRADICTED: "danger",
    "UNVERIFIED": "warning",
    "PARTIALLY_VERIFIED": "warning",
    "VERIFIED": "good",
}


def _requests():
    try:
        import requests  # imported lazily so the module loads without a network stack
        return requests
    except ImportError:  # pragma: no cover - requests is a hard dependency in practice
        return None


def _post_json(url: str, payload: Dict[str, Any], cfg: PipelineConfig) -> Dict[str, Any]:
    """POST JSON with bounded retries; never raises."""
    requests = _requests()
    if requests is None:
        return {"delivered": False, "error": "requests not installed"}
    last_error = ""
    for attempt in range(max(1, cfg.max_retries + 1)):
        try:
            resp = requests.post(url, json=payload, timeout=cfg.http_timeout_seconds)
            if resp.status_code < 400:
                return {"delivered": True, "status_code": resp.status_code}
            last_error = f"HTTP {resp.status_code}"
            # 4xx will not become a 2xx on retry; only 5xx and 429 are worth another go.
            if resp.status_code < 500 and resp.status_code != 429:
                break
        except Exception as exc:
            last_error = str(exc)
        logger.warning(
            "Pipeline notification attempt %s/%s failed: %s",
            attempt + 1, cfg.max_retries + 1, last_error,
        )
    return {"delivered": False, "error": last_error}



def build_slack_payload(verdict: Verdict) -> Dict[str, Any]:
    """Slack Block Kit message describing a verdict."""
    colour = _COLOURS.get(verdict.verdict, "good")
    observed = (
        f"{verdict.observed_reduction_pct:.2f}%"
        if verdict.observed_reduction_pct is not None
        else "not measured"
    )
    lines = [
        f"*Claim:* `{verdict.claim_id}` on `{verdict.repo}`",
        f"*Verdict:* *{verdict.verdict}* (confidence {verdict.confidence:.2f})",
        f"*Predicted:* {verdict.predicted_reduction_pct:.2f}% energy reduction",
        f"*Observed:* {observed}",
        f"*Evidence:* {verdict.evidence_count} sample(s), "
        f"{verdict.hardware_evidence_count} hardware-measured",
    ]
    if verdict.reasons:
        lines.append(f"*Why:* {verdict.reasons[0]}")
    if verdict.gaps:
        lines.append(f"*To close this:* {verdict.gaps[0]}")
    return {
        "text": f"GreenCode verification: {verdict.verdict} for {verdict.claim_id}",
        "attachments": [{
            "color": colour,
            "blocks": [
                {"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(lines)}}
            ],
        }],
    }


def build_teams_payload(verdict: Verdict) -> Dict[str, Any]:
    """Teams connector card describing a verdict."""
    observed = (
        f"{verdict.observed_reduction_pct:.2f}%"
        if verdict.observed_reduction_pct is not None
        else "not measured"
    )
    return {
        "@type": "MessageCard",
        "@context": "https://schema.org/extensions",
        "themeColor": "D32F2F" if verdict.verdict == VERDICT_CONTRADICTED else "2E7D32",
        "summary": f"GreenCode verification: {verdict.verdict}",
        "title": f"GreenCode Verification: {verdict.verdict}",
        "sections": [{
            "facts": [
                {"name": "Claim", "value": verdict.claim_id},
                {"name": "Repository", "value": verdict.repo},
                {"name": "Predicted reduction", "value": f"{verdict.predicted_reduction_pct:.2f}%"},
                {"name": "Observed reduction", "value": observed},
                {"name": "Hardware samples", "value": str(verdict.hardware_evidence_count)},
            ],
            "text": verdict.reasons[0] if verdict.reasons else "",
        }],
    }


def notify(verdict: Verdict, cfg: PipelineConfig) -> List[Dict[str, Any]]:
    """Dispatch a verdict to every configured channel.

    Returns a per-channel delivery report. Never raises: a notification failure
    must not roll back the ledger entry, because the ledger is the record of
    truth and the notification is only its announcement.
    """
    results: List[Dict[str, Any]] = []

    if cfg.slack_webhook_url:
        result = _post_json(cfg.slack_webhook_url, build_slack_payload(verdict), cfg)
        result["channel"] = "slack"
        results.append(result)

    if cfg.teams_webhook_url:
        result = _post_json(cfg.teams_webhook_url, build_teams_payload(verdict), cfg)
        result["channel"] = "teams"
        results.append(result)

    if cfg.notify_email_to:
        # Only the outcomes an operator must act on earn an email; sending one
        # for every routine confirmation trains people to ignore the channel.
        if verdict.verdict in (VERDICT_CONTRADICTED, VERDICT_INVALID):
            subject = f"[GreenCode] {verdict.verdict}: {verdict.repo} ({verdict.claim_id})"
            body = "\n".join(
                [f"Verdict: {verdict.verdict}", f"Confidence: {verdict.confidence:.2f}"]
                + [f"Reason: {r}" for r in verdict.reasons]
                + [f"Next step: {g}" for g in verdict.gaps]
            )
            for recipient in cfg.notify_email_to:
                try:
                    outcome = dispatch_email(recipient, subject, f"<pre>{body}</pre>", body)
                    results.append({
                        "channel": "email",
                        "delivered": bool(outcome.get("success")),
                        "to": recipient,
                        "mode": outcome.get("mode"),
                    })
                except Exception as exc:  # pragma: no cover - defensive
                    results.append({"channel": "email", "delivered": False, "error": str(exc)})

    if not results:
        results.append({
            "channel": "none",
            "delivered": False,
            "error": "no notification channel configured",
        })
    return results

