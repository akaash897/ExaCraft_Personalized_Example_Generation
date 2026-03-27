"""
Feedback Store Module
Indexed storage for user feedback history, subject tag indexes,
learning patterns, and accept insights.
"""

import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

FEEDBACK_DIR        = Path("data/feedback_history")
LEARNING_PATTERNS_DIR = Path("data/learning_patterns")
ACCEPT_INSIGHTS_DIR = Path("data/accept_insights")

# Ensure directories exist on import
for _d in [FEEDBACK_DIR, LEARNING_PATTERNS_DIR, ACCEPT_INSIGHTS_DIR]:
    _d.mkdir(parents=True, exist_ok=True)


# ─── Feedback History ─────────────────────────────────────────────────────────

def _feedback_path(user_id: str) -> Path:
    return FEEDBACK_DIR / f"{user_id}.json"


def _default_store(user_id: str) -> dict:
    return {
        "user_id": user_id,
        "entries": [],
        "subject_tag_index": {},
        "feedback_by_recency": [],
        "subject_tag_statistics": {}
    }


def _load_store(user_id: str) -> dict:
    path = _feedback_path(user_id)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: failed to load feedback store for {user_id}: {e}")
    return _default_store(user_id)


def _save_store(user_id: str, store: dict):
    path = _feedback_path(user_id)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(store, f, indent=2)
    except Exception as e:
        print(f"Warning: failed to save feedback store for {user_id}: {e}")


def get_feedback_history(user_id: str) -> dict:
    return _load_store(user_id)


def get_all_feedback_entries(user_id: str) -> list:
    return _load_store(user_id).get("entries", [])


def get_recent_feedback(user_id: str, days: int = 7) -> list:
    cutoff = datetime.now() - timedelta(days=days)
    result = []
    for entry in get_all_feedback_entries(user_id):
        try:
            ts = datetime.fromisoformat(entry.get("timestamp", "2000-01-01"))
            if ts >= cutoff:
                result.append(entry)
        except Exception:
            pass
    return result


def get_feedback_by_subject_tag(user_id: str, subject_tag: str) -> list:
    store = _load_store(user_id)
    tagged_ids = set(store.get("subject_tag_index", {}).get(subject_tag, []))
    return [e for e in store.get("entries", []) if e.get("example_id") in tagged_ids]


def load_subject_statistics(user_id: str) -> dict:
    return _load_store(user_id).get("subject_tag_statistics", {})


def save_nl_feedback_entry(user_id: str, feedback_record: dict) -> bool:
    """
    Save a natural-language feedback entry.

    Expected record shape:
    {
        entry_id, example_id, topic, subject_tag,
        user_feedback_text,          # replaces numerical ratings
        agent_decision,              # "regenerate" | "accept" | "flag_pattern" | "skipped"
        regeneration_requested,
        regeneration_instruction,
        timestamp
    }
    """
    try:
        store = _load_store(user_id)
        store.setdefault("entries", []).append(feedback_record)
        _save_store(user_id, store)
        return True
    except Exception as e:
        print(f"Warning: failed to save NL feedback entry for {user_id}: {e}")
        return False


def update_subject_tag_index(user_id: str, example_id: str, subject_tag: str) -> bool:
    try:
        store = _load_store(user_id)
        tag_list = store.setdefault("subject_tag_index", {}).setdefault(subject_tag, [])
        if example_id not in tag_list:
            tag_list.append(example_id)
        _save_store(user_id, store)
        return True
    except Exception as e:
        print(f"Warning: failed to update subject tag index for {user_id}: {e}")
        return False


def update_feedback_by_recency_index(user_id: str, example_id: str) -> bool:
    try:
        store = _load_store(user_id)
        recency = store.setdefault("feedback_by_recency", [])
        if example_id in recency:
            recency.remove(example_id)
        recency.insert(0, example_id)
        store["feedback_by_recency"] = recency[:200]
        _save_store(user_id, store)
        return True
    except Exception as e:
        print(f"Warning: failed to update recency index for {user_id}: {e}")
        return False


def update_subject_tag_statistics(user_id: str, subject_tag: str, agent_decision: str) -> dict:
    """
    Recalculate stats for subject_tag from all entries.
    effectiveness_score: regenerate→0.3, accept→0.8, flag_pattern→0.5, skipped→0.5
    """
    DECISION_SCORES = {
        "regenerate": 0.3,
        "accept": 0.8,
        "flag_pattern": 0.5,
        "skipped": 0.5
    }
    try:
        store = _load_store(user_id)
        entries = store.get("entries", [])
        tagged = [e for e in entries if e.get("subject_tag") == subject_tag]

        if not tagged:
            stats = {"count": 0, "avg_effectiveness": 0.0, "last_updated": datetime.now().isoformat()}
        else:
            scores = [DECISION_SCORES.get(e.get("agent_decision", "skipped"), 0.5) for e in tagged]
            stats = {
                "count": len(tagged),
                "avg_effectiveness": round(sum(scores) / len(scores), 4),
                "last_updated": datetime.now().isoformat()
            }

        store.setdefault("subject_tag_statistics", {})[subject_tag] = stats
        _save_store(user_id, store)
        return stats
    except Exception as e:
        print(f"Warning: failed to update subject tag statistics for {user_id}: {e}")
        return {}


# ─── Learning Patterns ────────────────────────────────────────────────────────

def _patterns_path(user_id: str) -> Path:
    return LEARNING_PATTERNS_DIR / f"{user_id}.json"


def load_learning_patterns(user_id: str) -> dict:
    """Load persistent learning trait patterns for user."""
    path = _patterns_path(user_id)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: failed to load learning patterns for {user_id}: {e}")
    return {"user_id": user_id, "patterns": []}


def append_learning_pattern(user_id: str, pattern_type: str, observation: str, example_id: str = "", source: str = "") -> bool:
    """Append a new persistent learning trait."""
    try:
        data = load_learning_patterns(user_id)
        entry = {
            "pattern_id": f"pat_{uuid.uuid4().hex[:10]}",
            "pattern_type": pattern_type,
            "observation": observation,
            "example_id": example_id,
            "timestamp": datetime.now().isoformat()
        }
        if source:
            entry["source"] = source
        data["patterns"].append(entry)
        path = _patterns_path(user_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"Warning: failed to append learning pattern for {user_id}: {e}")
        return False


# ─── Accept Insights ──────────────────────────────────────────────────────────

def _insights_path(user_id: str) -> Path:
    return ACCEPT_INSIGHTS_DIR / f"{user_id}.json"


def load_accept_insights(user_id: str) -> dict:
    """Load positive/neutral feedback insights for user."""
    path = _insights_path(user_id)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: failed to load accept insights for {user_id}: {e}")
    return {"user_id": user_id, "insights": []}


def append_accept_insight(user_id: str, insight: str, example_id: str = "") -> bool:
    """Append a new positive/neutral feedback insight."""
    try:
        data = load_accept_insights(user_id)
        data["insights"].append({
            "insight_id": f"ins_{uuid.uuid4().hex[:10]}",
            "insight": insight,
            "example_id": example_id,
            "timestamp": datetime.now().isoformat()
        })
        # Keep last 50 insights
        data["insights"] = data["insights"][-50:]
        path = _insights_path(user_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"Warning: failed to append accept insight for {user_id}: {e}")
        return False
