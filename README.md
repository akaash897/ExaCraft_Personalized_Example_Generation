# AdaCraft: Iterative Adaptive Personalization of Educational Examples via Agentic Feedback Loops

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.1.1-green.svg)
![LangGraph](https://img.shields.io/badge/LangGraph-Latest-purple.svg)
![LangChain](https://img.shields.io/badge/LangChain-Latest-orange.svg)
![Chrome](https://img.shields.io/badge/Chrome-Extension-yellow.svg)
![License](https://img.shields.io/badge/License-MIT-red.svg)

**An agentic system that generates personalized educational examples and continuously refines them based on natural-language feedback — without explicit rating prompts.**

[🎥 Video Demo](https://youtu.be/w1P3n8qEOdg) • [🚀 Quick Start](#quick-start)

</div>

---

## Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Capability Layers](#capability-layers)
- [Agentic Workflow](#agentic-workflow)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Evaluation](#evaluation)
- [Project Structure](#project-structure)
- [Publication](#publication)
- [License](#license)
- [Citation](#citation)
- [Authors](#authors)

---

## Overview

AdaCraft is an agentic system that generates contextually grounded educational examples on demand via a Chrome Extension. It addresses a fundamental gap in personalized educational AI: most systems treat personalization as a static, one-shot operation — reading a profile once, generating a response, and stopping. AdaCraft closes this gap through three capability layers:

1. **Static User Profile** — demographic, professional, and complexity preferences configured once via the extension
2. **Context Manager Agent** — retrieves and synthesizes cross-session learning patterns into a targeted personalization instruction before each generation
3. **Adaptive Response Agent** — interprets free-form natural-language feedback and autonomously decides whether to regenerate the example with targeted modifications, record a session insight, or persist a new long-term learning pattern

The system runs as a **Flask REST API** (v5.0.0) backend with a **Chrome Extension** (Manifest V3) frontend. Users interact entirely in natural language — no rating sliders or structured forms required.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         ADACRAFT SYSTEM                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────┐        ┌──────────────────────────┐     │
│  │  Chrome Extension │◄──────►│  Flask API Server        │     │
│  │  (Manifest V3)    │        │  (localhost:8000)         │     │
│  │                   │        └────────────┬─────────────┘     │
│  │  • Concept select │                     │                    │
│  │  • Profile config │                     ▼                    │
│  │  • Inline overlay │        ┌──────────────────────────┐     │
│  │  • NL feedback    │        │  LangGraph Workflow       │     │
│  └───────────────────┘        │                          │     │
│                               │  node_load_profile       │     │
│                               │       ↓                  │     │
│                               │  node_build_context      │     │
│                               │  (Context Mgr Agent)     │     │
│                               │       ↓                  │     │
│                               │  node_generate (LLM)     │     │
│                               │       ↓                  │     │
│                               │  node_format_and_save    │     │
│                               │       ↓                  │     │
│                               │  ⏸ node_user_review      │     │
│                               │       ↓ (NL feedback)    │     │
│                               │  node_process_feedback   │     │
│                               │  (Adaptive Resp. Agent)  │     │
│                               │  [loop ≤3 cycles / END]  │     │
│                               └────────────┬─────────────┘     │
│                                            │                    │
│                               ┌────────────▼─────────────┐     │
│                               │  Gemini / OpenAI (LLM)   │     │
│                               │  via LangChain LCEL       │     │
│                               └──────────────────────────┘     │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   Persistent Storage (JSON)               │  │
│  │  user_profiles/     learning_contexts/    data/           │  │
│  │  {user_id}.json     {user_id}.json        feedback/       │  │
│  │                                           example_history/ │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Capability Layers

### Layer 1 — Static User Profile

Configured once via the extension popup and synced to `user_profiles/{user_id}.json`.

| Field | Values |
|---|---|
| Name, Location | Free text |
| Education level | `high_school` / `undergraduate` / `graduate` / `professional` |
| Cultural background | Free text |
| Profession | Free text |
| Age range | `18-25` / `26-35` / `36-50` / `50+` |
| Interests | List |
| Complexity preference | `simple` / `medium` / `advanced` |
| Learning style | `theoretical` / `practical` / `visual` |

### Layer 2 — Context Manager Agent

For returning users, the Context Manager Agent runs before generation. It:

1. Resolves 1–3 canonical subject tags for the current topic (e.g., `"Newton's Second Law"` → `{physics, mechanics, forces}`)
2. Queries the user's history via four tools:

| Tool | Action |
|---|---|
| `Get Example By Tag` | Returns recent stored examples filtered by each resolved tag |
| `Get Linked Feedback` | Drills into a specific example to retrieve linked patterns and insights |
| `Get Global Signals` | Fallback — returns recent global patterns when no tag-matched history exists |
| `Emit Instruction` | Terminal action — writes a 2–3 sentence directive into the workflow state |

3. Emits a targeted instruction (e.g., *"Use medical equipment analogies. This user struggles with abstract formulas; ground all quantities in clinical measurements."*) passed to the generation node

A **domain-bleed guard** suppresses patterns whose subject tags share no overlap with the current topic, preventing unrelated prior sessions from contaminating the instruction.

First-time users bypass this step entirely — the cold-start path goes directly to generation.

### Layer 3 — Adaptive Response Agent

After the user submits natural-language feedback, the Adaptive Response Agent selects from three tools:

| Tool | Action |
|---|---|
| `Regenerate Example` | Triggers regeneration with a targeted rewrite directive; routes back to generation (up to 3 cycles) |
| `Accept Example` | Logs positive/neutral feedback as a session insight for future context retrieval |
| `Flag Pattern` | Persists a new long-term learning trait that influences all future sessions |

The agent can call multiple tools per turn. For example, *"too abstract, I'm a nurse"* triggers both `Regenerate Example` (with a clinical framing instruction) and `Flag Pattern` (records the professional domain preference).

### Prompt Assembly Order

```
1. Profile summary           (from node_load_profile)
2. Context Manager instruction (from node_build_context, if returning user)
3. Regeneration instruction  (from prior Adaptive Response Agent call, if looping)
```

---

## Agentic Workflow

AdaCraft's core is a six-node LangGraph graph with a human-in-the-loop interrupt.

```
START
  │
  ▼
node_load_profile        Load profile from user_profiles/{user_id}.json →
  │                      produce profile_summary.
  │                      eval_mode=t0: skips profile (generic baseline).
  ▼
node_build_context       Resolve topic tags → invoke Context Manager Agent →
  │                      produce context_instruction.
  │                      First-time users: red branch → skip directly to generate.
  │                      Returning users: green branch → agent runs.
  │                      eval_mode t0/t1: skipped entirely.
  ▼
node_generate            LLM call: profile_summary + context_instruction +
  │                      regeneration_instruction (if looping, cleared after use).
  ▼
node_format_and_save     Save example to ExampleHistory with subject tags,
  │                      profile snapshot, and session metadata.
  ▼
node_user_review         ⏸ PAUSE — return example + thread_id to caller.
  │                      Await natural-language feedback via
  │                      POST /workflows/<thread_id>/resume
  ▼  (resumed with user_feedback_text)
node_process_feedback    No feedback / acceptance → END (green branch).
  │                      Feedback present → invoke Adaptive Response Agent (red branch).
  │                      regenerate=True: loop back to node_generate (max 3×)
  │                      accept/flag_pattern: write to feedback_store → END
  │
 END
```

**State persistence**: in-session state is checkpointed by LangGraph's `MemorySaver`, keyed by `thread_id`. Cross-session data is stored in three per-user JSON structures: feedback history, learning patterns (persistent traits), and accepted insights (capped at 50 entries to prevent context overflow).

---

## Quick Start

### Prerequisites

- Python 3.8+
- Google Chrome
- At least one LLM API key:
  - Gemini: [ai.google.dev](https://ai.google.dev/)
  - OpenAI: [platform.openai.com](https://platform.openai.com/)

### Setup

```bash
# 1. Clone
git clone https://github.com/yourusername/AdaCraft.git
cd AdaCraft

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
# Create a .env file:
GEMINI_API_KEY=your_gemini_key_here
OPENAI_API_KEY=your_openai_key_here    # optional
DEFAULT_LLM_PROVIDER=gemini            # gemini | openai

# 4. Start the server
python api_server.py
# → http://localhost:8000
```

### Load the Chrome Extension

1. Go to `chrome://extensions/`
2. Enable **Developer mode**
3. Click **Load unpacked**
4. Select the repository root directory

> **Note**: `manifest.json`, `background.js`, `content.js`, `popup.html`, and `popup.js` must all be in the loaded directory root.

---

## Configuration

All settings are in `config/settings.py` and overridable via environment variables.

| Env Variable | Default | Description |
|---|---|---|
| `GEMINI_API_KEY` | — | Required if using Gemini provider |
| `OPENAI_API_KEY` | — | Required if using OpenAI provider |
| `DEFAULT_LLM_PROVIDER` | `gemini` | `gemini` or `openai` |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model name |
| `OPENAI_MODEL` | `gpt-5-nano` | OpenAI model name |
| `LLM_TEMPERATURE` | `0.3` | Generation temperature |
| `LLM_MAX_TOKENS` | `2048` | Max output tokens |
| `API_PORT` | `8000` | Flask server port |
| `CHECKPOINT_TYPE` | `memory` | `memory`, `postgres`, or `sqlite` |
| `DATABASE_URL` | — | Required only for `postgres` checkpoint type |

---

## API Reference

**Base URL**: `http://localhost:8000`

All endpoints return JSON. Success: `{"success": true, ...}`. Error: `{"success": false, "error": "..."}`.

---

### Workflow (Feedback Loop)

#### `POST /workflows/feedback/start`

Start a new generation workflow. Returns the example and a `thread_id` for follow-up.

```json
{
  "user_id": "john_doe",
  "topic": "Newton's Second Law",
  "provider": "openai"
}
```

Response:
```json
{
  "success": true,
  "thread_id": "abc-123",
  "generated_example": "...",
  "status": "awaiting_feedback"
}
```

#### `POST /workflows/<thread_id>/resume`

Resume a paused workflow with natural-language feedback. Pass an empty string to accept and complete.

```json
{
  "user_feedback_text": "Too abstract — can you use a cooking analogy?"
}
```

Response when regenerating:
```json
{
  "status": "awaiting_feedback",
  "regeneration_requested": true,
  "generated_example": "...",
  "thread_id": "abc-123"
}
```

Response when complete:
```json
{
  "status": "completed",
  "feedback_processed": true
}
```

#### `GET /workflows/<thread_id>/state`

Get current state of a workflow thread.

#### `DELETE /workflows/<thread_id>`

Cancel and delete a workflow thread.

#### `GET /workflows`

List all active workflow threads.

---

### Profile & Utilities

#### `POST /sync-profile`

Sync an extension profile (flat key format) to the server filesystem.

```json
{
  "profile": {
    "name": "Priya Sharma",
    "user_id": "priya_sharma",
    "location": "Chennai",
    "education": "professional",
    "profession": "Nurse",
    "cultural_background": "South Indian",
    "learning_style": "practical",
    "complexity": "simple"
  }
}
```

#### `POST /validate-profile`

Validate a profile object without saving it.

#### `GET /health`

Server health check with endpoint listing and workflow manager status.

#### `GET /api-info`

Provider info, model config, and full Adaptive Response Agent documentation.

---

## Evaluation

AdaCraft is evaluated via a **four-tier ablation protocol** that isolates each capability layer's independent contribution, paired with **three feedback-loop convergence metrics** that characterize how the system improves across a session.

### Ablation Tiers

| Tier | Profile | Context Mgr | Feedback & Patterns |
|---|---|---|---|
| T0: Generic LLM | — | — | — |
| T1: T0 + Profile | ✓ | — | — |
| T2: T1 + Context Manager | ✓ | ✓ | — |
| T3: Full AdaCraft | ✓ | ✓ | ✓ |

### Five-Axis Rubric

Each example is scored 1–5 on five axes by an LLM judge (G-Eval chain-of-thought + Prometheus 2 rubric injection):

| Axis | Weight | Description |
|---|---|---|
| Personalization Fidelity (PF) | 0.20 | Reflects cultural background, occupation, and domain |
| Complexity Calibration (CC) | 0.20 | Depth and vocabulary match requested complexity |
| Conceptual Accuracy (CA) | 0.30 | Factually and logically correct |
| Pedagogical Clarity (PC) | 0.20 | Clear, structured, and learner-friendly |
| Domain Appropriateness (DA) | 0.10 | Stays within user's domain without cross-domain bleed |

Composite: `C = 0.20·PF + 0.20·CC + 0.30·CA + 0.20·PC + 0.10·DA`

### Feedback-Loop Convergence Metrics

| Metric | Definition |
|---|---|
| **FCR** (Feedback Compliance Rate) | Fraction of regenerations that correctly address the prior critique (reported at @3 and @4 thresholds) |
| **LUR** (Loop Utilization Rate) | Fraction of T3 sessions where the agent triggered at least one regeneration in response to a complaint |
| **PPU** (Pattern Persistence Utilization) | Mean PF delta between warm-start T3 and warm-start T1 on the *initial* generation — measures whether stored patterns improve first-generation quality |

### Results Summary

| Run | T0 | T1 | T2 | T3 | T0→T3 Δ |
|---|---|---|---|---|---|
| DeepSeek V3.2 | 4.257 | 4.809 | 4.859 | 4.888 | +0.631 |
| GPT-5-nano | 3.712 | 4.388 | 4.791 | 4.981 | +1.269 |

FCR@4 ≥ 0.891 and LUR ≥ 0.938 across both providers. Inter-judge Cohen's κ ≥ 0.607 (GPT-4.1-nano vs. Llama 3.3 70B on 20% subsample).

Evaluation scripts are in the `eval/` directory. Run:

```bash
python eval/seed_warm_start.py           # seed warm-start users first
python eval/run_evaluation.py --run-tag myrun
python eval/analysis.py --results-dir eval/results/myrun --output-dir eval/figures/myrun
```

---

## Project Structure

```
AdaCraft/
│
├── api_server.py                  # Flask REST API — all endpoints (v5.0.0)
├── manifest.json                  # Chrome extension manifest (V3)
├── background.js                  # Extension service worker
├── content.js                     # Extension content script (inline overlay)
├── popup.html / popup.js          # Extension popup (profile configuration)
│
├── core/
│   ├── workflow_graphs.py         # LangGraph graph builder (build_primary_agent_graph)
│   ├── workflow_nodes.py          # 6 node implementations
│   ├── workflow_manager.py        # WorkflowManager — thread lifecycle (start / resume)
│   ├── workflow_state.py          # TypedDict state schema (PersonalizedGenerationState)
│   ├── adaptive_response_agent.py # Adaptive Response Agent — 3 tools
│   ├── context_manager_agent.py   # Context Manager Agent — 4 tools
│   ├── feedback_store.py          # Module-level functions — patterns + accept insights
│   ├── example_generator.py       # ExampleGenerator + profile validation helpers
│   ├── user_profile.py            # UserProfile — static profile load/save/summary
│   ├── learning_context.py        # LearningContext — session tracking, struggle/mastery
│   ├── example_history.py         # ExampleHistory — example records + tag indexing
│   ├── subject_tag_metadata.py    # Canonical subject tag taxonomy
│   ├── llm_provider.py            # LLMProviderFactory — Gemini / OpenAI abstraction
│   └── utils/
│       └── validators.py          # Request validation helpers
│
├── eval/
│   ├── run_evaluation.py          # Main evaluation runner (--run-tag namespaces results)
│   ├── analysis.py                # Full stats: Friedman, Wilcoxon, FCR/LUR/PPU, Cohen's κ
│   ├── baseline_runners.py        # T0–T3 tier runners
│   ├── seed_warm_start.py         # Seeds warm-start users before eval runs
│   ├── synthetic_profiles.py      # 8 synthetic users × 4 topics
│   └── llm_judge.py               # LLM-as-judge scoring (GPT-4.1-nano + Llama 3.3 70B)
│
├── config/
│   └── settings.py                # All configuration + env variable loading
│
├── data/
│   ├── feedback/                  # Per-user learning patterns + accept insights
│   └── example_history/           # Per-user generated example records
│
├── user_profiles/                 # Per-user static profile JSON files
├── learning_contexts/             # Per-user dynamic learning context JSON files
├── Research_Paper/                # LaTeX paper source
├── requirements.txt               # Python dependencies
├── .env                           # API keys (gitignored)
└── CLAUDE.md                      # Codebase guidance for Claude Code
```

---

## Publication

**Title**: AdaCraft: Iterative Adaptive Personalization of Educational Examples via Agentic Feedback Loops

**Authors**: Akaash Chatterjee, Suman Kundu

**Affiliation**: Indian Institute of Technology Jodhpur

**Video Demo**: [https://youtu.be/w1P3n8qEOdg](https://youtu.be/w1P3n8qEOdg)

### Abstract

AdaCraft is an agentic system that generates personalized educational examples through a multi-agent LangGraph workflow and continuously refines them based on natural-language feedback. The system operates through three capability layers: (1) a static user profile capturing demographic and complexity preferences, (2) a Context Manager Agent that retrieves historical learning patterns and synthesizes them into a targeted personalization instruction before each generation, and (3) an Adaptive Response Agent that interprets free-form user feedback and autonomously decides whether to regenerate the example, record a session insight, or persist a new long-term learning pattern. Evaluated via a four-tier ablation protocol (T0: generic baseline, T1: +profile, T2: +context manager, T3: full system) across two generator configurations (DeepSeek V3.2 and GPT-5-nano), the full system improves over the generic baseline by up to +1.269 composite points, with FCR@4 ≥ 0.891 and LUR ≥ 0.938 across both providers.

---

## License

MIT License — Copyright (c) 2025 Akaash Chatterjee, Suman Kundu

---

## Citation

```bibtex
@article{chatterjee2025adacraft,
  title={AdaCraft: Iterative Adaptive Personalization of Educational Examples via Agentic Feedback Loops},
  author={Chatterjee, Akaash and Kundu, Suman},
  year={2025}
}
```

---

## Authors

**Akaash Chatterjee** — Indian Institute of Technology Jodhpur

**Suman Kundu** — Indian Institute of Technology Jodhpur

---

<div align="center">

[⬆ Back to Top](#adacraft-iterative-adaptive-personalization-of-educational-examples-via-agentic-feedback-loops)

</div>
