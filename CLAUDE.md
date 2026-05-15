# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Context

This is the **AI Career Mentor** prototype for the WSU Everett AI-Ready Workforce Certificate Program Innovation Sprint (Problem 1). It is a **60-minute, 5-person team sprint build** — not a production application. Optimize for shipping a working live-browser demo, not for robustness, tests, or extensibility.

The full spec lives in `docs/AI_Career_Mentor_Sprint_Breakdown.pdf`. Read it before making non-trivial changes — it defines the problem, architecture, timeline, and team role boundaries.

**Deviation from the spec:** The PDF specifies Claude (Anthropic) for the AI integration. **This team is using OpenAI instead.** Wherever the PDF says "Claude API / Anthropic SDK / `claude-haiku-4-5-20251001` / `ANTHROPIC_API_KEY`", substitute the OpenAI equivalents below. The rest of the spec (problem, output contract, timeline, roles) still applies.

**What the app does:** User pastes a resume and a job description into two text areas. The app calls the OpenAI API, which returns a structured analysis: match score, strengths, skill gaps, resume improvements, and mock interview questions.

## Setup & Run

```bash
pip install streamlit openai
export OPENAI_API_KEY='sk-...'
streamlit run app.py
```

The `OPENAI_API_KEY` env var is the only configuration. Never hardcode the key.

## Hard Architectural Constraints

These are locked decisions for the sprint — do not change without explicit user direction:

- **Provider:** OpenAI (not Anthropic, despite what the PDF says).
- **SDK:** Official `openai` Python SDK.
- **Model:** A cheap, fast OpenAI chat model (e.g. `gpt-4o-mini` or similar). Optimize for cost and latency — the task is structured text analysis, not reasoning-heavy. Do not jump to a flagship model without a reason.
- **Frontend:** Streamlit only. No JS, no separate backend, no file upload — two plain text areas is the input contract.
- **No dataset / no RAG.** The model is the entire knowledge base. Do not introduce vector stores, embeddings, CSVs, or scraping.
- **Single file is fine.** The spec targets ~20 lines of Python in `app.py`. Avoid premature module-splitting, config files, or abstraction layers.

## Output Contract

The system prompt must produce exactly five markdown sections in this order: `MATCH SCORE: X/10`, `STRENGTHS`, `SKILL GAPS`, `RESUME IMPROVEMENTS`, `MOCK INTERVIEW QUESTIONS`. The starter system prompt is in section 06 of the PDF — treat it as the canonical baseline (it is provider-agnostic and works as-is with OpenAI). Iterate on prompt wording freely, but preserve these section names and their order, since the UI rendering and the demo script depend on them.

## What "Done" Looks Like

End-to-end flow works in a browser: paste resume → paste JD → click submit → see the five-section structured response. The demo is judged live, so prioritize: (1) the call succeeds, (2) the output renders cleanly as markdown, (3) a prepared sample resume/JD pair exists for the live demo. A multi-turn follow-up chat is a documented **stretch goal** — do not build it until the core flow is solid.
