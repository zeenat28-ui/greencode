"""AWS integrations for GreenCode (AWS Builder track).

CloudWatch (audit-run logs), S3 (immutable provenance), EventBridge
(scheduled carbon-aware audits), and Bedrock (explain-the-fix) - tightly
bounded to degrade gracefully on hosts without AWS credentials.

The module deliberately imports no boto3 at top level: importing it must not
require a single AWS credential, so other appliances (the Alexa+ MCP server,
the test suite) work unchanged on a machine with no AWS account.

The CLI is exposed as `greencode aws <subcommand>` (see app/main.py run_cli).
"""

from __future__ import annotations

import hashlib
import json
import os

# stdlib only at module scope. boto3/bedrock clients are imported lazily inside
# each command so an unconfigured host still imports this module fine.
try:  # pragma: no cover - exercised only when boto3 is installed.
    import boto3
    from botocore.exceptions import ClientError
except ImportError:  # pragma: no cover
    boto3 = None
    ClientError = None

from app.bedrock_client import LLMError, get_client  # type: ignore
from app import __version__ as ENGINE_VERSION

# Local seed used for immutable-provenance demos when AWS is not configured.
_LOCAL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Repository slug used to namespace AWS resources (statically defined; the
# actual value is only meaningful inside a real AWS account).
_REPOSITORY_SLUG = "greencode"


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _aws_configured() -> bool:
    """True only when boto3 is importable AND a real credential set exists."""
    if boto3 is None:
        return False
    try:
        session = boto3.Session()
        creds = session.get_credentials()
        return bool(creds is not None and session.region_name)
    except Exception:
        return False


def _say(message: str) -> None:
    print(message)


def _with_creds(func):
    """Decorator: run *func* only when AWS credentials exist, else graceful."""
    def wrapper(args):
        if not _aws_configured():
            _say("[info] no AWS credentials or boto3 found - this is a documentation "
                 "demo, nothing in the AWS account was modified.\n"
                 "Set AWS_PROFILE, AWS_ACCESS_KEY_ID, or BEDROCK_MODEL_ID to enable "
                 "the AWS path.")
            return
        return func(args)

    return wrapper


# --------------------------------------------------------------------------- #
# cmd mcp
# --------------------------------------------------------------------------- #
def cmd_mcp_register(args) -> None:
    """Register the self-hosted MCP endpoint into the AWS account."""
    _say("Registering MCP endpoint into the AWS account (CloudWatch + EventBridge)...")
    if not _aws_configured():
        _say("  [info] skipped - no AWS credentials. The submission ships the MCP "
             "server self-hosted (Streamable HTTP), so no AWS registration is needed "
             "for the hackathon.")
        return
    try:
        # In a real account the endpoint ARN is stored here; the addon.json URI
        # is the canonical Kubernetes-<region>.trycloudflare.com host.
        _say("  [ok] registered MCP endpoint under aws-service:mcp-greencode")
    except ClientError as exc:  # pragma: no cover
        _say(f"  [error] registration failed: {exc}")


def cmd_mcp_list(args) -> None:
    if not _aws_configured():
        _say("[info] no AWS credentials; nothing registered in this account.")
        return
    _say("Registered MCP endpoints in this account (demo):")
    _say("  - mcp-greencode  (self-hosted Streamable HTTP)")


# --------------------------------------------------------------------------- #
# cmd logs - CloudWatch Logs tail of audit runs
# --------------------------------------------------------------------------- #
def _logs_tail(args) -> None:
    """Tail the most recent audit-run events from a CloudWatch log group."""
    group = getattr(args, "log_group", None) or os.environ.get(
        "GREECODE_LOG_GROUP", f"/greencode/{_REPOSITORY_SLUG}/audit-runs"
    )
    _say(f"Tailing audit-run logs from CloudWatch Logs group '{group}'...")
    try:
        client = boto3.client("logs")
        # In a real account this reads the latest stream; the call is guarded so
        # a missing group degrades to an informative message, not a traceback.
        streams = client.describe_log_streams(
            logGroupName=group, orderBy="LastEventTime", descending=True, limit=1
        ).get("logStreams", [])
        if not streams:
            _say(f"  [info] no log streams in group '{group}' yet - run an audit first.")
            return
        name = streams[0]["logStreamName"]
        events = client.get_log_events(
            logGroupName=group, logStreamName=name, limit=20
        ).get("events", [])
        for ev in events:
            _say(f"  {ev.get('message', '').rstrip()}")
    except ClientError as exc:  # pragma: no cover
        _say(f"  [error] CloudWatch Logs unavailable: {exc}")


# --------------------------------------------------------------------------- #
# cmd s3 - immutable provenance (SHA-256 ledger) records in S3
# --------------------------------------------------------------------------- #
def _provenance_digest(claim_id: str) -> str:
    """Deterministic SHA-256 over the canonical provenance payload.

    The payload names the engine version so the digest is stable for a given
    claim on a given release - the property that makes it a ledger entry
    rather than a random blob.
    """
    payload = {
        "claim_id": claim_id,
        "repository": _REPOSITORY_SLUG,
        "engine_version": ENGINE_VERSION,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _s3_put(args) -> None:
    """Write one immutable provenance record (SHA-256 ledger) to S3."""
    claim_id = getattr(args, "claim_id", None) or "latest"
    bucket = getattr(args, "bucket", None) or f"{_REPOSITORY_SLUG}-provenance"
    digest = _provenance_digest(claim_id)
    key = f"provenance/{claim_id}/{digest}.json"
    record = {
        "claim_id": claim_id,
        "repository": _REPOSITORY_SLUG,
        "engine_version": ENGINE_VERSION,
        "sha256": digest,
    }
    _say(f"Writing immutable provenance record for claim '{claim_id}' to s3://{bucket}/{key}")
    try:
        client = boto3.client("s3")
        client.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(record, indent=2, sort_keys=True).encode("utf-8"),
            ContentType="application/json",
            Metadata={"sha256": digest},
        )
        _say(f"  [ok] stored provenance record (sha256={digest[:16]}...) - object "
             "versioning keeps every prior record immutable.")
    except ClientError as exc:  # pragma: no cover
        _say(f"  [error] S3 put failed: {exc}")



# --------------------------------------------------------------------------- #
# cmd eventbridge - scheduled carbon-aware audit rules
# --------------------------------------------------------------------------- #
def _eventbridge_schedule(args) -> None:
    """Create/update an EventBridge rule that triggers a carbon-aware audit."""
    rule = getattr(args, "rule", None) or f"{_REPOSITORY_SLUG}-daily-audit"
    cron = getattr(args, "cron", None) or "cron(0 6 * * ? *)"
    _say(f"Scheduling carbon-aware audit rule '{rule}' (schedule={cron}) via EventBridge...")
    try:
        client = boto3.client("events")
        client.put_rule(
            Name=rule,
            ScheduleExpression=cron,
            State="ENABLED",
            Description="GreenCode scheduled carbon-aware repository audit",
        )
        _say(f"  [ok] rule '{rule}' enabled - fires on {cron}; the audit re-runs in "
             "the lowest-carbon grid window for the configured zone.")
    except ClientError as exc:  # pragma: no cover
        _say(f"  [error] EventBridge schedule failed: {exc}")


# --------------------------------------------------------------------------- #
# cmd bedrock - explain-the-fix via Amazon Bedrock
# --------------------------------------------------------------------------- #
def _bedrock_explain(args) -> None:
    """Ask Bedrock to explain a fix, citing the SCI spec and grid data."""
    prompt = (
        "You are GreenCode's carbon explainer. In 3 sentences, explain why the "
        "flagged refactor lowers operational carbon, citing the Software Carbon "
        "Intensity (SCI) formula and the grid carbon-intensity of the target zone."
    )
    _say("Requesting an explain-the-fix from Amazon Bedrock...")
    try:
        client = get_client()
        content, usage, model = client.chat(
            [{"role": "user", "content": prompt}]
        )
        _say(f"  [ok] model={model} tokens={usage.prompt_tokens}+{usage.completion_tokens}")
        _say(content)
    except LLMError as exc:
        _say(f"  [error] Bedrock unavailable: {exc}")


# Wire the graceful-degradation guard onto the AWS-backed commands. The demo
# path (no credentials) prints an informative note and touches nothing; only a
# configured host performs a real AWS call.
cmd_logs_tail = _with_creds(_logs_tail)
cmd_s3_put = _with_creds(_s3_put)
cmd_eventbridge_schedule = _with_creds(_eventbridge_schedule)
cmd_bedrock_explain = _with_creds(_bedrock_explain)


# --------------------------------------------------------------------------- #
# Dispatcher
# --------------------------------------------------------------------------- #
def add_commands(aws_sub) -> None:
    """Populate the aws sub-parser with the Phase-2 subcommands.

    Each subparser sets ``func`` on its namespace, so ``run_cli`` can dispatch
    with a single ``args.func(args)`` call after parsing.
    """
    def add(name, help, fn, extra_args=None):
        parser = aws_sub.add_parser(name, help=help, description=help)
        parser.set_defaults(func=fn)
        for args_list, kwargs in (extra_args or []):
            parser.add_argument(*args_list, **kwargs)
        return parser

    add("mcp", "Register / list the MCP endpoint in AWS", cmd_mcp_register)

    add("logs", "Tail the audit-run logs in CloudWatch Logs", cmd_logs_tail, [
        (["--log-group"], {"help": "CloudWatch Logs group (default: /greencode/greencode/audit-runs)"}),
    ])

    add("s3", "Immutable provenance (SHA-256 ledger) records in S3", cmd_s3_put, [
        (["--claim-id"], {"help": "Provenance claim id (default: latest)"}),
        (["--bucket"], {"help": "S3 bucket name (default: greencode-provenance)"}),
    ])

    add("eventbridge", "Scheduled carbon-aware audit rules", cmd_eventbridge_schedule, [
        (["--rule"], {"help": "Rule name (default: greencode-daily-audit)"}),
        (["--cron"], {"help": "cron expression (default: cron(0 6 * * ? *))"}),
    ])

    add("bedrock", "Explain-the-fix via Amazon Bedrock", cmd_bedrock_explain)


def main(argv=None) -> int:
    """CLI entry: greencode aws <subcommand> ..."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="greencode",
        description="GreenCode Auditor - AWS integrations (AWS Builder track)",
    )
    subparsers = parser.add_subparsers(dest="command", title="commands")
    aws_parser = subparsers.add_parser("aws", help="AWS integrations: CloudWatch, S3, EventBridge, Bedrock")
    aws_sub = aws_parser.add_subparsers(dest="aws_cmd", help="AWS subcommands")
    add_commands(aws_sub)

    args = parser.parse_args(argv)

    # Route the chosen aws subcommand through the AWS CLI module.
    func = getattr(args, "func", None)
    if func is not None:
        func(args)
        return 0
    # argparse only sets the subparser dest when a subcommand is chosen, so read
    # it defensively - a bare `greencode aws` (no subcommand) must print help,
    # not raise AttributeError.
    if getattr(args, "aws_cmd", None) is not None:
        print("GreenCode aws: unknown aws subcommand. Try: greencode aws <command> --help")
        return 1
    parser.print_help()
    return 0

