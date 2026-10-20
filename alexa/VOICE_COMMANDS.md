# GreenCode Alexa Voice Control - Command Reference

Invocation name: **"green code auditor"**

Example: *"Alexa, ask Green Code Auditor to audit my repository"*

## 1. Repository Audits

| What the boss says | What happens |
|---|---|
| "audit my repository" | Full static analysis on your connected GitHub repo, returns green score + violations |
| "audit my repository acme/widgets" | Audits a specific repo (owner/repo format) |
| "audit my repository on branch develop" | Audits a specific branch |
| "scan my github repository" | Same as audit my repository |
| "check my code for energy waste" | Scans for nested loops, quadratic string building, etc. |
| "what is the green score of my repository" | Returns 0-100 score + letter grade |
| "run a green code audit" | Full audit pipeline |
| "find energy offenders in my repo" | Lists top energy anti-patterns |
| "run static analysis on my codebase" | Static AST/Tree-sitter analysis across all files |

## 2. Code Snippet Audit

| What the boss says | What happens |
|---|---|
| "audit my python code" | Audits a Python snippet for energy anti-patterns |
| "scan my javascript snippet for energy waste" | JS/TS specific scan |
| "check this function for energy waste" | Audits the provided snippet |
| "audit this python snippet" | Python-specific audit |
| "find nested loops in my code" | Detects O(N³) nested iteration |
| "find quadratic string building in my code" | Detects s = s + ... in loops |

> **Note:** For snippet audits, paste the code in the GreenCode dashboard first, or the system will run a demo audit.

## 3. Full Audit & Score

| What the boss says | What happens |
|---|---|
| "audit and score my code" | Static analysis + energy measurement + SCI in one call |
| "run a full audit and energy score" | Complete end-to-end verdict |
| "audit and score my python code in Ireland" | Full audit with Ireland grid intensity |
| "complete audit of my codebase" | Everything: violations, energy, SCI, remediation plan |
| "end to end green score for my code" | Single verdict with grade |


## 4. Grid Carbon Intensity

| What the boss says | What happens |
|---|---|
| "what is the carbon intensity in Ireland" | Live gCO2e/kWh for Ireland grid |
| "how clean is the grid in Virginia" | Grid cleanliness for US-East-1 |
| "check grid carbon intensity for Frankfurt" | DE region intensity |
| "live grid intensity in Singapore" | Real-time reading from SG |
| "carbon intensity of Paris" | FR region |
| "grid intensity right now" | Default zone reading |

## 5. Compare Regions (Deployment Planning)

| What the boss says | What happens |
|---|---|
| "which aws region is cleanest tonight" | Ranks all regions by carbon intensity |
| "compare Ireland and Virginia" | Side-by-side comparison of IE vs US-East-1 |
| "compare Frankfurt and Paris" | DE vs FR |
| "should we run this job in Oregon or Singapore" | Recommendation for batch job placement |
| "is Ireland cleaner than Virginia" | Direct comparison |
| "between Frankfurt and Paris which is greener" | Picks the cleaner one |
| "where should we schedule our kubernetes workload" | Deployment recommendation |
| "cleanest region for our workload" | Best region suggestion |

## 6. Software Carbon Intensity (SCI)

| What the boss says | What happens |
|---|---|
| "calculate software carbon intensity" | SCI = (E × I + M) / R per GSF spec |
| "calculate sci for Ireland" | SCI with Ireland grid intensity |
| "what is the sci score" | SCI value + grade |
| "compute sci for my workload" | Full SCI breakdown |
| "carbon emissions per request" | Per-functional-unit emissions |

## 7. Energy Measurement

| What the boss says | What happens |
|---|---|
| "measure energy" | Reads hardware energy counters (RAPL, etc.) |
| "power draw on this machine" | Current wattage |
| "watts and joules reading" | Energy and power figures |
| "energy consumption right now" | Instantaneous measurement |
| "hardware energy reading" | From RAPL/Scaphandre, not modelled |
| "measure power consumption" | Full power profile |
| "current energy draw" | Live watts |


## 8. Code Refactoring

| What the boss says | What happens |
|---|---|
| "refactor my code" | AI-powered refactor for energy efficiency |
| "optimize my python code for energy" | Python-specific refactor |
| "fix energy waste in my code" | Removes anti-patterns |
| "reduce carbon in my code" | Lowers carbon footprint |
| "clean up my code for efficiency" | General cleanup |
| "refactor this snippet" | Refactor the provided snippet |
| "optimize energy consumption" | Reduce joules per request |
| "make my code greener" | General energy optimization |

## 9. Explain Score

| What the boss says | What happens |
|---|---|
| "explain my green score" | Breaks down how the score was calculated |
| "why is my score low" | Explains the violations causing the low score |
| "breakdown of my carbon score" | Operational + embodied carbon split |
| "reason for my green grade" | Why you got an A/B/C/D/F |
| "explain score breakdown" | Full provenance: hardware vs modelled |
| "what affects my green score" | Factors that influence the score |

## 10. Repository Management

| What the boss says | What happens |
|---|---|
| "my repositories" | Lists all connected repos |
| "list my repos" | Same |
| "show all repositories" | Full repo list with scores |
| "what repos do I have" | Repo inventory |
| "show my connected repositories" | Connected GitHub repos |
| "list all my github repos" | All GitHub repos linked to your org |

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
- **Zero-knowledge**: GitHub tokens are sent per-request, never stored on the server

## Example Voice Session

> **Boss:** "Alexa, ask Green Code Auditor to audit my repository"
>
> **Alexa:** "Audit complete for acme/widgets on branch main. Green score: 72 percent, grade C. Found 4 energy anti-patterns. The top fixes are in your GreenCode dashboard."
>
> **Boss:** "Compare Ireland and Virginia"
>
> **Alexa:** "The cleanest region is Ireland at 26 grams CO2 per kilowatt hour. Among Virginia."
>
> **Boss:** "Measure energy"
>
> **Alexa:** "Energy: 45 joules at 45 watts. Source: hardware counter (RAPL)."

