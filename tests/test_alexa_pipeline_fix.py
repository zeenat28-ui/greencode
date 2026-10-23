"""Regression tests for the six Alexa pipeline fault fixes.

F1 - alexa_skill.router mounted in main.py
F2 - timestamp replay protection in alexa_request_guard
F3 - ASK cert chain verification helpers present
F4 - dispatch_nlu_action re-exported from alexa_dispatch (no circular import)
F5 - SSML outputSpeech + default reprompt in _build_ask_response
F6 - ASK and Alexa+ manifests point to their respective endpoints
"""
from __future__ import annotations
import json, os, sys, time, unittest, pathlib
from unittest import mock


def _fresh_ts():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _stale_ts(delta=200):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - delta))

LAUNCH = {"version": "1.0", "request": {"type": "LaunchRequest"}}


# ---------------------------------------------------------------------------
# F5 - SSML response builder
# ---------------------------------------------------------------------------
class TestF5SSML(unittest.TestCase):
    def _r(self, **kw):
        from app.mcp_server import _build_ask_response
        return _build_ask_response("Hello GreenCode.", **kw)

    def test_output_speech_type_is_ssml(self):
        self.assertEqual(self._r()["response"]["outputSpeech"]["type"], "SSML")

    def test_speech_wrapped_in_speak(self):
        ssml = self._r()["response"]["outputSpeech"]["ssml"]
        self.assertTrue(ssml.startswith("<speak>"), ssml[:60])

    def test_default_reprompt_for_non_terminal(self):
        resp = self._r(should_end_session=False)
        self.assertIn("reprompt", resp["response"])
        self.assertEqual(resp["response"]["reprompt"]["outputSpeech"]["type"], "SSML")

    def test_no_reprompt_for_terminal(self):
        self.assertNotIn("reprompt", self._r(should_end_session=True)["response"])

    def test_version_1_0(self):
        self.assertEqual(self._r()["version"], "1.0")


# ---------------------------------------------------------------------------
# F6 - ASK and Alexa+ endpoint URIs
# ---------------------------------------------------------------------------
class TestF6AddonJson(unittest.TestCase):
    def _manifest(self, name):
        p = pathlib.Path(__file__).parent.parent / "alexa" / name
        return json.loads(p.read_text(encoding="utf-8"))

    def test_ask_custom_skill_uses_ask_webhook(self):
        uri = self._manifest("skill.json")["manifest"]["apis"]["custom"]["endpoint"]["uri"]
        self.assertTrue(uri.endswith("/api/alexa/skill"), uri)

    def test_alexa_plus_addon_uses_mcp_transport(self):
        integration = self._manifest("addon.json")["integrations"][0]
        uri = integration["config"]["endpoints"]["default"]["uri"]
        self.assertEqual(integration["type"], "MCP")
        self.assertTrue(uri.endswith("/mcp"), uri)


# ---------------------------------------------------------------------------
# F4 - no circular import
# ---------------------------------------------------------------------------
class TestF4NoCircularImport(unittest.TestCase):
    def test_alexa_dispatch_importable(self):
        import importlib
        mod = importlib.import_module("app.alexa_dispatch")
        self.assertTrue(callable(getattr(mod, "dispatch_nlu_action", None)))

    def test_mcp_server_uses_alexa_dispatch(self):
        import inspect, app.mcp_server as ms
        src = inspect.getsource(ms._dispatch_nlu_action)
        self.assertIn("alexa_dispatch", src)

    def test_alexa_skill_reexports_from_alexa_dispatch(self):
        import pathlib
        code = (pathlib.Path(__file__).parent.parent / "app" / "alexa_skill.py").read_text(encoding="utf-8")
        self.assertIn("from app.alexa_dispatch import dispatch_nlu_action", code)


# ---------------------------------------------------------------------------
# F2 - timestamp replay protection
# ---------------------------------------------------------------------------
class TestF2Timestamp(unittest.TestCase):
    def _guard(self, payload, headers=None):
        from app.mcp_server import alexa_request_guard
        from starlette.requests import Request
        payload = json.loads(json.dumps(payload))
        payload.setdefault("session", {}).setdefault("application", {}).setdefault(
            "applicationId", "amzn1.ask.skill.TEST"
        )
        h = list((headers or {}).items())
        h.extend([
            ("SignatureCertChainUrl", "https://s3.amazonaws.com/echo.api/test.pem"),
            ("Signature-256", "dGVzdA=="),
        ])
        scope = {
            "type": "http", "method": "POST", "path": "/api/alexa/skill",
            "query_string": b"",
            "headers": [(k.lower().encode(), v.encode()) for k, v in h],
        }
        with mock.patch.dict(os.environ, {"GREENCODE_ALEXA_SKILL_ID": "amzn1.ask.skill.TEST", "GREENCODE_ALEXA_RATE_LIMIT": "1000"}):
            with mock.patch("app.mcp_server._verify_ask_cert_chain", return_value=None):
                return alexa_request_guard(Request(scope), payload, b"{}")

    def test_stale_timestamp_rejected_403(self):
        result = self._guard({"version": "1.0", "request": {"type": "LaunchRequest", "timestamp": _stale_ts(200)}})
        self.assertIsNotNone(result)
        self.assertEqual(result.status_code, 403)

    def test_fresh_timestamp_accepted(self):
        result = self._guard({"version": "1.0", "request": {"type": "LaunchRequest", "timestamp": _fresh_ts()}})
        self.assertIsNone(result)

    def test_missing_timestamp_rejected(self):
        result = self._guard({"version": "1.0", "request": {"type": "LaunchRequest"}})
        self.assertIsNotNone(result)
        self.assertEqual(result.status_code, 403)


# ---------------------------------------------------------------------------
# F3 - cert chain helpers present
# ---------------------------------------------------------------------------
class TestF3CertChainPresent(unittest.TestCase):
    def test_verify_function_exists(self):
        from app.mcp_server import _verify_ask_cert_chain
        self.assertTrue(callable(_verify_ask_cert_chain))

    def test_missing_headers_rejected(self):
        from app.mcp_server import _verify_ask_cert_chain
        from starlette.requests import Request
        scope = {"type": "http", "method": "POST", "path": "/", "query_string": b"", "headers": []}
        result = _verify_ask_cert_chain(Request(scope), b"body")
        self.assertIsNotNone(result)
        self.assertEqual(result.status_code, 400)

    def test_invalid_cert_domain_rejected(self):
        from app.mcp_server import _verify_ask_cert_chain
        from starlette.requests import Request
        headers = [
            (b"signaturecertchainurl", b"https://evil.com/echo.api/cert.pem"),
            (b"signature-256", b"dGVzdA=="),
        ]
        scope = {"type": "http", "method": "POST", "path": "/", "query_string": b"", "headers": headers}
        result = _verify_ask_cert_chain(Request(scope), b"body")
        self.assertIsNotNone(result)
        self.assertEqual(result.status_code, 400)


# ---------------------------------------------------------------------------
# F1 - router mounted
# ---------------------------------------------------------------------------
class TestF1RouterMounted(unittest.TestCase):
    def test_main_py_imports_alexa_skill_module(self):
        code = (pathlib.Path(__file__).parent.parent / "app" / "main.py").read_text(encoding="utf-8")
        self.assertIn("_alexa_skill_module", code)
        self.assertIn("include_router(_alexa_skill_module.router)", code)

    def test_alexa_skill_router_has_skill_route(self):
        from app.alexa_skill import router
        paths = [r.path for r in router.routes]
        self.assertIn("/skill", paths, f"router routes: {paths}")


# ---------------------------------------------------------------------------
# Preservation
# ---------------------------------------------------------------------------
class TestPreservation(unittest.TestCase):
    def _guard(self, payload, extra_env=None, headers=None):
        from app.mcp_server import alexa_request_guard, _alexa_rate_buckets
        from starlette.requests import Request
        _alexa_rate_buckets.clear()
        payload = json.loads(json.dumps(payload))
        payload.setdefault("session", {}).setdefault("application", {}).setdefault(
            "applicationId", "amzn1.ask.skill.TEST"
        )
        h = list((headers or {}).items())
        h.extend([
            ("SignatureCertChainUrl", "https://s3.amazonaws.com/echo.api/test.pem"),
            ("Signature-256", "dGVzdA=="),
        ])
        scope = {
            "type": "http", "method": "POST", "path": "/api/alexa/skill",
            "query_string": b"",
            "headers": [(k.lower().encode(), v.encode()) for k, v in h],
        }
        env = {"GREENCODE_ALEXA_SKILL_ID": "amzn1.ask.skill.TEST", "GREENCODE_ALEXA_RATE_LIMIT": "1000"}
        env.update(extra_env or {})
        with mock.patch.dict(os.environ, env):
            with mock.patch("app.mcp_server._verify_ask_cert_chain", return_value=None):
                return alexa_request_guard(Request(scope), payload, b"{}")

    def test_rate_limit_fires_429(self):
        from app.mcp_server import alexa_request_guard, _alexa_rate_buckets
        from starlette.requests import Request
        _alexa_rate_buckets.clear()
        payload = {"version": "1.0", "request": {"type": "LaunchRequest", "timestamp": _fresh_ts()}}
        scope = {"type": "http", "method": "POST", "path": "/", "query_string": b"",
                 "headers": [
                     (b"x-forwarded-for", b"10.0.0.99"),
                     (b"signaturecertchainurl", b"https://s3.amazonaws.com/echo.api/test.pem"),
                     (b"signature-256", b"dGVzdA=="),
                 ]}
        payload["session"] = {"application": {"applicationId": "amzn1.ask.skill.TEST"}}
        with mock.patch.dict(os.environ, {"GREENCODE_ALEXA_SKILL_ID": "amzn1.ask.skill.TEST", "GREENCODE_ALEXA_RATE_LIMIT": "2"}):
            with mock.patch("app.mcp_server._verify_ask_cert_chain", return_value=None):
                alexa_request_guard(Request(scope), payload, b"{}")
                alexa_request_guard(Request(scope), payload, b"{}")
                result = alexa_request_guard(Request(scope), payload, b"{}")
        self.assertIsNotNone(result)
        self.assertEqual(result.status_code, 429)
        _alexa_rate_buckets.clear()

    def test_skill_id_mismatch_fires_403(self):
        from app.mcp_server import alexa_request_guard, _alexa_rate_buckets
        from starlette.requests import Request
        _alexa_rate_buckets.clear()
        payload = {
            "version": "1.0",
            "request": {"type": "LaunchRequest", "timestamp": _fresh_ts()},
            "session": {"application": {"applicationId": "amzn1.ask.skill.WRONG"}},
        }
        scope = {"type": "http", "method": "POST", "path": "/", "query_string": b"",
                 "headers": [
                     (b"x-forwarded-for", b"10.0.0.88"),
                     (b"signaturecertchainurl", b"https://s3.amazonaws.com/echo.api/test.pem"),
                     (b"signature-256", b"dGVzdA=="),
                 ]}
        with mock.patch.dict(os.environ, {"GREENCODE_ALEXA_SKILL_ID": "amzn1.ask.skill.CORRECT", "GREENCODE_ALEXA_RATE_LIMIT": "1000"}):
            with mock.patch("app.mcp_server._verify_ask_cert_chain", return_value=None):
                result = alexa_request_guard(Request(scope), payload, b"{}")
        self.assertIsNotNone(result)
        self.assertEqual(result.status_code, 403)
        _alexa_rate_buckets.clear()

    def test_launch_request_returns_valid_envelope(self):
        from app.mcp_server import handle_alexa_skill_request
        resp = handle_alexa_skill_request(LAUNCH)
        self.assertEqual(resp["version"], "1.0")
        self.assertEqual(resp["response"]["outputSpeech"]["type"], "SSML")
        self.assertGreater(len(resp["response"]["outputSpeech"]["ssml"]), 20)

    def test_session_attributes_echoed(self):
        from app.mcp_server import handle_alexa_skill_request
        payload = {
            "version": "1.0",
            "request": {"type": "LaunchRequest"},
            "session": {"attributes": {"last_zone": "IE", "user_id": 7}},
        }
        resp = handle_alexa_skill_request(payload)
        self.assertEqual(resp["sessionAttributes"]["last_zone"], "IE")

    def test_addon_json_mcp_config_intact(self):
        p = pathlib.Path(__file__).parent.parent / "alexa" / "addon.json"
        addon = json.loads(p.read_text(encoding="utf-8"))
        self.assertEqual(addon["integrations"][0]["type"], "MCP")
        self.assertIn("endpoints", addon["integrations"][0]["config"])


if __name__ == "__main__":
    unittest.main()
