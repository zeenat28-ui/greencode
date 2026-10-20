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

from fastapi import HTTPException
from starlette.testclient import TestClient

from app import alexa_nlp, alexa_skill, alexa_responses, mcp_server

LAUNCH = {"version": "1.0", "request": {"type": "LaunchRequest"}}


class _WebhookTestBase(unittest.TestCase):
    """Shared setup: isolated rate-limit buckets and pinned environment."""

    def setUp(self):
        mcp_server._alexa_rate_buckets.clear()
        self._env = mock.patch.dict(
            os.environ,
            {"GREENCODE_ALEXA_SKILL_ID": "", "GREENCODE_ALEXA_RATE_LIMIT": "100"},
        )
        self._env.start()
        self.client = TestClient(mcp_server.create_app())

    def tearDown(self):
        self.client.close()
        self._env.stop()
        mcp_server._alexa_rate_buckets.clear()


class TestAskWebhookHardening(_WebhookTestBase):
    """The live endpoint must survive hostile and abusive traffic."""

    def test_launch_request_returns_valid_ask_envelope(self):
        resp = self.client.post("/alexa/skill", json=LAUNCH)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["version"], "1.0")
        speech = body["response"]["outputSpeech"]
        self.assertIn(speech["type"], ("SSML", "PlainText"))
        self.assertIn("GreenCode", json.dumps(speech))
        self.assertFalse(body["response"]["shouldEndSession"])

    def test_invalid_json_returns_400(self):
        resp = self.client.post(
            "/alexa/skill", content=b"{not json", headers={"Content-Type": "application/json"}
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error"], "invalid_json")

    def test_rate_limit_returns_429_with_retry_after(self):
        with mock.patch.dict(os.environ, {"GREENCODE_ALEXA_RATE_LIMIT": "3"}):
            for _ in range(3):
                self.assertEqual(self.client.post("/alexa/skill", json=LAUNCH).status_code, 200)
            resp = self.client.post("/alexa/skill", json=LAUNCH)
        self.assertEqual(resp.status_code, 429)
        self.assertEqual(resp.json()["error"], "rate_limited")
        self.assertIn("Retry-After", resp.headers)

    def test_rate_limit_is_keyed_by_forwarded_client(self):
        with mock.patch.dict(os.environ, {"GREENCODE_ALEXA_RATE_LIMIT": "1"}):
            first = self.client.post(
                "/api/alexa/skill", json=LAUNCH, headers={"X-Forwarded-For": "203.0.113.9"}
            )
            second = self.client.post(
                "/api/alexa/skill", json=LAUNCH, headers={"X-Forwarded-For": "203.0.113.9"}
            )
            other = self.client.post(
                "/api/alexa/skill", json=LAUNCH, headers={"X-Forwarded-For": "198.51.100.4"}
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
            forged = self.client.post("/alexa/skill", json=payload)
            payload["session"]["application"]["applicationId"] = good
            genuine = self.client.post("/alexa/skill", json=payload)
        self.assertEqual(forged.status_code, 403)
        self.assertEqual(forged.json()["error"], "forbidden_skill_id")
        self.assertEqual(genuine.status_code, 200)


class TestNlpMapper(unittest.TestCase):
    """Free-form utterances must resolve to the right GreenCode tool."""

    def test_repository_audit_utterance(self):
        cmd = alexa_nlp.MAPPER.map("audit my repository for energy waste")
        self.assertEqual(cmd.tool, "audit_repository")
        self.assertFalse(cmd.fallback)
        self.assertGreaterEqual(cmd.confidence, 0.65)

    def test_green_score_utterance_maps_to_end_to_end_audit(self):
        cmd = alexa_nlp.MAPPER.map("what is my green score")
        self.assertEqual(cmd.tool, "audit_and_score")

    def test_region_comparison_utterance(self):
        cmd = alexa_nlp.MAPPER.map("compare ireland and virginia for my batch job")
        self.assertEqual(cmd.tool, "compare_regions")
        self.assertIn("zones", cmd.payload)

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

    def test_help_response_lists_capabilities_and_reprompts(self):
        resp = alexa_responses.build_help_response()
        ssml = resp["response"]["outputSpeech"]["ssml"]
        for phrase in ("audit my repository", "green score", "compare", "refactor"):
            self.assertIn(phrase, ssml)
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


class TestInteractionModelAlignment(unittest.TestCase):
    """deploy.ps1 ships alexa/interaction_model_en_US.json; keep it complete."""

    MODEL = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "alexa", "interaction_model_en_US.json",
    )
    EXPECTED_INTENTS = {
        "CompareRegionsIntent", "GetGridIntensityIntent", "AuditCodeIntent",
        "AuditRepositoryIntent", "CalculateSciIntent", "MeasureEnergyIntent",
        "ExplainScoreIntent", "RefactorCodeIntent", "CheckSlaComplianceIntent",
        "AuditIaCIntent", "FreeformGreenCodeQueryIntent",
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
