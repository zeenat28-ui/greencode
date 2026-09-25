# 🌱 GreenCode Auditor

[![CI Gatekeeper](https://img.shields.io/badge/CI%2FCD-Active%20Quality%20Gate-success)](action.yml)
[![Green Computing](https://img.shields.io/badge/Standard-Green%20Software%20Foundation-brightgreen)](https://greensoftware.foundation)
[![SCI Standard](https://img.shields.io/badge/Specification-SCI%20v1.0-blue)](https://greensoftware.foundation)
[![ISO Compliant](https://img.shields.io/badge/Standard-ISO%2014064--1-emerald)](https://iso.org)

**GreenCode Auditor** is an industry-grade platform designed to enforce Green Computing standards across modern software engineering workflows. It audits multi-language GitHub and local codebases for architectural and algorithmic energy anti-patterns using Concrete and Abstract Syntax Tree (CST/AST) parsing, dynamically profiles execution inside isolated sandboxes to measure hardware TDP draw in Watt-hours, queries live regional grid carbon telemetry via Electricity Maps, automatically refactors inefficient code using GreenCode AI synthesis under Green Software Foundation (GSF) standards, and enforces non-breaking CI/CD quality gate blockers via a native GitHub Action.

---

## 🏛️ System Architecture

```
greencode/
├── app/
│   ├── __init__.py         # Package initialization
│   ├── main.py             # FastAPI backend server & CI/CD terminal CLI
│   ├── parser.py           # AST Static Analysis Engine (GSF Patterns)
│   ├── profiler.py         # Docker SDK Dynamic Container Sandbox & SCI Hardware Power Model
│   ├── optimizer.py        # Electricity Maps Client & GreenCode AI Refactoring Synthesizer
│   └── database.py         # SQLite + SQLAlchemy historic ledger & metrics persistence
├── samples/
│   ├── heavy_pipeline.py   # Benchmark script exhibiting all 4 GSF anti-patterns (Score: 47/100)
│   └── eco_pipeline.py     # Refactored script conforming to Green Computing standards (Score: 100/100)
├── tests/
│   ├── test_greencode.py   # Comprehensive unit test suite (AST, DB, Grid, Profiler, Refactoring)
│   └── test_api.py         # FastAPI REST endpoint integration tests
├── action.yml              # Native GitHub Action manifest for CI/CD blocker
├── ui.py                   # Streamlit green dashboard with side-by-side diffs & SCI charts
└── requirements.txt        # Production dependency specifications
```

---

## ⚡ Green Software Foundation (GSF) Patterns Enforced

1. **Deep Nested Iteration (`NESTED_LOOPS_DEPTH_3+`)**:
   - **Severity**: `HIGH` | **Deduction**: `-15 pts`
   - **Physics & Impact**: Loops with depth $\ge 3$ scale computational complexity to $\mathcal{O}(N^3)$, causing runaway CPU instruction cycles and elevated thermal design power (TDP) dissipation.
   - **Eco-Remediation**: Flatten iterations using `itertools.product`, generator pipelines, or hash set/dict lookups.

2. **Unmanaged Database Cursors (`RAW_DB_CURSOR_NO_CONTEXT`)**:
   - **Severity**: `HIGH` | **Deduction**: `-10 pts`
   - **Physics & Impact**: Creating DB cursors without a `with` context manager risks persistent unclosed sockets, forcing database servers to sustain unnecessary idle power states.
   - **Eco-Remediation**: Enclose cursor operations within `with connection.cursor() as cursor:`.

3. **Un-cached Network Requests Inside Loops (`UNCACHED_NETWORK_IN_LOOP`)**:
   - **Severity**: `CRITICAL` | **Deduction**: `-20 pts`
   - **Physics & Impact**: Synchronous HTTP calls inside iterations trigger repeated Radio / NIC transceiver wake-up energy and redundant TLS connection handshakes.
   - **Eco-Remediation**: Batch requests into single bulk endpoints, hoist connections with `requests.Session()`, or apply `@lru_cache` memoization.

4. **Quadratic String Concatenation (`QUADRATIC_STRING_CONCAT_IN_LOOP`)**:
   - **Severity**: `MEDIUM` | **Deduction**: `-8 pts`
   - **Physics & Impact**: Using `+` or `+=` string concatenation inside loops causes quadratic $\mathcal{O}(N^2)$ memory allocations and aggressive garbage collection thrashing.
   - **Eco-Remediation**: Accumulate string elements into a list and invoke `''.join(chunks)`.

---

## 🌐 Universal Omni-Language Engine (500+ Languages Supported)

GreenCode Auditor is built for universal, polyglot global scale. It natively audits code written in **every programming language in the world**, powered by a robust 3-Tier Multi-Paradigm Parsing Engine:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   UNIVERSAL SOURCE CODE INPUT                          │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
                 ┌───────────────────┴───────────────────┐
                 ▼                                       ▼
    ┌───────────────────────────┐           ┌───────────────────────────┐
    │  TIER 1: HIGH-FIDELITY    │           │  TIER 2: UNIVERSAL LEXICAL│
    │  TREE-SITTER CST          │           │  SCOPE & BLOCK ANALYZER   │
    │  Python, JS/TS, C/C++,    │           │  All 500+ Languages       │
    │  Java, Go, Rust, C#,      │           │  Solidity, Kotlin, Swift, │
    │  Ruby, PHP, Bash, SQL...  │           │  Pascal, COBOL, Zig, R,   │
    │  (Grammar S-Expressions)  │           │  Julia, Fortran, Lua...   │
    └────────────┬──────────────┘           └────────────┬──────────────┘
                 │                                       │
                 └───────────────────┬───────────────────┘
                                     ▼
                        ┌───────────────────────────┐
                        │  TIER 3: IBM GRANITE      │
                        │  POLYGLOT AI REFACTORING  │
                        │  116+ Languages & Zero-   │
                        │  Downtime Remediation     │
                        └───────────────────────────┘
```

1. **Tier 1: High-Fidelity Tree-sitter Concrete Syntax Trees (CST)**:
   Pre-compiled grammars for the most popular modern enterprise languages (Python, JavaScript, TypeScript, C, C++, C#, Java, Go, Rust, Ruby, PHP, Scala, Bash, SQL, R, Julia, Haskell, Elixir, YAML, HTML, CSS). Runs S-expression queries targeting nested loops and callback-driven iteration structures.
2. **Tier 2: Universal Lexical Scope & Block Analyzer**:
   Universal parser with bracket, indentation, and keyword-block matching (`begin/end`, `do/done`, `loop/end`, `perform/end-perform`) covering **500+ file extensions** (Solidity `.sol`, Kotlin `.kt`, Swift `.swift`, Pascal `.pas`, COBOL `.cbl`, Zig `.zig`, D `.d`, V `.v`, Nim `.nim`, Dart `.dart`, etc.).
3. **Dynamic Universal Fallback**:
   Any custom, proprietary, or emerging file extension (e.g., `.sol`, `.xyz`, `.custom`) is automatically identified and analyzed without crashing or dropping coverage.
4. **Embedded Multi-Language Blocks**:
   Recursively detects and parses polyglot code blocks (e.g. `<script>` inside HTML, markdown code fences, embedded C++/JavaScript string blocks inside Python).

---

## 📐 Software Carbon Intensity (SCI) Mathematical Model

Operational carbon footprints are calculated in accordance with the official Green Software Foundation SCI Standard:

$$SCI = \frac{(E \times I) + M}{R}$$

- **$E$ (Energy Consumption)**:
  $$P_{\text{cpu}} = P_{\text{idle}} + (P_{\text{peak}} - P_{\text{idle}}) \times \frac{CPU\%}{100}$$
  $$P_{\text{mem}} = RAM_{\text{GB}} \times 0.3725\text{ W/GB}$$
  $$P_{\text{total}} = (P_{\text{cpu}} + P_{\text{mem}}) \times PUE \quad (PUE = 1.2)$$
  $$E_{\text{Wh}} = \frac{P_{\text{total}} \times \Delta t}{3600}$$
- **$I$ (Grid Intensity)**: Real-time grams of $\text{CO}_2$ equivalent per kilowatt-hour ($g\text{CO}_2\text{eq/kWh}$) queried from Electricity Maps across global regions (e.g., California, Midwest, France, Germany, Great Britain, Pakistan, India, Sweden, Japan).
- **$M$ (Embodied Carbon)**: Hardware manufacturing carbon amortized over the runtime duration.
- **$R$ (Functional Unit)**: Per single execution run or modeled across 10,000 production cycles.

---

## 🚀 Quick Start Guide

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Launch the Streamlit Dashboard
```bash
streamlit run ui.py
```
Open your browser at `http://localhost:8501` to view:
- **Repository Explorer**: Scan local paths or drag-and-drop ZIP archives.
- **Global Grid Carbon Gauge**: Interactive live regional carbon intensities.
- **Dynamic Container Profiler**: Hardware CPU/RAM watts, Joules, and SCI metrics.
- **Interactive Code Diff**: Side-by-side comparison using `streamlit-code-diff` showcasing Original Inefficient Code vs. GreenCode AI Eco-Refactored Code.
- **SCI Carbon Analytics**: Plotly projections of carbon saved across 10,000 production cycles.

### 3. Run the FastAPI REST Server
```bash
python -m app.main --serve --port 8000
```
Interactive OpenAPI documentation will be accessible at `http://localhost:8000/docs`.

### 4. Execute the CI/CD Quality Gate Blocker
Run in your local terminal or CI pipeline:
```bash
# Auditing heavy pipeline (exits with code 1 - build blocked)
python -m app.main --path samples/heavy_pipeline.py --threshold 75 --ci

# Auditing eco pipeline (exits with code 0 - build passed)
python -m app.main --path samples/eco_pipeline.py --threshold 75 --ci
```

### 5. Run the Automated Test Suite
```bash
python -m unittest discover tests
```

---

## 🤖 GreenCode AI Refactoring Synthesizer

Flagged code patterns are transformed using Green Software Foundation SCI standards:
> *"You are a Green Computing Optimization Agent. Refactor this specific source code to drastically reduce physical CPU cycles, minimize memory foot-prints, and drop energy consumption, while guaranteeing identical output logical data."*

The application supports both direct AI model integration (IBM Granite 3.2, Qwen 2.5 Coder, Llama 3.2 via HuggingFace Inference API) and an offline AST-driven Green Code Synthesizer that produces immediate, deterministic code optimizations across 500+ languages.

---

## 🌟 Flagship Carbon Intelligence Features

1. **🏷️ Dynamic SVG GitHub README Badges**:
   - Generates pixel-perfect, vector SVG badges in Shields.io format at `/api/badge/score/{score}` and `/api/badge/repo/{repo_id}`.
   - Ready-to-embed Markdown and HTML snippets provided directly in the dashboard for repositories to display their Green Score globally on GitHub.

2. **🌍 Tangible Real-World Environmental Impact Calculator**:
   - Translates abstract Joules and Watt-hours into tangible everyday equivalencies using United States Environmental Protection Agency (EPA) standards:
     - 🌳 **Urban Trees Preserved**: $21.77\text{ kg CO}_2\text{/tree/year}$
     - 📱 **Smartphones Charged**: $8.22\text{ Wh/charge}$
     - 💵 **Cloud Hosting Costs Saved**: AWS/GCP compute & cooling billing reduction.
   - Includes interactive simulation slider scaling from 1,000 to 1,000,000 monthly transactions.

3. **📜 Official ESG Carbon Audit Certificate Export**:
   - Generates an official, ISO 14064-1 & Green Software Foundation (GSF) compliant HTML Carbon Audit Certificate.
   - Features SHA-256 cryptographic verification checksum, grade stamp, detailed metric breakdown, and built-in print CSS for 1-click PDF export (`Ctrl+P`).

---

## 🛠️ GitHub Actions Integration

Add GreenCode Auditor to `.github/workflows/greencode.yml`:

```yaml
name: Green Computing Quality Gate

on: [push, pull_request]

jobs:
  carbon-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Audit Green Score
        uses: ./
        with:
          repo-path: "."
          green-score-threshold: "75.0"
          target-zone: "US-CAL-CISO"
          electricity-maps-token: ${{ secrets.ELECTRICITY_MAPS_TOKEN }}
          ibm-bob-token: ${{ secrets.IBM_BOB_TOKEN }}
```

