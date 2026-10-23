"""Tests for the Alexa voice-control surface.

Three layers are covered, matching the three modules that make up the system:

1. ``app.mcp_server.alexa_skill_webhook`` - the LIVE ASK endpoint mounted on
   both the main FastAPI app and the MCP server (``/alexa/skill`` and
   ``/api/alexa/skill``). Production hardening lives here: skill-ID guard,
   rate limiting, and the spoken-error fallback.
2. ``app.alexa_nlp`` - the free-form utterance to GreenCode tool mapper used
   by the SearchQuery fallback path.
3. ``app.alexa_responses`` - the SSML builders; every number, score and list
   Alexa speaks passes through them, so escaping and formatting are asserted
   here rather than by ear.

Nothing opens a socket: the HTTP tests drive ``mcp_server.create_app()`` in
-process with Starlette's TestClient, the same code path a real Alexa turn
executes.
"""

import json
import os
import time
import unittest
from unittest import mock

from fastapi import FastAPI
from fastapi import HTTPException
from starlette.testclient import TestClient

from app import alexa_nlp, alexa_skill, alexa_responses, mcp_server
from app.auth.jwt import create_tokens

LAUNCH = {"version": "1.0", "request": {"type": "LaunchRequest"}}


class _WebhookTestBase(unittest.TestCase):
    """Shared setup: isolated rate-limit buckets and pinned environment."""

    def setUp(self):
        mcp_server._alexa_rate_buckets.clear()
        self.skill_id = "amzn1.ask.skill.test"
        self._env = mock.patch.dict(
            os.environ,
            {"GREENCODE_ALEXA_SKILL_ID": self.skill_id, "GREENCODE_ALEXA_RATE_LIMIT": "100"},
        )
        self._env.start()
        self._signature = mock.patch("app.mcp_server._verify_ask_cert_chain", return_value=None)
        self._signature.start()
        self.client = TestClient(mcp_server.create_app())

    def _post(self, path, *, json_body=None, content=None, headers=None):
        request_headers = dict(headers or {})
        if json_body is not None:
            json_body = json.loads(json.dumps(json_body))
            request = json_body.setdefault("request", {})
            request.setdefault("timestamp", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
            session = json_body.setdefault("session", {})
            application = session.setdefault("application", {})
            application.setdefault("applicationId", self.skill_id)
            request_headers.setdefault(
                "SignatureCertChainUrl", "https://s3.amazonaws.com/echo.api/test.pem"
            )
            request_headers.setdefault("Signature-256", "dGVzdA==")
        return self.client.post(path, json=json_body, content=content, headers=request_headers)

    def tearDown(self):
        self.client.close()
        self._signature.stop()
        self._env.stop()
        mcp_server._alexa_rate_buckets.clear()


class TestAskWebhookHardening(_WebhookTestBase):
    """The live endpoint must survive hostile and abusive traffic."""

    def test_launch_request_returns_valid_ask_envelope(self):
        resp = self._post("/alexa/skill", json_body=LAUNCH)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["version"], "1.0")
        speech = body["response"]["outputSpeech"]
        self.assertIn(speech["type"], ("SSML", "PlainText"))
        self.assertIn("GreenCode", json.dumps(speech))
        self.assertIn("link your GreenCode dashboard", speech["ssml"])
        self.assertIn("selected repository and audit", speech["ssml"])
        self.assertNotIn("audit your Python", speech["ssml"])
        self.assertFalse(body["response"]["shouldEndSession"])
        self.assertIn("compare named grid regions", body["response"]["reprompt"]["outputSpeech"]["ssml"])

    def test_help_intent_explains_dashboard_pairing(self):
        payload = {
            "version": "1.0",
            "request": {
                "type": "IntentRequest",
                "intent": {"name": "AMAZON.HelpIntent"},
            },
        }
        resp = self._post("/alexa/skill", json_body=payload)
        self.assertEqual(resp.status_code, 200)
        speech = resp.json()["response"]["outputSpeech"]["ssml"]
        self.assertIn("link your account", speech)
        self.assertIn("Pair Alexa", speech)
        self.assertNotIn("audit my Python code", speech)

    def test_invalid_json_returns_400(self):
        resp = self._post(
            "/alexa/skill", content=b"{not json", headers={"Content-Type": "application/json"}
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error"], "invalid_json")

    def test_rate_limit_returns_429_with_retry_after(self):
        with mock.patch.dict(os.environ, {"GREENCODE_ALEXA_RATE_LIMIT": "3"}):
            for _ in range(3):
                self.assertEqual(self._post("/alexa/skill", json_body=LAUNCH).status_code, 200)
            resp = self._post("/alexa/skill", json_body=LAUNCH)
        self.assertEqual(resp.status_code, 429)
        self.assertEqual(resp.json()["error"], "rate_limited")
        self.assertIn("Retry-After", resp.headers)

    def test_rate_limit_is_keyed_by_forwarded_client(self):
        with mock.patch.dict(os.environ, {"GREENCODE_ALEXA_RATE_LIMIT": "1"}):
            first = self._post(
                "/api/alexa/skill", json_body=LAUNCH, headers={"X-Forwarded-For": "203.0.113.9"}
            )
            second = self._post(
                "/api/alexa/skill", json_body=LAUNCH, headers={"X-Forwarded-For": "203.0.113.9"}
            )
            other = self._post(
                "/api/alexa/skill", json_body=LAUNCH, headers={"X-Forwarded-For": "198.51.100.4"}
            )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
        self.assertEqual(other.status_code, 200)

    def test_skill_id_mismatch_is_rejected(self):
        good = "amzn1.ask.skill.fd2a8106-e7fb-4f05-83b9-74590f7df6b8"
        payload = {
            "version": "1.0",
            "session": {"application": {"applicationId": "amzn1.ask.skill.evil"}},
            "request": {"type": "LaunchRequest"},
        }
        with mock.patch.dict(os.environ, {"GREENCODE_ALEXA_SKILL_ID": good}):
            forged = self._post("/alexa/skill", json_body=payload)
            payload["session"]["application"]["applicationId"] = good
            genuine = self._post("/alexa/skill", json_body=payload)
        self.assertEqual(forged.status_code, 403)
        self.assertEqual(forged.json()["error"], "forbidden_skill_id")
        self.assertEqual(genuine.status_code, 200)


class TestNlpMapper(unittest.TestCase):
    """Free-form utterances must resolve to the right GreenCode tool."""

    def test_repository_audit_utterance(self):
        cmd = alexa_nlp.MAPPER.map("audit my repository for energy waste")
        self.assertEqual(cmd.tool, "audit_repository")
        self.assertEqual(cmd.payload["repo"], "")
        self.assertFalse(cmd.fallback)
        self.assertGreaterEqual(cmd.confidence, 0.65)

    def test_list_github_repositories_utterance(self):
        for utterance in (
            "list my GitHub repositories",
            "show my repositories",
            "get repositories",
        ):
            with self.subTest(utterance=utterance):
                command = alexa_nlp.MAPPER.map(utterance)
                self.assertEqual(command.tool, "list_repositories")
                self.assertFalse(command.fallback)

    def test_green_score_utterance_maps_to_end_to_end_audit(self):
        cmd = alexa_nlp.MAPPER.map("what is my green score")
        self.assertEqual(cmd.tool, "audit_and_score")
        self.assertEqual(cmd.payload["source_code"], "")

    def test_region_comparison_utterance(self):
        cmd = alexa_nlp.MAPPER.map("compare ireland and virginia for my batch job")
        self.assertEqual(cmd.tool, "compare_regions")
        self.assertIn("zones", cmd.payload)
        self.assertEqual(len(cmd.payload["zones"]), 2)

    def test_voice_commands_do_not_fill_in_sample_measurements(self):
        sci = alexa_nlp.MAPPER.map("calculate sci")
        sla = alexa_nlp.MAPPER.map("check my energy sla")
        energy = alexa_nlp.MAPPER.map("measure energy")

        self.assertIsNone(sci.payload["energy_joules"])
        self.assertIsNone(sci.payload["duration_seconds"])
        self.assertIsNone(sci.payload["functional_unit"])
        self.assertEqual(sci.payload["zone"], "")
        self.assertIsNone(sla.payload["total_joules"])
        self.assertIsNone(sla.payload["green_score"])
        self.assertEqual(energy.payload, {})

    def test_sci_command_extracts_explicit_measurement_values(self):
        command = alexa_nlp.MAPPER.map(
            "calculate sci using 1000 joules in 30 seconds for 200 requests in Ireland"
        )

        self.assertEqual(command.tool, "calculate_sci")
        self.assertEqual(command.payload["energy_joules"], 1000.0)
        self.assertEqual(command.payload["duration_seconds"], 30.0)
        self.assertEqual(command.payload["functional_unit"], 200.0)
        self.assertEqual(command.payload["zone"], "IE")

    def test_unintelligible_utterance_falls_back_to_help(self):
        cmd = alexa_nlp.MAPPER.map("flurble glurble wompus")
        self.assertTrue(cmd.fallback)
        self.assertEqual(cmd.tool, "help")
        self.assertEqual(cmd.confidence, 0.0)
        self.assertIn("audit my repository", cmd.summary)

    def test_empty_utterance_falls_back_without_raising(self):
        for blank in ("", "   "):
            cmd = alexa_nlp.MAPPER.map(blank)
            self.assertTrue(cmd.fallback)
            self.assertEqual(cmd.tool, "help")


class TestSsmlBuilders(unittest.TestCase):
    """Alexa speaks raw SSML: escaping and number formatting are load-bearing."""

    def test_response_wraps_speech_and_escapes_markup(self):
        resp = alexa_responses.build_response("Tom & Jerry <win> the 'race'")
        ssml = resp["response"]["outputSpeech"]["ssml"]
        self.assertTrue(ssml.startswith("<speak>"))
        self.assertTrue(ssml.endswith("</speak>"))
        self.assertIn("&amp; Jerry &lt;win&gt; the &apos;race&apos;", ssml)

    def test_session_attributes_round_trip(self):
        resp = alexa_responses.build_response("hi", session_attributes={"last_zone": "IE"})
        self.assertEqual(resp["sessionAttributes"], {"last_zone": "IE"})

    def test_error_response_apologises_and_keeps_session_open(self):
        resp = alexa_responses.build_error_response("the grid source is unreachable.")
        self.assertIn("I&apos;m sorry", resp["response"]["outputSpeech"]["ssml"])
        self.assertFalse(resp["response"]["shouldEndSession"])
        self.assertIn("reprompt", resp["response"])

    def test_help_response_describes_supported_features_and_action_limits(self):
        resp = alexa_responses.build_help_response()
        ssml = resp["response"]["outputSpeech"]["ssml"]
        for phrase in (
            "documented features",
            "compare named grid regions",
            "uses its connected GitHub account",
            "Pair the standalone Alexa skill",
            "Amazon controls when the session ends",
        ):
            self.assertIn(phrase, ssml)
        self.assertNotIn("not linked to your GitHub account", ssml)
        self.assertNotIn("cannot scan your repositories", ssml)
        self.assertFalse(resp["response"]["shouldEndSession"])

    def test_scores_are_spoken_as_cardinal_percent(self):
        resp = alexa_responses.build_response(
            alexa_responses._say_score(87.6), card_title="Score"
        )
        ssml = resp["response"]["outputSpeech"]["ssml"]
        # The generated <say-as> tag must reach Alexa unescaped...
        self.assertIn("<say-as interpret-as='cardinal'>88</say-as> percent", ssml)
        # ...and the phone card must show plain text, not markup.
        self.assertEqual(resp["response"]["card"]["content"], "88 percent")

    def test_repository_list_does_not_claim_dashboard_selection_is_unknown(self):
        resp = alexa_responses.build_list_response(
            {"data": {"repositories": [{"name": "greencode"}]}}
        )
        ssml = resp["response"]["outputSpeech"]["ssml"]

        self.assertIn("connected repositories: greencode", ssml)
        self.assertNotIn("cannot tell which repository", ssml)


class TestStandaloneRouterGuards(unittest.TestCase):
    """``app.alexa_skill`` router guards (unit level, no server needed)."""

    def test_rate_limit_raises_429_after_budget(self):
        alexa_skill._rate_limit_buckets.clear()
        with mock.patch.object(alexa_skill, "RATE_LIMIT_MAX_REQUESTS", 2):
            alexa_skill._check_rate_limit("192.0.2.10")
            alexa_skill._check_rate_limit("192.0.2.10")
            with self.assertRaises(HTTPException) as ctx:
                alexa_skill._check_rate_limit("192.0.2.10")
        self.assertEqual(ctx.exception.status_code, 429)
        alexa_skill._rate_limit_buckets.clear()

    def test_rate_limit_budget_is_per_client(self):
        alexa_skill._rate_limit_buckets.clear()
        with mock.patch.object(alexa_skill, "RATE_LIMIT_MAX_REQUESTS", 1):
            alexa_skill._check_rate_limit("192.0.2.11")
            with self.assertRaises(HTTPException):
                alexa_skill._check_rate_limit("192.0.2.11")
            alexa_skill._check_rate_limit("192.0.2.12")
        alexa_skill._rate_limit_buckets.clear()

    def test_stale_timestamp_is_rejected(self):
        with mock.patch.object(alexa_skill, "ALEXA_SKILL_ID", None):
            with self.assertRaises(HTTPException) as ctx:
                alexa_skill._verify_alexa_request({"date": "2026-10-19T00:00:00Z"}, b"{}")
        self.assertEqual(ctx.exception.status_code, 403)


class TestVoiceActionInputRequirements(unittest.TestCase):
    def test_repository_audit_without_repository_does_not_call_backend(self):
        command = alexa_nlp.MAPPER.map("audit my repository")
        with mock.patch.object(mcp_server, "audit_repository") as audit:
            result = alexa_skill._call_greencode_tool(command)

        self.assertEqual(result["status"], "error")
        self.assertIn("repository", result["data"]["reason"])
        audit.assert_not_called()

    def test_dynamic_analysis_requires_measured_grid_intensity(self):
        command = alexa_nlp.MAPPER.map("run owner/repo dynamically")
        result = alexa_skill._call_greencode_tool(command)

        self.assertEqual(result["status"], "error")
        self.assertIn("grid intensity", result["data"]["reason"])

    def test_sla_without_real_metrics_is_not_evaluated(self):
        command = alexa_nlp.MAPPER.map("check my energy sla")
        with mock.patch("app.alexa_actions.evaluate_sla") as evaluate:
            result = alexa_skill._call_greencode_tool(command)

        self.assertEqual(result["status"], "error")
        evaluate.assert_not_called()

    def test_scope_inventory_does_not_use_sample_inputs(self):
        command = alexa_nlp.MAPPER.map("scope 1 2 3 inventory")
        with mock.patch("app.alexa_actions.scope_inventory") as inventory:
            result = alexa_skill._call_greencode_tool(command)

        self.assertEqual(result["status"], "error")
        self.assertIn("actual workload", result["data"]["reason"])
        inventory.assert_not_called()

    def test_deployment_voice_command_never_claims_success(self):
        command = alexa_nlp.MAPPER.map("deploy to production")
        result = alexa_skill._call_greencode_tool(command)

        self.assertEqual(result["status"], "error")
        self.assertIn("configured for Alexa", result["data"]["reason"])

    def test_fresh_request_with_wrong_skill_id_is_rejected(self):
        fresh = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        body = json.dumps({"request": {"skillId": "amzn1.ask.skill.wrong"}}).encode()
        with mock.patch.object(alexa_skill, "ALEXA_SKILL_ID", "amzn1.ask.skill.right"):
            with self.assertRaises(HTTPException) as ctx:
                alexa_skill._verify_alexa_request({"date": fresh}, body)
        self.assertEqual(ctx.exception.status_code, 403)

    def test_matching_skill_id_passes_verification(self):
        fresh = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        skill_id = "amzn1.ask.skill.fd2a8106-e7fb-4f05-83b9-74590f7df6b8"
        body = json.dumps({"request": {"skillId": skill_id}}).encode()
        with mock.patch.object(alexa_skill, "ALEXA_SKILL_ID", skill_id):
            alexa_skill._verify_alexa_request({"date": fresh}, body)  # must not raise

    def test_cloud_webhook_requires_signature_and_timestamp(self):
        with self.assertRaises(HTTPException) as ctx:
            alexa_skill._verify_alexa_request({}, b'{"request":{}}', require_signature=True)
        self.assertEqual(ctx.exception.status_code, 403)

        fresh = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        body = json.dumps({"request": {"timestamp": fresh}}).encode()
        with self.assertRaises(HTTPException) as ctx:
            alexa_skill._verify_alexa_request(
                {},
                body,
                require_signature=True,
            )
        self.assertEqual(ctx.exception.status_code, 400)

    def test_browser_session_jwt_is_not_forwarded_as_github_token(self):
        app = FastAPI()
        app.include_router(alexa_skill.router)
        client = TestClient(app)
        command = alexa_nlp.AlexaCommand(
            tool="help",
            payload={},
            summary="help",
            confidence=1.0,
            raw_utterance="help",
        )
        payload = {
            "version": "1.0",
            "session": {"application": {}, "attributes": {}},
            "request": {
                "type": "IntentRequest",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "intent": {
                    "name": "FreeformGreenCodeQueryIntent",
                    "slots": {"query": {"name": "query", "value": "help"}},
                },
            },
        }
        app_tokens = create_tokens(user_id=19, org_id=23, role="developer")
        with (
            mock.patch.object(alexa_skill, "MAPPER") as mapper,
            mock.patch.object(alexa_skill, "_call_greencode_tool", return_value={"status": "ok"}) as call_tool,
            mock.patch.object(alexa_skill, "ALEXA_SKILL_ID", None),
        ):
            mapper.map.return_value = command
            response = client.post(
                "/api/voice/alexa/ask",
                json=payload,
                headers={
                    "Authorization": f"Bearer {app_tokens['access_token']}",
                    "X-GitHub-Token": "github-session-token",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(call_tool.call_args.kwargs["org_id"], 23)
        self.assertEqual(call_tool.call_args.kwargs["user_id"], 19)
        self.assertEqual(call_tool.call_args.kwargs["github_token"], "github-session-token")
        client.close()

    def test_dashboard_pr_briefing_uses_scanned_repo_and_authenticated_github(self):
        app = FastAPI()
        app.include_router(alexa_skill.router)
        client = TestClient(app)
        payload = {
            "version": "1.0",
            "session": {
                "application": {},
                "attributes": {"active_repo": "owner/repo"},
            },
            "request": {
                "type": "IntentRequest",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "intent": {
                    "name": "FreeformGreenCodeQueryIntent",
                    "slots": {
                        "query": {
                            "name": "query",
                            "value": "audit pull request 42",
                        }
                    },
                },
            },
        }
        tokens = create_tokens(user_id=19, org_id=23, role="developer")
        audit_result = {
            "status": "ok",
            "data": {
                "diff_green_score": 84,
                "total_diff_violations": 1,
                "modified_files_count": 2,
                "hunks_analyzed": 3,
                "violations": [
                    {
                        "title": "Repeated database query",
                        "severity": "HIGH",
                        "file_path": "app.py",
                        "line_number": 42,
                        "deduction": 8,
                    }
                ],
            },
        }
        with mock.patch.object(alexa_skill, "ALEXA_SKILL_ID", None), mock.patch(
            "app.alexa_actions.audit_diff", return_value=audit_result
        ) as audit:
            response = client.post(
                "/api/voice/alexa/ask",
                json=payload,
                headers={
                    "Authorization": f"Bearer {tokens['access_token']}",
                    "X-GitHub-Token": "github-session-token",
                },
            )

        self.assertEqual(response.status_code, 200)
        audit.assert_called_once_with(
            diff_text="",
            repo="owner/repo",
            pr_number=42,
            github_token="github-session-token",
        )
        speech = response.json()["response"]["outputSpeech"]["ssml"]
        self.assertIn("highest-priority finding is high", speech)
        self.assertIn("Repeated database query", speech)
        self.assertIn("app.py at line 42", speech)
        client.close()

    def test_dashboard_pr_briefing_requires_signed_in_user(self):
        app = FastAPI()
        app.include_router(alexa_skill.router)
        client = TestClient(app)
        payload = {
            "version": "1.0",
            "session": {
                "application": {},
                "attributes": {"active_repo": "owner/repo"},
            },
            "request": {
                "type": "IntentRequest",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "intent": {
                    "name": "FreeformGreenCodeQueryIntent",
                    "slots": {
                        "query": {
                            "name": "query",
                            "value": "audit pull request 42",
                        }
                    },
                },
            },
        }
        with mock.patch.object(alexa_skill, "ALEXA_SKILL_ID", None), mock.patch.object(
            alexa_skill, "_call_greencode_tool"
        ) as call_tool:
            response = client.post(
                "/api/voice/alexa/ask",
                json=payload,
                headers={"X-GitHub-Token": "github-session-token"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "requires a signed-in GreenCode dashboard session",
            response.json()["response"]["outputSpeech"]["ssml"],
        )
        call_tool.assert_not_called()
        client.close()

    def test_dashboard_pr_briefing_requires_github_connection(self):
        app = FastAPI()
        app.include_router(alexa_skill.router)
        client = TestClient(app)
        payload = {
            "version": "1.0",
            "session": {
                "application": {},
                "attributes": {"active_repo": "owner/repo"},
            },
            "request": {
                "type": "IntentRequest",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "intent": {
                    "name": "FreeformGreenCodeQueryIntent",
                    "slots": {
                        "query": {
                            "name": "query",
                            "value": "audit pull request 42",
                        }
                    },
                },
            },
        }
        tokens = create_tokens(user_id=19, org_id=23, role="developer")
        with mock.patch.object(alexa_skill, "ALEXA_SKILL_ID", None), mock.patch.object(
            alexa_skill, "_call_greencode_tool"
        ) as call_tool:
            response = client.post(
                "/api/voice/alexa/ask",
                json=payload,
                headers={"Authorization": f"Bearer {tokens['access_token']}"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "needs your GitHub connection",
            response.json()["response"]["outputSpeech"]["ssml"],
        )
        call_tool.assert_not_called()
        client.close()

    def test_dashboard_pr_briefing_needs_scanned_repository_context(self):
        app = FastAPI()
        app.include_router(alexa_skill.router)
        client = TestClient(app)
        payload = {
            "version": "1.0",
            "session": {"application": {}, "attributes": {}},
            "request": {
                "type": "IntentRequest",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "intent": {
                    "name": "FreeformGreenCodeQueryIntent",
                    "slots": {
                        "query": {
                            "name": "query",
                            "value": "audit pull request 42",
                        }
                    },
                },
            },
        }
        tokens = create_tokens(user_id=19, org_id=23, role="developer")
        with mock.patch.object(alexa_skill, "ALEXA_SKILL_ID", None), mock.patch.object(
            alexa_skill, "_call_greencode_tool"
        ) as call_tool:
            response = client.post(
                "/api/voice/alexa/ask",
                json=payload,
                headers={
                    "Authorization": f"Bearer {tokens['access_token']}",
                    "X-GitHub-Token": "github-session-token",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "Run a repository scan in the dashboard first",
            response.json()["response"]["outputSpeech"]["ssml"],
        )
        call_tool.assert_not_called()
        client.close()


class TestInteractionModelAlignment(unittest.TestCase):
    """deploy.ps1 ships the canonical Alexa interaction model; keep it complete."""

    MODEL = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "alexa", "interactionModels", "custom", "en-US.json",
    )
    EXPECTED_INTENTS = {
        "CompareRegionsIntent", "GetGridIntensityIntent", "AuditCodeIntent",
        "AuditRepositoryIntent", "CalculateSciIntent", "MeasureEnergyIntent",
        "ExplainScoreIntent", "RefactorCodeIntent", "CheckSlaComplianceIntent",
        "AuditIaCIntent", "FreeformGreenCodeQueryIntent", "GetCurrentRepositoryIntent",
        "AboutGreenCodeIntent",
    }

    def test_all_custom_intents_present(self):
        with open(self.MODEL, encoding="utf-8") as fh:
            model = json.load(fh)
        names = {i["name"] for i in model["interactionModel"]["languageModel"]["intents"]}
        self.assertTrue(self.EXPECTED_INTENTS.issubset(names),
                        f"missing: {self.EXPECTED_INTENTS - names}")

    def test_search_query_slot_is_wired_to_freeform_intent(self):
        # AMAZON.SearchQuery is a built-in slot type: it is referenced on the
        # intent's slot, not declared in languageModel.types (which only
        # carries the custom AWS_REGION / CODE_LANGUAGE vocabularies).
        with open(self.MODEL, encoding="utf-8") as fh:
            model = json.load(fh)
        intents = {i["name"]: i for i in model["interactionModel"]["languageModel"]["intents"]}
        slots = intents["FreeformGreenCodeQueryIntent"].get("slots", [])
        self.assertTrue(
            any(s.get("type") == "AMAZON.SearchQuery" for s in slots),
            "FreeformGreenCodeQueryIntent must expose an AMAZON.SearchQuery slot",
        )


if __name__ == "__main__":
    unittest.main()
