"""GreenCode Auditor CLI - High-Performance CI/CD Gatekeeper & Local Terminal Suite.

Provides sub-200ms startup static carbon analysis, automated refactoring,
OASIS SARIF export, FOCUS 1.4 billing reconciliation, and AWS cloud integrations.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# GreenCode Engine Metadata
VERSION = "2.0.0"
ENGINE_NAME = "GreenCode Carbon & Energy Engine"
SPECIFICATION = "ISO/IEC 21031 (GSF SCI v1.0)"


# --------------------------------------------------------------------------- #
# Terminal Styling & Colors (ANSI)
# --------------------------------------------------------------------------- #
class Term:
    # Disable color if stdout is piped or NO_COLOR is set
    USE_COLOR = sys.stdout.isatty() and "NO_COLOR" not in os.environ

    RESET = "\033[0m" if USE_COLOR else ""
    BOLD = "\033[1m" if USE_COLOR else ""
    DIM = "\033[2m" if USE_COLOR else ""
    UNDERLINE = "\033[4m" if USE_COLOR else ""

    # Palette
    EMERALD = "\033[38;2;16;185;129m" if USE_COLOR else ""
    SKY = "\033[38;2;56;189;248m" if USE_COLOR else ""
    AMBER = "\033[38;2;245;158;11m" if USE_COLOR else ""
    ROSE = "\033[38;2;244;63;94m" if USE_COLOR else ""
    SLATE = "\033[38;2;148;163;184m" if USE_COLOR else ""
    WHITE = "\033[38;2;255;255;255m" if USE_COLOR else ""
    DARK_BG = "\033[48;2;15;23;42m" if USE_COLOR else ""


def _banner() -> None:
    print(f"\n{Term.BOLD}{Term.EMERALD}   ____                      _____          _      {Term.RESET}")
    print(f"{Term.BOLD}{Term.EMERALD}  / ___|_ __ ___  ___ _ __  / ____|___   __| | ___ {Term.RESET}")
    print(f"{Term.BOLD}{Term.EMERALD} | |  _| '__/ _ \\/ _ \\ '_ \\| |   / _ \\ / _` |/ _ \\{Term.RESET}")
    print(f"{Term.BOLD}{Term.EMERALD} | |_| | | |  __/  __/ | | | |__| (_) | (_| |  __/{Term.RESET}")
    print(f"{Term.BOLD}{Term.EMERALD}  \\____|_|  \\___|\\___|_| |_|\\_____\\___/ \\__,_|\\___|{Term.RESET}")
    print(f" {Term.DIM}AST Carbon & Energy Engine | {SPECIFICATION} | v{VERSION}{Term.RESET}\n")


# --------------------------------------------------------------------------- #
# Subcommand: check-keys (Diagnostic & Environment Inspector)
# --------------------------------------------------------------------------- #
def cmd_check_keys(args: argparse.Namespace) -> int:
    """Check and report the status of required & optional API keys."""
    _banner()
    print(f"{Term.BOLD}Environment & API Key Diagnostics:{Term.RESET}")
    print(f"{Term.SLATE}{'=' * 65}{Term.RESET}")

    # 1. GitHub Token
    gh_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if gh_token:
        # Mask token
        masked = gh_token[:4] + "..." + gh_token[-4:] if len(gh_token) > 8 else "***"
        print(f"  {Term.EMERALD}✔{Term.RESET} {Term.BOLD}GITHUB_TOKEN{Term.RESET}               : [{masked}] (Connected)")
        print(f"    {Term.DIM}↳ Unlocks: 5,000 req/hr GitHub API rate limit, private repo scans, PR bot comments{Term.RESET}")
    else:
        print(f"  {Term.AMBER}⚠{Term.RESET} {Term.BOLD}GITHUB_TOKEN{Term.RESET}               : {Term.AMBER}Not Set{Term.RESET} (Public rate limit: 60 req/hr)")
        print(f"    {Term.DIM}↳ Tip: Set via: export GITHUB_TOKEN=ghp_xxx (or PowerShell: $env:GITHUB_TOKEN='ghp_xxx'){Term.RESET}")

    # 2. AWS Credentials
    aws_key = os.environ.get("AWS_ACCESS_KEY_ID")
    aws_region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
    if aws_key:
        masked_aws = aws_key[:4] + "..." + aws_key[-4:] if len(aws_key) > 8 else "***"
        print(f"  {Term.EMERALD}✔{Term.RESET} {Term.BOLD}AWS_ACCESS_KEY_ID{Term.RESET}          : [{masked_aws}] (Region: {aws_region})")
        print(f"    {Term.DIM}↳ Unlocks: Amazon Bedrock (Claude 3.5 Sonnet refactor), S3 Audit Ledger, CloudWatch Gatekeeper{Term.RESET}")
    else:
        print(f"  {Term.AMBER}⚠{Term.RESET} {Term.BOLD}AWS_ACCESS_KEY_ID{Term.RESET}          : {Term.AMBER}Not Set{Term.RESET} (Using local heuristic mode)")
        print(f"    {Term.DIM}↳ Tip: Set AWS_ACCESS_KEY_ID & AWS_SECRET_ACCESS_KEY to unlock Amazon Bedrock synthesis{Term.RESET}")

    # 3. Electricity Maps
    emaps_key = os.environ.get("ELECTRICITY_MAPS_API_KEY")
    if emaps_key:
        masked_emaps = emaps_key[:4] + "..." + emaps_key[-4:] if len(emaps_key) > 8 else "***"
        print(f"  {Term.EMERALD}✔{Term.RESET} {Term.BOLD}ELECTRICITY_MAPS_API_KEY{Term.RESET}   : [{masked_emaps}] (Live Grid Feed)")
        print(f"    {Term.DIM}↳ Unlocks: Real-time marginal grid emission telemetry per ISO/IEC 21031{Term.RESET}")
    else:
        print(f"  {Term.SKY}ℹ{Term.RESET} {Term.BOLD}ELECTRICITY_MAPS_API_KEY{Term.RESET}   : {Term.SLATE}Using Built-in Global Grid Matrix{Term.RESET}")
        print(f"    {Term.DIM}↳ Uses authoritative cached emission factors (e.g. US-East PJM: 379 gCO2/kWh, Sweden: 18 gCO2/kWh){Term.RESET}")

    # 4. Database
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        print(f"  {Term.EMERALD}✔{Term.RESET} {Term.BOLD}DATABASE_URL{Term.RESET}               : {db_url.split('@')[-1] if '@' in db_url else db_url}")
    else:
        print(f"  {Term.SKY}ℹ{Term.RESET} {Term.BOLD}DATABASE_URL{Term.RESET}               : sqlite:///./greencode.db (Local zero-config)")

    print(f"{Term.SLATE}{'=' * 65}{Term.RESET}")
    print(f"\n{Term.EMERALD}{Term.BOLD}All core local AST engines are 100% operational offline without any keys.{Term.RESET}")
    print(f"{Term.DIM}Adding keys enables live cloud superpowers (Bedrock synthesis & automated PR comments).{Term.RESET}\n")
    return 0


# --------------------------------------------------------------------------- #
# Subcommand: scan (Audit File, Folder, Git Diff, or Remote Repo)
# --------------------------------------------------------------------------- #
def cmd_scan(args: argparse.Namespace) -> int:
    """Execute static AST carbon and energy audit on the specified target."""
    target = args.target or args.path or "."
    threshold = float(args.threshold)
    zone = args.zone
    quiet = args.quiet
    out_format = args.format.lower()

    if not quiet and out_format == "table":
        _banner()
        print(f"Target          : {Term.BOLD}{target}{Term.RESET}")
        print(f"Quality Gate    : {Term.BOLD}Score >= {threshold}/100.0{Term.RESET}")
        print(f"Grid Region     : {Term.SKY}{zone}{Term.RESET}")
        if args.diff:
            print(f"Diff Filter     : {Term.AMBER}{args.diff}{Term.RESET}")
        print(f"{Term.SLATE}{'-' * 70}{Term.RESET}")

    # Check for FOCUS CSV mode
    if args.focus_csv:
        from app.finops_focus import reconcile_focus_billing
        focus_path = os.path.abspath(args.focus_csv)
        if not os.path.isfile(focus_path):
            print(f"{Term.ROSE}[ERROR] FOCUS CSV file does not exist: {focus_path}{Term.RESET}", file=sys.stderr)
            return 1
        with open(focus_path, "r", encoding="utf-8", errors="replace") as f:
            res = reconcile_focus_billing(f.read())
        print(json.dumps(res, indent=2))
        return 0

    # Check for IaC file mode
    if args.iac:
        from app.iac_linter import audit_iac_content
        iac_path = os.path.abspath(args.iac)
        if not os.path.isfile(iac_path):
            print(f"{Term.ROSE}[ERROR] IaC manifest does not exist: {iac_path}{Term.RESET}", file=sys.stderr)
            return 1
        with open(iac_path, "r", encoding="utf-8", errors="replace") as f:
            res = audit_iac_content(f.read(), file_path=args.iac)
        if out_format == "json":
            print(json.dumps(res, indent=2))
        else:
            print(f"IaC Manifest: {iac_path}")
            print(f"Green Score : {res.get('green_score', 100.0)} / 100.0")
            print(f"Violations  : {len(res.get('violations', []))}")
        return 1 if (res.get("green_score", 100.0) < threshold) else 0

    # Diff Mode
    if args.diff:
        from app.parser import audit_git_diff
        import subprocess
        diff_arg = str(args.diff).strip()
        diff_text = ""
        if os.path.isfile(diff_arg):
            with open(diff_arg, "r", encoding="utf-8", errors="replace") as df:
                diff_text = df.read()
        else:
            repo_cwd = target if os.path.isdir(target) else "."
            proc = subprocess.run(
                ["git", "diff", "--unified=0", diff_arg],
                cwd=repo_cwd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            diff_text = proc.stdout or ""
        diff_res = audit_git_diff(diff_text, repo_root=target if os.path.isdir(target) else ".")
        result = {
            "repo_path": target,
            "total_files": diff_res.get("files_modified", 0),
            "total_lines": diff_res.get("hunks_evaluated", 0),
            "total_violations": diff_res.get("total_diff_violations", 0),
            "green_score": diff_res.get("diff_green_score", 100.0),
            "violations": diff_res.get("violations", []),
            "diff_mode": True,
        }
    else:
        # Determine whether target is a remote GitHub repo, a local file, or a directory
        is_remote_github = (
            target.startswith("http://") or
            target.startswith("https://") or
            (not os.path.exists(target) and "/" in target and not target.startswith(".") and not "\\" in target)
        )

        if is_remote_github:
            from app.github_client import download_repository_archive, normalize_repo_slug
            from app.parser import audit_zip_archive
            slug = normalize_repo_slug(target)
            if not quiet:
                print(f"Fetching remote GitHub archive for '{slug}'...")
            try:
                zip_path = download_repository_archive(slug)
                result = audit_zip_archive(zip_path)
                result["repo_path"] = f"github.com/{slug}"
            except Exception as exc:
                print(f"{Term.ROSE}[ERROR] Failed to fetch remote repository '{slug}': {exc}{Term.RESET}", file=sys.stderr)
                return 1
        elif os.path.isfile(target):
            from app.parser import audit_file
            res = audit_file(target)
            result = {
                "repo_path": target,
                "total_files": 1,
                "total_lines": res.get("lines_count") or res.get("lines_of_code") or 0,
                "total_violations": len(res.get("violations", [])),
                "green_score": res.get("green_score", 100.0),
                "violations": res.get("violations", []),
                "file_mode": True,
            }
        elif os.path.isdir(target):
            from app.parser import audit_repository
            result = audit_repository(target)
        else:
            print(f"{Term.ROSE}[ERROR] Target '{target}' not found (not a file, directory, or valid GitHub slug).{Term.RESET}", file=sys.stderr)
            return 1

    score = float(result.get("green_score", 100.0))
    violations: List[Dict[str, Any]] = result.get("violations", [])
    total_files = result.get("total_files", 0)
    total_lines = result.get("total_lines", 0)

    # ----------------------------------------------------------------------- #
    # Output Formats
    # ----------------------------------------------------------------------- #
    if out_format == "json":
        json_output = json.dumps(result, indent=2)
        if args.output:
            Path(args.output).write_text(json_output, encoding="utf-8")
        else:
            print(json_output)
    elif out_format == "sarif":
        from app.sarif import generate_sarif_report
        sarif_data = generate_sarif_report(result, output_path=args.output, base_dir=target if os.path.isdir(target) else ".")
        if not args.output:
            print(json.dumps(sarif_data, indent=2))
        else:
            if not quiet:
                print(f"{Term.EMERALD}[SARIF]{Term.RESET} OASIS SARIF v2.1.0 written to: {args.output}")
    elif out_format == "markdown":
        md = [
            f"## 🌿 GreenCode Carbon Quality Gate: {'PASSED' if score >= threshold else 'BLOCKED'}",
            f"- **Green Score**: `{score}/100.0` (Threshold: `{threshold}`)",
            f"- **Files Audited**: `{total_files}` | **Lines**: `{total_lines}`",
            f"- **Violations**: `{len(violations)}`",
            "",
            "| Severity | File:Line | Rule | Deduction | Guidance |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ]
        for v in violations[:15]:
            rel = v.get("relative_path") or v.get("file_path", "unknown")
            md.append(f"| **{v.get('severity')}** | `{rel}:{v.get('line_number')}` | {v.get('title')} | -{v.get('deduction')} pts | {v.get('suggested_fix')} |")
        md_text = "\n".join(md)
        if args.output:
            Path(args.output).write_text(md_text, encoding="utf-8")
        else:
            print(md_text)
    else:
        # Default: High-Density Table
        print(f"Total Files Audited : {Term.BOLD}{total_files}{Term.RESET}")
        print(f"Total Lines of Code : {Term.BOLD}{total_lines:,}{Term.RESET}")
        print(f"Total Violations    : {Term.BOLD}{len(violations)}{Term.RESET}")

        score_color = Term.EMERALD if score >= 80 else (Term.AMBER if score >= 60 else Term.ROSE)
        print(f"Overall Green Score : {score_color}{Term.BOLD}{score:.1f} / 100.0{Term.RESET}")
        print(f"{Term.SLATE}{'-' * 70}{Term.RESET}")

        if violations:
            print(f"{Term.BOLD}[!] DETECTED GREEN COMPUTING ANOMALIES:{Term.RESET}\n")
            violation_blocks = []
            for idx, v in enumerate(violations[:12], 1):
                sev = v.get("severity", "MEDIUM")
                sev_color = Term.ROSE if sev == "CRITICAL" else (Term.AMBER if sev == "HIGH" else Term.SKY)
                rel = v.get("relative_path") or v.get("file_path", "unknown")
                line = v.get("line_number", 1)
                ded = v.get("deduction", 0.0)

                entry = (
                    f"  {idx}. {sev_color}[{sev}]{Term.RESET} {Term.BOLD}{v.get('title')}{Term.RESET} ({Term.UNDERLINE}{rel}:{line}{Term.RESET})\n"
                    f"     Deduction: {Term.ROSE}-{ded} pts{Term.RESET} | Pattern: {Term.SLATE}{v.get('gsf_pattern', 'General')}{Term.RESET}\n"
                    f"     Fix      : {Term.EMERALD}{v.get('suggested_fix')}{Term.RESET}"
                )
                violation_blocks.append(entry)

            if violation_blocks:
                print("\n\n".join(violation_blocks) + "\n")

            if len(violations) > 12:
                print(f"  {Term.DIM}... and {len(violations) - 12} more bottlenecks omitted.{Term.RESET}\n")
            print(f"{Term.SLATE}{'-' * 70}{Term.RESET}")

        # Gate Result
        if score < threshold:
            print(f"{Term.ROSE}{Term.BOLD}[BLOCKED] Green Score {score:.1f} is BELOW threshold ({threshold:.1f}).{Term.RESET}")
            print(f"   Refactor flagged bottlenecks to reduce CPU energy & cloud carbon before merging.")
            print(f"{Term.SLATE}{'=' * 70}{Term.RESET}\n")
        else:
            print(f"{Term.EMERALD}{Term.BOLD}[PASSED] Green Score {score:.1f} meets criteria (>= {threshold:.1f}).{Term.RESET}")
            print(f"   Complies with Green Software Foundation ISO/IEC 21031 guidelines.")
            print(f"{Term.SLATE}{'=' * 70}{Term.RESET}\n")

    # GitHub Actions $GITHUB_OUTPUT support
    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        try:
            with open(gh_out, "a", encoding="utf-8") as gho:
                gho.write(f"green_score={score}\n")
                gho.write(f"total_violations={len(violations)}\n")
                gho.write(f"passed={str(score >= threshold).lower()}\n")
        except Exception:
            pass

    # Export SARIF if specifically requested via --sarif
    if args.sarif:
        from app.sarif import generate_sarif_report
        generate_sarif_report(result, output_path=args.sarif, base_dir=target if os.path.isdir(target) else ".")
        if not quiet:
            print(f"{Term.EMERALD}[SARIF]{Term.RESET} Exported: {args.sarif}")

    # PR Bot Commenting
    if args.pr and (args.repo_name or os.environ.get("GITHUB_REPOSITORY")):
        from app.github_client import post_pr_carbon_comment
        repo_slug = args.repo_name or os.environ.get("GITHUB_REPOSITORY")
        if repo_slug:
            if not quiet:
                print(f"Posting automated audit comment to PR #{args.pr} in {repo_slug}...")
            post_pr_carbon_comment(
                repo_full_name=repo_slug,
                pr_number=int(args.pr),
                scan_result=result,
                gate_threshold=threshold,
            )

    # Return exit code: 1 if score below threshold, 0 if passed
    return 1 if score < threshold else 0


# --------------------------------------------------------------------------- #
# Subcommand: fix (Apply Green Patches to Code)
# --------------------------------------------------------------------------- #
def cmd_fix(args: argparse.Namespace) -> int:
    """Analyze a file and apply green algorithmic refactorings."""
    target_file = os.path.abspath(args.file)
    if not os.path.isfile(target_file):
        print(f"{Term.ROSE}[ERROR] File not found: {target_file}{Term.RESET}", file=sys.stderr)
        return 1

    from app.parser import audit_file
    from app.optimizer import _synthesize_green_code

    with open(target_file, "r", encoding="utf-8", errors="replace") as f:
        original_code = f.read()

    audit_res = audit_file(target_file)
    violations = audit_res.get("violations", [])

    if not violations:
        print(f"{Term.EMERALD}✔ No carbon bottlenecks detected in {target_file}. Code is already green!{Term.RESET}")
        return 0

    print(f"\nFound {len(violations)} bottleneck(s) in {Term.BOLD}{target_file}{Term.RESET}:")
    summary_lines = [
        f"  {idx}. [{v.get('severity')}] {v.get('title')} (Line {v.get('line_number')})"
        for idx, v in enumerate(violations, 1)
    ]
    if summary_lines:
        print("\n".join(summary_lines))

    # Pick first or primary violation to refactor
    primary = violations[0]
    snippet = primary.get("code_snippet") or original_code
    synth_res = _synthesize_green_code(snippet, primary.get("violation_type", "inefficient_loop"), "python")
    fixed_code = synth_res.get("refactored_code", snippet) if isinstance(synth_res, dict) else str(synth_res)
    explanation = synth_res.get("explanation", "") if isinstance(synth_res, dict) else ""
    reduction_pct = synth_res.get("energy_reduction_pct", 0) if isinstance(synth_res, dict) else 0

    print(f"\n{Term.BOLD}--- Suggested Green Refactoring (-{reduction_pct}% Energy) ---{Term.RESET}")
    if explanation:
        print(f"{Term.DIM}{explanation}{Term.RESET}\n")
    print(f"{Term.EMERALD}{fixed_code}{Term.RESET}")
    print(f"{Term.BOLD}-------------------------------------------------------------{Term.RESET}")

    if args.apply:
        # Create backup
        backup_path = target_file + ".bak"
        with open(backup_path, "w", encoding="utf-8") as bf:
            bf.write(original_code)
        # Apply replacement if snippet found
        if snippet in original_code:
            new_full_code = original_code.replace(snippet, fixed_code, 1)
            with open(target_file, "w", encoding="utf-8") as wf:
                wf.write(new_full_code)
            print(f"{Term.EMERALD}✔ Successfully patched {target_file}! (Backup saved to {backup_path}){Term.RESET}")
        else:
            print(f"{Term.AMBER}⚠ Snippet could not be cleanly replaced automatically. Please verify diff manually.{Term.RESET}")
    else:
        print(f"\n{Term.DIM}Run with '--apply' (or '-y') to overwrite the file automatically with the green patch.{Term.RESET}")

    return 0


# --------------------------------------------------------------------------- #
# Subcommand: serve (FastAPI Server Daemon)
# --------------------------------------------------------------------------- #
def cmd_serve(args: argparse.Namespace) -> int:
    """Start the FastAPI backend server daemon."""
    import uvicorn
    print(f"\n{Term.EMERALD}{Term.BOLD}Starting GreenCode Auditor FastAPI server on port {args.port}...{Term.RESET}")
    uvicorn.run("app.main:app", host=args.host, port=args.port, reload=args.reload)
    return 0


# --------------------------------------------------------------------------- #
# Subcommand: aws (AWS native services)
# --------------------------------------------------------------------------- #
def cmd_aws(args: argparse.Namespace) -> int:
    """Forward subcommands to the AWS CLI module."""
    from app.aws_cli import main as aws_main
    return aws_main(args.aws_args)


# --------------------------------------------------------------------------- #
# Main Argument Parser
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="greencode",
        description="GreenCode Auditor - ISO/IEC 21031 Carbon Intensity & Energy Gatekeeper",
    )
    parser.add_argument("-V", "--version", action="version", version=f"GreenCode v{VERSION} ({SPECIFICATION})")

    subparsers = parser.add_subparsers(dest="subcommand", help="Available commands")

    # 1. SCAN (Default)
    scan_p = subparsers.add_parser("scan", help="Audit local file, folder, git diff, or remote GitHub repository")
    scan_p.add_argument("target", nargs="?", default=".", help="File, directory path, or remote GitHub slug (e.g. 'bottlepy/bottle')")
    scan_p.add_argument("--path", default=None, help="Alias for target path")
    scan_p.add_argument("--threshold", type=float, default=75.0, help="Minimum acceptable Green Score (0-100) before blocking (default: 75.0)")
    scan_p.add_argument("--format", choices=["table", "json", "sarif", "markdown"], default="table", help="Output format (default: table)")
    scan_p.add_argument("--output", "-o", default=None, help="Write output report to file")
    scan_p.add_argument("--zone", default="US-CAL-CISO", help="Grid region identifier (default: US-CAL-CISO)")
    scan_p.add_argument("--diff", default=None, help="Audit only modified lines in git diff range or .diff file")
    scan_p.add_argument("--iac", default=None, help="Audit Terraform, Kubernetes, or Dockerfile manifest")
    scan_p.add_argument("--focus-csv", default=None, help="Reconcile FinOps FOCUS 1.4 CSV billing file")
    scan_p.add_argument("--sarif", default=None, help="Export OASIS SARIF v2.1.0 file path")
    scan_p.add_argument("--pr", type=int, default=None, help="GitHub Pull Request number for bot commenting")
    scan_p.add_argument("--repo-name", default=None, help="GitHub repository name (e.g. 'owner/repo') for PR comments")
    scan_p.add_argument("--ci", action="store_true", help="Run in strict CI mode (fails with exit code 1 if score < threshold)")
    scan_p.add_argument("--quiet", "-q", action="store_true", help="Suppress non-essential banner and info")

    # 2. FIX
    fix_p = subparsers.add_parser("fix", help="Synthesize and apply green algorithmic refactoring patches")
    fix_p.add_argument("file", help="File to inspect and patch")
    fix_p.add_argument("--apply", "-y", action="store_true", help="Apply patch directly to the file with automatic .bak backup")

    # 3. CHECK-KEYS
    subparsers.add_parser("check-keys", help="Verify status and capabilities of GITHUB_TOKEN, AWS, and Electricity Maps keys")

    # 4. SERVE
    serve_p = subparsers.add_parser("serve", help="Start the FastAPI backend server daemon")
    serve_p.add_argument("--port", type=int, default=8000, help="Port to bind server (default: 8000)")
    serve_p.add_argument("--host", default="0.0.0.0", help="Host address to bind (default: 0.0.0.0)")
    serve_p.add_argument("--reload", action="store_true", help="Enable auto-reload on code change")

    # 5. AWS
    aws_p = subparsers.add_parser("aws", help="Interact with AWS Bedrock, S3 Ledger, CloudWatch, and SSM Parameter Store")
    aws_p.add_argument("aws_args", nargs=argparse.REMAINDER, help="Subcommand passed to app.aws_cli")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Entry point for greencode CLI."""
    # Ensure Windows console handles UTF-8 cleanly
    if sys.platform.startswith("win"):
        try:
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            if hasattr(sys.stderr, "reconfigure"):
                sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = build_parser()

    # If first argument is not a known subcommand or help flag, default to 'scan'
    args_list = list(sys.argv[1:] if argv is None else argv)
    known_subs = {"scan", "fix", "check-keys", "serve", "aws"}
    help_version = {"-h", "--help", "-V", "--version"}

    if args_list and args_list[0] not in known_subs and args_list[0] not in help_version:
        args_list.insert(0, "scan")
    elif not args_list:
        # Default with no arguments: show help
        parser.print_help()
        return 0

    parsed = parser.parse_args(args_list)

    if parsed.subcommand == "scan" or parsed.subcommand is None:
        return cmd_scan(parsed)
    elif parsed.subcommand == "fix":
        return cmd_fix(parsed)
    elif parsed.subcommand == "check-keys":
        return cmd_check_keys(parsed)
    elif parsed.subcommand == "serve":
        return cmd_serve(parsed)
    elif parsed.subcommand == "aws":
        return cmd_aws(parsed)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
