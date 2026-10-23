"""SSML response builder for Alexa voice responses.

Produces SSML so Alexa speaks naturally: numbers, units, scores, and lists are
spoken correctly, not read as raw JSON.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

_SSML_ESCAPE = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&apos;",
}

# Structural markers around SSML fragments the builders generate themselves
# (see _render_ssml). They survive _escape so the final pass cannot mangle
# the tags, and are stripped from any text they never legitimately touch.
_TAG_OPEN = "\x01"
_TAG_CLOSE = "\x02"
_TAG_STRIP_RE = re.compile(r"<[^>]*>")


def _escape(text: str) -> str:
    text = text.replace(_TAG_OPEN, "").replace(_TAG_CLOSE, "")
    return "".join(_SSML_ESCAPE.get(ch, ch) for ch in text)


def _render_ssml(speech: str) -> str:
    """Compose the inner SSML: escape prose, pass trusted fragments through.

    ``_say_number``/``_say_score`` wrap their markup in the sentinels above;
    without this, escaping would turn ``<say-as>`` into spoken literal text.
    Everything outside a sentinel pair is escaped, so tool-provided strings
    (repository names, error reasons, caveats) remain inert content.
    """
    out: List[str] = []
    pos = 0
    while True:
        start = speech.find(_TAG_OPEN, pos)
        if start < 0:
            out.append(_escape(speech[pos:]))
            return "".join(out)
        end = speech.find(_TAG_CLOSE, start)
        if end < 0:
            # Unbalanced marker (caller-supplied text): treat the remainder
            # as prose; _escape drops the stray marker.
            out.append(_escape(speech[pos:]))
            return "".join(out)
        out.append(_escape(speech[pos:start]))
        out.append(speech[start + 1 : end])  # trusted SSML fragment, verbatim
        pos = end + 1


def _plain_text(speech: str) -> str:
    """Flatten speech for the phone card: keep tag contents, drop markup."""
    out: List[str] = []
    pos = 0
    while True:
        start = speech.find(_TAG_OPEN, pos)
        if start < 0:
            out.append(speech[pos:])
            break
        end = speech.find(_TAG_CLOSE, start)
        if end < 0:
            out.append(speech[pos:])
            break
        out.append(speech[pos:start])
        out.append(_TAG_STRIP_RE.sub("", speech[start + 1 : end]))
        pos = end + 1
    return "".join(out).replace(_TAG_OPEN, "").replace(_TAG_CLOSE, "")


def _say_number(value: Any) -> str:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return str(value)
    if f == int(f):
        return f"{_TAG_OPEN}<say-as interpret-as='cardinal'>{int(f)}</say-as>{_TAG_CLOSE}"
    return f"{_TAG_OPEN}<say-as interpret-as='number'>{f}</say-as>{_TAG_CLOSE}"


def _say_score(score: Any) -> str:
    try:
        f = float(score)
    except (TypeError, ValueError):
        return str(score)
    return (
        f"{_TAG_OPEN}<say-as interpret-as='cardinal'>{int(round(f))}</say-as>"
        f"{_TAG_CLOSE} percent"
    )


def _list_items(items: List[str], conjunction: str = "and") -> str:
    # Escaping happens once in _render_ssml; pre-escaping here would emit
    # entities like &amp;amp; into the spoken output.
    if not items:
        return "none"
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} {conjunction} {items[1]}"
    head = ", ".join(items[:-1])
    return f"{head}, {conjunction} {items[-1]}"


def build_response(
    speech: str,
    *,
    reprompt: Optional[str] = None,
    should_end_session: bool = True,
    card_title: Optional[str] = None,
    card_content: Optional[str] = None,
    directives: Optional[List[Dict[str, Any]]] = None,
    session_attributes: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    ssml = f"<speak>{_render_ssml(speech)}</speak>"
    response: Dict[str, Any] = {
        "outputSpeech": {"type": "SSML", "ssml": ssml},
        "shouldEndSession": should_end_session,
    }
    if reprompt:
        response["reprompt"] = {
            "outputSpeech": {
                "type": "SSML",
                "ssml": f"<speak>{_render_ssml(reprompt)}</speak>",
            }
        }
    if card_title or card_content:
        response["card"] = {
            "type": "Simple",
            "title": card_title or "GreenCode",
            "content": _plain_text(card_content) if card_content else _plain_text(speech),
        }
    if directives:
        response["directives"] = directives
    return {
        "version": "1.0",
        "response": response,
        "sessionAttributes": dict(session_attributes or {}),
    }


def build_error_response(message: str, reprompt: Optional[str] = None) -> Dict[str, Any]:
    return build_response(
        f"I'm sorry, {message}",
        reprompt=reprompt or "You can say 'help' to hear what I can do.",
        should_end_session=False,
    )


def build_help_response(
    session_attributes: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    speech = (
        "You can ask questions about GreenCode's documented features and local setup, "
        "compare named grid regions such as Ireland and Virginia, or ask which energy "
        "sensor the GreenCode server reports. The signed-in dashboard voice assistant "
        "uses its connected GitHub account. Pair the standalone Alexa skill from the "
        "dashboard before asking it to access your repositories. Alexa listens during "
        "this conversation, but Amazon controls when the session ends."
    )
    return build_response(
        speech, should_end_session=False, session_attributes=session_attributes
    )

def build_audit_response(result: Dict[str, Any]) -> Dict[str, Any]:
    """Speak an audit verdict.

    Handles the three audit shapes: ``audit_repository`` (repo + branch),
    ``audit_code`` (a snippet) and ``audit_and_score`` (snippet + energy).
    The repository fields are only spoken when the payload actually carries
    them.
    """
    data = result.get("data", {}) or {}
    score = data.get("green_score", 0)
    violations = data.get("violation_count", 0)
    repo = data.get("repo")
    branch = data.get("branch")
    grade = data.get("grade", "N/A")

    if repo:
        target = f"for {_escape(repo)}"
        if branch:
            target += f" on branch {_escape(branch)}"
        target += ". "
    else:
        target = ""

    speech = (
        f"Audit complete {target}Green score: {_say_score(score)}, "
        f"grade {_escape(str(grade))}. "
        f"Found {_say_number(violations)} energy anti-patterns."
    )
    if violations:
        speech += " The top fixes are in your GreenCode dashboard."

    card_title = f"GreenCode Audit - {repo}" if repo else "GreenCode Audit"
    return build_response(
        speech,
        card_title=card_title,
        card_content=(
            f"Score: {score} ({grade})\nViolations: {violations}"
            + (f"\nBranch: {branch}" if branch else "")
        ),
    )


def build_grid_response(result: Dict[str, Any]) -> Dict[str, Any]:
    data = result.get("data", {}) or {}
    zone = data.get("zone", "your region")
    intensity = data.get("carbon_intensity")
    source = data.get("intensity_source", "unknown")
    is_live = data.get("is_live", False)

    if intensity is None:
        speech = (
            f"I could not get a live carbon intensity reading for {_escape(zone)}. "
            f"No grid provider was reachable."
        )
    else:
        live_word = "live" if is_live else "reference"
        speech = (
            f"Grid carbon intensity for {_escape(zone)}: "
            f"{_say_number(intensity)} grams CO2 per kilowatt hour, "
            f"{live_word} data from {_escape(str(source))}."
        )

    return build_response(speech, card_title="Grid Carbon Intensity")


def build_compare_response(result: Dict[str, Any]) -> Dict[str, Any]:
    """Speak a region comparison.

    ``app.mcp_server.compare_regions`` returns ``readings`` plus the ranked
    ``cleanest`` / ``dirtiest`` entries and ``improvement_pct`` - it does not
    return a ``comparisons`` list, so this builder reads the real shape.
    """
    data = result.get("data", {}) or {}
    readings = data.get("readings", []) or []
    cleanest = data.get("cleanest")
    dirtiest = data.get("dirtiest")
    improvement = data.get("improvement_pct")

    if not cleanest:
        return build_response(
            "I could not compare those regions. Please try again with two AWS region names."
        )

    best_zone = cleanest.get("zone", "unknown")
    best_intensity = cleanest.get("carbon_intensity", 0)
    speech = (
        f"The cleanest region is {_escape(str(best_zone))} "
        f"at {_say_number(best_intensity)} grams CO2 per kilowatt hour."
    )

    others = [r.get("zone", "?") for r in readings if r.get("zone") != best_zone]
    if others:
        speech += f" Among {_list_items(others)}."

    if dirtiest and dirtiest.get("zone") != best_zone:
        speech += (
            f" The highest emission region is {_escape(str(dirtiest.get('zone')))} "
            f"at {_say_number(dirtiest.get('carbon_intensity', 0))} grams CO2 per kilowatt hour."
        )
    if improvement:
        speech += (
            f" Moving your workload to {_escape(str(best_zone))} cuts grid carbon "
            f"intensity by {_say_number(improvement)} percent."
        )

    return build_response(speech, card_title="Region Comparison")


def build_sci_response(result: Dict[str, Any]) -> Dict[str, Any]:
    data = result.get("data", {}) or {}
    sci = data.get("sci", {}) or {}
    sci_value = sci.get("sci_gco2_per_functional_unit", 0)
    grade = sci.get("grade", "N/A")
    speech = (
        f"Software Carbon Intensity: {_say_number(sci_value)} "
        f"grams CO2e per functional unit, grade {_escape(str(grade))}."
    )
    return build_response(speech, card_title="SCI Score")


def build_measure_response(result: Dict[str, Any]) -> Dict[str, Any]:
    data = result.get("data", {}) or {}
    joules = data.get("energy_joules", 0)
    watts = data.get("power_watts", 0)
    method = data.get("measurement_method", "model")
    is_hardware = data.get("measurement_is_hardware", False)
    source_word = "hardware counter" if is_hardware else "modelled estimate"
    speech = (
        f"Energy: {_say_number(joules)} joules at {_say_number(watts)} watts. "
        f"Source: {source_word} ({_escape(str(method))})."
    )
    return build_response(speech, card_title="Energy Measurement")


def build_refactor_response(result: Dict[str, Any]) -> Dict[str, Any]:
    data = result.get("data", {}) or {}
    accepted = data.get("accepted", False)
    if accepted:
        speech = "Refactor accepted. Your code has been optimized for energy efficiency."
    else:
        reason = data.get("reason", "unknown")
        speech = f"Refactor could not be applied: {_escape(str(reason))}."
    return build_response(speech, card_title="Code Refactor")


def build_explain_response(result: Dict[str, Any]) -> Dict[str, Any]:
    """Speak the provenance of a green score.

    ``app.mcp_server.explain_score`` returns the trace: hardware-vs-model, the
    grid source tier, the SCI breakdown (only when the caller supplied the
    energy measurement) and the caveats that must be stated with the number.
    """
    data = result.get("data", {}) or {}
    score = data.get("green_score", 0)
    grade = data.get("grade", "N/A")
    method = data.get("measurement_method", "model")
    is_hw = bool(data.get("measurement_is_hardware", False))
    grid = data.get("grid_intensity") or {}
    sci_ctx = data.get("scientific_context") or {}

    source_word = "a hardware counter" if is_hw else "a TDP model estimate"
    speech = (
        f"Your green score is {_say_score(score)}, grade {_escape(str(grade))}. "
        f"The energy behind it came from {source_word} ({_escape(str(method))}). "
        f"Grid zone {_escape(str(grid.get('zone', 'unknown')))} is at "
        f"{_say_number(grid.get('carbon_intensity', 0))} grams CO2 per kilowatt hour, "
        f"source tier {_escape(str(grid.get('tier', 'unavailable')))}."
    )

    sci_value = sci_ctx.get("sci_gco2_per_functional_unit")
    if sci_value is not None:
        speech += (
            f" Traceable SCI is {_say_number(sci_value)} grams CO2 per functional unit."
        )
    else:
        speech += " No SCI was computed because no energy measurement was supplied."

    caveats = data.get("caveats") or []
    if caveats:
        speech += " " + _escape(str(caveats[0]))

    return build_response(speech, card_title="Green Score Provenance")


def build_billing_response(result: Dict[str, Any]) -> Dict[str, Any]:
    """Speak the FOCUS billing / carbon reconciliation summary."""
    data = result.get("data", {}) or {}
    summary = data.get("summary") or {}
    if not summary:
        return build_response(
            "I could not reconcile that billing data. Please try again."
        )

    speech = (
        f"Billing reconciliation across {_say_number(data.get('line_items_evaluated', 0))} "
        f"line items. Effective cost {_say_number(summary.get('total_effective_cost_usd', 0))} "
        f"dollars, with {_say_number(summary.get('total_carbon_kg_co2e', 0))} kilograms "
        f"CO2e. I found {_say_number(summary.get('identified_monthly_usd_savings', 0))} "
        f"dollars of monthly savings and "
        f"{_say_number(summary.get('identified_co2e_savings_kg', 0))} kilograms of "
        f"avoidable CO2e."
    )
    return build_response(speech, card_title="FOCUS Billing Reconciliation")


def build_list_response(result: Dict[str, Any]) -> Dict[str, Any]:
    data = result.get("data", {}) or {}
    repos = data.get("repositories", []) or []
    if not repos:
        speech = "You have no repositories connected to GreenCode."
    else:
        names = [r.get("name", "unknown") for r in repos[:10]]
        speech = (
            f"You have {_say_number(len(repos))} connected repositories: {_list_items(names)}."
        )

    return build_response(speech, card_title="Your Repositories")


def build_help_from_hint(hint: str) -> Dict[str, Any]:
    return build_response(hint, should_end_session=False)


def build_github_response(result: Dict[str, Any]) -> Dict[str, Any]:
    data = result.get("data", {}) or {}
    message = data.get("message", "GitHub operation completed.")
    pr_url = data.get("pr_url", "")
    branch = data.get("branch", "")
    speech = message
    if pr_url:
        speech += f" Pull Request: {pr_url}."
    if branch:
        speech += f" Branch: {branch}."
    return build_response(speech, card_title="GitHub Action")


def build_deploy_response(result: Dict[str, Any]) -> Dict[str, Any]:
    data = result.get("data", {}) or {}
    status = data.get("status", "deployed")
    url = data.get("url", "")
    message = data.get("message", f"Deployment to {status} complete.")
    speech = message
    if url:
        speech += f" Live at {url}."
    return build_response(speech, card_title="Deployment")


def build_diff_response(result: Dict[str, Any]) -> Dict[str, Any]:
    """Speak the result of a diff-scoped audit."""
    data = result.get("data", {}) or {}
    score = data.get("diff_green_score", 0.0)
    violations = data.get("total_diff_violations", 0)
    files = data.get("modified_files_count", 0)
    hunks = data.get("hunks_analyzed", 0)

    speech = (
        f"Diff audit complete. I looked at {_say_number(hunks)} changed hunks "
        f"across {_say_number(files)} files. "
        f"Diff green score: {_say_score(score)}. "
        f"{_say_number(violations)} energy anti-patterns in the changed lines."
    )
    findings = data.get("violations") or []
    if violations:
        if findings:
            highest_priority = max(
                findings,
                key=lambda finding: (
                    {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(
                        str(finding.get("severity", "")).upper(), 0
                    ),
                    float(finding.get("deduction", 0) or 0),
                ),
            )
            title = str(highest_priority.get("title") or "an energy anti-pattern")
            severity = str(highest_priority.get("severity") or "unrated").lower()
            file_path = str(highest_priority.get("file_path") or "")
            line_number = highest_priority.get("line_number")
            location = f" in {file_path}" if file_path else ""
            if line_number is not None:
                location += f" at line {line_number}"
            speech += (
                f" The highest-priority finding is {severity}: {title}{location}."
            )
        speech += " Review the changed-line findings in your GreenCode dashboard."

    pr = data.get("pr_number")
    title = f"GreenCode Diff Audit - PR {pr}" if pr else "GreenCode Diff Audit"
    return build_response(
        speech,
        card_title=title,
        card_content=(
            f"Diff score: {score}\nViolations: {violations}\n"
            f"Modified files: {files}\nHunks analyzed: {hunks}"
        ),
    )


def build_sla_response(result: Dict[str, Any]) -> Dict[str, Any]:
    """Speak an energy SLA verdict."""
    data = result.get("data", {}) or {}
    status = str(data.get("status", "UNKNOWN")).upper()
    violations = data.get("violations", []) or []
    summary = str(data.get("summary", ""))
    suggestion = str(data.get("suggested_action", ""))

    if status == "COMPLIANT":
        speech = f"Your deployment passes the energy SLA. {summary}".strip()
    elif status == "BREACHED":
        speech = f"Your deployment breaches the energy SLA. {summary}".strip()
    else:
        speech = f"Your deployment is on an SLA warning. {summary}".strip()

    if violations:
        first = violations[0]
        speech += (
            f" The first issue is {_escape(str(first.get('metric', 'the limit')))}: "
            f"measured {_say_number(first.get('measured_value', 0))} "
            f"{_escape(str(first.get('unit', ''))).strip()}, limit "
            f"{_say_number(first.get('limit_value', 0))}."
        )
    if suggestion:
        speech += f" {suggestion}"

    return build_response(
        speech,
        card_title="Energy SLA Verdict",
        card_content=f"Status: {status}\n{summary}",
    )


def build_scope_response(result: Dict[str, Any]) -> Dict[str, Any]:
    """Speak a Scope 1, 2 and 3 GHG inventory."""
    data = result.get("data", {}) or {}
    scope_1 = data.get("scope_1", {}) or {}
    scope_2 = data.get("scope_2", {}) or {}
    scope_3 = data.get("scope_3", {}) or {}
    breakdown = data.get("scope_breakdown_pct", {}) or {}
    total = data.get("total_carbon_kgco2e_annual", 0.0)
    recs = data.get("recommendations", []) or []

    speech = (
        f"Scope 1, 2 and 3 inventory ready. Total annual footprint "
        f"{_say_number(total)} kilograms of CO2 equivalent. "
        f"Scope 1 is {_say_number(breakdown.get('scope_1_pct', 0))} percent, "
        f"Scope 2 is {_say_number(breakdown.get('scope_2_pct', 0))} percent, "
        f"and Scope 3 is {_say_number(breakdown.get('scope_3_pct', 0))} percent."
    )
    if recs:
        speech += f" {_escape(str(recs[0]))}"

    return build_response(
        speech,
        card_title="Scope 1-3 Emissions Inventory",
        card_content=(
            f"Total: {total} kg CO2e/yr\n"
            f"Scope 1: {scope_1.get('direct_emissions_kgco2e', 0)} kg CO2e\n"
            f"Scope 2: {scope_2.get('operational_emissions_kgco2e_annual', 0)} kg CO2e\n"
            f"Scope 3: {scope_3.get('total_scope3_kgco2e_annual', 0)} kg CO2e"
        ),
    )


def build_history_response(result: Dict[str, Any]) -> Dict[str, Any]:
    """Speak recent audits and cumulative carbon savings."""
    data = result.get("data", {}) or {}
    repos = data.get("repositories", []) or []
    savings = data.get("cumulative_savings", {}) or {}
    total = data.get("total", len(repos))

    if not repos:
        speech = (
            "You have no audits in your history yet. Say 'audit my repository' "
            "to start one."
        )
    else:
        names = [
            str(r.get("name") or r.get("full_name") or r.get("path_or_url") or "unknown")
            for r in repos[:5]
        ]
        speech = (
            f"You have {_say_number(total)} audits in your history. "
            f"The most recent are {_list_items(names)}."
        )

    saved = savings.get("total_carbon_saved_gco2_10k_runs")
    if saved:
        speech += (
            f" So far that has saved {_say_number(saved)} grams of CO2 "
            "over ten thousand runs."
        )
    reduction = savings.get("average_energy_reduction_pct")
    if reduction:
        speech += f" Average energy reduction {_say_number(reduction)} percent."

    return build_response(
        speech,
        card_title="Audit History",
        card_content=(
            f"Total audits: {total}\n"
            + "\n".join(
                f"- {r.get('name') or r.get('full_name') or 'unknown'}"
                for r in repos[:10]
            )
        ),
    )


def build_dynamic_response(result: Dict[str, Any]) -> Dict[str, Any]:
    """Speak the outcome of a sandboxed, measured run."""
    data = result.get("data", {}) or {}
    ok = bool(data.get("ok"))
    if not ok:
        reason = str(data.get("reason", "unknown error"))
        return build_response(
            f"I could not run that repository: {_escape(reason)}.",
            should_end_session=False,
        )

    sci = data.get("sci", {}) or {}
    grade = data.get("grade", {}) or {}
    it_joules = data.get("it_energy_joules", 0.0)
    duration = data.get("duration_seconds", 0.0)
    method = data.get("measurement_method", "model")

    speech = (
        f"The run finished in {_say_number(duration)} seconds and used "
        f"{_say_number(it_joules)} joules of IT energy, measured by "
        f"{_escape(str(method))}."
    )
    sci_value = sci.get("sci_gco2_per_functional_unit")
    if sci_value is not None:
        speech += (
            f" That is {_say_number(sci_value)} grams of CO2 per functional unit, "
            f"grade {_escape(str(grade.get('grade', 'unknown')))}."
        )
    warnings = data.get("warnings", []) or []
    if warnings:
        speech += f" {_escape(str(warnings[0]))}"

    return build_response(
        speech,
        card_title="Dynamic Analysis",
        card_content=(
            f"Duration: {duration}s\nIT energy: {it_joules} J\n"
            f"SCI: {sci.get('sci_gco2_per_functional_unit', 'n/a')} gCO2/unit"
        ),
    )



# ---------------------------------------------------------------------------
# Dashboard-backed actions.
#
# The standalone router (``app.alexa_skill``) and the live ASK webhook
# (``app.mcp_server``) both speak the same five actions, so the builders
# live here and the registry below is the single source of truth.
# ---------------------------------------------------------------------------

ACTION_BUILDERS: Dict[str, Any] = {
    "audit_diff": build_diff_response,
    "evaluate_sla": build_sla_response,
    "scope_inventory": build_scope_response,
    "audit_history": build_history_response,
    "dynamic_analyze": build_dynamic_response,
}


def build_action_response(tool: str, result: Dict[str, Any]) -> Dict[str, Any]:
    """Speak one dashboard-backed action as a full ASK response."""
    if result.get("status") != "ok":
        reason = (result.get("data", {}) or {}).get(
            "reason", "The requested action could not be completed."
        )
        return build_error_response(str(reason))
    builder = ACTION_BUILDERS.get(tool)
    if builder is None:
        reason = (result.get("data", {}) or {}).get("reason", "Command completed.")
        return build_response(str(reason), should_end_session=False)
    return builder(result)


def action_speech(tool: str, result: Dict[str, Any]) -> str:
    """Return the spoken text for one dashboard-backed action.

    The live ASK webhook answers in PlainText, so the SSML the builders
    produce is flattened to the words Alexa should say: tags are removed
    and the escaped entities are turned back into characters.
    """
    response = build_action_response(tool, result)
    ssml = (
        response.get("response", {})
        .get("outputSpeech", {})
        .get("ssml", "")
    )
    if not ssml:
        return _plain_text(
            (result.get("data", {}) or {}).get("reason", "Command completed.")
        ).strip()
    text = _TAG_STRIP_RE.sub(" ", ssml)
    for entity, char in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                         ("&quot;", '"'), ("&apos;", "'")):
        text = text.replace(entity, char)
    return re.sub(r"\s+", " ", text).strip()
