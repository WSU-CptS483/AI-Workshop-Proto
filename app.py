import os

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

def get_openai_client():
    api_key = st.secrets.get("OPENAI_API_KEY") if hasattr(st, "secrets") else None
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("Missing OpenAI API key. Add it to .streamlit/secrets.toml or set OPENAI_API_KEY.")
        st.stop()
    return OpenAI(api_key=api_key)

st.set_page_config(page_title="AI Career Mentor", layout="wide")
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
        with st.spinner("Analyzing..."):
            try:
                client = get_openai_client()
                response = client.chat.completions.create(
                    model=selected_model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": f"Resume:\n{resume}\n\nJob Description:\n{jd}"},
                    ],
                    reasoning_effort="low",
                    max_completion_tokens=1500,
                )
                st.markdown(response.choices[0].message.content)
            except Exception as e:
                st.error(f"OpenAI API error: {e}")
