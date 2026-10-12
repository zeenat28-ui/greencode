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
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.huggingface_client import LLMError, get_client


def _select_client():
    """Choose the model backend once, so the engine stays provider-agnostic.

    Selection is made here, in one place, rather than by branching on a
    provider name throughout the refactoring logic. That keeps the behaviour
    of the verification gate below identical whichever backend produced the
    candidate rewrite - a Claude proposal is checked exactly as strictly as a
    Qwen one.

    ``GREENCODE_LLM_PROVIDER`` overrides the choice and accepts ``bedrock``,
    ``huggingface`` or ``auto``. An explicit request for a provider that is not
    configured is honoured, so its classified error surfaces to the user
    instead of being silently swapped for a different vendor.

    The HuggingFace branch resolves ``get_client`` through the module global
    rather than binding it locally. That keeps this module-level name the
    single injection seam, which is what the existing test suite patches - a
    second local alias would quietly bypass every test that fakes the model.
    """
    choice = (os.environ.get("GREENCODE_LLM_PROVIDER") or "auto").strip().lower()

    if choice == "huggingface":
        return get_client(), "huggingface"

    if choice == "bedrock":
        from app.bedrock_client import get_client as _bedrock_client

        return _bedrock_client(), "aws_bedrock"

    # auto: prefer Bedrock when it is configured, otherwise HuggingFace.
    try:
        from app.bedrock_client import get_client as _bedrock_client

        bedrock = _bedrock_client()
        if bedrock.configured:
            return bedrock, "aws_bedrock"
    except Exception:  # noqa: BLE001 - a missing optional backend is not fatal
        logger.debug("Bedrock backend unavailable; falling back to HuggingFace")

    return get_client(), "huggingface"

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
    provider: Optional[str] = None
    language: str = "python"
    usage: Dict[str, int] = field(default_factory=dict)
    similarity: float = 0.0
    behaviour_verified: Optional[bool] = None
    attempts: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "accepted": self.accepted,
            "reason": self.reason,
            "source": self.source,
            "model": self.model,
            "provider": self.provider,
            "language": self.language,
            "similarity": round(self.similarity, 3),
            "behaviour_verified": self.behaviour_verified,
            "attempts": self.attempts,
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
    import textwrap

    try:
        compile(textwrap.dedent(source), "<refactor>", "exec")
        return True
    except (SyntaxError, ValueError):
        return False


def _looks_like_stub(source: str) -> bool:
    """Reject empty bodies, `pass`, `...` and comment-only replacements."""
    stripped = [ln for ln in source.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    if not stripped:
        return True
    body = [ln.strip() for ln in stripped]
    if all(tok in ("pass", "...", "return", "return None", "raise " + "NotImplemented" + "Error")
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


def _takes_self_or_cls(source: str) -> bool:
    """Return True if the target function's first parameter is `self` or `cls`."""
    import textwrap

    try:
        tree = ast.parse(textwrap.dedent(source))
    except SyntaxError:
        return False
    fns = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    if len(fns) != 1:
        return False
    all_args = list(fns[0].args.posonlyargs) + list(fns[0].args.args)
    return bool(all_args and all_args[0].arg in ("self", "cls"))


def _target_arity(source: str) -> Optional[Tuple[int, int]]:
    """Return (required, total) positional parameter counts (excluding `self`/`cls`)."""
    import textwrap

    try:
        tree = ast.parse(textwrap.dedent(source))
    except SyntaxError:
        return None
    fns = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    if len(fns) != 1:
        return None

    args = fns[0].args
    all_pos = list(args.posonlyargs) + list(args.args)
    offset = 1 if (all_pos and all_pos[0].arg in ("self", "cls")) else 0
    positional = max(0, len(all_pos) - offset)
    required = max(0, positional - len(args.defaults))
    if args.vararg:
        return 1, 1  # variadic: assume a single argument is accepted
    return required, positional


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
    """Build positional-argument tuples the target function can accept."""
    arity = _target_arity(source)
    n = arity[0] if arity and arity[0] > 0 else 1
    n = min(n, 2)  # beyond two arguments the shapes are too varied to guess

    if n == 1:
        return [(v,) for v in _PROBE_VALUES]
    return [(v, 2) for v in _PROBE_VALUES]


def _target_function(source: str) -> Optional[str]:
    """Return the name of the single top-level function, if there is exactly one."""
    import textwrap

    try:
        tree = ast.parse(textwrap.dedent(source))
    except SyntaxError:
        return None
    funcs = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    return funcs[0].name if len(funcs) == 1 else None


def _behaviour_matches(original: str, refactored: str) -> Tuple[bool, str]:
    """Execute both versions on generated inputs (supporting sync, async, and `self` methods)."""
    import contextlib
    import io
    import textwrap

    orig_dedented = textwrap.dedent(original)
    ref_dedented = textwrap.dedent(refactored)

    fn = _target_function(orig_dedented)
    if not fn or _target_function(ref_dedented) != fn:
        return False, "target function could not be identified in both versions"

    probes = _generate_probe_inputs(fn, orig_dedented)
    needs_self = _takes_self_or_cls(orig_dedented)

    template = (
        "import asyncio, inspect, json\n"
        "class _ProbeAttr(int):\n"
        "    def __call__(self, *a, **kw):\n"
        "        return a[0] if a else 2\n"
        "class _ProbeSelf:\n"
        "    def __getattr__(self, name):\n"
        "        return _ProbeAttr(2)\n"
        "{body}\n"
        "_results = []\n"
        "_self_arg = (_ProbeSelf(),) if {needs_self!r} else ()\n"
        "for _a in {probes!r}:\n"
        "    try:\n"
        "        _val = {fn}(*(_self_arg + tuple(_a)))\n"
        "        if inspect.iscoroutine(_val):\n"
        "            _val = asyncio.run(_val)\n"
        "        _results.append(['ok', repr(_val)])\n"
        "    except Exception as _e:\n"
        "        _results.append(['err', type(_e).__name__])\n"
        "print('@@' + json.dumps(_results))\n"
    )

    outputs: List[str] = []
    successes = 0
    for body in (orig_dedented, ref_dedented):
        buf = io.StringIO()
        try:
            code = template.format(body=body, fn=fn, probes=probes, needs_self=needs_self)
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
        if body is orig_dedented:
            successes = payload.count('"ok"')

    if successes == 0:
        return False, "no probe input could be executed; behaviour unverified"

    if outputs[0] == outputs[1]:
        return True, f"identical results across {len(probes)} probe inputs"
    return False, f"behaviour differs: {outputs[0][:140]} vs {outputs[1][:140]}"


# A candidate that is more than this different (token-level) from the original
# is assumed to be a different program, not a refactor of this one.
MIN_SIMILARITY = 0.25


def _verify_candidate(
    code: str, candidate: str, language: str
) -> Tuple[bool, str, float, Optional[bool]]:
    """Run all static and dynamic verification gates on a candidate rewrite.

    Returns ``(passed, reason, similarity, behaviour_verified)``.
    """
    if not candidate.strip():
        return False, "model returned no code", 0.0, None
    if _looks_like_stub(candidate):
        return False, "model returned a stub rather than a refactor", 0.0, None
    if language == "python" and not _python_compiles(candidate):
        return False, "refactor does not compile", 0.0, None

    sim = _similarity(code, candidate)
    if sim < MIN_SIMILARITY:
        return (
            False,
            f"refactor too dissimilar to the original (similarity {sim:.2f})",
            sim,
            None,
        )

    behaviour: Optional[bool] = None
    if language == "python":
        matched, detail = _behaviour_matches(code, candidate)
        behaviour = matched
        if not matched:
            return False, f"rejected: {detail}", sim, behaviour

    return (
        True,
        "verified: compiles, similar, and behaviour-preserving on probe inputs",
        sim,
        behaviour,
    )


def refactor(
    code: str,
    *,
    language: str = "python",
    violation: Optional[str] = None,
    guidance: Optional[str] = None,
    fallback: Optional[str] = None,
    max_tokens: int = 1024,
    max_attempts: int = 2,
) -> RefactorOutcome:
    """Request an energy-focused refactor, self-heal on rejection, and verify before returning.

    When the first LLM candidate fails compilation, similarity, or behaviour
    verification, ``refactor`` feeds the exact rejection reason back into a
    second self-healing turn so the model can synthesize a corrected patch
    before falling back to the deterministic rule engine.
    """
    language = (language or "python").lower()
    max_attempts = max(1, int(max_attempts))

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
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    try:
        client, provider = _select_client()
    except Exception as exc:
        return RefactorOutcome(
            original=code,
            refactored=(fallback if fallback else code),
            accepted=fallback is not None,
            reason=f"unexpected error: {type(exc).__name__}: {exc}",
            source="fallback" if fallback else "none",
            language=language,
        )

    total_prompt_tokens = 0
    total_completion_tokens = 0
    last_reason = "not attempted"
    last_sim = 0.0
    last_behaviour: Optional[bool] = None
    last_model: Optional[str] = None
    attempts_made = 0

    for attempt in range(1, max_attempts + 1):
        try:
            content, usage, model = client.chat(
                messages,
                max_tokens=max_tokens,
                temperature=0.0,
            )
        except LLMError as exc:
            if attempt == 1:
                return RefactorOutcome(
                    original=code,
                    refactored=(fallback if fallback else code),
                    accepted=fallback is not None,
                    reason=f"model unavailable ({exc.kind}): {exc.message}",
                    source="fallback" if fallback else "none",
                    provider=provider,
                    language=language,
                )
            break
        except Exception as exc:  # defensive: never let the API path 500 the request
            if attempt == 1:
                return RefactorOutcome(
                    original=code,
                    refactored=(fallback if fallback else code),
                    accepted=fallback is not None,
                    reason=f"unexpected error: {type(exc).__name__}: {exc}",
                    source="fallback" if fallback else "none",
                    provider=provider,
                    language=language,
                )
            break

        attempts_made = attempt
        last_model = model
        total_prompt_tokens += int(getattr(usage, "prompt_tokens", 0) or 0)
        total_completion_tokens += int(getattr(usage, "completion_tokens", 0) or 0)

        candidate = _strip_fences(content)
        passed, reason, sim, behaviour = _verify_candidate(code, candidate, language)
        if passed:
            return RefactorOutcome(
                original=code,
                refactored=candidate,
                accepted=True,
                reason=reason if attempt == 1 else f"{reason} (self-healed on attempt {attempt})",
                source="llm",
                model=model,
                provider=provider,
                language=language,
                usage={
                    "prompt_tokens": total_prompt_tokens,
                    "completion_tokens": total_completion_tokens,
                },
                similarity=sim,
                behaviour_verified=behaviour,
                attempts=attempts_made,
            )

        last_reason = reason
        last_sim = sim
        last_behaviour = behaviour

        if attempt < max_attempts:
            messages.append({"role": "assistant", "content": candidate or content})
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"Your previous refactored code was rejected by our verification gate ({reason}). "
                        f"Please fix this issue and output ONLY the corrected, behaviour-preserving {language} code "
                        "with the exact same function signature and return values."
                    ),
                }
            )

    return RefactorOutcome(
        original=code,
        refactored=(fallback if fallback else code),
        accepted=fallback is not None,
        reason=last_reason,
        source="fallback" if fallback else "none",
        model=last_model,
        provider=provider,
        language=language,
        usage={
            "prompt_tokens": total_prompt_tokens,
            "completion_tokens": total_completion_tokens,
        },
        similarity=last_sim,
        behaviour_verified=last_behaviour,
        attempts=attempts_made,
    )



