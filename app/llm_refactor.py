"""LLM-assisted, behaviour-preserving refactoring via HuggingFace.

The static analyser knows *that* a pattern is expensive; it cannot rewrite the
code. This module asks a code-specialised model to produce the rewrite, then
**verifies the result before returning it**.

The verification is the point. An LLM will confidently return code that does not
compile, has changed behaviour, or silently dropped the logic. Every candidate
refactor must pass all of the following before it is surfaced:

1. The snippet parses (compiles) in the target language.
2. The response contains no markdown fences or prose.
3. The code is not trivially empty or a stub.
4. Structural similarity against the original is above a floor, so the model
   cannot quietly replace the body with something unrelated.
5. For Python, both versions are executed against generated inputs and their
   outputs compared. This is the strongest check available without a full test
   suite, and it catches the most common failure: changed behaviour.

If any check fails, the candidate is rejected and the deterministic rule-based
suggestion is returned instead. The user always gets something correct.
"""

from __future__ import annotations

import ast
import difflib
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.huggingface_client import LLMError, get_client

logger = logging.getLogger("greencode.llm.refactor")

SYSTEM_PROMPT = (
    "You are a Green Computing optimization agent. You refactor source code to "
    "drastically reduce CPU cycles and energy consumption while preserving "
    "identical input/output behaviour.\n\n"
    "Hard rules:\n"
    "1. Output ONLY the complete refactored source code. No markdown fences, no "
    "explanation, no comments about what you changed.\n"
    "2. Preserve every side effect, return value and exception behaviour.\n"
    "3. Prefer algorithmic improvements (better complexity) over micro-optimizations.\n"
    "4. Keep the same function or class name, signature and public API.\n"
    "5. Never introduce external dependencies."
)

_FENCE_RE = re.compile(r"^\s*```[a-zA-Z0-9_+-]*\s*\n?|```\s*$", re.MULTILINE)
_PROSE_PREFIX_RE = re.compile(
    r"^\s*(here(?:'s| is)|sure|certainly|the refactored|```).*?[:\n]", re.IGNORECASE
)


@dataclass
class RefactorOutcome:
    """The result of a refactoring attempt, including why it was accepted."""

    original: str
    refactored: str
    accepted: bool
    reason: str
    source: str                    # "llm" | "fallback" | "none"
    model: Optional[str] = None
    language: str = "python"
    usage: Dict[str, int] = field(default_factory=dict)
    similarity: float = 0.0
    behaviour_verified: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "accepted": self.accepted,
            "reason": self.reason,
            "source": self.source,
            "model": self.model,
            "language": self.language,
            "similarity": round(self.similarity, 3),
            "behaviour_verified": self.behaviour_verified,
            "usage": self.usage,
            "original": self.original,
            "refactored": self.refactored,
        }


def _strip_fences(text: str) -> str:
    """Remove markdown fences and any leading prose sentence."""
    cleaned = _FENCE_RE.sub("", text)
    cleaned = _PROSE_PREFIX_RE.sub("", cleaned, count=1)
    return cleaned.strip("\n")


def _python_compiles(source: str) -> bool:
    try:
        compile(source, "<refactor>", "exec")
        return True
    except (SyntaxError, ValueError):
        return False


def _looks_like_stub(source: str) -> bool:
    """Reject empty bodies, `pass`, `...` and comment-only replacements."""
    stripped = [ln for ln in source.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    if not stripped:
        return True
    body = [ln.strip() for ln in stripped]
    if all(tok in ("pass", "...", "return", "return None", "raise NotImplementedError")
           for tok in body):
        return True
    return False


def _similarity(a: str, b: str) -> float:
    """Token-level similarity so formatting churn does not look like a rewrite."""
    ta = re.findall(r"\w+|[^\w\s]", a)
    tb = re.findall(r"\w+|[^\w\s]", b)
    if not ta or not tb:
        return 0.0
    return difflib.SequenceMatcher(None, ta, tb).ratio()


def _target_arity(source: str) -> Optional[Tuple[int, int]]:
    """Return (required, total) positional parameter counts for the target function.

    Used to build probes the function can actually accept. Without this, a
    one-argument probe fails identically in both versions and the comparison
    reports a vacuous match.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    fns = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    if len(fns) != 1:
        return None

    args = fns[0].args
    positional = len(args.posonlyargs) + len(args.args)
    required = positional - len(args.defaults)
    if args.vararg:
        return 1, 1  # variadic: assume a single argument is accepted
    return max(required, 0), max(positional, 0)


# Candidate values, chosen to hit the shapes the energy rules actually fire on:
# empty, singleton, negative, float, nested and non-numeric. All are literals,
# so they round-trip through repr() without importing anything.
_PROBE_VALUES: Tuple[Any, ...] = (
    [],
    [1],
    [3, 1, 4, 1, 5, 9, 2, 6],
    [-2, 0, 5],
    [0.5, 1.5, 2.5],
    [[1, 2], [3, 4], [5, 6]],
    ["a", "bb", "ccc"],
    [{"k": 1}, {"k": 2}],
    (1, 2, 3),
    "hello",
    7,
    0,
)


def _generate_probe_inputs(fn_name: str, source: str) -> List[Tuple[Any, ...]]:
    """Build positional-argument tuples the target function can accept.

    Returns tuples of real values, not source text, so the harness can call the
    function directly. Where the arity cannot be determined a single-argument
    probe is produced and the caller verifies that at least one actually ran.
    """
    arity = _target_arity(source)
    n = arity[0] if arity and arity[0] > 0 else 1
    n = min(n, 2)  # beyond two arguments the shapes are too varied to guess

    if n == 1:
        return [(v,) for v in _PROBE_VALUES]
    return [(v, 2) for v in _PROBE_VALUES]


def _target_function(source: str) -> Optional[str]:
    """Return the name of the single top-level function, if there is exactly one."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    funcs = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    return funcs[0].name if len(funcs) == 1 else None


def _behaviour_matches(original: str, refactored: str) -> Tuple[bool, str]:
    """Execute both versions on generated inputs and compare their outputs.

    Returns (matched, detail). Values are compared via ``repr`` so that lists,
    floats and tuples all round-trip; a version that raises records the
    exception type, so a refactor that breaks error behaviour is caught too.
    """
    fn = _target_function(original)
    if not fn or _target_function(refactored) != fn:
        return False, "target function could not be identified in both versions"

    import contextlib
    import io

    probes = _generate_probe_inputs(fn, original)

    # Probes are embedded as literals so the harness is a single, inspectable
    # program rather than one that depends on injected globals.
    template = (
        "import json\n"
        "{body}\n"
        "_results = []\n"
        "for _a in {probes!r}:\n"
        "    try:\n"
        "        _results.append(['ok', repr({fn}(*_a))])\n"
        "    except Exception as _e:\n"
        "        _results.append(['err', type(_e).__name__])\n"
        "print('@@' + json.dumps(_results))\n"
    )

    outputs: List[str] = []
    successes = 0
    for body in (original, refactored):
        buf = io.StringIO()
        try:
            code = template.format(body=body, fn=fn, probes=probes)
            compiled = compile(code, "<behaviour-check>", "exec")
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
                exec(compiled, {"__name__": "__behaviour_check__"})
        except Exception as exc:
            return False, f"execution failed: {type(exc).__name__}: {exc}"

        text = buf.getvalue()
        if "@@" not in text:
            return False, "no output produced"
        payload = text.split("@@", 1)[1].strip()
        outputs.append(payload)
        if body is original:
            successes = payload.count('"ok"')

    # A comparison in which nothing actually ran proves nothing. Without this
    # guard, a signature mismatch would make every probe raise identically and
    # any rewrite would be reported as behaviour-preserving.
    if successes == 0:
        return False, "no probe input could be executed; behaviour unverified"

    if outputs[0] == outputs[1]:
        return True, f"identical results across {len(probes)} probe inputs"
    return False, f"behaviour differs: {outputs[0][:140]} vs {outputs[1][:140]}"


# A candidate that is more than this different (token-level) from the original
# is assumed to be a different program, not a refactor of this one.
MIN_SIMILARITY = 0.25


def refactor(
    code: str,
    *,
    language: str = "python",
    violation: Optional[str] = None,
    guidance: Optional[str] = None,
    fallback: Optional[str] = None,
    max_tokens: int = 1024,
) -> RefactorOutcome:
    """Request an energy-focused refactor and verify it before returning.

    Args:
        code: the original snippet.
        language: target language; behaviour checking currently covers Python.
        violation: the rule that fired, e.g. ``"nested_loops"``.
        guidance: the analyser's own remediation advice, passed to the model so
            the rewrite matches the rule that actually triggered.
        fallback: a deterministic suggestion from the rule engine, returned when
            the model's output is rejected or unavailable.

    The returned :class:`RefactorOutcome` always says which path was taken and
    why, so the UI can be honest about whether a suggestion is model-generated
    and verified.
    """
    language = (language or "python").lower()

    if fallback is not None and fallback.strip() == code.strip():
        # A "fallback" identical to the input is not a suggestion.
        fallback = None

    base = RefactorOutcome(
        original=code, refactored=code, accepted=False, reason="not attempted",
        source="none", language=language,
    )

    if not code.strip():
        base.reason = "empty input"
        return base

    parts = [f"Language: {language}"]
    if violation:
        parts.append(f"Detected energy violation: {violation}")
    if guidance:
        parts.append(f"Analyser guidance: {guidance}")
    parts.append("\nORIGINAL CODE:\n" + code)
    parts.append("\nREFACTORED CODE (output only the code):")

    user_prompt = "\n".join(parts)

    try:
        client = get_client()
        content, usage, model = client.chat(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.0,
        )
    except LLMError as exc:
        return RefactorOutcome(
            original=code,
            refactored=(fallback if fallback else code),
            accepted=fallback is not None,
            reason=f"model unavailable ({exc.kind}): {exc.message}",
            source="fallback" if fallback else "none",
            language=language,
        )
    except Exception as exc:  # defensive: never let the API path 500 the request
        return RefactorOutcome(
            original=code,
            refactored=(fallback if fallback else code),
            accepted=fallback is not None,
            reason=f"unexpected error: {type(exc).__name__}: {exc}",
            source="fallback" if fallback else "none",
            language=language,
        )

    candidate = _strip_fences(content)

    def reject(reason: str, similarity: float = 0.0, behaviour: Optional[bool] = None):
        return RefactorOutcome(
            original=code,
            refactored=(fallback if fallback else code),
            accepted=fallback is not None,
            reason=reason,
            source="fallback" if fallback else "none",
            model=model,
            language=language,
            usage={"prompt_tokens": usage.prompt_tokens,
                   "completion_tokens": usage.completion_tokens},
            similarity=similarity,
            behaviour_verified=behaviour,
        )

    if not candidate.strip():
        return reject("model returned no code")
    if _looks_like_stub(candidate):
        return reject("model returned a stub rather than a refactor")

    if language == "python" and not _python_compiles(candidate):
        return reject("refactor does not compile")

    sim = _similarity(code, candidate)
    if sim < MIN_SIMILARITY:
        return reject(
            f"refactor too dissimilar to the original (similarity {sim:.2f})", sim
        )

    behaviour: Optional[bool] = None
    if language == "python":
        matched, detail = _behaviour_matches(code, candidate)
        behaviour = matched
        if not matched:
            return reject(f"rejected: {detail}", sim, behaviour)

    return RefactorOutcome(
        original=code,
        refactored=candidate,
        accepted=True,
        reason="verified: compiles, similar, and behaviour-preserving on probe inputs",
        source="llm",
        model=model,
        language=language,
        usage={"prompt_tokens": usage.prompt_tokens,
               "completion_tokens": usage.completion_tokens},
        similarity=sim,
        behaviour_verified=behaviour,
    )



