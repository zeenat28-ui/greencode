# Friction Log — GreenCode (Build, Ship, Shape: Amazon Developer Hackathon)

Real problems we hit while building the Alexa+ / AWS submission, what we
expected, what actually happened, and the workaround. This is the raw signal
the engineering team asked for.

## 1. `aws` command not found after installing AWS CLI v2

- **What we tried:** Installed `AWSCLIV2.msi`, opened the *already running*
  PowerShell window, ran `aws --version`.
- **Expected:** `aws-cli/2.x.x`.
- **Got:** `The term 'aws' is not recognized as the name of a cmdlet...`
- **Why:** The MSI installs the binary correctly
  (`C:\Program Files\Amazon\AWSCLIV2\aws.exe`) and updates the *machine* PATH,
  but a shell opened before the install keeps its stale PATH copy.
- **Fix:** Close and reopen the terminal (or run the absolute path once to
  confirm the install). "Command not found right after install" reads like a
  broken installer when it is only an environment refresh.

## 2. Alexa+ deploy path requires an AWS account with a card on file

- **What we tried:** `aws configure --profile alexa-ai` → no access key yet →
  followed the console flow, which lands on signup asking for a card
  (`$1` verification hold).
- **Expected:** A free path to a key, like most developer programs.
- **Got:** Billing Information / card wall before an IAM user could get an
  access key, so `aws codeartifact login` and `npm install -g @alexa-ai/cli`
  were unreachable without it.
- **Why:** The Alexa+ CLI ships through a private CodeArtifact registry gated
  behind AWS auth; AWS gates new accounts behind card verification.
- **Workaround:** The hackathon explicitly allows testing in the web simulator
  *or* a device, and hosting is not required for submission. We shipped the
  self-hosted MCP server + `alexa/addon.json` manifest + compliance proofs
  (`check_mcp_alexa.py`, `check_mcp_live.py`) so judges can verify with one
  command, and documented the exact `alexa-ai configure` / `alexa-ai deploy`
  steps for anyone with an AWS account. No AWS billing is used anywhere in the

## 6. Amazon-hosted vs self-hosted manifest confusion

- **What we tried:** Compared our `alexa/addon.json` against the sample in the
  Alexa+ dashboard screenshot, which showed `mcpServer` + `regionalEndpoints`
  on an `execute-api...amazonaws.com` domain.
- **Expected:** That our manifest was missing fields.
- **Got:** The 37-schema compliance tests passed with our shape.
- **Why:** Two different hosting modes. `regionalEndpoints` is what *Amazon*
  fills in when **they** host your server behind their own API Gateway (the
  hotel-booking demo). Self-hosted add-ons use
  `integrations[0].type = "MCP"` with `config.endpoints.default.uri` pointing
  at your own HTTPS endpoint — exactly what our manifest has. Following the
  screenshot would have been wrong for us.
- **Takeaway:** The dashboard sample is not a template for self-hosted
  servers; the compliance tests are the source of truth.

## 7. Inline `python -c "..."` quoting kept breaking inside PowerShell

- **What we tried:** Running multi-line Python one-liners through
  `powershell -Command "python -c \"...\""`.
- **Expected:** Script output.
- **Got:** `Missing expression after ','`, `Missing closing ')'` — PowerShell
  re-parsed the Python source as its own language after `$`-expansion and
  quote unescaping shuffled the boundaries.
- **Fix:** Moved every verification step into real files under `vfy/`
  (`check_manifest.py`, `verify_submission.py`) and run those. Anything more
  than one line of Python deserves a file — this cost real debugging minutes.

## 8. Devpost site blocks automated fetching (HTTP 403)

- **What we tried:** Reading the hackathon rules page directly to confirm
  submission requirements.
- **Expected:** The rules page.
- **Got:** `403 Forbidden` for programmatic requests.
- **Workaround:** Used publicly mirrored rule listings plus Amazon's official
  announcement to reconstruct the checklist (6 required submission fields,
  judging criteria, +10% friction-log bonus), then verified each item against
  our own repo.

## 9. The Alexa mobile app is not available in our region's store

- **What we tried:** Searching Play Store for "HeyAlex" / "Alexa setup".
- **Expected:** The official app.
- **Got:** Not available / wrong look-alike apps in the results.
- **Why:** Amazon's Alexa app is not distributed in all storefronts, and voice
  testing also assumes a US marketplace + English (US) language setting for
  Alexa+ features.
- **Fix:** Skipped the phone entirely — the documented flow explicitly allows
  the **web simulator** for testing, which is what we used. No Echo device was
  required for the hackathon.

## 10. `alexa-ai` CLI install is a 3-step private-registry dance

- **What we tried:** `npm install -g @alexa-ai/cli` from a default registry.
- **Expected:** The package to resolve.
- **Got:** 404 — the CLI lives in a private AWS CodeArtifact repository.
- **Fix:** Documented sequence: `aws configure --profile alexa-ai` →
  `aws codeartifact login --tool npm --domain alexa-ai ...` → `npm install`.
  The `codeartifact login` token expires every 12 hours, so a fresh install on
  a new machine must redo step 2. Flagging because "install our CLI" normally
  means one command, and the expiry silently breaks later installs.

  project code — Bedrock access is optional and degrades gracefully
  (`app/bedrock_client.py` imports boto3 lazily; the app falls back to the
  local rule-based refactorer).

## 3. Cloudflare quick tunnels rotate their domain on every restart

- **What we tried:** Pointed `alexa/addon.json` at the first
  `*.trycloudflare.com` URL we got.
- **Expected:** The URL stays valid until judging.
- **Got:** Every restart issues a brand-new random domain
  (`constitutional-options...` → `suggestion-emily-beatles-italiano...`), which
  silently breaks the endpoint URI, the privacy/terms URLs and every icon URL
  in the manifest at once.
- **Fix:** `scripts/start_mcp_remote.ps1` now rewrites every
  `https://*.trycloudflare.com` occurrence inside `alexa/addon.json` right
  after the tunnel prints its URL, and re-adds the new host to
  `GREENCODE_MCP_ALLOWED_HOSTS`. For a stable judging link, swap the quick
  tunnel for a named Cloudflare tunnel — the script is the only thing that
  changes.

## 4. Public URL answered `421` for every MCP request (DNS-rebinding guard)

- **What we tried:** Opened the fresh tunnel URL and POSTed to `/mcp`.
- **Expected:** `401` (no token) per the Alexa+ checklist.
- **Got:** `421 Misdirected Request` from the MCP transport.
- **Why:** The Python MCP streamable-HTTP transport refuses requests whose
  `Host` header is not loopback unless it is explicitly allow-listed — a
  legitimate DNS-rebinding defense that makes every tunneled request fail until
  configured.
- **Fix:** The start script appends the tunnel host to
  `GREENCODE_MCP_ALLOWED_HOSTS` automatically. Documented in the script header
  because it is the difference between "server is broken" and "server is
  correctly locked down".

## 5. cloudflared prints the tunnel URL to stderr, not stdout

- **What we tried:** Started `cloudflared tunnel --url ...` with only stdout
  redirected to a file and waited for the URL.
- **Expected:** URL appears in the log file.
- **Got:** Timed out waiting, even though the tunnel was healthy.
- **Why:** cloudflared's log stream (which contains the `https://...` line)
  goes to stderr.
- **Fix:** The wait loop reads both the stdout and stderr redirect files.
