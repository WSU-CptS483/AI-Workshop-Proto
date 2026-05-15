import os
import json
import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI

# ── Meridian design system (shared with app.py) ─────────────────────────────
MERIDIAN_CSS = """<style>
html, body, [data-testid="stApp"] {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
button[data-testid="baseButton-primary"] {
    background-color: #0D2137 !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    letter-spacing: 0.01em !important;
}
button[data-testid="baseButton-primary"]:hover {
    background-color: #1B3A5C !important;
    color: #FFFFFF !important;
}
.m-card {
    background: #FFFFFF;
    border-left: 4px solid var(--mc-accent, #3B82F6);
    border-radius: 0 8px 8px 0;
    padding: 16px 20px 14px 16px;
    margin-bottom: 14px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
.m-card-label {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 6px;
}
.m-card-body {
    color: #374151;
    font-size: 14px;
    line-height: 1.65;
}
.m-card-body ul { margin: 0; padding-left: 18px; }
.m-card-body li { margin-bottom: 5px; }
.m-card-body p  { margin: 0 0 6px 0; }
</style>"""

ROADMAP_PROMPT = """You are a technical learning coach. Given a list of skill gaps, create a focused 4-week learning roadmap.

Return ONLY this JSON object (no markdown fence, no preamble, no extra keys):
{
  "weeks": [
    {
      "week": 1,
      "focus": "Focus area title — 4-6 words",
      "resources": [
        "Complete the [specific tutorial name] at https://real-url.com/path",
        "Follow the [specific guide] at https://real-url.com/path"
      ]
    }
  ]
}

Requirements:
- Exactly 4 week objects
- 2-3 resources per week (never 1, never 4+)
- Every resource MUST include a real, working URL (official docs, freeCodeCamp, Coursera, YouTube, etc.)
- Each resource begins with an action verb: Complete / Follow / Read / Work through / Watch
- Be specific: name the exact tutorial, course, or doc section and include its real URL
- No vague advice — not "Learn Docker", but "Complete the Docker Getting Started tutorial at docs.docker.com/get-started"
- Sequence: Week 1 = foundations, Week 2-3 = core skills, Week 4 = advanced or integration"""


def get_client():
    api_key = (st.secrets.get("OPENAI_API_KEY") if hasattr(st, "secrets") else None) or os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("Missing OPENAI_API_KEY. Add it to .streamlit/secrets.toml or set the env var.")
        st.stop()
    return OpenAI(api_key=api_key)


def generate_roadmap(gaps: list) -> dict:
    client = get_client()
    gaps_list = "\n".join(f"- {g}" for g in gaps)
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": ROADMAP_PROMPT},
            {"role": "user",   "content": f"Skill gaps to address:\n{gaps_list}"},
        ],
        response_format={"type": "json_object"},
        max_tokens=1500,
    )
    return json.loads(resp.choices[0].message.content)


def week_card(num: int, focus: str, resources: list) -> str:
    items = "".join(f"<li>{r}</li>" for r in resources)
    return (
        f'<div class="m-card" style="--mc-accent:#BA7517;">'
        f'<div class="m-card-label" style="color:#854F0B;">WEEK {num}</div>'
        f'<div style="font-size:15px;font-weight:700;color:#111827;margin-bottom:8px;">{focus}</div>'
        f'<div class="m-card-body"><ul>{items}</ul></div>'
        f'</div>'
    )


def roadmap_as_text(weeks: list) -> str:
    parts = []
    for w in weeks:
        parts.append(f"WEEK {w['week']}: {w['focus']}")
        for r in w["resources"]:
            parts.append(f"  • {r}")
        parts.append("")
    return "\n".join(parts).strip()


# ── Page ─────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Learning Roadmap — Meridian", layout="wide")
st.markdown(MERIDIAN_CSS, unsafe_allow_html=True)

with st.sidebar:
    st.markdown("**Meridian**")
    st.page_link("app.py",               label="Home",              icon="🏠")
    st.page_link("pages/roadmap.py",      label="Learning Roadmap",  icon="📚")

st.title("Learning Roadmap")
st.caption("A personalized 4-week plan to close your skill gaps.")

# ── Guard: analysis must exist ────────────────────────────────────────────────
results = st.session_state.get("results")
if not results or not results.get("gaps"):
    st.info("No analysis found yet. Run a resume analysis on the home page first, then come back here.")
    st.page_link("app.py", label="← Go to Home", icon="🏠")
    st.stop()

gaps = results["gaps"]

# ── Generate once per unique set of gaps ─────────────────────────────────────
gaps_key = "|".join(gaps)
if st.session_state.get("roadmap_for") != gaps_key:
    with st.spinner("Building your 4-week roadmap…"):
        try:
            data = generate_roadmap(gaps)
            st.session_state.roadmap     = data
            st.session_state.roadmap_for = gaps_key
        except Exception as e:
            st.error(f"OpenAI API error: {e}")
            st.stop()

weeks = st.session_state.roadmap.get("weeks", [])

# ── Skill gaps summary ────────────────────────────────────────────────────────
with st.expander(f"Addressing {len(gaps)} skill gap(s)", expanded=False):
    for g in gaps:
        st.markdown(f"• {g}")

if st.button("Regenerate roadmap", type="secondary"):
    del st.session_state["roadmap"]
    del st.session_state["roadmap_for"]
    st.rerun()

st.markdown("---")

# ── 2×2 week grid ─────────────────────────────────────────────────────────────
col_a, col_b = st.columns(2)
with col_a:
    if len(weeks) > 0:
        st.markdown(week_card(weeks[0]["week"], weeks[0]["focus"], weeks[0]["resources"]), unsafe_allow_html=True)
    if len(weeks) > 2:
        st.markdown(week_card(weeks[2]["week"], weeks[2]["focus"], weeks[2]["resources"]), unsafe_allow_html=True)
with col_b:
    if len(weeks) > 1:
        st.markdown(week_card(weeks[1]["week"], weeks[1]["focus"], weeks[1]["resources"]), unsafe_allow_html=True)
    if len(weeks) > 3:
        st.markdown(week_card(weeks[3]["week"], weeks[3]["focus"], weeks[3]["resources"]), unsafe_allow_html=True)

st.markdown("---")

# ── Copy roadmap as text ──────────────────────────────────────────────────────
# json.dumps produces a properly escaped JS string literal
js_text = json.dumps(roadmap_as_text(weeks))
components.html(
    f"""<style>
#cp{{background:#0D2137;color:#fff;border:none;border-radius:6px;
     padding:10px 24px;font-weight:600;cursor:pointer;font-size:14px;
     font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
     transition:background .15s;}}
#cp:hover{{background:#1B3A5C;}}
</style>
<button id="cp" onclick="
  navigator.clipboard.writeText({js_text});
  this.innerText='Copied!';
  setTimeout(()=>this.innerText='Copy roadmap as text',2000);
">Copy roadmap as text</button>""",
    height=55,
)
