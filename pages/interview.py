import os
import json
import streamlit as st
from openai import OpenAI

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

QUESTIONS_PROMPT = """You are an experienced technical interviewer. Given a job description, generate 5 thoughtful interview questions that assess the candidate's fit for this specific role.

Return ONLY this JSON (no markdown fence, no preamble, no extra keys):
{
  "questions": ["...", "...", "...", "...", "..."]
}

Requirements:
- 2 behavioral questions and 3 technical questions specific to the role
- Reference actual skills and responsibilities from the JD — no generic questions
- Do not number the questions in the text
- Each question is a single sentence ending with a question mark"""

EVAL_PROMPT = """You are an experienced technical interviewer evaluating a candidate's answer for a specific role.

Return ONLY this JSON (no markdown fence, no preamble, no extra keys):
{
  "strengths": "What the answer did well — 2-3 sentences.",
  "weaknesses": "What was missing or could be stronger — 2-3 sentences.",
  "suggested_answer": "A stronger version of the answer that would impress the interviewer — 3-5 sentences.",
  "score": <integer 1 to 5>
}

Scoring: 1=poor, 2=below average, 3=adequate, 4=good, 5=excellent.
If the answer is blank or nonsensical, score it 1. Be honest and constructive."""

SUMMARY_PROMPT = """You are a career coach summarizing a mock interview session.

Return ONLY this JSON (no markdown fence, no preamble, no extra keys):
{
  "label": "<one of: Strong, Good, Needs Work>",
  "feedback": "<One encouraging but honest sentence of overall feedback.>"
}

Score guide: 20-25 = Strong, 13-19 = Good, 5-12 = Needs Work."""


def get_client():
    api_key = (st.secrets.get("OPENAI_API_KEY") if hasattr(st, "secrets") else None) or os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("Missing OPENAI_API_KEY. Add it to .streamlit/secrets.toml or set the env var.")
        st.stop()
    return OpenAI(api_key=api_key)


def generate_questions(jd: str) -> list:
    client = get_client()
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": QUESTIONS_PROMPT},
            {"role": "user",   "content": f"Job Description:\n{jd}"},
        ],
        response_format={"type": "json_object"},
        max_tokens=1000,
    )
    return json.loads(resp.choices[0].message.content)["questions"]


def evaluate_answer(question: str, answer: str, jd: str) -> dict:
    client = get_client()
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": EVAL_PROMPT},
            {"role": "user",   "content": f"Job Description:\n{jd}\n\nQuestion:\n{question}\n\nCandidate's Answer:\n{answer}"},
        ],
        response_format={"type": "json_object"},
        max_tokens=800,
    )
    return json.loads(resp.choices[0].message.content)


def generate_summary(total: int, evaluations: list) -> dict:
    client = get_client()
    scores_text = "\n".join(f"Q{i+1}: {e['score']}/5" for i, e in enumerate(evaluations))
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SUMMARY_PROMPT},
            {"role": "user",   "content": f"Total score: {total}/25\n\nPer-question scores:\n{scores_text}"},
        ],
        response_format={"type": "json_object"},
        max_tokens=200,
    )
    return json.loads(resp.choices[0].message.content)


def simple_card(accent: str, label_color: str, title: str, body: str) -> str:
    return (
        f'<div class="m-card" style="--mc-accent:{accent};">'
        f'<div class="m-card-label" style="color:{label_color};">{title}</div>'
        f'<div class="m-card-body"><p>{body}</p></div>'
        f'</div>'
    )


def reset_interview():
    for key in ["iv_questions", "iv_jd_key", "iv_q_index", "iv_evaluations", "iv_summary"]:
        st.session_state.pop(key, None)


# ── Page ─────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Mock Interview — Meridian", layout="wide")
st.markdown(MERIDIAN_CSS, unsafe_allow_html=True)

with st.sidebar:
    st.markdown("**Meridian**")
    st.page_link("app.py",             label="Home",             icon="🏠")
    st.page_link("pages/roadmap.py",   label="Learning Roadmap", icon="📚")
    st.page_link("pages/interview.py", label="Mock Interview",   icon="🎤")

st.title("Mock Interview Simulator")
st.caption("Practice answering questions tailored to your target role. Get AI feedback after each answer.")

# ── Guard ─────────────────────────────────────────────────────────────────────
results = st.session_state.get("results")
if not results or not results.get("jd"):
    st.info("No job analysis found. Run a resume analysis on the home page first, then come back here.")
    st.page_link("app.py", label="← Go to Home", icon="🏠")
    st.stop()

jd = results["jd"]
jd_key = str(hash(jd))

# ── Generate questions once per JD ────────────────────────────────────────────
if st.session_state.get("iv_jd_key") != jd_key:
    reset_interview()
    with st.spinner("Generating interview questions…"):
        try:
            st.session_state.iv_questions   = generate_questions(jd)
            st.session_state.iv_jd_key      = jd_key
            st.session_state.iv_q_index     = 0
            st.session_state.iv_evaluations = []
            st.session_state.iv_summary     = None
        except Exception as e:
            st.error(f"OpenAI API error: {e}")
            st.stop()

questions   = st.session_state.iv_questions
q_index     = st.session_state.iv_q_index
evaluations = st.session_state.iv_evaluations

# ── Summary screen ────────────────────────────────────────────────────────────
if q_index >= 5:
    total = sum(e["score"] for e in evaluations)

    if not st.session_state.get("iv_summary"):
        with st.spinner("Generating overall feedback…"):
            try:
                st.session_state.iv_summary = generate_summary(total, evaluations)
            except Exception as e:
                st.error(f"OpenAI API error: {e}")
                st.stop()

    summary  = st.session_state.iv_summary
    label    = summary.get("label", "")
    feedback = summary.get("feedback", "")

    label_colors = {
        "Strong":     ("#10B981", "#065F46"),
        "Good":       ("#3B82F6", "#1E40AF"),
        "Needs Work": ("#BA7517", "#854F0B"),
    }
    accent, label_color = label_colors.get(label, ("#534AB7", "#3C3489"))

    st.markdown(
        f'<div class="m-card" style="--mc-accent:{accent};">'
        f'<div class="m-card-label" style="color:{label_color};">INTERVIEW COMPLETE</div>'
        f'<div style="font-size:28px;font-weight:800;color:#111827;margin:8px 0 4px;">{total} / 25</div>'
        f'<div style="font-size:16px;font-weight:700;color:{accent};margin-bottom:8px;">{label}</div>'
        f'<div class="m-card-body"><p>{feedback}</p></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown("**Score breakdown**")
    for i, e in enumerate(evaluations):
        stars = "★" * e["score"] + "☆" * (5 - e["score"])
        st.markdown(f"Q{i+1}: {stars} &nbsp; {e['score']}/5")

    st.markdown("---")
    if st.button("Start Over", type="primary"):
        reset_interview()
        st.rerun()
    st.stop()

# ── Active interview ──────────────────────────────────────────────────────────
st.markdown(f"**Question {q_index + 1} of 5**")
st.progress(q_index / 5)
st.markdown("---")

st.markdown(
    f'<div class="m-card" style="--mc-accent:#534AB7;">'
    f'<div class="m-card-label" style="color:#3C3489;">QUESTION {q_index + 1}</div>'
    f'<div class="m-card-body"><p style="font-size:15px;font-weight:600;color:#111827;">{questions[q_index]}</p></div>'
    f'</div>',
    unsafe_allow_html=True,
)

# Answer input — not yet evaluated for this question
if len(evaluations) <= q_index:
    answer = st.text_area("Your answer", height=200, placeholder="Type your answer here…")
    if st.button("Submit Answer", type="primary"):
        if not answer.strip():
            st.warning("Please type an answer before submitting.")
        else:
            with st.spinner("Evaluating your answer…"):
                try:
                    ev = evaluate_answer(questions[q_index], answer, jd)
                    st.session_state.iv_evaluations.append(ev)
                    st.rerun()
                except Exception as e:
                    st.error(f"OpenAI API error: {e}")

# Feedback — already evaluated
else:
    ev    = evaluations[q_index]
    score = ev.get("score", 0)
    stars = "★" * score + "☆" * (5 - score)
    st.markdown(f"**Score: {stars} &nbsp; ({score}/5)**")
    st.markdown("")

    st.markdown(simple_card("#10B981", "#065F46", "STRENGTHS",        ev.get("strengths", "")),        unsafe_allow_html=True)
    st.markdown(simple_card("#BA7517", "#854F0B", "AREAS TO IMPROVE", ev.get("weaknesses", "")),       unsafe_allow_html=True)
    st.markdown(simple_card("#534AB7", "#3C3489", "SUGGESTED ANSWER", ev.get("suggested_answer", "")), unsafe_allow_html=True)

    st.markdown("---")
    if q_index < 4:
        if st.button("Next Question →", type="primary"):
            st.session_state.iv_q_index += 1
            st.rerun()
    else:
        if st.button("See My Results →", type="primary"):
            st.session_state.iv_q_index = 5
            st.rerun()
