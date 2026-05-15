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

INTERVIEW_SYSTEM_PROMPT = """You are a mock interviewer. Use the resume and job description context to tailor questions.
Ask one question at a time, wait for the user's answer, then follow up with a harder or deeper question.
Keep questions concise and job-agnostic unless the resume suggests a clear focus area.
Resume context:
{resume}

Job description context:
{job_description}
"""

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
    try:
        api_key = st.secrets.get("OPENAI_API_KEY") if hasattr(st, "secrets") else None
    except Exception:
        api_key = None
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("Missing OpenAI API key. Add it to .streamlit/secrets.toml or set OPENAI_API_KEY.")
        st.stop()
    return OpenAI(api_key=api_key)

def init_session_state():
    if "page" not in st.session_state:
        st.session_state.page = "analysis"
    if "resume_context" not in st.session_state:
        st.session_state.resume_context = ""
    if "jd_context" not in st.session_state:
        st.session_state.jd_context = ""
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

st.set_page_config(page_title="AI Career Mentor", layout="wide")
init_session_state()

if st.session_state.page == "analysis":
    st.title("AI Career Mentor")
    st.caption("Paste a resume and a job description — get a match score, skill gaps, and interview prep.")

    col1, col2 = st.columns(2)
    with col1:
        resume = st.text_area("Resume", value=SAMPLE_RESUME, height=380)
    with col2:
        jd = st.text_area("Job Description", value=SAMPLE_JD, height=380)

    action_col1, action_col2 = st.columns(2)
    with action_col1:
        analyze_clicked = st.button("Analyze", type="primary")
    with action_col2:
        interview_clicked = st.button("Start Mock Interview")

    if interview_clicked:
        if not resume.strip() or not jd.strip():
            st.warning("Please provide both a resume and a job description to start the mock interview.")
        else:
            st.session_state.page = "interview"
            st.session_state.resume_context = resume.strip()
            st.session_state.jd_context = jd.strip()
            st.session_state.chat_history = []
            st.rerun()

    if analyze_clicked:
        if not resume.strip() or not jd.strip():
            st.warning("Please provide both a resume and a job description.")
        else:
            with st.spinner("Analyzing..."):
                try:
                    client = get_openai_client()
                    response = client.chat.completions.create(
                        model="gpt-5-mini",
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
else:
    st.title("Mock Interview")
    st.caption("Answer each question and get a tailored follow-up based on your resume and job description.")

    if st.button("Back to Analysis"):
        st.session_state.page = "analysis"
        st.rerun()

    with st.expander("Resume context", expanded=False):
        st.write(st.session_state.resume_context or "No resume provided.")
    with st.expander("Job description context", expanded=False):
        st.write(st.session_state.jd_context or "No job description provided.")

    if not st.session_state.chat_history:
        st.session_state.chat_history.append(
            {
                "role": "assistant",
                "content": "Hi! Let's start with a quick overview. Can you summarize your recent work and the impact you had?",
            }
        )

    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    user_input = st.chat_input("Your answer")
    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    client = get_openai_client()
                    response = client.chat.completions.create(
                        model="gpt-5-mini",
                        messages=[
                            {
                                "role": "system",
                                "content": INTERVIEW_SYSTEM_PROMPT.format(
                                    resume=st.session_state.resume_context,
                                    job_description=st.session_state.jd_context,
                                ),
                            },
                            *st.session_state.chat_history,
                        ],
                        reasoning_effort="low",
                        max_completion_tokens=600,
                    )
                    reply = response.choices[0].message.content
                    st.markdown(reply)
                    st.session_state.chat_history.append({"role": "assistant", "content": reply})
                except Exception as e:
                    st.error(f"OpenAI API error: {e}")
