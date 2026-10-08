"""Tests for the Amazon Bedrock backend and the MCP server surface.

Nothing here calls AWS or starts a transport. The Bedrock runtime is replaced
with a fake so that what is under test is the client's own behaviour - model
fallback, error classification, and failing closed without credentials - none
of which is reproducible against the live service. The MCP tests drive the
registered tool functions directly, which is the same code the transport
invokes, so a broken contract still fails here rather than in a demo.
"""

import os
import unittest
from unittest import mock

from app.bedrock_client import (
    DEFAULT_MODELS,
    BedrockClient,
    BedrockError,
    _provider_of,
)
from app.huggingface_client import LLMError

CLAUDE = DEFAULT_MODELS[0]

CREDENTIAL_KEYS = (
    "AWS_ACCESS_KEY_ID",
    "AWS_PROFILE",
    "AWS_WEB_IDENTITY_TOKEN_FILE",
    "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI",
    "BEDROCK_MODEL_ID",
)


class FakeRuntime:
    """Stand-in for boto3's bedrock-runtime client."""

    def __init__(self, fail_times: int = 0, content: str = "def f():\n    return 1"):
        self.calls = []
        self.fail_times = fail_times
        self.content = content

    def converse(self, **kwargs):
        self.calls.append(kwargs)
        if len(self.calls) <= self.fail_times:
            raise RuntimeError("service unavailable")
        return {
            "output": {"message": {"content": [{"text": self.content}]}},
            "usage": {"inputTokens": 11, "outputTokens": 7},
        }


class Boom(Exception):
    """An exception shaped like a botocore ClientError."""

    def __init__(self, code):
        super().__init__(code)
        self.response = {"Error": {"Code": code}}


class ClearCredentials:
    """Context manager that strips every AWS credential source."""

    def __enter__(self):
        self.saved = {k: os.environ.pop(k, None) for k in CREDENTIAL_KEYS}
        return self

    def __exit__(self, *exc):
        for key in CREDENTIAL_KEYS:
            os.environ.pop(key, None)
        os.environ.update({k: v for k, v in self.saved.items() if v is not None})
        return False


class TestBedrockContract(unittest.TestCase):
    """The client must be a drop-in for the HuggingFace client."""

    def test_error_is_catchable_as_llm_error(self):
        # app.llm_refactor catches LLMError, so anything raised here must
        # reach its handler rather than becoming an unhandled 500.
        self.assertTrue(issubclass(BedrockError, LLMError))

    def test_exposes_the_same_public_surface(self):
        for name in ("chat", "health", "list_models", "configured"):
            self.assertTrue(hasattr(BedrockClient, name), name)


class TestBedrockChat(unittest.TestCase):

    def _client(self, fail_times=0, **kwargs):
        client = BedrockClient(region_name="us-east-1", model=CLAUDE, **kwargs)
        runtime = FakeRuntime(fail_times)
        client._client = runtime
        return client, runtime

    def test_returns_content_usage_and_model(self):
        client, runtime = self._client()
        content, usage, model = client.chat(
            [{"role": "system", "content": "refactor"},
             {"role": "human", "content": "fix this"}],
            max_tokens=64,
        )
        self.assertIn("return 1", content)
        self.assertEqual(usage.total_tokens, 18)
        self.assertEqual(model, CLAUDE)

        request = runtime.calls[0]
        self.assertEqual(request["modelId"], CLAUDE)
        # Bedrock takes the system prompt out of band, not as a message.
        self.assertEqual(request["system"][0]["text"], "refactor")
        # Anthropic names the human turn "user".
        self.assertEqual(request["messages"][0]["role"], "user")
        self.assertEqual(request["inferenceConfig"]["maxTokens"], 64)

    def test_falls_through_to_the_next_model_when_one_is_unavailable(self):
        client, runtime = self._client(fail_times=1)
        _, _, model = client.chat([{"role": "human", "content": "x"}])
        self.assertEqual(len(runtime.calls), 2)
        self.assertNotEqual(model, CLAUDE)

    def test_raises_the_last_classified_error_when_all_models_fail(self):
        client, _ = self._client(fail_times=99)
        with self.assertRaises(BedrockError) as ctx:
            client.chat([{"role": "human", "content": "x"}])
        self.assertEqual(ctx.exception.kind, "network")

    def test_system_only_request_still_sends_one_turn(self):
        # Converse rejects an empty message list outright.
        client, runtime = self._client()
        client.chat([{"role": "system", "content": "only system"}])
        messages = runtime.calls[0]["messages"]
        self.assertEqual(len(messages), 1)
        self.assertTrue(messages[0]["content"][0]["text"])

    def test_stop_sequences_reach_the_inference_config(self):
        client, runtime = self._client()
        client.chat([{"role": "human", "content": "x"}], stop=["```"])
        self.assertEqual(runtime.calls[0]["inferenceConfig"]["stopSequences"], ["```"])
class TestBedrockCredentials(unittest.TestCase):

    def test_fails_closed_without_credentials(self):
        with ClearCredentials():
            client = BedrockClient()
            runtime = FakeRuntime()
            client._client = runtime
            self.assertFalse(client.configured)

            with self.assertRaises(BedrockError) as ctx:
                client.chat([{"role": "human", "content": "x"}])
            self.assertEqual(ctx.exception.kind, "auth")
            # The point of failing closed: no request is attempted at all.
            self.assertEqual(runtime.calls, [])

    def test_health_explains_why_it_is_unavailable(self):
        with ClearCredentials():
            report = BedrockClient().health()
            self.assertFalse(report["reachable"])
            self.assertIn("No AWS credentials", report["detail"])

    def test_configured_accepts_an_instance_role(self):
        # No key material, but an instance profile is a complete credential source.
        with ClearCredentials():
            os.environ["AWS_CONTAINER_CREDENTIALS_RELATIVE_URI"] = "/v4/task"
            self.assertTrue(BedrockClient().configured)


class TestBedrockClassification(unittest.TestCase):

    def test_maps_error_codes_to_actionable_kinds(self):
        expected = {
            "AccessDeniedException": "auth",
            "ThrottlingException": "rate_limit",
            "ValidationException": "bad_request",
            "ModelNotReadyException": "unavailable",
        }
        for code, kind in expected.items():
            with self.subTest(code=code):
                self.assertEqual(BedrockClient._classify(Boom(code)).kind, kind)

    def test_unrecognised_failure_is_retryable(self):
        error = BedrockClient._classify(RuntimeError("socket closed"))
        self.assertEqual(error.kind, "network")
        self.assertTrue(error.retryable)


class TestBedrockRoles(unittest.TestCase):

    def test_reads_the_provider_from_a_model_id(self):
        self.assertEqual(_provider_of(CLAUDE), "anthropic")
        self.assertEqual(_provider_of("amazon.nova-pro-v1:0"), "amazon")

    def test_aws_native_models_keep_their_own_role_names(self):
        client = BedrockClient(model="amazon.nova-pro-v1:0")
        _, messages = client._to_converse([{"role": "human", "content": "hi"}])
        self.assertEqual(messages[0]["role"], "user")
class TestMcpSurface(unittest.TestCase):
    """The Alexa+ track surface: tools must exist, be typed, and fail honestly."""

    def setUp(self):
        import asyncio

        from app import mcp_server

        self.mcp_server = mcp_server
        # The latency caches are process-wide; tests that patch the underlying
        # providers must start from an empty cache or a previous test's reading
        # would satisfy the lookup and never reach the mock.
        mcp_server.clear_intensity_cache()
        self.tools = asyncio.run(mcp_server.mcp.list_tools())
        self.names = {tool.name for tool in self.tools}

    def test_protocol_version_meets_the_track_minimum(self):
        from mcp.types import LATEST_PROTOCOL_VERSION

        self.assertGreaterEqual(
            LATEST_PROTOCOL_VERSION, self.mcp_server.MIN_REQUIRED_MCP_VERSION
        )

    def test_exposes_the_expected_tools(self):
        for name in ("audit_code", "audit_repository", "audit_and_score",
                     "calculate_sci", "measure_energy", "get_grid_intensity",
                     "compare_regions", "refactor_code"):
            self.assertIn(name, self.names)

    def test_every_tool_has_a_description(self):
        # An agent routes on the description; an empty one makes the tool
        # effectively unreachable.
        for tool in self.tools:
            with self.subTest(tool=tool.name):
                self.assertTrue((tool.description or "").strip())

    def test_audit_code_finds_a_triple_nested_loop(self):
        result = self.mcp_server.audit_code(
            "def f(rows):\n"
            "    t = 0\n"
            "    for a in rows:\n"
            "        for b in rows:\n"
            "            for c in rows:\n"
            "                t += a * b * c\n"
            "    return t\n"
        )
        self.assertEqual(result["status"], "ok")
        self.assertGreater(result["data"]["violation_count"], 0)
        self.assertIn(result["data"]["grade"], "ABCDEF")

    def test_audit_code_rejects_empty_input(self):
        self.assertEqual(self.mcp_server.audit_code("")["status"], "error")

    def test_every_result_carries_the_envelope(self):
        for result in (self.mcp_server.audit_code("x = 1"),
                       self.mcp_server.measure_energy(),
                       self.mcp_server.compare_regions(["IE"])):
            for key in ("status", "server", "version", "mcp_protocol_version", "data"):
                self.assertIn(key, result)

    def test_measure_energy_never_hides_that_a_model_is_not_a_measurement(self):
        result = self.mcp_server.measure_energy()
        data = result["data"]
        self.assertIn("measurement_is_hardware", data)
        if data["measurement_method"] == "model":
            self.assertFalse(data["measurement_is_hardware"])
            self.assertTrue(any("model" in w.lower() for w in result["warnings"]))

    def test_calculate_sci_refuses_a_zero_functional_unit(self):
        result = self.mcp_server.calculate_sci(
            energy_joules=100.0, duration_seconds=1.0, functional_unit=0
        )
        self.assertEqual(result["status"], "error")

    def test_compare_regions_needs_two_zones(self):
        self.assertEqual(self.mcp_server.compare_regions(["IE"])["status"], "error")

    def test_unknown_zone_is_not_ranked_as_the_cleanest_grid(self):
        # The resolver returns 0.0 for "no data". Left alone, a typo'd zone
        # would win the ranking and be recommended as the greenest option.
        unknown = self.mcp_server._resolve_intensity("ZZ-NOT-A-ZONE")
        self.assertIsNone(unknown["carbon_intensity"])
        self.assertIn("unavailable_reason", unknown)

    def test_compare_regions_excludes_zones_with_no_reading(self):
        with mock.patch.object(
            self.mcp_server.optimizer,
            "get_zone_carbon_intensity",
            side_effect=lambda zone, **_: {
                "zone": zone,
                "carbon_intensity": None if zone == "BAD" else 50.0,
                "intensity_source": "test",
                "intensity_source_tier": "customer_key",
            },
        ):
            result = self.mcp_server.compare_regions(["IE", "BAD"])
        self.assertEqual(result["data"]["cleanest"]["zone"], "IE")
        self.assertIsNone(
            [r for r in result["data"]["readings"] if r["zone"] == "BAD"][0]["carbon_intensity"]
        )
    def test_audit_and_score_returns_one_actionable_verdict(self):
        result = self.mcp_server.audit_and_score(
            "def f(rows):\n"
            "    t = 0\n"
            "    for a in rows:\n"
            "        for b in rows:\n"
            "            for c in rows:\n"
            "                t += a * b * c\n"
            "    return t\n"
        )
        self.assertEqual(result["status"], "ok")
        self.assertIn("green_score", result["data"])
        self.assertIsInstance(result["data"]["remediation_plan"], list)
        self.assertIn("energy", result["data"])

    def test_remediation_plan_is_ordered_by_severity(self):
        with mock.patch.object(self.mcp_server, "audit_code", return_value={
            "status": "ok", "warnings": [],
            "data": {"green_score": 40.0, "grade": "F", "violation_count": 3,
                     "violations": [
                         {"severity": "LOW", "violation_type": "L", "line_number": 3},
                         {"severity": "HIGH", "violation_type": "H", "line_number": 1},
                         {"severity": "MEDIUM", "violation_type": "M", "line_number": 2},
                     ]},
        }):
            result = self.mcp_server.audit_and_score("x = 1")
        order = [step["violation_type"] for step in result["data"]["remediation_plan"]]
        self.assertEqual(order, ["H", "M", "L"])


class TestProviderSelection(unittest.TestCase):

    KEYS = CREDENTIAL_KEYS + ("GREENCODE_LLM_PROVIDER",)

    def setUp(self):
        self.saved = {k: os.environ.pop(k, None) for k in self.KEYS}

    def tearDown(self):
        for key in self.KEYS:
            os.environ.pop(key, None)
        os.environ.update({k: v for k, v in self.saved.items() if v is not None})

    def _provider(self):
        from app.llm_refactor import _select_client

        return _select_client()[1]

    def test_auto_prefers_bedrock_when_aws_is_configured(self):
        os.environ["AWS_PROFILE"] = "hackathon"
        self.assertEqual(self._provider(), "aws_bedrock")

    def test_auto_falls_back_to_huggingface_without_aws(self):
        self.assertEqual(self._provider(), "huggingface")

    def test_explicit_choice_is_honoured(self):
        os.environ["GREENCODE_LLM_PROVIDER"] = "huggingface"
        os.environ["AWS_PROFILE"] = "hackathon"
        self.assertEqual(self._provider(), "huggingface")

    def test_explicit_bedrock_is_not_swapped_silently(self):
        os.environ["GREENCODE_LLM_PROVIDER"] = "bedrock"
        self.assertEqual(self._provider(), "aws_bedrock")


if __name__ == "__main__":
    unittest.main()


