# Bugfix Requirements Document

## Introduction

The GreenCode Alexa voice integration pipeline is completely non-functional due to six compounding structural faults. Together they produce a total silent failure: Alexa neither listens nor responds. The faults span router mounting (`alexa_skill.router` is dead code), security gaps in the active webhook guard (no timestamp replay protection, no ASK certificate chain verification), a circular import that silently swallows `FreeformGreenCodeQueryIntent` at runtime, a response format mismatch (`PlainText` vs SSML), and a misconfigured `addon.json` endpoint URL that sends Alexa devices to the MCP transport instead of the ASK webhook.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN `app/alexa_skill.py` defines `router = APIRouter(prefix="/alexa")` with the complete SSML pipeline and intent handlers THEN `app/main.py` never calls `app.include_router(alexa_skill.router)`, making all handlers in that router permanently unreachable via HTTP

1.2 WHEN a POST request arrives at `/api/alexa/skill` THEN `mcp_server.alexa_request_guard()` processes it with only rate-limit and skill-ID checks, performing no timestamp verification, leaving the active webhook vulnerable to replayed requests

1.3 WHEN a POST request arrives at `/api/alexa/skill` THEN neither `mcp_server.alexa_request_guard()` nor `main.api_alexa_custom_skill_webhook()` verifies the `SignatureCertChainUrl` and `Signature` ASK request headers, causing the skill to fail Amazon certification

1.4 WHEN `handle_alexa_skill_request()` dispatches a `FreeformGreenCodeQueryIntent` THEN `_dispatch_nlu_action()` executes `from app.alexa_skill import dispatch_nlu_action` while `alexa_skill.py` itself imports from `app.mcp_server`, creating a circular import that can silently fail at import time and return nothing

1.5 WHEN `mcp_server._build_ask_response()` constructs an ASK response envelope THEN `outputSpeech.type` is hardcoded to `"PlainText"` rather than `"SSML"`, producing degraded speech without prosody markup, and any intent handler that omits `reprompt_text` silently ends the Alexa session on a mishear

1.6 WHEN the Alexa device resolves the integration endpoint from `alexa/addon.json` THEN it reads `"uri": "https://greencode-teal.vercel.app/mcp"`, which points at the MCP Streamable HTTP transport rather than the ASK webhook at `/api/alexa/skill`, so no voice request ever reaches the correct handler

### Expected Behavior (Correct)

2.1 WHEN `app/main.py` starts up THEN it SHALL call `app.include_router(alexa_skill.router)` so that all handlers defined in `app/alexa_skill.py` are reachable via HTTP at the `/alexa` prefix

2.2 WHEN a POST request arrives at `/api/alexa/skill` THEN the active guard SHALL extract the timestamp from the ASK JSON payload (`request.timestamp`), parse it as UTC, and reject with HTTP 403 any request whose timestamp differs from the current time by more than 150 seconds

2.3 WHEN a POST request arrives at `/api/alexa/skill` THEN the handler SHALL verify the `SignatureCertChainUrl` and `Signature` request headers against the request body per the ASK specification, rejecting invalid signatures with HTTP 400

2.4 WHEN `FreeformGreenCodeQueryIntent` is dispatched THEN the system SHALL resolve `dispatch_nlu_action` without triggering a circular import, either by removing the deferred `from app.alexa_skill import dispatch_nlu_action` call inside `mcp_server` or by restructuring the shared logic into a third module that neither `mcp_server` nor `alexa_skill` imports from the other

2.5 WHEN `_build_ask_response()` constructs an ASK response THEN it SHALL emit `outputSpeech.type = "SSML"` with speech wrapped in `<speak>` tags, and every active intent handler that does not explicitly end the session SHALL include a non-empty `reprompt` block

2.6 WHEN the Alexa device reads the integration endpoint from `alexa/addon.json` THEN the `"uri"` field SHALL point to the correct ASK webhook URL (e.g. `https://greencode-teal.vercel.app/api/alexa/skill`) rather than the MCP transport path

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a POST arrives at `/api/alexa/skill` with a valid ASK payload within the rate-limit budget THEN the system SHALL CONTINUE TO enforce rate limiting per client IP and return HTTP 429 with a `Retry-After` header when the budget is exceeded

3.2 WHEN a POST arrives at `/api/alexa/skill` with an `applicationId` that does not match the configured `GREENCODE_ALEXA_SKILL_ID` THEN the system SHALL CONTINUE TO reject the request with HTTP 403

3.3 WHEN `handle_alexa_skill_request()` receives a `LaunchRequest` THEN the system SHALL CONTINUE TO return a valid ASK 1.0 JSON envelope with `version: "1.0"` and non-empty speech output

3.4 WHEN `handle_alexa_skill_request()` receives a `CompareRegionsIntent` with two region slots THEN the system SHALL CONTINUE TO return a region comparison speech response including a `reprompt`

3.5 WHEN `handle_alexa_skill_request()` successfully processes any intent THEN the system SHALL CONTINUE TO echo the session attributes from the incoming request back in the `sessionAttributes` field of the response

3.6 WHEN `addon.json` is updated with the corrected ASK webhook URL THEN the MCP integration entry SHALL CONTINUE TO reference the `integrations` array with `type: "MCP"` so the MCP Streamable HTTP transport configuration is not disrupted

3.7 WHEN all six faults are fixed THEN the existing behaviour of every other FastAPI endpoint in `main.py` that is not part of the Alexa voice pipeline SHALL CONTINUE TO be unaffected
