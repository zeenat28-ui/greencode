# Carbon-Aware Coding Guidelines

> **Status:** Mandatory for all code changes — enforced in CI via the GreenCode
> Auditor parser (\pp/parser.py\).

## 1. Core Principle: Efficiency Is Carbon

Every CPU cycle, network request, and byte of DRAM consumed by software
transduces to real energy, and energy sourced from fossil fuels emits CO2e.
Writing efficient code is therefore **carbon accounting**, not just performance
optimization.

## 2. Algorithm Design

### 2.1 Avoid Quadratic Complexity
- **Never** concatenate strings inside a loop — use \join()\ or a buffer.
- **Never** call \list.insert(0, ...)\ or \Array.unshift()\ in a hot loop.
- Prefer \dict\/Map lookups (O(1)) over \list\.includes() (O(n)).

### 2.2 Cache Expensive Computations
- Cache results that depend only on their inputs (memoization).
- Cache external API responses with TTL (see \pp/carbon_intensity.py\ for
  the reference pattern: 5-minute TTL with LRU eviction).

### 2.3 Break Early, Skip Early
- Use \reak\ and \continue\ liberally.
- Short-circuit boolean evaluation.

### 2.4 Batch, Do Not Fan Out
- Batch database queries: \WHERE id IN (...)\ instead of N+1 calls.
- Batch API requests: one request with 50 IDs instead of 50 requests.

## 3. Data Handling

### 3.1 Minimize Serialization
- Avoid \json.dumps\ or \JSON.stringify\ in hot loops.
- Use binary protocols when the payload is large and latency matters.

### 3.2 Paginate Everything
- Never \SELECT * FROM table\ without \LIMIT\.
- Paginate API responses.

### 3.3 Stream, Do Not Buffer
- For large file processing, stream line-by-line rather than loading into memory.

## 4. Network & I/O

### 4.1 Cache at the Edge
- Use CDN caching for static assets.
- Cache API responses at the reverse proxy where possible.

### 4.2 Prefer GET Over POST for Reads
- GET responses are cacheable; POST responses are not.

### 4.3 Use Conditional Requests
- Send \If-None-Match\ / \If-Modified-Since\ headers on polling requests.

## 5. CI/CD & Deployment

### 5.1 Run Audits in CI
- The gatekeeper workflow blocks PRs below the team green-score threshold.
- Fix violations locally before pushing.

### 5.2 Use Carbon-Aware Regions
- Prefer grid zones with low marginal carbon intensity.

### 5.3 Optimize Build Pipelines
- Use incremental builds and cache dependency layers.

## 6. Runtime Observability

### 6.1 Measure, Do Not Guess
- Use \POST /api/profile\ for energy/SGI measurement.
- The \GET /api/health\ endpoint reports hardware measurement availability.

### 6.2 Set Carbon Budgets
- Every team has a monthly carbon budget.
- The SLA engine blocks deployments exceeding SCI thresholds.

### 6.3 Log Judiciously
- Avoid verbose logging in production.
- Use structured logging with sampling for high-frequency events.

## 7. AI / LLM-Specific Guidance

### 7.1 Prefer Fewer, Better Tokens
- A single long call is more efficient than multiple short sequential calls.

### 7.2 Cache Model Outputs
- Cache LLM responses keyed by hash of (prompt, model, temperature).

### 7.3 Choose Smaller Models
- Use distilled or quantized models when quality permits.

## 8. Code Review Checklist

Before merging, verify:

- [ ] No loops with N+1 database or API calls
- [ ] No string concatenation in loops
- [ ] No \sleep()\ or retry backoff in production code paths
- [ ] Caching used for repeated external fetches
- [ ] Payloads are paginated
- [ ] No unnecessary serialization/deserialization
- [ ] Build pipeline is incremental and cache-optimized

---
*These guidelines are enforced by the GreenCode Auditor parser.*
