# GreenCode Alexa Voice Control - Command Reference

Invocation name: **"green code auditor"**

Example: *"Alexa, ask Green Code Auditor how GreenCode measures energy"*

## Important limits

The ASK Custom Skill can read the dashboard's selected GitHub repository after
you pair it from **Scan Repository** using an eight-digit, single-use code. Ask
“which repository is currently selected” or “audit my repository” after
pairing; say “unlink my GreenCode account” to revoke access. Pairing requires
`SECRETS_ENCRYPTION_KEY`; the skill stores the linked GitHub credential
encrypted at rest until you unlink. This custom pairing flow is separate from
Amazon OAuth account linking.

The Alexa skill can answer questions grounded in the project documentation,
look up grid intensity, compare named regions, and report which host energy
backend is available. Energy backend availability is not a measurement of a
specific running workload. Repository audits report static findings only and
do not measure workload energy or SCI.

### Green Release Briefing in the signed-in dashboard

In the GreenCode browser voice assistant, after scanning a GitHub repository
and connecting GitHub, say **"audit pull request 42"** (replace 42 with the PR
number). GreenCode fetches and audits only that PR's changed lines, then speaks
the diff score, finding count, and highest-priority finding with its file and
line. This is read-only: it does not edit files, push commits, or create a PR.
The request requires a signed-in GreenCode session and the browser's connected
GitHub token. If either is missing, or no GitHub repository scan is available
in the dashboard, the briefing is refused rather than guessing. The standalone
Echo/Developer Console skill can access the selected repository after it is
paired from the dashboard using the one-time account-link flow described above.

## 1. Repository Audits

| What the boss says | What happens |
|---|---|
| "audit my repository" | After pairing, Alexa audits the selected repository and reports its static score, finding count, and leading findings |
| "which repository am I working on" | After pairing, Alexa names the dashboard's current repository selection |
| "run a green code audit" | After pairing and selecting a repository, Alexa runs a static audit; otherwise pair or select a repository in the dashboard |

## 2. Code Snippet Audit

| What the boss says | What happens |
|---|---|
| "audit my python code" | Alexa asks you to provide source code in the dashboard; it does not invent a snippet |
| "scan my javascript snippet for energy waste" | Run the scan with the actual source in the dashboard |

> **Note:** Alexa voice requests do not carry source code. No audit or refactor is
> claimed until you submit actual code in the dashboard.

## GreenCode Overview

| What the user says | What happens |
|---|---|
| "what is GreenCode" | Answers from GreenCode project documentation |
| "what does GreenCode do" | Gives a documentation-grounded overview |

## 3. Full Audit & Score

| What the boss says | What happens |
|---|---|
| "audit and score my code" | Requires real source code and workload measurements; use the dashboard |
| "run a full audit and energy score" | Alexa does not claim a full audit without selected repository and measured inputs |
| "audit and score my python code in Ireland" | A region and language are not source code or an energy measurement |
| "complete audit of my codebase" | Select the repository in the authenticated dashboard |
| "end to end green score for my code" | Run a real audit from the dashboard to get a score |


## 4. Grid Carbon Intensity

| What the boss says | What happens |
|---|---|
| "what is the carbon intensity in Ireland" | Live gCO2e/kWh for Ireland grid |
| "how clean is the grid in Virginia" | Grid intensity for US-MIDA-PJM |
| "check grid carbon intensity for Frankfurt" | DE region intensity |
| "live grid intensity in Singapore" | Real-time reading from SG |
| "carbon intensity of Paris" | FR region |
| "grid intensity right now" | Alexa asks for a region; it does not guess one |

## 5. Compare Regions (Deployment Planning)

| What the boss says | What happens |
|---|---|
| "which aws region is cleanest tonight" | Name two regions to compare; Alexa does not assume a region list |
| "compare Ireland and Virginia" | Side-by-side comparison of IE and US-MIDA-PJM |
| "compare Frankfurt and Paris" | DE vs FR |
| "should we run this job in Oregon or Singapore" | Compares those two named grid regions; workload placement is not executed |
| "is Ireland cleaner than Virginia" | Direct comparison |
| "between Frankfurt and Paris which is greener" | Compares those named regions if current intensity data is available |
| "where should we schedule our kubernetes workload" | Name two regions; Alexa does not know your workload or deployment |
| "cleanest region for our workload" | Name regions to compare; Alexa does not assume a list |

## 6. Software Carbon Intensity (SCI)

| What the boss says | What happens |
|---|---|
| "calculate software carbon intensity" | Requires a real energy measurement and functional unit; use the dashboard |
| "calculate sci for Ireland" | A region alone is not enough; provide measured workload inputs in the dashboard |
| "what is the sci score" | Alexa does not invent a score when no measurement is available |
| "compute sci for my workload" | Enter actual workload measurements and the functional unit in the dashboard |
| "carbon emissions per request" | Requires measured energy and a real request count |

## 7. Energy Measurement

| What the boss says | What happens |
|---|---|
| "measure energy" | Reports which energy backend is available; does not measure a selected workload |
| "power draw on this machine" | Use GreenCode Profiler to select and measure a process |
| "watts and joules reading" | No workload values are reported unless a process was actually measured |
| "energy consumption right now" | Alexa does not claim an instantaneous workload measurement |
| "hardware energy reading" | Backend availability is not proof that hardware counters measured a workload |
| "measure power consumption" | Run the Profiler on the target workload |
| "current energy draw" | Use the Profiler; Alexa does not invent watts |


## 8. Code Refactoring

| What the boss says | What happens |
|---|---|
| "how does refactoring work" | Answers from GreenCode project documentation |
| "refactor my code" | Alexa directs you to submit actual source in the dashboard; it does not claim to refactor a sample |

## 9. Explain Score

| What the boss says | What happens |
|---|---|
| "explain my green score" | Requires an actual score and audit result from the dashboard |
| "why is my score low" | Use the dashboard audit findings; Alexa cannot see the selected repository |
| "breakdown of my carbon score" | Alexa does not infer or invent a score breakdown |
| "reason for my green grade" | Requires a real audit result |
| "explain score breakdown" | Use the audit result's recorded measurement provenance |
| "what affects my green score" | Alexa can answer only when project documentation supports the explanation |

## 10. Repository Management

| What the boss says | What happens |
|---|---|
| "list my GitHub repositories" | The dashboard assistant lists connected repositories after GitHub sign-in; the standalone Alexa skill lists them after pairing from Scan Repository |
| "which repository am I working on" | Reports the dashboard's selected repository when the dashboard has one, or the paired repository for the standalone Alexa skill |
| "audit my repository" | After GitHub sign-in in the dashboard or account pairing in the standalone skill, reports the selected repository's static audit |

## 11. Billing & FinOps

| What the boss says | What happens |
|---|---|
| "cloud billing report" | FOCUS 1.4 billing reconciliation |
| "finops reconciliation" | Cloud cost vs carbon reconciliation |
| "aws cost report" | AWS billing with carbon intensity |
| "monthly cloud spend" | Monthly cost breakdown |
| "reconcile billing with carbon" | Cost + Scope 2/3 emissions |
| "cloud cost and carbon report" | Combined FinOps report |
| "finops report for my organization" | Org-level FinOps dashboard |

## 12. Help

| What the boss says | What happens |
|---|---|
| "help" | Full command list |
| "what can you do" | Capabilities overview |
| "capabilities" | What GreenCode voice supports |
| "voice commands" | Available utterances |
| "how to use green code" | Getting started guide |
| "what commands are available" | Command inventory |


## Enterprise Deployment (Big Companies)

For enterprise deployments, the boss can also say:

- "audit all repositories in my organization" - Batch audit every repo in the org
- "compare my team's green scores" - Leaderboard across developers
- "show me the cloud billing report" - Org-level FinOps
- "schedule a weekly audit" - Automated recurring audits

Each developer can also have their own individual instance:
- `developer1.greencode.company.com` - Personal dashboard + Alexa
- `developer2.greencode.company.com` - Personal dashboard + Alexa

## Multi-Tenant Isolation

- **Individual developers**: Each gets their own GreenCode instance with isolated data
- **Enterprises**: Central Alexa skill routes to the correct org based on the JWT token or `x-greencode-org` header
- **Credential protection**: GitHub credentials are encrypted at rest when the encryption key is configured; the Alexa link is removed when you unlink the skill

## Example of a truthful response

> **Boss:** "Alexa, ask Green Code Auditor to audit my repository"
>
> **Alexa (unlinked):** "Your Alexa account is not linked to GreenCode yet. Pair it from the dashboard using the displayed one-time code."
>
> **Alexa (linked):** "Audited owner/repository. The Green Score is 91 out of 100 with 2 energy anti-patterns detected. This is a static audit; it did not measure workload energy or software carbon intensity."
>
> **Boss:** "Compare Ireland and Virginia"
>
> **Alexa:** Reports the lookup result only if both region intensities are returned successfully.
>
> **Boss:** "Measure energy"
>
> **Alexa:** Reports backend availability, not a workload's joules or watts.
