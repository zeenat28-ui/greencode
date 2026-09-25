"""Tests for the HuggingFace refactoring pipeline and its verification gate.

The model is never called. These tests inject a fake client so that what is
under test is the *verification logic* - the part that decides whether a rewrite
is ever shown to a user - rather than the model's output, which is not
reproducible.
"""

import os
import unittest
from unittest import mock

from app.huggingface_client import HuggingFaceClient, LLMError, LLMUsage
from app.llm_refactor import (
    MIN_SIMILARITY,
    _behaviour_matches,
    _looks_like_stub,
    _python_compiles,
    _similarity,
    _strip_fences,
    refactor,
)

QUADRATIC = """def total(m):
    t = 0
    for i in range(len(m)):
        for j in range(len(m)):
            for k in range(len(m)):
                t += m[i] * m[j] * m[k]
    return t
"""

# The triple loop computes sum_{i,j,k} m[i]*m[j]*m[k], which factorises to
# (sum m)^3. This O(N) form is therefore provably equivalent, not merely similar.
CORRECT_O_N = """def total(m):
    s = 0
    for v in m:
        s += v
    return s * s * s
"""

WRONG_BEHAVIOUR = """def total(m):
    return 42
"""

# Same tokens, different meaning: `+=` becomes `-=`. This is the case the
# similarity gate cannot catch and the behaviour gate exists for.
SUBTLE_BREAK = QUADRATIC.replace("t += m[i]", "t -= m[i]")


def _client_returning(text, model="test/model"):
    """A HuggingFaceClient whose chat() returns a canned completion."""
    client = mock.Mock(spec=HuggingFaceClient)
    client.chat.return_value = (text, LLMUsage(10, 20), model)
    return client


class TestOutputSanitisation(unittest.TestCase):
    def test_markdown_fences_are_stripped(self):
        raw = "```python\ndef f():\n    return 1\n```"
        self.assertNotIn("```", _strip_fences(raw))
        self.assertIn("def f():", _strip_fences(raw))

    def test_prose_prefix_is_stripped(self):
        raw = "Here is the refactored code:\ndef f():\n    return 1"
        self.assertTrue(_strip_fences(raw).startswith("def f():"))

    def test_compile_detection(self):
        self.assertTrue(_python_compiles("x = 1"))
        self.assertFalse(_python_compiles("def broken( :"))

    def test_stub_detection(self):
        self.assertTrue(_looks_like_stub(""))
        self.assertTrue(_looks_like_stub("pass"))
        self.assertTrue(_looks_like_stub("..."))
        self.assertTrue(_looks_like_stub("# just a comment"))
        self.assertFalse(_looks_like_stub("return sum(m)"))

    def test_similarity_bounds(self):
        self.assertEqual(_similarity("abc", "abc"), 1.0)
        self.assertLess(_similarity("def a(): pass", "totally unrelated text"), 0.3)


class TestBehaviourVerification(unittest.TestCase):
    def test_equivalent_code_matches(self):
        matched, detail = _behaviour_matches(QUADRATIC, CORRECT_O_N)
        self.assertTrue(matched, detail)

    def test_changed_behaviour_is_caught(self):
        matched, _ = _behaviour_matches(QUADRATIC, WRONG_BEHAVIOUR)
        self.assertFalse(matched)



class TestRefactorGate(unittest.TestCase):
    def _refactor(self, text, **kw):
        with mock.patch("app.llm_refactor.get_client", return_value=_client_returning(text)):
            return refactor(QUADRATIC, language="python", **kw)

    def test_correct_rewrite_is_accepted(self):
        r = self._refactor(CORRECT_O_N)
        self.assertTrue(r.accepted)
        self.assertEqual(r.source, "llm")
        self.assertTrue(r.behaviour_verified)
        self.assertEqual(r.model, "test/model")

    def test_behaviour_change_is_rejected(self):
        r = self._refactor(WRONG_BEHAVIOUR)
        self.assertFalse(r.accepted)
        self.assertNotEqual(r.refactored, WRONG_BEHAVIOUR)
        self.assertEqual(r.source, "none")

    def test_subtle_behaviour_break_is_caught_by_execution(self):
        """`+=` -> `-=` is a one-character change the similarity gate misses.

        This is the specific failure the behaviour gate exists to prevent: the
        rewrite looks almost identical but computes the wrong answer.
        """
        self.assertGreater(
            _similarity(QUADRATIC, SUBTLE_BREAK), MIN_SIMILARITY
        )  # the cheap gate would have passed it
        r = self._refactor(SUBTLE_BREAK)
        self.assertFalse(r.accepted)
        self.assertIn("behaviour differs", r.reason)

    def test_non_compiling_output_is_rejected(self):
        r = self._refactor("def total(m)\n    return (((")
        self.assertFalse(r.accepted)
        self.assertIn("compile", r.reason)

    def test_stub_output_is_rejected(self):
        r = self._refactor("pass")
        self.assertFalse(r.accepted)
        self.assertIn("stub", r.reason)

    def test_fenced_output_is_accepted_after_cleaning(self):
        r = self._refactor("```python\n" + CORRECT_O_N + "\n```")
        self.assertTrue(r.accepted)
        self.assertNotIn("```", r.refactored)

    def test_unrelated_output_is_rejected(self):
        r = self._refactor("import os\ndef unrelated():\n    return os.getcwd()\n")
        self.assertFalse(r.accepted)
        self.assertLessEqual(r.similarity, MIN_SIMILARITY + 1e-9)

    def test_fallback_used_when_model_fails(self):
        client = mock.Mock(spec=HuggingFaceClient)
        client.chat.side_effect = LLMError("down", kind="unavailable", retryable=True)
        with mock.patch("app.llm_refactor.get_client", return_value=client):
            r = refactor(QUADRATIC, language="python", fallback="FALLBACK")
        self.assertEqual(r.refactored, "FALLBACK")
        self.assertEqual(r.source, "fallback")
        self.assertIn("unavailable", r.reason)

    def test_empty_input_short_circuits(self):
        with mock.patch("app.llm_refactor.get_client") as get_client:
            r = refactor("   ")
        get_client.assert_not_called()
        self.assertEqual(r.reason, "empty input")

    def test_no_fallback_yields_no_change(self):
        client = mock.Mock(spec=HuggingFaceClient)
        client.chat.side_effect = LLMError("nokey", kind="auth")
        with mock.patch("app.llm_refactor.get_client", return_value=client):
            r = refactor(QUADRATIC, language="python")
        self.assertFalse(r.accepted)
        self.assertEqual(r.refactored, QUADRATIC)
        self.assertEqual(r.source, "none")

    def test_usage_is_reported(self):
        r = self._refactor(CORRECT_O_N)
        self.assertEqual(r.usage["prompt_tokens"], 10)
        self.assertEqual(r.usage["completion_tokens"], 20)

    def test_unexpected_exception_does_not_propagate(self):
        client = mock.Mock(spec=HuggingFaceClient)
        client.chat.side_effect = RuntimeError("boom")
        with mock.patch("app.llm_refactor.get_client", return_value=client):
            r = refactor(QUADRATIC, language="python", fallback="FALLBACK")
        self.assertEqual(r.refactored, "FALLBACK")


class TestClientErrorClassification(unittest.TestCase):
    def setUp(self):
        self.client = HuggingFaceClient(api_key="k")

    def test_auth_error_is_not_retryable(self):
        err = self.client._classify(401, "")
        self.assertEqual(err.kind, "auth")
        self.assertFalse(err.retryable)

    def test_rate_limit_is_retryable(self):
        self.assertTrue(self.client._classify(429, "").retryable)

    def test_server_error_is_retryable(self):
        self.assertTrue(self.client._classify(503, "").retryable)

    def test_model_not_enabled_is_not_retryable(self):
        err = self.client._classify(400, "not supported by any provider")
        self.assertEqual(err.kind, "bad_request")
        self.assertFalse(err.retryable)

    def test_unconfigured_client_raises_rather_than_calling(self):
        empty = HuggingFaceClient(api_key="")
        # Force the empty-key branch even when the ambient environment has one.
        with mock.patch.dict(os.environ, {"HUGGINGFACE_API_KEY": "", "HF_TOKEN": ""},
                             clear=False):
            empty.api_key = ""
            with self.assertRaises(LLMError) as ctx:
                empty.chat([{"role": "user", "content": "hi"}])
        self.assertEqual(ctx.exception.kind, "auth")

    def test_response_parsing(self):
        content, usage = HuggingFaceClient._parse(
            {"choices": [{"message": {"content": "ok"}}],
             "usage": {"prompt_tokens": 5, "completion_tokens": 7}}
        )
        self.assertEqual(content, "ok")
        self.assertEqual(usage.total_tokens, 12)

    def test_empty_choices_rejected(self):
        with self.assertRaises(LLMError):
            HuggingFaceClient._parse({"choices": []})

    def test_renamed_function_is_rejected(self):
        other = CORRECT_O_N.replace("def total", "def other")
        matched, _ = _behaviour_matches(QUADRATIC, other)
        self.assertFalse(matched)
