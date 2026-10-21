# Implementation Plan

## Overview

Fix all six structural faults in the GreenCode Alexa voice pipeline that cause total silent failure. The workflow follows the bug condition methodology: write exploration and preservation tests first (before touching any production code), then apply each fix, then verify the tests pass.

## Task Dependency Graph

```json
{
  "waves": [
    { "wave": 1, "tasks": ["1", "2"] },
    { "wave": 2, "tasks": ["3"] },
    { "wave": 3, "tasks": ["4", "5", "6", "7", "8"] },
    { "wave": 4, "tasks": ["9"] },
    { "wave": 5, "tasks": ["10"] }
  ]
}
```

## Tasks

- [ ] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - Alexa Pipeline Six-Fault Silent Failure
  - **CRITICAL**: This test MUST FAIL on unfixed code — failure confirms the bugs exist
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior — it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples demonstrating each of the six structural faults
  - **Scoped PBT Approach**: Scope each sub-check to a concrete failing case to ensure reproducibility
  - Create `tests/test_alexa_pipeline_fix.py` and write the following six targeted checks:
    - **Fault 1 — Router not mounted**: POST to `/alexa/skill` on the unfixed `main.py` app; assert response is NOT HTTP 404 (confirms router is mounted); expect FAILURE with 404 on unfixed code
    - **Fault 2 — Timestamp not checked**: Call `alexa_request_guard` with a payload whose `request.timestamp` is 200 seconds in the past; assert HTTP 403; expect FAILURE (guard passes stale payload on unfixed code)
    - **Fault 3 — Cert chain not verified**: Call the webhook handler with forged `SignatureCertChainUrl` and `Signature` headers; assert HTTP 400; expect FAILURE (handler ignores headers on unfixed code)
    - **Fault 4 — Circular import swallows intent**: Trigger `handle_alexa_skill_request` with a `FreeformGreenCodeQueryIntent` payload; assert the response contains a non-empty `outputSpeech.text`; expect FAILURE (circular import returns None/error on unfixed code)
    - **Fault 5 — Wrong response type**: Call `_build_ask_response("hello", should_end_session=False)` and assert `outputSpeech.type == "SSML"` and `response.reprompt` is present; expect FAILURE (`"PlainText"` and missing reprompt on unfixed code)
    - **Fault 6 — Wrong addon.json URI**: Parse `alexa/addon.json` and assert `integrations[0].config.endpoints.default.uri` ends with `/api/alexa/skill`; expect FAILURE (points to `/mcp` on unfixed code)
  - Run all six checks on UNFIXED code
  - **EXPECTED OUTCOME**: All six checks FAIL (this is correct — it proves each fault exists)
  - Document the counterexamples found (e.g. "POST /alexa/skill → 404", "`outputSpeech.type` is `PlainText`", "addon.json URI is `.../mcp`")
  - Mark task complete when tests are written, run, and all six failures are documented
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

- [ ] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Non-Alexa and Existing-Alexa Behavior Unchanged
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for all non-buggy inputs (inputs where `isBugCondition` returns false):
    - Observe: rate-limit guard fires HTTP 429 with `Retry-After` when budget is exceeded
    - Observe: skill-ID guard fires HTTP 403 when `applicationId` mismatches `GREENCODE_ALEXA_SKILL_ID`
    - Observe: `handle_alexa_skill_request(LaunchRequest)` returns envelope with `version: "1.0"` and non-empty speech
    - Observe: `handle_alexa_skill_request(CompareRegionsIntent, zone1=ireland, zone2=california)` returns speech and `reprompt`
    - Observe: any intent with `sessionAttributes` echoes those attributes back in the response
    - Observe: `POST /mcp` with valid `tools/list` JSON-RPC body returns a valid JSON-RPC response
    - Observe: `addon.json` `integrations[0].type == "MCP"` and the MCP config block is intact
  - Write property-based tests in `tests/test_alexa_pipeline_fix.py` capturing each observed behavior pattern (from Preservation Requirements in design):
    - For all request counts ≤ rate-limit budget: `alexa_request_guard` does NOT return HTTP 429
    - For all request counts > rate-limit budget from the same IP: response is HTTP 429 with `Retry-After` header
    - For all payloads where `applicationId != GREENCODE_ALEXA_SKILL_ID` (when env var is set): response is HTTP 403
    - For all valid `LaunchRequest` payloads: response `version == "1.0"` and `outputSpeech` is non-empty
    - For all intents with non-empty `sessionAttributes` dict: response `sessionAttributes` equals input `sessionAttributes`
    - For all non-Alexa path requests: response is identical to unfixed behavior
  - Run all preservation tests on UNFIXED code
  - **EXPECTED OUTCOME**: All preservation tests PASS (confirms baseline behavior to protect)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

- [ ] 3. Break the circular import — create `app/alexa_dispatch.py`

  - [ ] 3.1 Create `app/alexa_dispatch.py` with extracted `dispatch_nlu_action`
    - Create new module `app/alexa_dispatch.py`
    - Import only from `app.alexa_nlp` (NLU mapper) and `app.alexa_actions` (action runners) — no imports from `app.mcp_server` or `app.alexa_skill`
    - Move the `dispatch_nlu_action` function body from `app/alexa_skill.py` into this module
    - _Bug_Condition: `isBugCondition(input)` Fault 4 — circular import between `mcp_server` and `alexa_skill` causes `dispatch_nlu_action` to be `None` or raise `ImportError`_
    - _Expected_Behavior: `dispatch_nlu_action` is importable from `app.alexa_dispatch` and returns a valid speech string for any NLU query_
    - _Preservation: All existing intent handlers and NLU action logic must produce identical output; no changes to `app.alexa_nlp` or `app.alexa_actions`_
    - _Requirements: 2.4_

  - [ ] 3.2 Update `app/alexa_skill.py` to import from `app.alexa_dispatch`
    - Replace the `dispatch_nlu_action` function definition in `app/alexa_skill.py` with `from app.alexa_dispatch import dispatch_nlu_action`
    - Confirm no other functions in `alexa_skill.py` are moved or removed
    - _Requirements: 2.4_

  - [ ] 3.3 Update `app/mcp_server.py` `_dispatch_nlu_action` to import from `app.alexa_dispatch`
    - Change the deferred `from app.alexa_skill import dispatch_nlu_action` inside `_dispatch_nlu_action` to `from app.alexa_dispatch import dispatch_nlu_action`
    - Verify the call site and argument list are unchanged
    - _Requirements: 2.4_

- [ ] 4. Fix `_build_ask_response` to emit SSML with reprompt

  - [ ] 4.1 Change `outputSpeech.type` from `"PlainText"` to `"SSML"` and wrap speech in `<speak>` tags
    - In `app/mcp_server.py`, locate `_build_ask_response`
    - Change `"type": "PlainText"` to `"type": "SSML"` in the `outputSpeech` block
    - Wrap `speech_text` in `<speak>…</speak>` if it does not already start with `<speak>`
    - Apply the same wrapping to the `reprompt` `outputSpeech` block
    - _Bug_Condition: `isBugCondition(input)` Fault 5 — `_build_ask_response` hardcodes `"PlainText"` and omits reprompt, degrading speech and silently ending sessions_
    - _Expected_Behavior: every ASK response envelope has `outputSpeech.type == "SSML"` and speech wrapped in `<speak>` tags_
    - _Preservation: All callers of `_build_ask_response` that already pass `reprompt_text` must continue to receive an identical envelope structure_
    - _Requirements: 2.5_

  - [ ] 4.2 Add default `reprompt_text` when `reprompt_text` is None and `should_end_session` is False
    - In `_build_ask_response`, when `reprompt_text is None` and `should_end_session` is `False`, set `reprompt_text` to `"Ask me for another audit, a region comparison, or explain a score."`
    - Ensure the `reprompt` block is always included in the response envelope for non-terminal responses
    - _Requirements: 2.5_

- [ ] 5. Add timestamp replay protection to `alexa_request_guard`

  - [ ] 5.1 Extract and validate `request.timestamp` in `alexa_request_guard`
    - In `app/mcp_server.py`, locate `alexa_request_guard`
    - Extract `payload.get("request", {}).get("timestamp")` from the parsed JSON body
    - Parse the timestamp as UTC using `datetime.fromisoformat` (Python 3.7+) or `time.strptime(..., "%Y-%m-%dT%H:%M:%SZ")` with `calendar.timegm`
    - If the absolute difference from `time.time()` exceeds 150 seconds, return a JSON 403 response immediately
    - Apply this check before the rate-limit check so it is unconditional
    - _Bug_Condition: `isBugCondition(input)` Fault 2 — `alexa_request_guard` performs no timestamp extraction, allowing replayed requests older than 150 s through_
    - _Expected_Behavior: any ASK POST whose `request.timestamp` differs from `now_utc()` by more than 150 seconds is rejected with HTTP 403_
    - _Preservation: Valid fresh requests (timestamp within ±150 s) continue to pass the guard unchanged; rate-limit and skill-ID checks are unaffected_
    - _Requirements: 2.2, 3.1, 3.2_

- [ ] 6. Add ASK certificate chain verification to `alexa_request_guard`

  - [ ] 6.1 Read `SignatureCertChainUrl` and `Signature` headers and verify against request body
    - In `app/mcp_server.py` `alexa_request_guard`, read `SignatureCertChainUrl` and `Signature` from `request.headers`
    - Attempt verification using `ask_sdk_core` verifier if `ask-sdk-core` is installed
    - Fall back to `cryptography`-based implementation: fetch the cert chain URL, verify it is from Amazon's allowed domain (`s3.amazonaws.com/.../echo.api/...`), extract the public key, and verify the base64-decoded signature against the raw request body using RSA-SHA1 (`PKCS1v15` padding)
    - If neither library is available, log a clear warning (`"ASK cert verification unavailable — skipping (stub)"`) and skip without raising
    - Reject requests with invalid signatures with HTTP 400
    - _Bug_Condition: `isBugCondition(input)` Fault 3 — neither `alexa_request_guard` nor the webhook handler in `main.py` inspects `SignatureCertChainUrl` / `Signature` headers, causing skill certification failure_
    - _Expected_Behavior: requests with invalid or missing ASK signature headers are rejected with HTTP 400; requests with valid headers pass through_
    - _Preservation: Existing rate-limit and skill-ID checks are unaffected; cert verification is applied only to ASK POST paths_
    - _Requirements: 2.3, 3.1, 3.2_

- [ ] 7. Mount `alexa_skill.router` in `app/main.py`

  - [ ] 7.1 Add `app.include_router(alexa_skill_module.router)` after existing router includes
    - In `app/main.py`, add:
      ```python
      from app import alexa_skill as _alexa_skill_module
      app.include_router(_alexa_skill_module.router)
      ```
      immediately after the existing `app.include_router(amazon_router)` call
    - Do NOT remove or modify the two existing `@app.post` decorators for `/api/alexa/skill` in `main.py` — they must remain to preserve the `mcp_server` pipeline path
    - _Bug_Condition: `isBugCondition(input)` Fault 1 — `app/main.py` never calls `app.include_router(alexa_skill.router)`, making all handlers in `app/alexa_skill.py` permanently unreachable (HTTP 404)_
    - _Expected_Behavior: all routes defined in `app/alexa_skill.py` (including `POST /alexa/skill`) are reachable via HTTP after startup_
    - _Preservation: All existing FastAPI endpoints in `main.py` must continue to function; the MCP transport path at `/mcp` is unaffected_
    - _Requirements: 2.1, 3.7_

- [ ] 8. Fix `alexa/addon.json` endpoint URI

  - [ ] 8.1 Update `integrations[0].config.endpoints.default.uri` to the correct ASK webhook URL
    - In `alexa/addon.json`, change `integrations[0].config.endpoints.default.uri` from `"https://greencode-teal.vercel.app/mcp"` to `"https://greencode-teal.vercel.app/api/alexa/skill"`
    - Leave `integrations[0].type`, all other fields in the `integrations` array, and the MCP config block completely unchanged
    - _Bug_Condition: `isBugCondition(input)` Fault 6 — `addon.json` points Alexa devices to the MCP Streamable HTTP transport (`/mcp`) instead of the ASK webhook (`/api/alexa/skill`), so all voice requests are mishandled silently_
    - _Expected_Behavior: Alexa devices resolve the correct ASK webhook URI from `addon.json` and route voice requests to `/api/alexa/skill`_
    - _Preservation: `integrations[0].type == "MCP"` and all other MCP config fields remain intact_
    - _Requirements: 2.6, 3.6_

- [ ] 9. Verify bug condition exploration test now passes

  - [ ] 9.1 Re-run all six bug condition checks from task 1 against fixed code
    - **Property 1: Expected Behavior** - Alexa Pipeline Six-Fault Silent Failure
    - **IMPORTANT**: Re-run the SAME tests from task 1 — do NOT write new tests
    - The tests from task 1 encode the expected behavior for all six faults
    - When all six checks pass, it confirms the expected behavior is satisfied for every fault
    - Run all six bug condition checks from `tests/test_alexa_pipeline_fix.py`
    - **EXPECTED OUTCOME**: All six checks PASS (confirms all six bugs are fixed)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

  - [ ] 9.2 Verify preservation tests still pass
    - **Property 2: Preservation** - Non-Alexa and Existing-Alexa Behavior Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 — do NOT write new tests
    - Run all preservation property tests from `tests/test_alexa_pipeline_fix.py`
    - **EXPECTED OUTCOME**: All preservation tests PASS (confirms no regressions)
    - Confirm rate-limit enforcement, skill-ID enforcement, existing intent handlers, session attribute echo, MCP transport, and `addon.json` MCP config are all unchanged
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

  - [ ] 9.3 Verify existing test suites still pass
    - Run `tests/test_alexa_skill.py` and `tests/test_alexa_compliance.py`
    - **EXPECTED OUTCOME**: All pre-existing tests PASS (no regressions introduced by any of the six fixes)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

- [ ] 10. Checkpoint — Ensure all tests pass
  - Run the full test suite: `tests/test_alexa_pipeline_fix.py`, `tests/test_alexa_skill.py`, and `tests/test_alexa_compliance.py`
  - Ensure all tests pass. Ask the user if questions arise.
  - Confirm no new test failures have been introduced across any other test file in the repository

## Notes

- Tasks 1 and 2 (exploration and preservation tests) MUST be written and run on unfixed code before any implementation task begins.
- Task 3 (circular import fix) is a prerequisite for tasks 4–7 because `app/alexa_dispatch.py` must exist before other modules can reference it cleanly.
- Tasks 4–8 are independent of each other and can be executed in any order after task 3 is complete.
- Task 9 re-runs the tests from tasks 1 and 2 — do NOT write new tests.
- The six fault fixes target three files (`app/mcp_server.py`, `app/main.py`, `alexa/addon.json`), one updated file (`app/alexa_skill.py`), and one new file (`app/alexa_dispatch.py`).
- Cert verification (task 6) may be a documented stub if neither `ask-sdk-core` nor `cryptography` can be installed in the target environment; log a clear warning in that case.
