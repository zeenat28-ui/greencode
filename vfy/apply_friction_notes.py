"""Apply the 'runnable notes' (### Run it to verify) to the tracked friction-log
sections the plan tracks: #1 (aws cmd), #2 (Alexa+ card), #7 (PowerShell
quoting), #9 (Alexa app region), #10 (alexa-ai CLI private registry).
"""
import io

PATH = "FRICTION_LOG.md"

NOTES = {
    "broken installer when it is only an environment refresh.": (
        "### Run it to verify\n"
        "- Reopen the terminal, then `get-command aws` shows the MSI binary in\n"
        "  `C:\\Program Files\\Amazon\\AWSCLIV2` (a stale pre-install shell keeps the old\n"
        "  PATH - this is an environment refresh, not a broken installer).\n"
        "- `python -c \"import shutil; print(shutil.which('aws'))\"` resolves PATH the\n"
        "  same way a non-interactive shell does.\n"
    ),
    "command, and documented the exact `alexa-ai configure`": (
        "### Run it to verify\n"
        "- `aws sts get-caller-identity` (or `aws configure list`) returns your account -\n"
        "  no card is required for MCP-only work.\n"
        "- `python check_mcp_live.py` prints `ALL LIVE MCP CHECKS PASSED` on a loopback\n"
        "  server, so judges verify the submission with one command and no AWS billing.\n"
        "- Self-hosting the MCP server means `alexa-ai deploy` (private CodeArtifact\n"
        "  registry) is optional for the submission.\n"
    ),
    "and run those. Anything more": (
        "### Run it to verify\n"
        "- `python vfy\\check_manifest.py --manifest alexa/addon.json` and\n"
        "  `python vfy\\verify_submission.py` (already produced by this friction fix) are\n"
        "  the only commands you need for the Alexa+ checklist.\n"
        "- Anything more than one line of Python belongs in `vfy/`, not in a\n"
        "  `powershell -Command \"python -c ...\"` one-liner.\n"
    ),
    "which is what we used. No Echo device was": (
        "### Run it to verify\n"
        "- The Alexa+ checking script confirms the live end-to-end state in the browser\n"
        "  web simulator: `python check_mcp_alexa.py --url <tunnel> --token $env:GREENCODE_MCP_TOKEN`\n"
        "  prints the checklist (401 + PRM + PKCE + DNS-rebind + <500ms).\n"
        "- No physical Echo device is needed: the web simulator is the documented,\n"
        "  submission-allowed path.\n"
    ),
    "expiry silently breaks later installs.": (
        "### Run it to verify\n"
        "- The private-registry dance only matters if you install `alexa-ai`\n"
        "  (`@alexa-ai/cli`). The shipped submission is self-hosted MCP + `addon.json`,\n"
        "  so the command that matters is `python check_mcp_live.py` (prints\n"
        "  `ALL LIVE MCP CHECKS PASSED`).\n"
        "- If you do install the CLI, `aws codeartifact login --tool npm` tokens expire\n"
        "  every 12 hours - re-run step 2 on a new machine; that expiry is why later\n"
        "  installs appear to 404. See `scripts/start_mcp_remote.ps1`.\n"
    ),
}

PAIRS = list(NOTES.items())


def main():
    with io.open(PATH, encoding="utf-8") as fh:
        lines = fh.readlines()

    inserted = 0
    for idx, line in enumerate(lines):
        for anchor, note in PAIRS:
            if anchor in line:
                indent = line[:len(line) - len(line.lstrip())]
                lines.insert(idx + 1, indent + note)
                inserted += 1
                PAIRS.remove((anchor, note))
                break

    if PAIRS:
        print("WARN: anchors not all found in FRICTION_LOG.md:")
        for anchor, _ in PAIRS:
            print(f"  - {anchor!r}")
        return 1

    with io.open(PATH, "w", encoding="utf-8") as fh:
        fh.writelines(lines)

    print(f"Inserted {inserted} 'Run it to verify' blocks into {PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
