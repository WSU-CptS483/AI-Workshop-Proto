import streamlit as st
from openai import OpenAI
import json
import math

st.set_page_config(
    page_title="Meridian — AI Career Mentor",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="collapsed"
)

client = OpenAI()  # reads OPENAI_API_KEY from environment

SYSTEM_PROMPT = """You are an expert career coach and resume analyst.

The user will provide their resume and a job description.

Return ONLY a valid JSON object with no other text or markdown:
{
  "score": <integer 1-10>,
  "scoreLabel": <string, e.g. "Strong Match", "Good Match", "Partial Match", "Weak Match">,
  "scoreDesc": <one sentence explaining the score>,
  "strengths": ["...", "...", "..."],
  "gaps": ["...", "...", "..."],
  "improvements": ["...", "...", "..."],
  "questions": ["...", "..."]
}

strengths: 3-4 specific items. gaps: 3-5 items. improvements: 3-4 actionable items. questions: exactly 2.
Be specific, direct, and encouraging."""

CSS = """
<style>
    #MainMenu, footer, header { visibility: hidden; }
    .block-container { padding-top: 2rem; padding-bottom: 2rem; max-width: 920px; }

    .app-header {
        display: flex; align-items: center; justify-content: space-between;
        margin-bottom: 6px;
    }
    .app-title {
        font-size: 1.65rem; font-weight: 700; color: #0d0d1a;
        letter-spacing: -0.03em;
    }
    .app-badge {
        font-size: 11px; font-weight: 600; letter-spacing: 0.07em;
        text-transform: uppercase; background: #e6f5f0; color: #0f6e56;
        padding: 4px 12px; border-radius: 20px; border: 1px solid #9fe1cb;
    }
    .app-sub {
        font-size: 14px; color: #777; margin-bottom: 24px; margin-top: 2px;
    }
    .col-label {
        font-size: 11px; font-weight: 600; letter-spacing: 0.07em;
        text-transform: uppercase; color: #555; margin-bottom: 6px;
        display: block;
    }

    .stTextArea textarea {
        font-size: 13px !important;
        border-radius: 8px !important;
        border: 1px solid #e2e2e2 !important;
        background: #fafafa !important;
        line-height: 1.6 !important;
        font-family: ui-monospace, 'Cascadia Code', monospace !important;
        color: #1a1a2e !important;
    }
    .stTextArea textarea:focus {
        border-color: #1D9E75 !important;
        box-shadow: 0 0 0 3px rgba(29,158,117,0.08) !important;
        background: white !important;
    }

    .stButton > button {
        width: 100%;
        background: #0d0d1a !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 13px 20px !important;
        font-size: 15px !important;
        font-weight: 600 !important;
        letter-spacing: -0.01em !important;
        margin-top: 4px;
    }
    .stButton > button:hover {
        background: #1c1c3a !important;
    }
    .stButton > button:active {
        transform: scale(0.99) !important;
    }

    .result-card {
        background: white;
        border-radius: 10px;
        border: 1px solid #ebebeb;
        padding: 18px 20px;
        margin-bottom: 14px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .card-header {
        display: flex; align-items: center; gap: 8px; margin-bottom: 14px;
    }
    .card-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
    .card-label {
        font-size: 11px; font-weight: 700; letter-spacing: 0.09em;
        text-transform: uppercase;
    }
    .card-item {
        font-size: 13.5px; line-height: 1.6; color: #2a2a3a;
        padding: 7px 0; border-bottom: 1px solid #f5f5f5;
        display: flex; gap: 10px; align-items: flex-start;
    }
    .card-item:last-child { border-bottom: none; padding-bottom: 0; }
    .card-bullet { flex-shrink: 0; margin-top: 4px; font-size: 9px; }

    .improve-grid {
        display: grid; grid-template-columns: 1fr 1fr; gap: 8px;
    }
    .improve-item {
        background: #f8f9fb; border-radius: 8px;
        padding: 12px 14px; font-size: 13.5px;
        line-height: 1.55; color: #2a2a3a;
        border: 1px solid #eee;
    }
    .question-item {
        background: #f8f9fb; border-radius: 8px;
        padding: 14px 16px; font-size: 13.5px;
        line-height: 1.55; color: #2a2a3a;
        display: flex; gap: 12px; align-items: flex-start;
        margin-bottom: 8px; border: 1px solid #eee;
    }
    .question-item:last-child { margin-bottom: 0; }
    .q-num {
        flex-shrink: 0; width: 24px; height: 24px; border-radius: 50%;
        background: white; border: 1px solid #ddd;
        display: flex; align-items: center; justify-content: center;
        font-size: 11px; font-weight: 700; color: #666;
    }

    .section-title {
        font-size: 18px; font-weight: 700; color: #0d0d1a;
        margin-bottom: 16px; letter-spacing: -0.02em;
    }
    .privacy-note {
        text-align: center; font-size: 12px; color: #bbb; margin-top: 8px;
    }
    .results-meta {
        font-size: 12px; color: #aaa; text-align: right; padding-top: 6px;
    }

    div[data-testid="column"] { padding: 0 6px; }
    div[data-testid="column"]:first-child { padding-left: 0; }
    div[data-testid="column"]:last-child { padding-right: 0; }
</style>
"""

def score_color(score):
    if score >= 8: return "#1D9E75"
    if score >= 6: return "#378ADD"
    if score >= 4: return "#BA7517"
    return "#E24B4A"

def score_text_color(score):
    if score >= 8: return "#0F6E56"
    if score >= 6: return "#185FA5"
    if score >= 4: return "#854F0B"
    return "#A32D2D"

def render_score_card(data):
    score = data["score"]
    color = score_color(score)
    txt_color = score_text_color(score)
    r = 38
    circ = 2 * math.pi * r
    offset = circ - (score / 10) * circ
    html = f"""
    <div class="result-card" style="display:flex; align-items:center; gap:28px;">
        <svg width="100" height="100" viewBox="0 0 100 100" style="flex-shrink:0;">
            <circle cx="50" cy="50" r="{r}" fill="none" stroke="#f0f0f0" stroke-width="7"/>
            <circle cx="50" cy="50" r="{r}" fill="none" stroke="{color}" stroke-width="7"
                stroke-linecap="round"
                stroke-dasharray="{circ:.2f}"
                stroke-dashoffset="{offset:.2f}"
                transform="rotate(-90 50 50)"/>
            <text x="50" y="46" text-anchor="middle"
                font-size="24" font-weight="700" fill="#0d0d1a"
                font-family="system-ui, sans-serif">{score}</text>
            <text x="50" y="62" text-anchor="middle"
                font-size="11" fill="#aaa"
                font-family="system-ui, sans-serif">/ 10</text>
        </svg>
        <div>
            <p style="font-size:21px; font-weight:700; color:#0d0d1a;
                      margin:0 0 6px; letter-spacing:-0.02em;">{data['scoreLabel']}</p>
            <p style="font-size:14px; color:#666; margin:0; line-height:1.55;">{data['scoreDesc']}</p>
        </div>
    </div>"""
    st.markdown(html, unsafe_allow_html=True)

def render_two_col_section(label_l, items_l, dot_l, text_l,
                            label_r, items_r, dot_r, text_r):
    def build_items(items, bullet_color):
        out = ""
        for item in items:
            out += f"""
            <div class="card-item">
                <span class="card-bullet" style="color:{bullet_color};">&#9679;</span>
                <span>{item}</span>
            </div>"""
        return out

    html = f"""
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-bottom:14px;">
        <div class="result-card" style="margin-bottom:0;">
            <div class="card-header">
                <div class="card-dot" style="background:{dot_l};"></div>
                <span class="card-label" style="color:{text_l};">{label_l}</span>
            </div>
            {build_items(items_l, dot_l)}
        </div>
        <div class="result-card" style="margin-bottom:0;">
            <div class="card-header">
                <div class="card-dot" style="background:{dot_r};"></div>
                <span class="card-label" style="color:{text_r};">{label_r}</span>
            </div>
            {build_items(items_r, dot_r)}
        </div>
    </div>"""
    st.markdown(html, unsafe_allow_html=True)

def render_improvements(items):
    grid = "".join(f'<div class="improve-item">{i}</div>' for i in items)
    html = f"""
    <div class="result-card">
        <div class="card-header">
            <div class="card-dot" style="background:#378ADD;"></div>
            <span class="card-label" style="color:#185FA5;">Resume improvements</span>
        </div>
        <div class="improve-grid">{grid}</div>
    </div>"""
    st.markdown(html, unsafe_allow_html=True)

def render_questions(items):
    qs = "".join(
        f'<div class="question-item"><div class="q-num">{i}</div><span>{q}</span></div>'
        for i, q in enumerate(items, 1)
    )
    html = f"""
    <div class="result-card">
        <div class="card-header">
            <div class="card-dot" style="background:#534AB7;"></div>
            <span class="card-label" style="color:#3C3489;">Mock interview questions</span>
        </div>
        {qs}
    </div>"""
    st.markdown(html, unsafe_allow_html=True)

def analyze(resume, jd):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": f"Resume:\n{resume}\n\nJob Description:\n{jd}"}
        ],
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

# ─── Render ────────────────────────────────────────────────────────

st.markdown(CSS, unsafe_allow_html=True)

st.markdown("""
<div class="app-header">
    <span class="app-title">Meridian</span>
    <span class="app-badge">AI Career Mentor</span>
</div>
<p class="app-sub">Paste your resume and a job description. Get a full match analysis in seconds.</p>
""", unsafe_allow_html=True)

if "results" not in st.session_state:
    st.session_state.results = None

if st.session_state.results is None:
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<span class="col-label">Your Resume</span>', unsafe_allow_html=True)
        resume = st.text_area("resume", height=260,
                              label_visibility="collapsed",
                              placeholder="Paste your full resume text here...")
    with col2:
        st.markdown('<span class="col-label">Job Description</span>', unsafe_allow_html=True)
        jd = st.text_area("jd", height=260,
                          label_visibility="collapsed",
                          placeholder="Paste the full job description here...")

    if st.button("✦  Analyze Match"):
        if not resume.strip() or not jd.strip():
            st.warning("Add both your resume and the job description before analyzing.")
        else:
            with st.spinner("AI is analyzing your profile..."):
                try:
                    st.session_state.results = analyze(resume, jd)
                    st.rerun()
                except json.JSONDecodeError:
                    st.error("Couldn't parse the AI response. Try again.")
                except Exception as e:
                    st.error(f"Something went wrong: {e}")

    st.markdown('<p class="privacy-note">🔒 Your data is never stored</p>',
                unsafe_allow_html=True)

else:
    data = st.session_state.results

    col_back, col_meta = st.columns([1, 1])
    with col_back:
        if st.button("← New analysis"):
            st.session_state.results = None
            st.rerun()
    with col_meta:
        st.markdown('<p class="results-meta">Analyzed just now · gpt-4o-mini</p>',
                    unsafe_allow_html=True)

    st.markdown('<p class="section-title">Your Match Analysis</p>',
                unsafe_allow_html=True)

    render_score_card(data)

    render_two_col_section(
        "Strengths",     data["strengths"], "#1D9E75", "#0F6E56",
        "Skill gaps",    data["gaps"],      "#BA7517", "#854F0B"
    )
    render_improvements(data["improvements"])
    render_questions(data["questions"])
