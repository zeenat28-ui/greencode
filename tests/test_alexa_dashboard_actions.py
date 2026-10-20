"""Tests for the five dashboard-backed Alexa voice actions.

These close the gap between the voice surface and the GreenCode dashboard:

- ``audit_diff``       - audit only the lines a pull request touches
- ``evaluate_sla``     - energy SLA verdict
- ``scope_inventory``  - Scope 1/2/3 GHG inventory
- ``audit_history``    - recent audits and cumulative carbon savings
- ``dynamic_analyze``  - sandboxed, measured repository run

Three layers are covered, matching the three modules involved:

1. ``app.alexa_nlp``      - the utterance to tool routing, including the
   priority rule that keeps a specific command from being swallowed by a
   generic one ("audit pull request 42" must not become "audit repository").
2. ``app.alexa_actions``  - the backend calls, with the real engines.
3. ``app.alexa_responses`` - the SSML the speaker hears.

Nothing opens a socket: the webhook test drives
``mcp_server.handle_alexa_skill_request`` in-process, the same code path a
real Alexa turn executes.
"""

import unittest
from unittest import mock

from app import alexa_actions, alexa_nlp, alexa_responses, mcp_server


SAMPLE_DIFF = """diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -1,3 +1,6 @@
 def f(x):
+    for i in range(x):
+        for j in range(x):
+            print(i * j)
     return 0
"""


def _ask(query: str) -> str:
    """Send a free-form query through the live ASK handler and return speech."""
    payload = {
        "version": "1.0",
        "request": {
            "type": "IntentRequest",
            "intent": {
                "name": "FreeformGreenCodeQueryIntent",
                "slots": {"query": {"name": "query", "value": query}},
            },
        },
    }
    resp = mcp_server.handle_alexa_skill_request(payload)
    return resp["response"]["outputSpeech"]["text"]


class TestDashboardActionRouting(unittest.TestCase):
    """The NLU must reach each dashboard action, and reach it first."""

    def test_pull_request_audit_beats_generic_repository_audit(self):
        cmd = alexa_nlp.MAPPER.map("audit pull request 42 in owner/repo")
        self.assertEqual(cmd.tool, "audit_diff")
        self.assertEqual(cmd.payload["pr_number"], 42)
        self.assertEqual(cmd.payload["repo"], "owner/repo")

    def test_diff_audit_without_a_number_still_routes(self):
        cmd = alexa_nlp.MAPPER.map("audit the diff for owner/repo")
        self.assertEqual(cmd.tool, "audit_diff")
        self.assertIsNone(cmd.payload["pr_number"])

    def test_sla_check_routes_and_reads_the_numbers(self):
        cmd = alexa_nlp.MAPPER.map(
            "check my energy sla for 1200 joules and score 80"
        )
        self.assertEqual(cmd.tool, "evaluate_sla")
        self.assertEqual(cmd.payload["total_joules"], 1200.0)
        self.assertEqual(cmd.payload["green_score"], 80.0)

    def test_sla_check_with_the_words_the_other_way_round(self):
        cmd = alexa_nlp.MAPPER.map("does this deployment meet the sla")
        self.assertEqual(cmd.tool, "evaluate_sla")

    def test_scope_inventory_routes_and_resolves_the_zone(self):
        cmd = alexa_nlp.MAPPER.map("scope 1 2 3 inventory for ireland")
        self.assertEqual(cmd.tool, "scope_inventory")
        self.assertEqual(cmd.payload["grid_zone"], "IE")

    def test_audit_history_routes(self):
        for phrase in ("show my audit history", "my recent audits"):
            cmd = alexa_nlp.MAPPER.map(phrase)
            self.assertEqual(cmd.tool, "audit_history", phrase)

    def test_dynamic_analysis_routes_and_reads_the_repo(self):
        cmd = alexa_nlp.MAPPER.map("run owner/repo dynamically")
        self.assertEqual(cmd.tool, "dynamic_analyze")
        self.assertEqual(cmd.payload["repo"], "owner/repo")

    def test_generic_repository_audit_still_works(self):
        cmd = alexa_nlp.MAPPER.map("audit my repository")
        self.assertEqual(cmd.tool, "audit_repository")

    def test_unknown_utterance_still_falls_back(self):
        cmd = alexa_nlp.MAPPER.map("flurble glurble wompus")
        self.assertTrue(cmd.fallback)
        self.assertEqual(cmd.tool, "help")



class TestDashboardActionBackends(unittest.TestCase):
    """Each action calls the real engine and returns the shared envelope."""

    def test_audit_diff_reports_only_changed_lines(self):
        result = alexa_actions.audit_diff(diff_text=SAMPLE_DIFF)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["modified_files_count"], 1)
        self.assertGreaterEqual(result["data"]["hunks_analyzed"], 1)
        self.assertGreaterEqual(result["data"]["total_diff_violations"], 1)
        self.assertLess(result["data"]["diff_green_score"], 100.0)

    def test_audit_diff_without_a_target_is_an_error_not_a_crash(self):
        result = alexa_actions.audit_diff()
        self.assertEqual(result["status"], "error")
        self.assertIn("reason", result["data"])

    def test_audit_diff_fetches_the_pr_when_no_diff_is_supplied(self):
        fetched = {
            "success": True,
            "repo": "owner/repo",
            "diff_text": SAMPLE_DIFF,
        }
        with mock.patch(
            "app.github_client.get_pull_request_diff", return_value=fetched
        ) as fetch:
            result = alexa_actions.audit_diff(repo="owner/repo", pr_number=7)
        fetch.assert_called_once()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["pr_number"], 7)

    def test_evaluate_sla_passes_a_compliant_deployment(self):
        result = alexa_actions.evaluate_sla(total_joules=1200, green_score=80)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["status"], "COMPLIANT")
        self.assertFalse(result["data"]["violations"])

    def test_evaluate_sla_breach_is_reported(self):
        result = alexa_actions.evaluate_sla(total_joules=999999, green_score=10)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["status"], "BREACHED")
        self.assertTrue(result["data"]["violations"])

    def test_scope_inventory_returns_all_three_scopes(self):
        result = alexa_actions.scope_inventory(grid_zone="IE")
        self.assertEqual(result["status"], "ok")
        for scope in ("scope_1", "scope_2", "scope_3"):
            self.assertIn(scope, result["data"])
        self.assertIn("scope_1_pct", result["data"]["scope_breakdown_pct"])
        self.assertGreater(result["data"]["total_carbon_kgco2e_annual"], 0)

    def test_audit_history_is_scoped_to_the_caller(self):
        with mock.patch(
            "app.database.get_latest_repositories",
            return_value={"items": [{"name": "a/b"}], "total": 1, "limit": 5, "offset": 0},
        ) as latest, mock.patch(
            "app.database.get_cumulative_carbon_savings",
            return_value={"total_carbon_saved_gco2_10k_runs": 12.5},
        ):
            result = alexa_actions.audit_history(user_id=42)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["repositories"], [{"name": "a/b"}])
        latest.assert_called_once()
        self.assertEqual(latest.call_args.kwargs["user_id"], 42)

    def test_dynamic_analysis_without_a_repo_is_an_error(self):
        result = alexa_actions.dynamic_analyze()
        self.assertEqual(result["status"], "error")

    def test_dynamic_analysis_refuses_on_serverless(self):
        with mock.patch.dict("os.environ", {"VERCEL": "1"}):
            result = alexa_actions.dynamic_analyze(repo="owner/repo")
        self.assertEqual(result["status"], "error")
        self.assertIn("Docker", result["data"]["reason"])



class TestDashboardActionSpeech(unittest.TestCase):
    """Each action must produce spoken words, not raw JSON."""

    def test_diff_speech_reports_the_score_and_the_count(self):
        result = alexa_actions.audit_diff(diff_text=SAMPLE_DIFF)
        resp = alexa_responses.build_diff_response(result)
        ssml = resp["response"]["outputSpeech"]["ssml"]
        self.assertIn("Diff audit complete", ssml)
        self.assertIn("Diff green score", ssml)

    def test_sla_speech_states_the_verdict(self):
        result = alexa_actions.evaluate_sla(total_joules=1200, green_score=80)
        ssml = alexa_responses.build_sla_response(result)["response"]["outputSpeech"]["ssml"]
        self.assertIn("passes the energy SLA", ssml)

        breached = alexa_actions.evaluate_sla(total_joules=999999, green_score=10)
        ssml = alexa_responses.build_sla_response(breached)["response"]["outputSpeech"]["ssml"]
        self.assertIn("breaches the energy SLA", ssml)

    def test_scope_speech_names_every_scope(self):
        result = alexa_actions.scope_inventory(grid_zone="IE")
        ssml = alexa_responses.build_scope_response(result)["response"]["outputSpeech"]["ssml"]
        self.assertIn("Scope 1", ssml)
        self.assertIn("Scope 2", ssml)
        self.assertIn("Scope 3", ssml)

    def test_history_speech_mentions_the_savings(self):
        result = {
            "status": "ok",
            "data": {
                "repositories": [{"name": "owner/repo"}],
                "total": 1,
                "cumulative_savings": {
                    "total_carbon_saved_gco2_10k_runs": 12.5,
                    "average_energy_reduction_pct": 8.0,
                },
            },
        }
        ssml = alexa_responses.build_history_response(result)["response"]["outputSpeech"]["ssml"]
        self.assertIn("owner/repo", ssml)
        self.assertIn("saved", ssml)

    def test_dynamic_speech_explains_a_sandbox_failure(self):
        result = {"status": "ok", "data": {"ok": False, "reason": "sandbox_unavailable"}}
        resp = alexa_responses.build_dynamic_response(result)
        self.assertIn("sandbox_unavailable", resp["response"]["outputSpeech"]["ssml"])
        self.assertFalse(resp["response"]["shouldEndSession"])

    def test_action_speech_is_plain_text_without_markup(self):
        result = alexa_actions.audit_diff(diff_text=SAMPLE_DIFF)
        speech = alexa_responses.action_speech("audit_diff", result)
        self.assertNotIn("<", speech)
        self.assertNotIn("say-as", speech)
        self.assertIn("Diff audit complete", speech)

    def test_every_action_has_a_builder(self):
        from app.alexa_skill import NLU_ACTION_TOOLS

        for tool in NLU_ACTION_TOOLS:
            self.assertIn(tool, alexa_responses.ACTION_BUILDERS, tool)


class TestDashboardActionWebhook(unittest.TestCase):
    """The live ASK webhook must reach the dashboard actions."""

    def test_scope_inventory_is_spoken_by_the_webhook(self):
        speech = _ask("scope one two three inventory")
        self.assertIn("Scope 1, 2 and 3 inventory ready", speech)

    def test_sla_check_is_spoken_by_the_webhook(self):
        speech = _ask("check my energy sla")
        self.assertIn("energy SLA", speech)

    def test_region_query_still_uses_the_region_heuristics(self):
        # The new actions must not swallow the free-form region questions.
        speech = _ask("compare ireland and virginia")
        self.assertIn("cleanest", speech.lower())


if __name__ == "__main__":
    unittest.main()
