# API Keys & Credentials Guide

Every external service GreenCode talks to, where to get the credential, which
environment variable holds it, and what breaks without it.

Run `python -m app.cli check-keys` at any time to see the live status of the
keys on the current machine.

---

## 1. GitHub — `GITHUB_TOKEN`

**Needed for:** PR diff auditing (`audit_diff`), repository listing, PR comments,
and the `RefactorCode` action. Without it, GitHub's anonymous rate limit of
60 requests/hour applies, which the voice surface will hit quickly.

**How to get it:**

1. Sign in to GitHub → [Settings → Developer settings](https://github.com/settings/tokens)
2. Open the **Personal access tokens → Fine-grained tokens** tab
3. Click **Generate new token**
4. Set an expiry, then grant:
   - **Repository access:** select the repositories GreenCode should audit
   - **Permissions → Repository permissions → Contents:** *Read-only*
     (this is what fetches the PR diff)
   - **Permissions → Metadata:** *Read-only* (mandatory, always required)
5. Click **Generate token** and copy the `github_pat_...` value. It is shown
   only once.

**Fine-grained** is strongly preferred over classic. Classic tokens are
account-wide and cannot be limited to individual repositories.

**Set it as:** `GITHUB_TOKEN`

**Verify:**

```bash
python -m app.cli check-keys
# or
curl -H "Authorization: Bearer $GITHUB_TOKEN" https://api.github.com/user
```

---

## 2. Amazon Alexa — `GREENCODE_ALEXA_SKILL_ID`

**Needed for:** the skill-ID guard on the ASK webhook. When set, the endpoint
rejects any request whose `request.skillId` does not match, which stops a
third party from driving your backend. When unset, the endpoint is open.

**How to get it:**

1. Sign in to the [Alexa Developer Console](https://developer.amazon.com/alexa/console/ask)
2. **Create skill → Custom → Skill Builder**
3. Set the invocation name, e.g. `green code auditor`
4. Import `alexa/interaction_model_en_US.json` into the Interaction Model tab
5. Copy the **Skill ID** from the top of the skill page. It looks like
   `amzn1.ask.skill.fd2a8106-e7fb-4f05-83b9-74590f7df6b8`

**Set it as:** `GREENCODE_ALEXA_SKILL_ID`

**Also set the HTTPS endpoint** in the console to
`https://<your-domain>/api/alexa/skill` and pick your locale (en-US).

**Note:** the console is free, but the skill is **not in the Alexa Skill Store**
without a separate review, and it will not pass Amazon certification for
real-household use until privacy and terms pages are live at
`https://<your-domain>/privacy` and `https://<your-domain>/terms`
(`alexa/pages/privacy.html` and `alexa/pages/terms.html` are the sources).

---

## 3. Electricity Maps — `ELECTRICITY_MAPS_API_KEY`

**Needed for:** live grid carbon intensity instead of the built-in grid
matrix. Used by `scope_inventory` and the "cleanest region" questions.

**How to get it:**

1. Go to [api.electricitymaps.com](https://api.electricitymaps.com/)
2. Click **Request a trial** (or **Get started**)
3. Fill the form; a token arrives by email

**Set it as:** `ELECTRICITY_MAPS_API_KEY`
(the code also accepts `GREENCODE_ELECTRICITY_MAPS_KEY`)

---

## 4. WattTime — `WATTTIME_API_TOKEN`

**Needed for:** a second live carbon-intensity source, used as a fallback
when Electricity Maps has no coverage for a zone.

**How to get it:**

1. Go to [watttime.org](https://www.watttime.org/) and sign up
2. Request API access through the [API documentation](https://docs.watttime.org/)
   portal, or via the developer signup on the main site
3. The token is emailed to you

**Set it as:** `WATTTIME_API_TOKEN`

---

## 5. ENTSO-E — `ENTSOE_API_TOKEN`

**Needed for:** European grid intensity, the most accurate source for the
EU zones GreenCode reports on.

**How to get it:**

1. Register on the [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/)
2. After email verification, request an API token from your account page
3. The token is only visible once

**Set it as:** `ENTSOE_API_TOKEN`

---

## 6. AWS (Bedrock / IAM / Budgets) — `AWS_PROFILE` or standard chain

**Needed for:** Bedrock refactoring synthesis, cross-account IAM role
linking, and AWS Budgets cost attribution. The MCP server also uses AWS
credentials for the Amazon integration.

**How to get it:**

1. Create an AWS account and an IAM user with `bedrock:InvokeModel`
   (plus `sts:AssumeRole` and `budgets:*` if you use those features)
2. Configure credentials with the standard AWS chain — nothing needs to be
   pasted into `.env`:
   - `aws sso login` for SSO, or
   - `aws configure` to write `~/.aws/credentials`
3. Optionally point at a named profile

**Set it as:** `AWS_PROFILE` (or rely on `AWS_ACCESS_KEY_ID` /
`AWS_SECRET_ACCESS_KEY` / instance role / SSO cache)

**Never** paste raw AWS keys into `.env` or the Vercel dashboard if you can
avoid it — the role/instance-role path is safer and the codebase explicitly
supports it.

---

## 7. Hugging Face — `HUGGINGFACE_API_KEY` / `HUGGINGFACE_TOKEN`

**Needed for:** the Hugging Face refactoring backend when
`GREENCODE_LLM_PROVIDER=huggingface`.

**How to get it:**

1. Sign in at [huggingface.co](https://huggingface.co/)
2. Go to [Settings → Access Tokens](https://huggingface.co/settings/tokens)
3. Click **+ Create new token**, choose a role (`read` is enough for
   inference), and copy the `hf_...` value

**Set it as:** `HUGGINGFACE_API_KEY` (the Vercel config uses `HUGGINGFACE_TOKEN`)

---

---



---

## 8. GreenCode's own secrets (no external signup needed)

These you generate yourself. They are already present in your `.env`.

| Variable | How to generate |
|----------|-----------------|
| `JWT_SECRET` | `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `SECRETS_ENCRYPTION_KEY` | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `POSTGRES_PASSWORD` | `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `REDIS_PASSWORD` | `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `GREENCODE_MCP_TOKEN` | `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `GOOGLE_CLIENT_ID` / `_SECRET` | [Google Cloud Console → APIs & Services → Credentials](https://console.cloud.google.com/apis/credentials) → *Create OAuth client ID* → Web application |
| `GITHUB_CLIENT_ID` / `_SECRET` | GitHub → [Settings → Developer settings → OAuth Apps](https://github.com/settings/developers) → *New OAuth App* → callback URL `https://<your-domain>/api/auth/github/callback` |

**`GREENCODE_MCP_TOKEN`** deserves a note: the MCP transport binds to
`127.0.0.1` by default and exposes a shell-capable analyser. If you ever
publish it, that token is the only thing standing between the internet and
a command runner. Keep it long, keep it secret, and always put a gateway
in front of it.


**Without it:** GreenCode uses the built-in global grid matrix of cached
emission factors. Results stay correct and offline, but they are not
real-time. This is why `check-keys` reports "Using Built-in Global Grid
Matrix" rather than an error.
## 9. Where to put the keys

### Local development

```bash
# Windows PowerShell
Copy-Item .env.example .env
```

Then fill in `.env`. The app loads it at startup.

### Vercel (the hosted deployment)

Vercel does **not** read `.env` from the repo. Set each variable in
**Project → Settings → Environment Variables**, for all three environments
(Production, Preview, Development).

`vercel.json` already references these Vercel secret names via `@name`
placeholders — create matching secrets with `vercel secret add <name> <value>`:

| Vercel secret | Maps to |
|---------------|---------|
| `@database_url` | `DATABASE_URL` |
| `@jwt_secret` | `JWT_SECRET` |
| `@secrets_encryption_key` | `SECRETS_ENCRYPTION_KEY` |
| `@github_token` | `GITHUB_TOKEN` |
| `@huggingface_token` | `HUGGINGFACE_TOKEN` |
| `@electricity_maps_api_key` | `ELECTRICITY_MAPS_API_KEY` |
| `@redis_url` | `REDIS_URL` |

Plain (non-secret) values you can set directly in the dashboard:
`GREENCODE_ALEXA_SKILL_ID`, `GREENCODE_MCP_TOKEN`, `GREENCODE_ALEXA_RATE_LIMIT`,
`GREENCODE_ALEXA_RATE_WINDOW_SECONDS`, `AWS_REGION`, `AWS_PROFILE`.

**Secrets are per-environment.** A value added to Production is not
available to Preview builds, so a Preview that "loses" its GitHub token is
expected, not a bug.

### Docker / self-hosted

`docker compose --env-file .env up -d` — the compose file reads `.env`
directly.

---

## 10. What works with no keys at all

This is worth knowing, because GreenCode is designed to degrade gracefully:

- **All AST engines** (the green score, the 30+ violation rules, the SCI
  formula) run 100% offline
- **Scope 1/2/3 inventory** works using the built-in grid matrix
- **SLA evaluation** works
- **Audit history** works
- **Diff auditing** works *if* the diff is supplied; fetching it from GitHub
  needs `GITHUB_TOKEN`
- **Live grid intensity** falls back to the cached matrix
- **Bedrock refactoring** falls back to the local heuristic refactorer
- **Dynamic analysis** still needs Docker, but no API key

So you can demo the entire voice surface offline. Keys only upgrade the data
from "accurate but cached" to "live".


