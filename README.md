# ExaCraft: Dynamic Learning Context Adaptation for Personalized Educational Examples

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.1.1-green.svg)
![LangChain](https://img.shields.io/badge/LangChain-Latest-orange.svg)
![LangGraph](https://img.shields.io/badge/LangGraph-Latest-purple.svg)
![Chrome](https://img.shields.io/badge/Chrome-Extension-yellow.svg)
![License](https://img.shields.io/badge/License-MIT-red.svg)

**An AI-powered educational system that generates culturally relevant, personalized examples by adapting to learners' dynamic context in real-time.**

[🎥 Video Demo](https://youtu.be/w1P3n8qEOdg) • [🚀 Quick Start](#quick-start)

</div>

---

## Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Personalization Layers](#personalization-layers)
- [LangGraph Workflow](#langgraph-workflow)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Project Structure](#project-structure)
- [Publication](#publication)
- [License](#license)
- [Citation](#citation)
- [Authors](#authors)

---

## Overview

ExaCraft is an educational AI system that generates personalized examples by combining three personalization layers:

1. **Static User Profile** — location, education, profession, cultural background, learning style, complexity preference
2. **Dynamic Learning Context** — real-time behavioral signals (struggle, mastery, recent topics) tracked per-session
3. **Collaborative Filtering** — effective examples from similar users inform generation for new requests

The system runs as a **Flask REST API** backend and integrates with a **Chrome Extension** (Manifest V3) that lets users highlight text on any webpage and instantly receive a personalized example.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        EXACRAFT SYSTEM                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────┐        ┌──────────────────────────┐     │
│  │  Chrome Extension │◄──────►│  Flask API Server        │     │
│  │  (Manifest V3)    │        │  (localhost:8000)         │     │
│  │                   │        └────────────┬─────────────┘     │
│  │  • Text selection │                     │                    │
│  │  • Profile config │                     ▼                    │
│  │  • Result overlay │        ┌──────────────────────────┐     │
│  └───────────────────┘        │  LangGraph Workflow       │     │
│                               │                          │     │
│                               │  find_similar_users      │     │
│                               │       ↓                  │     │
│                               │  generate_example (LLM)  │     │
│                               │       ↓                  │     │
│                               │  prepare_display         │     │
│                               │       ↓                  │     │
│                               │  ⏸ interrupt             │     │
│                               │       ↓ (feedback)       │     │
│                               │  record_feedback         │     │
│                               │       ↓                  │     │
│                               │  record_history          │     │
│                               │       ↓                  │     │
│                               │  update_indicators       │     │
│                               │       ↓                  │     │
│                               │  calc_thresholds → END   │     │
│                               └────────────┬─────────────┘     │
│                                            │                    │
│                               ┌────────────▼─────────────┐     │
│                               │  Gemini 2.5 Flash (LLM)  │     │
│                               │  via LangChain LCEL       │     │
│                               └──────────────────────────┘     │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   Persistent Storage                      │  │
│  │  user_profiles/     learning_contexts/    data/           │  │
│  │  {user_id}.json     {user_id}.json        feedback/       │  │
│  │                                           example_history/ │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Personalization Layers

### 1. Static User Profile

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

### 2. Dynamic Learning Context

Tracked in `learning_contexts/{user_id}.json`. Updates automatically on every interaction.

**Struggle detection** (simplifies output):
- Same topic requested ≥ 3 times, OR
- ≥ 2 regeneration requests on the same topic within a session

**Mastery detection** (increases complexity):
- ≥ 3 unique topics in the last 5 interactions

**Data retention**: last 20 topics, last 10 sessions, entries older than 7 days are auto-purged.

### 3. Collaborative Filtering

On each generation request, the system:
1. Finds up to 5 similar users (minimum 30% similarity) using a weighted profile comparison across 8 dimensions:

   | Dimension | Weight |
   |---|---|
   | Education level | 20% |
   | Profession | 15% |
   | Complexity preference | 15% |
   | Learning style | 15% |
   | Cultural background | 10% |
   | Location | 10% |
   | Age range | 10% |
   | Interests | 5% |

2. Retrieves up to 3 effective examples (≥ 50% effectiveness score) those users received for the same topic
3. Injects them into the LLM prompt as inspiration — patterns are adapted, not copied

Effectiveness scores are computed from user feedback collected via the LangGraph workflow interrupt.

### Personalization Hierarchy

The LLM applies factors in this strict order:

```
1. Dynamic learning context  (struggle / mastery / recent topics)
2. Collaborative insights     (effective patterns from similar users)
3. Cultural personalization   (location, background)
4. Professional relevance
```

---

## LangGraph Workflow

The full feedback-loop pipeline runs as a **stateful LangGraph graph** with an interrupt for human-in-the-loop feedback collection.

```
START
  │
  ▼
node_00_find_similar_users       Find top-5 similar users; fetch their effective
  │                              examples for the topic (collaborative filtering)
  ▼
node_01_generate_example         LLM call with profile + learning context +
  │                              CF examples (if any). Tracks feedback_influence.
  ▼
node_02_prepare_display          Format example and build display metadata
  │
  ▼
node_03_interrupt_for_feedback   ⏸ PAUSE — returns example to caller with
  │                              thread_id. Awaits difficulty/clarity/usefulness
  │                              ratings (1–5) via /workflows/<thread_id>/resume
  ▼  (resumed with ratings)
node_04_record_feedback          Write ratings to FeedbackManager
  │
  ▼
node_04b_record_example_history  Save example + effectiveness to ExampleHistory
  │                              (feeds future collaborative filtering)
  ▼
node_05_update_indicators        If difficulty ≥ 4, record struggle signal on
  │                              LearningContext
  ▼
node_06_calc_thresholds          Recalculate adaptive struggle/mastery thresholds
  │                              from full feedback history
  ▼
node_07_store_thresholds         Mark workflow complete
  │
 END
```

**Thread management**: each workflow run gets a unique `thread_id`. State is checkpointed via `MemorySaver` by default (configurable to Postgres or SQLite via `CHECKPOINT_TYPE` env var).

---

## Quick Start

### Prerequisites

- Python 3.8+
- Google Chrome
- Gemini API key — [Get one here](https://ai.google.dev/)

### Setup

```bash
# 1. Clone
git clone https://github.com/yourusername/ExaCraft.git
cd ExaCraft

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure API key
echo "GEMINI_API_KEY=your_key_here" > .env

# 4. Start the server
python api_server.py
# → http://localhost:8000
```

### Load the Chrome Extension

1. Go to `chrome://extensions/`
2. Enable **Developer mode**
3. Click **Load unpacked**
4. Select the `D:\MTP` repository root directory

> **Note**: The extension files (`manifest.json`, `background.js`, `content.js`, `popup.html`, `popup.js`) must be in the directory you load. Do not load a subdirectory.

---

## Configuration

All settings are in `config/settings.py` and overridable via environment variables.

| Env Variable | Default | Description |
|---|---|---|
| `GEMINI_API_KEY` | — | Required. Gemini API key |
| `OPENAI_API_KEY` | — | Optional. Enables OpenAI provider |
| `DEFAULT_LLM_PROVIDER` | `gemini` | `gemini` or `openai` |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model name |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model name |
| `LLM_TEMPERATURE` | `0.3` | Generation temperature |
| `LLM_MAX_TOKENS` | `2048` | Max output tokens |
| `API_PORT` | `8000` | Flask server port |
| `CHECKPOINT_TYPE` | `memory` | `memory`, `postgres`, or `sqlite` |
| `DATABASE_URL` | — | Required only for `postgres` checkpoint type |

---

## API Reference

**Base URL**: `http://localhost:8000`

All endpoints return JSON. Success: `{"success": true, ...}`. Error: `{"success": false, "error": "..."}`.

### Generation

#### `POST /generate-adaptive-example`
Generate with dynamic learning context (static personalization + behavior signals).
```json
{
  "topic": "recursion",
  "user_id": "john_doe",
  "user_profile": { "name": "...", "location": "...", "education": "...", "profession": "...", "complexity": "medium" }
}
```

#### `POST /generate-example`
Generate with static profile only (no learning context).
```json
{
  "topic": "recursion",
  "user_profile": { ... }
}
```

#### `POST /generate-collaborative-example`
Full generation with collaborative filtering + learning context.
```json
{
  "topic": "recursion",
  "user_id": "john_doe",
  "user_profile": { ... },
  "use_collaborative_filtering": true
}
```

---

### LangGraph Workflow (Feedback Loop)

#### `POST /workflows/feedback/start`
Start the full feedback-loop workflow. Returns example + `thread_id`.
```json
{
  "user_id": "john_doe",
  "topic": "recursion",
  "mode": "adaptive",
  "use_collaborative_filtering": true
}
```
Response includes `thread_id`, `generated_example`, `feedback_influence`, `similar_users`, `collaborative_metadata`.

#### `POST /workflows/<thread_id>/resume`
Resume a paused workflow with user feedback ratings.
```json
{
  "difficulty_rating": 3,
  "clarity_rating": 4,
  "usefulness_rating": 5
}
```

#### `GET /workflows/<thread_id>/state`
Get current state of a workflow thread.

#### `DELETE /workflows/<thread_id>`
Delete/cancel a workflow thread.

#### `GET /workflows`
List all active workflow threads.

---

### Learning Context

#### `GET /get-learning-context?user_id=john_doe`
Get full learning context (recent topics, struggle/mastery indicators, session history).

#### `POST /start-learning-session`
```json
{ "user_id": "john_doe" }
```

#### `POST /end-learning-session`
```json
{ "user_id": "john_doe" }
```

#### `GET /get-session-status?user_id=john_doe`

#### `POST /record-struggle-signal`
```json
{ "user_id": "john_doe", "topic": "recursion", "signal_type": "regeneration_requested" }
```

---

### Collaborative Filtering

#### `POST /find-similar-users`
```json
{ "user_id": "john_doe", "top_k": 5, "min_similarity": 0.3 }
```

#### `GET /example-history/effective-examples?user_id=john_doe&topic=recursion`

#### `POST /example-history/record-feedback`
```json
{ "user_id": "john_doe", "example_id": "ex_abc123", "accepted": true, "regeneration_requested": false }
```

#### `GET /example-history/statistics?user_id=john_doe`

---

### Profile & Utilities

#### `POST /sync-profile`
Sync extension profile (flat format) to server filesystem.
```json
{ "profile": { "name": "...", "user_id": "...", ... } }
```

#### `POST /validate-profile`
```json
{ "profile": { ... } }
```

#### `GET /health`
Server health check and endpoint listing.

#### `GET /api-info`
Provider info, model config, enabled phases.

#### `GET /test-example`
Quick test generation (GET, no body required).

---

## Project Structure

```
ExaCraft/
│
├── api_server.py                  # Flask REST API — all endpoints
├── manifest.json                  # Chrome extension manifest (V3)
├── background.js                  # Extension service worker
├── content.js                     # Extension content script (result overlay)
├── popup.html / popup.js          # Extension popup (profile configuration)
│
├── core/
│   ├── example_generator.py       # ExampleGenerator — LLM chain + all generation methods
│   ├── user_profile.py            # UserProfile — static profile load/save/summary
│   ├── learning_context.py        # LearningContext — session tracking, struggle/mastery detection
│   ├── feedback_manager.py        # FeedbackManager — ratings storage + adaptive thresholds
│   ├── user_similarity.py         # UserSimilarity — weighted profile similarity for CF
│   ├── example_history.py         # ExampleHistory — example records + effectiveness scoring
│   ├── llm_provider.py            # LLMProviderFactory — Gemini / OpenAI abstraction
│   ├── workflow_graphs.py         # LangGraph graph builders
│   ├── workflow_nodes.py          # LangGraph node implementations
│   ├── workflow_manager.py        # WorkflowManager — thread lifecycle, start/resume
│   ├── workflow_state.py          # TypedDict state schemas
│   ├── phase2/                    # Reserved for Phase 2 features
│   ├── phase3/                    # Reserved for Phase 3 features
│   └── utils/
│       └── validators.py          # Request validation helpers
│
├── config/
│   └── settings.py                # All configuration + env variable loading
│
├── data/
│   ├── feedback/                  # Per-user feedback history
│   ├── example_history/           # Per-user generated example records
│   └── similarity_cache.json      # Cached similarity scores
│
├── user_profiles/                 # Per-user static profile JSON files
├── learning_contexts/             # Per-user dynamic learning context JSON files
├── logs/                          # Server logs
│
├── requirements.txt               # Python dependencies
├── .env                           # API keys (gitignored)
├── CLAUDE.md                      # Codebase guidance for Claude Code
└── README.md                      # This file
```

---

## Publication

**Title**: ExaCraft: Dynamic Learning Context Adaptation for Personalized Educational Examples

**Authors**: Akaash Chatterjee, Suman Kundu

**Affiliation**: Indian Institute of Technology Jodhpur

**Conference**: ACM India Joint International Conference on Data Science and Management of Data (CODS-COMAD 2025) — Demo Track

**Video Demo**: [https://youtu.be/w1P3n8qEOdg](https://youtu.be/w1P3n8qEOdg)

### Abstract

ExaCraft presents a novel approach to generating personalized educational examples through a hybrid personalization framework combining static user profiles with dynamic learning context adaptation and collaborative filtering. The system implements a three-component architecture consisting of a Chrome browser extension, Flask API server, and a stateful LangGraph workflow with human-in-the-loop feedback collection. Real-time behavioral analytics detect struggle indicators and mastery patterns, automatically adjusting example complexity while maintaining cultural and professional relevance. Collaborative filtering leverages example effectiveness data from similar users to further improve generation quality. Cross-session continuity enables long-term learning progression tracking with persistent context retention.

---

## License

MIT License — Copyright (c) 2025 Akaash Chatterjee, Suman Kundu

---

## Citation

```bibtex
@inproceedings{chatterjee2025exacraft,
  title={ExaCraft: Dynamic Learning Context Adaptation for Personalized Educational Examples},
  author={Chatterjee, Akaash and Kundu, Suman},
  booktitle={Proceedings of the ACM India Joint International Conference on Data Science and Management of Data (CODS-COMAD)},
  year={2025},
  organization={ACM},
  note={Demo Track}
}
```

---

## Authors

**Akaash Chatterjee** — Indian Institute of Technology Jodhpur

**Suman Kundu** — Indian Institute of Technology Jodhpur

---

<div align="center">

[⬆ Back to Top](#exacraft-dynamic-learning-context-adaptation-for-personalized-educational-examples)

</div>
