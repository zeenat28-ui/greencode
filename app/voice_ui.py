"""Voice web cockpit driving the GreenCode engine end-to-end.

Streamlit page. The agent answers carbon-audit questions and surfaces the
"explain this score" provenance breakdown.
Run:  streamlit run app/voice_ui.py

Every answer uses the same engine the self-hosted MCP server exposes over
Streamable HTTP (app.mcp_server -> app.parser, app.energy_sensors, app.optimizer),
so the voice cockpit runs standalone, with no server. No figure is invented:
grid intensity comes from the live provider chain, the green score from the
real static analyser, and energy from a hardware counter when the host exposes
one (otherwise an explicitly-labelled TDP model).
"""

from __future__ import annotations

import html
import json
from typing import Optional

import streamlit as st

from app.mcp_server import SERVER_VERSION
from app.optimizer import get_zone_carbon_intensity
from app import __version__ as SCI_VERSION

STYLE = """
<style>
  .alexa-header { font-family: 'Amazon Ember', 'Segoe UI', sans-serif; }
  .alexa-avatar { background:#232f3e; color:#fff; border-radius:50%; width:48px; height:48px;
                  display:inline-block; line-height:48px; text-align:center; font-weight:700;
                  margin-right:12px; }
  .user-bubble { background:#232f3e; color:#fff; border-radius:18px 18px 2px 18px;
                 padding:10px 16px; max-width:80%; text-align:right; font-size:0.95rem; }
  .alexa-bubble { background:#fff4e5; color:#232f3e; border-radius:18px 18px 18px 2px;
                  padding:10px 16px; max-width:80%; font-size:0.95rem;
                  border-top:3px solid #ff9900; }
  .explain-box { background:#f0f7f0; border:1px solid #b6d8b6; border-radius:10px;
                 padding:12px 16px; font-size:0.85rem; white-space:pre-line; }
  .kpi { flex:1; background:#eaf3e6; border-radius:8px; padding:8px; text-align:center; }
  .kpi .v { font-size:1.25rem; font-weight:700; color:#232f3e; }
</style>
"""
st.set_page_config(page_title="GreenCode — Voice", layout="wide")
st.markdown(STYLE, unsafe_allow_html=True)

if "dialogue" not in st.session_state:
    st.session_state.dialogue = []
if "region" not in st.session_state:
    st.session_state.region = "IE"
if "last_audit" not in st.session_state:
    st.session_state.last_audit = None


def _say(text: str) -> None:
    """Alexa-flavoured spoken turn; echoed into the conversation."""
    st.session_state.dialogue.append({"role": "alexa", "text": text})


def _voice_speak(text: str) -> None:
    """Client-side speech synthesis (safe JSON string serialization + try/catch)."""
    payload = json.dumps(str(text or "")).replace("</", "<\\/")
    st.components.v1.html(
        f"<script>try {{ if (window.speechSynthesis) {{ window.speechSynthesis.cancel(); window.speechSynthesis.speak(new SpeechSynthesisUtterance({payload})); }} }} catch (e) {{}}</script>",
        height=0,
    )


def _normalize_zone(zone: str) -> str:
    """Map AWS region IDs or common shorthands to canonical grid zone identifiers."""
    shorthands = {
        "US-VA": "US-MIDA-PJM",
        "US-CA": "US-CAL-CISO",
        "US-TX": "US-TEX-ERCO",
        "US-NY": "US-NY-NYIS",
    }
    if zone in shorthands:
        return shorthands[zone]
    try:
        from app.amazon_service import AWS_REGION_TO_GRID_ZONE
        return AWS_REGION_TO_GRID_ZONE.get(zone, zone)
    except Exception:
        return "SG" if zone == "ap-southeast-1" else zone


def _region_snapshots() -> dict:
    """Provider-chain readings for three representative zones.

    Each value comes from ``get_zone_carbon_intensity`` (EIA-930 / Electricity
    Maps -> annual dataset -> bundled static reference), so every number carries
    the source tier that actually produced it - live when a live provider
    answered, a cited static reference otherwise. The AWS regions
    ``us-east-1`` (Virginia) and ``ap-southeast-1`` (Singapore) are mapped to
    their grid zones via the same table the AWS carbon endpoints use.
    """
    va_zone = _normalize_zone("us-east-1")
    sg_zone = _normalize_zone("ap-southeast-1")
    targets = (
        ("Ireland (IE)", "IE"),
        ("Virginia (" + va_zone + ")", va_zone),
        ("ap-southeast-1 (" + sg_zone + ")", sg_zone),
    )
    out = {}
    for label, zone in targets:
        data = get_zone_carbon_intensity(zone)
        raw_carbon = data.get("carbon_intensity")
        # 0.0 with intensity_source=='none' means 'no data', never 'zero-carbon grid'
        if data.get("intensity_source") == "none" or not raw_carbon:
            raw_carbon = None
        out[label] = {
            "zone": data.get("zone") or zone,
            "carbon": raw_carbon,
            "source": data.get("intensity_source"),
            "tier": data.get("intensity_source_tier"),
            "is_live": bool(data.get("is_live")),
            "region": data.get("region"),
        }
    return out


def _explain_score(score: float, **kw) -> dict:
    """Local mirror of the MCP 'explain_score' tool for the voice panel."""
    from app.mcp_server import explain_score as _es
    if "zone" in kw and kw["zone"]:
        kw["zone"] = _normalize_zone(str(kw["zone"]))
    return _es(score, **kw)


# --------------------------------------------------------------------------- #
# Tabs: region readings + explain score
# --------------------------------------------------------------------------- #
tab_voice, tab_region_demo, tab_explain = st.tabs(["Voice agent", "Live grid readings", "Explain this score"])

def _render_region_tab(container) -> None:
    """Render the live grid-intensity comparison into the given tab container.

    Every value is resolved through the real provider chain; none is seeded.
    """
    with container:
        st.markdown("### Live grid intensity - Ireland / Virginia / ap-southeast-1")
        st.caption("Each reading is resolved through the provider chain (Electricity Maps "
                   "/ EIA-930 -> annual dataset -> bundled static reference), so the value "
                   "shown is whatever tier actually answered - live when a live provider "
                   "responded, a cited static reference otherwise. No value is invented.")
        snapshots = _region_snapshots()
        col_r1, col_r2, col_r3 = st.columns(3)
        for (label, info), col in zip(snapshots.items(), (col_r1, col_r2, col_r3)):
            with col:
                val = info["carbon"] if info["carbon"] is not None else "no data"
                delta = ("live" if info["is_live"] else "static reference") + " - " + str(info["tier"])
                st.metric(label=label, value=str(val) + " gCO2e/kWh", delta=delta)
        with st.expander("Full readings (source + tier + region)", expanded=False):
            for label, info in snapshots.items():
                st.json(info)


def _render_explain_tab(container) -> None:
    """Render the 'explain this score' traceability view.

    The SCI breakdown is shown only when the caller supplies the energy
    measurement that produced the score. Without it the tool withholds the
    number rather than inventing inputs, and the panel says so explicitly
    instead of crashing on a missing figure.
    """
    with container:
        st.markdown("### 'Explain this score' - traceability")
        st.caption("Hardware vs model, data source + freshness, and the SCI that backs the number.")
        with st.form("explain_form"):
            score = st.slider("Green score (0-100)", 0.0, 100.0, 73.5, 0.5)
            zone = st.selectbox("Zone to explain", ["IE", "US-MIDA-PJM", "ap-southeast-1", "US-MIDW-MISO"])
            method = st.selectbox("Energy source", ["model", "rapl", "perf", "battery"], index=0)
            energy_joules = st.number_input(
                "Energy that produced the score (Joules, optional)",
                min_value=0.0, value=0.0, step=1.0,
                help="Leave at 0 to see the withheld-SCI behaviour: without a real "
                     "measurement the tool refuses to fabricate an SCI.",
            )
            submit = st.form_submit_button("Explain")
        if not submit:
            return
        kwargs = {"zone": _normalize_zone(zone), "measurement_method": method}
        if energy_joules and energy_joules > 0.0:
            kwargs["energy_joules"] = float(energy_joules)
        res = _explain_score(float(score), **kwargs)
        if res["status"] != "ok":
            st.error(res["data"].get("reason", "unexplained"))
            return
        d = res["data"]
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Grade", d["grade"])
            st.metric("Score", str(round(d["green_score"], 1)))
            st.metric("Hardware?", d["measurement_is_hardware"])
            st.metric("Method", d["measurement_method"])
        with c2:
            gi = d["grid_intensity"]
            gin = ("%.3f" % gi["carbon_intensity"]) if gi["carbon_intensity"] is not None else "-"
            st.metric("Grid intensity", gin + " gCO2e/kWh")
            st.metric("Grid source", gi["source"])
            st.metric("Grid tier", str(gi["tier"]) + " (live=" + str(gi["is_live"]) + ")")
        with st.expander("SCI breakdown", expanded=True):
            sc = d["scientific_context"]
            if sc.get("sci_gco2_per_functional_unit") is not None:
                st.write("SCI = " + ("%.3e" % sc["sci_gco2_per_functional_unit"]) + " gCO2e/unit")
                grade = sc.get("grade") or {}
                st.write("Grade = " + str(grade.get("grade")) + " - " + str(grade.get("label")))
                eqs = []
                for k, v in (sc.get("carbon_equivalents") or {}).items():
                    eqs.append(k.replace("_", "-") + "=" + ("%.4g" % v))
                st.write("Equivalents: " + ", ".join(eqs))
            else:
                st.info(sc.get("reason", "No SCI computed: no energy measurement was supplied."))
            st.write("Freshness: " + d["data_freshness"]["as_of"] + " (" + d["data_freshness"]["tier"] + ")")
        st.markdown("### Caveats")
        for i, c in enumerate(d["caveats"], 1):
            st.write(str(i) + ". " + c)


# --------------------------------------------------------------------------- #
# Voice agent chat
# --------------------------------------------------------------------------- #
DEFAULT_SNIPPET = (
    "def build(n):\n"
    "    s = ''\n"
    "    for i in range(n):\n"
    "        s = s + str(i)\n"
    "    return s\n"
)


def _live_audit(zone: str, snippet: Optional[str] = None) -> dict:
    """Run the real end-to-end MCP pipeline on the supplied or reference snippet."""
    from app.mcp_server import audit_and_score

    code = snippet if (snippet and snippet.strip()) else DEFAULT_SNIPPET
    res = audit_and_score(
        source_code=code,
        language="python",
        zone=_normalize_zone(zone),
        duration_seconds=0.1,
    )
    if res.get("status") == "ok":
        st.session_state.last_audit = res.get("data")
    return res


def _answer(user_text: str) -> str:
    """Map a natural-language question to a deterministic, spoken answer.

    Every number in the reply is produced by the live engine (``audit_and_score``,
    ``explain_score``, ``refactor_code``); none is hard-coded. When the host
    exposes a hardware energy counter the reply says so, otherwise it states
    plainly that the figure is a TDP model rather than a measurement.
    """
    low = user_text.lower()
    zone = _normalize_zone(st.session_state.region)

    if "region" in low or "cleanest" in low or "where" in low:
        snapshots = _region_snapshots()
        ranked = sorted(
            ((label, info) for label, info in snapshots.items()
             if info.get("carbon") is not None),
            key=lambda kv: kv[1]["carbon"],
        )
        if not ranked:
            return ("I could not read a carbon intensity for any region right now, "
                    "so I cannot rank them.")
        label, best = ranked[0]
        return ("The cleanest region I can currently read is " + label + " at "
                + str(best["carbon"]) + " gCO2e/kWh from the " + str(best["source"])
                + " (" + str(best["tier"]) + "). Run the same workload there first.")

    if "refactor" in low or "optimize" in low or "rewrite" in low:
        from app.mcp_server import refactor_code
        ref = refactor_code(
            source_code=DEFAULT_SNIPPET,
            language="python",
            violation_type="string_concatenation_in_loop",
        )
        if ref.get("status") == "ok":
            rd = ref["data"]
            verified_str = "behaviour-verified" if rd.get("behaviour_verified") else "deterministic fallback"
            return (
                "I refactored the loop via " + str(rd.get("source")) + " ("
                + str(rd.get("model")) + "), " + verified_str + ": "
                + str(rd.get("reason")) + "."
            )
        return "I could not complete a verified refactor right now."

    if "explain" in low and "score" in low:
        d = st.session_state.last_audit
        if not d:
            audit = _live_audit(zone)
            if audit["status"] != "ok":
                return "I could not explain that score right now."
            d = audit["data"]
        energy = d.get("energy", {})
        res = _explain_score(
            float(d["green_score"]),
            zone=zone,
            measurement_method=energy.get("measurement_method", "model"),
            energy_joules=float(energy.get("energy_joules", 0.0)),
            duration_seconds=float(energy.get("duration_seconds", 0.1)),
            violation_count=int(d.get("violation_count", 0)),
        )
        if res["status"] == "ok":
            ed = res["data"]
            sc = ed.get("scientific_context", {})
            grid = ed.get("grid_intensity", {})
            sci_val = sc.get("sci_gco2_per_functional_unit")
            if sci_val is not None:
                sci_txt = (" Its SCI is " + ("%.2e" % sci_val) + " gCO2e per unit, grade "
                           + str((sc.get("grade") or {}).get("grade")) + ".")
            else:
                sci_txt = (" No SCI is quoted because no energy measurement accompanied "
                           "the score.")
            hw = ("a hardware counter" if ed.get("measurement_is_hardware")
                  else "a TDP model, not a hardware counter")
            v_count = ed.get("violation_count")
            if v_count is None:
                v_count = (ed.get("findings_summary") or {}).get("violation_count", 0)
            return ("Your green score is " + str(round(ed["green_score"])) + " ("
                    + str(ed["grade"]) + "), from " + str(v_count)
                    + " energy finding(s). The energy came from " + hw
                    + ", and the grid intensity for " + zone + " is "
                    + str(grid.get("carbon_intensity")) + " gCO2e/kWh from the "
                    + str(grid.get("tier")) + " tier." + sci_txt)
        return "I could not explain that score right now."

    # Default: run a real audit (using user-supplied Python code if present).
    custom_snippet = user_text if ("def " in user_text or "for " in user_text) else None
    audit = _live_audit(zone, snippet=custom_snippet)
    if audit["status"] != "ok":
        return "I could not complete an audit right now."
    d = audit["data"]
    energy = d.get("energy", {})
    sci = d.get("sci") or {}
    grade = d.get("sci_grade") or {}
    hw = ("a hardware counter" if energy.get("measurement_is_hardware")
          else "a TDP model, not a hardware reading")
    sci_val = sci.get("sci_gco2_per_functional_unit")
    if sci_val is not None:
        sci_txt = (" Its SCI is " + ("%.2e" % sci_val) + " gCO2e per unit (grade "
                   + str(grade.get("grade")) + ").")
    else:
        sci_txt = ""
    return ("I audited the Python snippet (" + str(d.get("violation_count", 0))
            + " finding(s)). Green score " + str(round(d["green_score"])) + " ("
            + str(d.get("grade")) + ")." + sci_txt + " Energy is " + hw
            + " (method: " + str(energy.get("measurement_method")) + "). "
            "Collect loop outputs in a list and join or vectorize once, and I will re-measure.")


# --------------------------------------------------------------------------- #
# Boot
# --------------------------------------------------------------------------- #
def main() -> None:
    header_l, header_r = st.columns([1, 4])
    with header_l:
        st.markdown("<div class='alexa-avatar'>G</div>", unsafe_allow_html=True)
    with header_r:
        st.title("GreenCode Auditor")
        st.caption("Carbon accounting for software - voice-first, traceable, grid-aware.")

    sel = st.sidebar.selectbox("Voice UI", ["voice", "region", "explain"],
                               index=0, key="vu_tab")
    st.sidebar.caption("Active session: region=" + st.session_state.region)

    st.markdown("---")
    if sel == "voice":
        with tab_voice:
            st.markdown("<div class='alexa-header'><b>GreenCode Auditor - Voice "
                        "Agent</b></div>", unsafe_allow_html=True)
            st.caption("Responses are text-audio mirrored; every answer exposes its provenance.")
            if st.session_state.dialogue:
                last = st.session_state.dialogue[-1]
                if last["role"] == "alexa":
                    st.markdown("<div class='alexa-bubble'><b>GreenCode:</b> " +
                                html.escape(str(last["text"])) + "</div>", unsafe_allow_html=True)
            if st.button("REPLAY SPOKEN RESPONSES", key="replay_form"):
                _voice_speak(" ".join(x["text"] for x in st.session_state.dialogue
                                      if x["role"] == "alexa"))
            user = st.text_input("You", key="voice_input")
            if user:
                st.session_state.dialogue.append({"role": "user", "text": user})
                st.markdown("<div class='user-bubble'><b>You:</b> " + html.escape(user) +
                            "</div>", unsafe_allow_html=True)
                with st.spinner("GreenCode is thinking..."):
                    answer = _answer(user)
                    _say(answer)
                    st.markdown("<div class='alexa-bubble'><b>GreenCode:</b> " +
                                html.escape(answer) + "</div>", unsafe_allow_html=True)

    elif sel == "region":
        _render_region_tab(tab_region_demo)
    else:
        _render_explain_tab(tab_explain)

    st.markdown("---")
    st.caption("GreenCode voice UI | engine " + SCI_VERSION + " | MCP server v" +
               str(SERVER_VERSION) + " | same engine the self-hosted Alexa+ MCP server "
               "exposes over Streamable HTTP.")


if __name__ == "__main__":
    main()


