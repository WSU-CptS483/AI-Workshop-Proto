import os
import re
import streamlit as st
from openai import OpenAI

SYSTEM_PROMPT = """You are an expert career coach and resume analyst.
The user will provide:
1. Their resume (as plain text)
2. A job description (as plain text)
Return a structured response with exactly these sections:

**MATCH SCORE: X/10**
A score from 1-10 with one sentence explaining it.

**STRENGTHS**
3-4 bullets — what the resume does well for this role.

**SKILL GAPS**
3-5 bullets — skills/keywords in the JD missing from the resume.

**RESUME IMPROVEMENTS**
3-4 specific, actionable suggestions.

**MOCK INTERVIEW QUESTIONS**
2 questions the candidate should prepare for based on this JD.

Be specific, direct, and encouraging. Do not summarize the resume or JD."""

SAMPLE_RESUME = """Alex Chen
alex.chen@email.com | github.com/alexchen

EDUCATION
B.S. Information Systems, Western Washington University, 2024

EXPERIENCE
Junior Data Analyst, Brightleaf Retail — June 2024 to present
- Built weekly sales dashboards in Tableau for 12 regional managers, cutting reporting time from 4 hours to 20 minutes
- Wrote SQL queries against PostgreSQL to investigate inventory discrepancies, surfacing $40k in lost product
- Partnered with marketing to A/B test promo email subject lines; identified the winning variant for the Q4 campaign

Data Analytics Intern, City of Bellingham — Summer 2023
- Cleaned and joined three years of permit application data in Python (pandas) to identify processing bottlenecks
- Presented findings to the Planning Department in a 15-minute briefing

SKILLS
SQL (PostgreSQL, BigQuery), Python (pandas, matplotlib), Tableau, Excel, Git"""

MODELS = {
    "gpt-5-nano (cheapest, fastest)": ("gpt-5-nano", "$0.05 / $0.40 per 1M tokens"),
    "gpt-5-mini (default, balanced)": ("gpt-5-mini", "$0.25 / $2.00 per 1M tokens"),
    "gpt-5 (best quality)": ("gpt-5", "$1.25 / $10.00 per 1M tokens"),
}
DEFAULT_MODEL_LABEL = "gpt-5-mini (default, balanced)"

SAMPLE_JD = """Data Engineer — Greenpath Analytics (Seattle, hybrid)

We're hiring a Data Engineer to build the pipelines that power our analytics products. You'll own ingestion, transformation, and orchestration for a growing portfolio of B2B customers.

Responsibilities:
- Design and maintain ETL/ELT pipelines using Airflow and dbt
- Build streaming ingestion with Kafka and Spark Structured Streaming
- Manage our Snowflake warehouse: modeling, performance tuning, cost monitoring
- Containerize pipeline jobs with Docker and deploy to AWS (ECS, S3, Lambda)
- Write production-grade Python with type hints and pytest coverage

Requirements:
- 3+ years building data pipelines in production
- Strong SQL and Python
- Hands-on with at least one orchestrator (Airflow, Dagster, Prefect) and one warehouse (Snowflake, BigQuery, Redshift)
- Experience with cloud infrastructure (AWS preferred)
- Comfortable with CI/CD, infrastructure as code (Terraform a plus)

Nice to have: dbt, Kafka, Spark, ML pipeline experience."""

# ── Meridian design system ────────────────────────────────────────────────────
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
.m-card-body li { margin-bottom: 4px; }
.m-card-body p  { margin: 0 0 6px 0; }
</style>"""

# Section display config: accent color, label color
SECTION_META = {
    "MATCH SCORE":              ("#3B82F6", "#1E40AF"),
    "STRENGTHS":                ("#10B981", "#065F46"),
    "SKILL GAPS":               ("#BA7517", "#854F0B"),
    "RESUME IMPROVEMENTS":      ("#7C3AED", "#4C1D95"),
    "MOCK INTERVIEW QUESTIONS": ("#0891B2", "#164E63"),
}

KNOWN_SECTIONS = set(SECTION_META.keys())


def get_openai_client():
    api_key = st.secrets.get("OPENAI_API_KEY") if hasattr(st, "secrets") else None
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("Missing OpenAI API key. Add it to .streamlit/secrets.toml or set OPENAI_API_KEY.")
        st.stop()
    return OpenAI(api_key=api_key)


def parse_sections(text: str):
    """Return ({lookup_key: content}, [(raw_title, lookup_key), ...])."""
    sections = {}
    order = []
    current_key = None
    current_lines = []

    for line in text.split("\n"):
        m = re.match(r"^\*\*([^*]+)\*\*\s*(.*)", line.strip())
        if m:
            raw = m.group(1).strip()
            # Strip "MATCH SCORE: 7/10" → "MATCH SCORE" for the lookup key
            lookup = re.sub(r":\s*\d+/\d+$", "", raw).strip()
            if lookup in KNOWN_SECTIONS:
                if current_key is not None:
                    sections[current_key] = "\n".join(current_lines).strip()
                current_key = lookup
                order.append((raw, lookup))
                rest = m.group(2).strip()
                current_lines = [rest] if rest else []
                continue
        if current_key is not None:
            current_lines.append(line)

    if current_key is not None:
        sections[current_key] = "\n".join(current_lines).strip()

    return sections, order


def extract_gaps(sections: dict) -> list:
    gaps = []
    for line in sections.get("SKILL GAPS", "").split("\n"):
        line = line.strip()
        if line and re.match(r"^[-•*](?!\*)", line):
            gap = re.sub(r"^[-•*]\s*", "", line).strip()
            if gap:
                gaps.append(gap)
    return gaps


def render_card(raw_title: str, lookup_key: str, content: str):
    accent, label_color = SECTION_META.get(lookup_key, ("#6B7280", "#374151"))

    lines = content.split("\n")
    html_lines = []
    in_list = False
    for line in lines:
        s = line.strip()
        if re.match(r"^[-•*](?!\*)", s):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            item = re.sub(r"^[-•*]\s*", "", s)
            item = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", item)
            html_lines.append(f"<li>{item}</li>")
        else:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            if s:
                s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
                html_lines.append(f"<p>{s}</p>")
    if in_list:
        html_lines.append("</ul>")

    body = "\n".join(html_lines)
    card = (
        f'<div class="m-card" style="--mc-accent:{accent};">'
        f'<div class="m-card-label" style="color:{label_color};">{raw_title}</div>'
        f'<div class="m-card-body">{body}</div>'
        f'</div>'
    )
    st.markdown(card, unsafe_allow_html=True)


# ── Page ──────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="AI Career Mentor — Meridian", layout="wide")
st.markdown(MERIDIAN_CSS, unsafe_allow_html=True)

with st.sidebar:
    st.markdown("**Meridian**")
    st.page_link("app.py",           label="Home",             icon="🏠")
    st.page_link("pages/roadmap.py", label="Learning Roadmap", icon="📚")

st.title("AI Career Mentor")
st.caption("Paste a resume and a job description — get a match score, skill gaps, and interview prep.")

model_label = st.sidebar.selectbox(
    "Model",
    options=list(MODELS.keys()),
    index=list(MODELS.keys()).index(DEFAULT_MODEL_LABEL),
)
selected_model, selected_price = MODELS[model_label]
st.sidebar.caption(f"`{selected_model}` — {selected_price}")

col1, col2 = st.columns(2)
with col1:
    resume = st.text_area("Resume", value=SAMPLE_RESUME, height=380)
with col2:
    jd = st.text_area("Job Description", value=SAMPLE_JD, height=380)

if st.button("Analyze", type="primary"):
    if not resume.strip() or not jd.strip():
        st.warning("Please provide both a resume and a job description.")
    else:
        with st.spinner("Analyzing…"):
            try:
                client = get_openai_client()
                response = client.chat.completions.create(
                    model=selected_model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user",   "content": f"Resume:\n{resume}\n\nJob Description:\n{jd}"},
                    ],
                    reasoning_effort="low",
                    max_completion_tokens=1500,
                )
                raw = response.choices[0].message.content
                sections, order = parse_sections(raw)
                gaps = extract_gaps(sections)
                st.session_state.results = {"raw": raw, "sections": sections, "order": order, "gaps": gaps}
            except Exception as e:
                st.error(f"OpenAI API error: {e}")

if "results" in st.session_state:
    r = st.session_state.results
    for raw_title, lookup_key in r["order"]:
        render_card(raw_title, lookup_key, r["sections"].get(lookup_key, ""))

    gaps = r.get("gaps", [])
    if gaps:
        st.markdown("---")
        st.page_link("pages/roadmap.py", label="Build a 4-week plan to close these gaps →", icon="📚")
