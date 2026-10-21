# Alexa Voice Pipeline Silent Failure — Bugfix Design

## Overview

The GreenCode Alexa voice integration pipeline is completely non-functional due to six compounding structural faults. Together they produce a total silent failure: Alexa neither listens nor responds. The faults span:

1. `alexa_skill.router` dead code — never mounted in `main.py`
2. Active webhook guard (`mcp_server.alexa_request_guard`) lacks timestamp replay protection
3. ASK certificate chain verification absent from both active handlers
4. Circular import between `mcp_server` and `alexa_skill` silently swallows `FreeformGreenCodeQueryIntent`
5. `_build_ask_response` hardcodes `"PlainText"` instead of `"SSML"`, and most intent handlers omit `reprompt`
6. `alexa/addon.json` points to `/mcp` (MCP transport) instead of `/api/alexa/skill` (ASK webhook)

The fix strategy is surgical: correct each fault in the smallest possible scope without disturbing any other FastAPI endpoint, the MCP Streamable HTTP transport, or any passing tests.

## Glossary

- **Bug_Condition (C)**: Any of the six structural conditions that cause the Alexa pipeline to fail silently — dead router, missing timestamp check, absent cert verification, circular import, wrong response type, or misconfigured endpoint URL
- **Property (P)**: The desired correct behavior — a valid ASK v1.0 JSON envelope is produced and delivered to the requesting Alexa device for every well-formed ASK request
- **Preservation**: All non-Alexa FastAPI endpoints, the MCP transport (`create_app()`), existing rate-limit and skill-ID enforcement, and all intent handlers already exercised by passing tests must remain completely unaffected
- **`alexa_skill.router`**: The `APIRouter(prefix="/alexa")` defined in `app/alexa_skill.py` that holds the full SSML pipeline and intent handler chain — currently never mounted
- **`alexa_request_guard`**: The active guard function in `app/mcp_server.py` that performs rate limiting and skill-ID verification — currently missing timestamp replay protection
- **`_build_ask_response`**: The response builder in `app/mcp_server.py` that constructs the ASK v1.0 JSON envelope — currently hardcodes `"PlainText"` instead of `"SSML"`
- **`_dispatch_nlu_action`**: The function in `app/mcp_server.py` that defers to `app.alexa_skill.dispatch_nlu_action` at call time, creating a circular import with `app.alexa_skill` which itself imports from `app.mcp_server`
- **ASK timestamp**: The ISO 8601 UTC timestamp in `request.timestamp` of every ASK payload; Amazon requires rejection of requests older than 150 seconds to prevent replay attacks
- **ASK cert chain**: The `SignatureCertChainUrl` and `Signature` HTTP headers Amazon attaches to every ASK POST; verifying them against the raw request body is required for Amazon certification

## Bug Details

### Bug Condition

The pipeline fails under six independent conditions, each of which is sufficient to produce a silent failure on its own. Together they guarantee total non-function.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type AlexaRequest (HTTP POST to any /alexa/* or /api/alexa/* path)
  OUTPUT: boolean

  RETURN
    -- Fault 1: router never mounted
    (input.path STARTS_WITH "/alexa/" AND app.include_router(alexa_skill.router) NOT CALLED)
    OR
    -- Fault 2: timestamp not checked in active guard
    (input.path == "/api/alexa/skill"
     AND abs(now_utc() - parse_utc(input.body.request.timestamp)) > 150
     AND alexa_request_guard DOES_NOT check input.body.request.timestamp)
    OR
    -- Fault 3: cert chain not verified in active handler
    (input.path == "/api/alexa/skill"
     AND input.headers["SignatureCertChainUrl"] EXISTS
     AND handler DOES_NOT verify SignatureCertChainUrl + Signature)
    OR
    -- Fault 4: circular import silently swallows FreeformGreenCodeQueryIntent
    (input.body.request.intent.name == "FreeformGreenCodeQueryIntent"
     AND circular_import(mcp_server <-> alexa_skill) CAUSES dispatch_nlu_action TO RETURN None)
    OR
    -- Fault 5: wrong outputSpeech type
    (response._build_ask_response CALLED
     AND response.outputSpeech.type == "PlainText"  -- should be "SSML"
     AND response.response.reprompt MISSING
     AND NOT input.body.request.type == "SessionEndedRequest")
    OR
    -- Fault 6: addon.json points to wrong endpoint
    (alexa_device READS addon.json
     AND addon.json.integrations[0].config.endpoints.default.uri == ".../mcp"
     AND correct_uri == ".../api/alexa/skill")
END FUNCTION
```

### Examples

- **Fault 1**: User invokes the GreenCode Alexa skill → Alexa POSTs to `/alexa/skill` → 404 Not Found because the router was never mounted in `main.py`, even though `app/alexa_skill.py` defines a full `APIRouter(prefix="/alexa")`
- **Fault 2**: A replayed POST arrives at `/api/alexa/skill` with a timestamp 10 minutes in the past → `alexa_request_guard` accepts it (no timestamp check) → skill processes a stale request it should have rejected with HTTP 403
- **Fault 3**: Amazon sends a POST with `SignatureCertChainUrl` and `Signature` headers → neither `alexa_request_guard` nor `api_alexa_custom_skill_webhook` in `main.py` inspects these headers → skill fails Amazon's certification automated scan
- **Fault 4**: `FreeformGreenCodeQueryIntent` arrives → `handle_alexa_skill_request` in `mcp_server.py` calls `_dispatch_nlu_action(raw_query)` → that function does `from app.alexa_skill import dispatch_nlu_action` at call time → `alexa_skill` is already mid-import of `mcp_server` → circular import may cause `dispatch_nlu_action` to be `None` or raise `ImportError`, resulting in silence or error
- **Fault 5**: Any intent succeeds → `_build_ask_response` returns `{"outputSpeech": {"type": "PlainText", "text": "..."}}` → Alexa renders as flat text, not SSML; no `reprompt` block means a mishear silently ends the session
- **Fault 6**: Alexa device reads `alexa/addon.json` to discover the skill endpoint → finds `"uri": "https://greencode-teal.vercel.app/mcp"` → routes all voice requests to the MCP transport, which speaks JSON-RPC, not ASK, so every request is mishandled silently

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Every non-Alexa FastAPI endpoint in `main.py` must continue to work exactly as before
- The MCP Streamable HTTP transport (`create_app()` in `mcp_server.py`) must continue to work; the `/mcp` path, auth middleware, and discovery documents are untouched
- The existing rate-limiting enforcement (HTTP 429 with `Retry-After` header) in `alexa_request_guard` must continue to fire for clients exceeding the budget
- The existing skill-ID enforcement (HTTP 403 on applicationId mismatch) in `alexa_request_guard` must continue to fire when `GREENCODE_ALEXA_SKILL_ID` is configured
- All intent handlers (LaunchRequest, CompareRegionsIntent, etc.) that currently return valid ASK envelopes must continue to do so; `sessionAttributes` must still be echoed back on every response
- The MCP integration entry in `addon.json` (`integrations` array with `type: "MCP"`) must remain; only the ASK webhook URI is changed, not the MCP config block
- All passing tests in `tests/test_alexa_skill.py` and `tests/test_alexa_compliance.py` must continue to pass

**Scope:**
All inputs that do NOT involve the Alexa voice pipeline paths (`/alexa/skill`, `/api/alexa/skill`) are completely unaffected. The `addon.json` change only updates the ASK webhook URI; the `integrations[0]` MCP config block remains intact.

## Hypothesized Root Cause

Based on code inspection:

1. **Fault 1 — Missing `include_router` call**: `app/alexa_skill.py` correctly creates `router = APIRouter(prefix="/alexa")` and registers `/skill` on it. However, `app/main.py` never calls `app.include_router(alexa_skill.router)`. The module defines the two webhook paths (`/alexa/skill`, `/api/alexa/skill`) directly on the `app` object but uses the `mcp_server` pipeline, not the `alexa_skill` router. The `alexa_skill.router` routes are permanently unreachable.

2. **Fault 2 — Timestamp check uses wrong header**: `_verify_alexa_request` in `alexa_skill.py` reads `x-amzn-requestid` or `date` HTTP headers to find the timestamp, but Amazon ASK embeds the canonical timestamp in the JSON body at `request.timestamp` (ISO 8601 UTC, e.g. `"2025-01-15T12:00:00Z"`). The `alexa_request_guard` in `mcp_server.py` (the active guard) performs no timestamp extraction at all. Neither path enforces replay protection against the body timestamp.

3. **Fault 3 — No ASK signature verification implemented**: Amazon's ASK specification requires verifying `SignatureCertChainUrl` (a URL pointing to Amazon's certificate chain) and `Signature` (a base64-encoded RSA-SHA1 signature of the raw request body) on every request. Neither `alexa_request_guard` nor `api_alexa_custom_skill_webhook` in `main.py` accesses these headers. The `ask-sdk-core` package provides a ready-made verifier but may not be installed; a `cryptography`-based fallback or documented stub is needed.

4. **Fault 4 — Circular import between `mcp_server` and `alexa_skill`**: `app/mcp_server.py` defines `_dispatch_nlu_action` which at call time does `from app.alexa_skill import dispatch_nlu_action`. Meanwhile `app/alexa_skill.py` imports `from app import mcp_server` (via `_call_greencode_tool`) at module level. When both modules are first loaded, Python may not yet have finished executing `alexa_skill` when `mcp_server` tries to import from it, leaving `dispatch_nlu_action` as `None` or raising `ImportError`. The fix is to move the shared NLU dispatch logic to a third module (`app/alexa_dispatch.py`) that neither `mcp_server` nor `alexa_skill` imports in the other direction.

5. **Fault 5 — `_build_ask_response` hardcodes `"PlainText"`**: The ASK v1.0 spec distinguishes `"PlainText"` (flat text, no markup) from `"SSML"` (Speech Synthesis Markup Language, supports `<break>`, `<emphasis>`, prosody). GreenCode intends to use SSML (the module docstring says "SSML responses"), but `_build_ask_response` emits `{"type": "PlainText"}`. Additionally, most callers of `_build_ask_response` omit `reprompt_text`, which means any mishear silently ends the session (`shouldEndSession` defaults to `false` but without a reprompt Alexa closes the session after a timeout).

6. **Fault 6 — `addon.json` URI points to MCP transport**: `alexa/addon.json` `integrations[0].config.endpoints.default.uri` is set to `https://greencode-teal.vercel.app/mcp`. This is the MCP Streamable HTTP transport path, which expects JSON-RPC, not ASK. The ASK webhook is at `/api/alexa/skill`. Every voice request from an Alexa device reads this file to discover the endpoint, so all traffic goes to the wrong handler.

## Correctness Properties

Property 1: Bug Condition — Alexa Pipeline Delivers Valid ASK Responses

_For any_ well-formed ASK HTTP POST request (with a valid timestamp, correct skill ID, and valid cert chain signature) sent to `/api/alexa/skill` or `/alexa/skill`, the fixed pipeline SHALL return a valid ASK v1.0 JSON envelope with `version: "1.0"`, `outputSpeech.type: "SSML"`, speech text wrapped in `<speak>` tags, a `reprompt` block for non-terminal responses, and `sessionAttributes` echoing back the incoming session attributes.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6**

Property 2: Preservation — Non-Alexa Behavior Unchanged

_For any_ HTTP request that is NOT an ASK POST to `/api/alexa/skill` or `/alexa/skill` (i.e., any request to the MCP transport `/mcp`, to other FastAPI endpoints, or an ASK request with valid payload that exercises existing rate-limit or skill-ID enforcement), the fixed code SHALL produce exactly the same response as the original code, preserving all existing FastAPI endpoint behavior, MCP transport behavior, rate-limit enforcement (HTTP 429 with `Retry-After`), and skill-ID enforcement (HTTP 403).

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7**

## Fix Implementation

### Changes Required

Assuming the root cause analysis above is correct:

**File 1**: `app/main.py`

**Changes**:
1. **Mount `alexa_skill.router`**: After the existing `app.include_router(amazon_router)` call, add:
   ```python
   from app import alexa_skill as alexa_skill_module
   app.include_router(alexa_skill_module.router)
   ```
   This makes all routes in `app/alexa_skill.py` (including `POST /alexa/skill`) reachable via HTTP. The two existing direct `@app.post` decorators in `main.py` are preserved to avoid breaking the `mcp_server` pipeline path at `/api/alexa/skill`.

**File 2**: `app/mcp_server.py`

**Function**: `alexa_request_guard` and `_build_ask_response`

**Changes**:
2. **Add timestamp replay protection to `alexa_request_guard`**: Extract `payload.get("request", {}).get("timestamp")` from the JSON body. Parse it as UTC using `datetime.fromisoformat` or `time.strptime(..., "%Y-%m-%dT%H:%M:%SZ")` with `calendar.timegm`. If the absolute difference from `time.time()` exceeds 150 seconds, return a JSON 403 response immediately. Apply this check before rate limiting to make it unconditional regardless of the skill-ID configuration.

3. **Add ASK certificate chain verification to `alexa_request_guard`**: Read `SignatureCertChainUrl` and `Signature` headers from the raw Starlette `request.headers`. Attempt to use `ask_sdk_core.skill_builder.SkillBuilder` verifier if `ask-sdk-core` is installed. Fall back to a `cryptography`-based implementation: fetch the cert chain from the URL, verify it is from Amazon's allowed domain (`s3.amazonaws.com/.../echo.api/...`), extract the public key, and verify the base64-decoded signature against the raw request body using RSA-SHA1 (`PKCS1v15` padding). If neither is available, log a clear warning and skip (documented stub behaviour for environments where the library cannot be installed).

4. **Fix `_build_ask_response` to emit SSML**: Change `"type": "PlainText"` to `"type": "SSML"` and wrap `speech_text` in `<speak>` tags if it does not already contain them. Do the same for the `reprompt` block. Add a sensible default `reprompt_text` (`"Ask me for another audit, a region comparison, or explain a score."`) when `reprompt_text` is `None` and `should_end_session` is `False`.

**File 3**: `app/alexa_dispatch.py` (new module)

**Changes**:
5. **Extract `dispatch_nlu_action` to break the circular import**: Create `app/alexa_dispatch.py` that imports only from `app.alexa_nlp` (the NLU mapper) and `app.alexa_actions` (the action runners). Move the `dispatch_nlu_action` logic from `app/alexa_skill.py` into this new module. Update `app/alexa_skill.py` to import `dispatch_nlu_action` from `app.alexa_dispatch` (removing its own definition). Update `app/mcp_server.py`'s `_dispatch_nlu_action` to import from `app.alexa_dispatch` instead of `app.alexa_skill`, eliminating the circular dependency entirely.

**File 4**: `alexa/addon.json`

**Changes**:
6. **Fix the ASK webhook URI**: Change `integrations[0].config.endpoints.default.uri` from `"https://greencode-teal.vercel.app/mcp"` to `"https://greencode-teal.vercel.app/api/alexa/skill"`. Leave the `type: "MCP"` and all other fields in the `integrations` array unchanged.

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate each bug on unfixed code to confirm the root cause analysis, then verify the fix works and that existing behavior is preserved.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples demonstrating each of the six faults BEFORE implementing the fix. Confirm or refute the root cause analysis.

**Test Plan**: Write tests that target each fault directly against the unfixed code. Run them to observe failures and understand exact failure modes.

**Test Cases**:
1. **Fault 1 — Router not mounted**: Send a POST to `/alexa/skill` on the unfixed `main.py` app; assert HTTP 404 (will fail with 404 on unfixed code, should return a valid ASK envelope after fix)
2. **Fault 2 — Timestamp not checked**: Call `alexa_request_guard` with a payload whose `request.timestamp` is 200 seconds in the past; assert HTTP 403 (will return `None` / pass on unfixed code)
3. **Fault 3 — Cert chain not verified**: Call `alexa_request_guard` (or the full webhook handler) with forged `SignatureCertChainUrl` and `Signature` headers; assert HTTP 400 (will return `None` / pass on unfixed code)
4. **Fault 4 — Circular import swallows intent**: Trigger `handle_alexa_skill_request` with a `FreeformGreenCodeQueryIntent` payload; assert the response contains valid speech text (may return an empty/error response on unfixed code due to circular import)
5. **Fault 5 — Wrong response type**: Call `_build_ask_response("hello")` and inspect the envelope; assert `outputSpeech.type == "SSML"` and `response.reprompt` is present (will fail with `"PlainText"` and missing reprompt on unfixed code)
6. **Fault 6 — Wrong addon.json URI**: Parse `alexa/addon.json` and assert `integrations[0].config.endpoints.default.uri` ends with `/api/alexa/skill` (will fail with `/mcp` on unfixed code)

**Expected Counterexamples**:
- HTTP 404 for routes defined only in the unmounted router
- Missing timestamp enforcement allows stale payloads through
- Missing cert verification allows unsigned requests through
- `dispatch_nlu_action` returns `None` or raises for `FreeformGreenCodeQueryIntent`
- `outputSpeech.type` is `"PlainText"` and `reprompt` key is absent from the response body
- `addon.json` contains the MCP transport URI instead of the ASK webhook URI

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed pipeline produces the expected behavior.

**Pseudocode:**
```
FOR ALL input WHERE isBugCondition(input) DO
  result := alexa_pipeline_fixed(input)
  ASSERT expectedBehavior(result)
    -- result.version == "1.0"
    -- result.response.outputSpeech.type == "SSML"
    -- result.response.outputSpeech.ssml STARTS_WITH "<speak>"
    -- result.response.reprompt EXISTS (for non-terminal responses)
    -- result.sessionAttributes == input.session.attributes
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed pipeline produces the same result as the original pipeline.

**Pseudocode:**
```
FOR ALL input WHERE NOT isBugCondition(input) DO
  ASSERT original_pipeline(input) == fixed_pipeline(input)
    -- rate limit enforcement identical
    -- skill-ID enforcement identical
    -- MCP transport responses identical
    -- all other FastAPI endpoint responses identical
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many test cases automatically across the input domain
- It catches edge cases that manual unit tests might miss
- It provides strong guarantees that behavior is unchanged for all non-buggy inputs

**Test Plan**: Observe behavior on unfixed code first for rate-limit, skill-ID, and existing intent responses, then write property-based tests capturing that behavior.

**Test Cases**:
1. **Rate Limit Preservation**: Fire more than `GREENCODE_ALEXA_RATE_LIMIT` requests from one IP within the window; verify HTTP 429 with `Retry-After` header still fires after the fix
2. **Skill ID Preservation**: Send a payload with a mismatched `applicationId` when `GREENCODE_ALEXA_SKILL_ID` is set; verify HTTP 403 still fires after the fix
3. **LaunchRequest Preservation**: Send a `LaunchRequest`; verify response still contains `version: "1.0"` and non-empty speech output after the fix
4. **CompareRegionsIntent Preservation**: Send `CompareRegionsIntent` with two region slots; verify response includes region comparison speech and a `reprompt` block after the fix
5. **SessionAttributes Preservation**: Send any intent with `sessionAttributes`; verify the same attributes appear in the response after the fix
6. **MCP Transport Preservation**: Issue a JSON-RPC call to `/mcp`; verify response is unchanged after the fix (no cross-contamination from the router mount)
7. **addon.json MCP Config Preservation**: Parse `alexa/addon.json` after the fix; verify `integrations[0].type == "MCP"` and the MCP config block is otherwise intact

### Unit Tests

- Test `alexa_request_guard` rejects payloads with a timestamp older than 150 seconds (Fault 2)
- Test `alexa_request_guard` rejects payloads with invalid/missing `SignatureCertChainUrl` (Fault 3)
- Test `_build_ask_response` returns `outputSpeech.type == "SSML"` with speech wrapped in `<speak>` (Fault 5)
- Test `_build_ask_response` includes `reprompt` block when `should_end_session=False` (Fault 5)
- Test `dispatch_nlu_action` is importable from `app.alexa_dispatch` and returns correct result for `FreeformGreenCodeQueryIntent` without circular import (Fault 4)
- Test that `GET /alexa/skill` (router-mounted path) is reachable after the fix (Fault 1)
- Test `alexa/addon.json` URI points to `/api/alexa/skill` (Fault 6)

### Property-Based Tests

- Generate random ASK payloads with timestamps in `[now - 149s, now + 149s]` and verify they pass the timestamp guard (preservation: valid fresh requests are accepted)
- Generate random ASK payloads with timestamps outside `[now - 150s, now + 150s]` and verify they are rejected with HTTP 403 (fix: stale requests are always rejected)
- Generate random non-`"SessionEndedRequest"` intents and verify every `_build_ask_response` output has `outputSpeech.type == "SSML"` and a `reprompt` block (fix: correct response format)
- Generate random non-Alexa HTTP requests to `main.py` endpoints and verify responses are identical before and after the fix (preservation: no regressions)

### Integration Tests

- Full round-trip: POST a valid `LaunchRequest` to `/api/alexa/skill` with a fresh timestamp and valid cert chain headers; verify a valid ASK v1.0 SSML envelope is returned
- Full round-trip: POST `CompareRegionsIntent` with `zone1=ireland` and `zone2=california`; verify SSML response with region data and reprompt
- Context switching: Send `LaunchRequest` followed by `CompareRegionsIntent` in the same session; verify `sessionAttributes` are propagated between turns
- Replay attack: Re-send a captured valid request payload with the original timestamp after 151 seconds; verify HTTP 403 is returned
- MCP transport: Confirm `POST /mcp` with a valid `tools/list` JSON-RPC body still returns a valid JSON-RPC response after all Alexa fixes are applied
