"""
Baseline Runners — Tier Execution
Implements run_tier0 through run_tier3 for the ablation study.

Each tier maps to an eval_mode value that gates capability layers:
  T0 (t0): Generic LLM — no profile, no context, no feedback processing
  T1 (t1): Static Profile — profile injected, no context manager, no feedback
  T2 (t2): +ContextManager — profile + context manager, no feedback loop
  T3 (t3/None): Full ExaCraft — all capabilities enabled

Returns a dict with:
  - generated_example: str
  - rounds: List[Dict] — per-round {example, feedback_given, loop_count}
  - error: Optional[str]
"""

import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, Any, Optional, List
from core.workflow_manager import WorkflowManager
from core.user_profile import UserProfile
from langgraph.checkpoint.memory import MemorySaver
from eval.synthetic_profiles import get_feedback_for_round

# Shared manager instance (one per run to preserve memory)
_manager: Optional[WorkflowManager] = None


def _get_manager() -> WorkflowManager:
    global _manager
    if _manager is None:
        _manager = WorkflowManager(MemorySaver())
    return _manager


def reset_manager() -> None:
    """Call between tiers or before a fresh run to clear thread state."""
    global _manager
    _manager = None


def _check_t3_contamination(user_id: str, tier: str) -> None:
    """
    Warn if T2 is about to run but T3 has already written learning patterns
    for this user. This only occurs on partial re-runs (e.g. --tiers t2 after
    t3 already ran). It does not affect a clean first-run in default order.
    """
    if tier != "t2":
        return
    import os, json
    patterns_file = os.path.join("data", "learning_patterns", f"{user_id}.json")
    if not os.path.exists(patterns_file):
        return
    try:
        with open(patterns_file) as f:
            data = json.load(f)
        patterns = data.get("patterns", [])
        # Seeded patterns (from seed_warm_start.py) have pattern_type in
        # ["domain_preference", "complexity_preference"] with source="seed".
        # T3-generated patterns have source="adaptive_response_agent" or no source.
        t3_patterns = [p for p in patterns if p.get("source") != "seed"]
        if t3_patterns:
            print(
                f"  [WARN] T2 re-run contamination risk: {user_id} has "
                f"{len(t3_patterns)} T3-generated pattern(s) in learning_patterns. "
                f"ContextManager will see these. Re-seed warm users or run tiers "
                f"in order (t0→t1→t2→t3) to avoid cross-tier contamination."
            )
    except Exception:
        pass


def _ensure_profile_exists(profile: Dict[str, Any]) -> None:
    """Write profile to disk so workflow can load it."""
    up = UserProfile(user_id=profile["user_id"])
    # Only update if the profile fields aren't set yet
    current = up.profile_data or {}
    update_fields = {
        "name": profile["name"],
        "role": profile["role"],
        "education_level": profile["education_level"],
        "profession": profile["profession"],
        "location": profile["location"],
        "cultural_background": profile["cultural_background"],
        "learning_style": profile["learning_style"],
        "complexity": profile["complexity"],
    }
    for k, v in update_fields.items():
        current[k] = v
    up.update_profile(current)


def run_tier(
    tier: str,
    profile: Dict[str, Any],
    topic: str,
    num_feedback_rounds: int = 3,
    provider: str = None,
    delay_seconds: float = 1.5,
) -> Dict[str, Any]:
    """
    Generic tier runner.

    tier: "t0" | "t1" | "t2" | "t3"
    profile: synthetic user profile dict
    topic: topic string
    num_feedback_rounds: how many feedback rounds to simulate
    """
    manager = _get_manager()
    user_id = profile["user_id"]
    eval_mode = tier if tier != "t3" else None  # t3 = full system (no gate)

    # Warn if T2 re-run would see T3's feedback patterns
    _check_t3_contamination(user_id, tier)

    # Ensure profile exists on disk for tiers that use it
    if tier != "t0":
        try:
            _ensure_profile_exists(profile)
        except Exception as e:
            return {"error": f"Profile setup failed: {e}", "rounds": []}

    # Start workflow
    try:
        start_result = manager.start_feedback_workflow(
            user_id=user_id,
            topic=topic,
            provider=provider,
            eval_mode=eval_mode,
        )
    except Exception as e:
        return {"error": f"start_feedback_workflow failed: {e}", "rounds": []}

    if not start_result.get("success"):
        return {
            "error": start_result.get("error") or start_result.get("error_message"),
            "rounds": [],
        }

    thread_id = start_result["thread_id"]
    rounds: List[Dict[str, Any]] = []

    # Round 0 — initial example (no feedback yet)
    rounds.append({
        "round": 0,
        "example": start_result.get("generated_example", ""),
        "example_id": start_result.get("example_id"),
        "feedback_given": None,
        "loop_count": 0,
        "status": "awaiting_feedback",
    })

    # Feedback rounds
    for r in range(1, num_feedback_rounds + 1):
        feedback_text = get_feedback_for_round(user_id, r)
        time.sleep(delay_seconds)  # rate limiting

        try:
            resume_result = manager.resume_feedback_workflow(
                thread_id=thread_id,
                user_feedback_text=feedback_text,
            )
        except Exception as e:
            rounds.append({
                "round": r,
                "error": str(e),
                "feedback_given": feedback_text,
            })
            break

        round_data = {
            "round": r,
            "feedback_given": feedback_text,
            "status": resume_result.get("status"),
            "loop_count": resume_result.get("loop_count", 0),
        }
        round_data["agent_action"] = resume_result.get("last_agent_action")

        if resume_result.get("status") == "awaiting_feedback":
            round_data["example"] = resume_result.get("generated_example", "")
            round_data["example_id"] = resume_result.get("example_id")
        else:
            # completed — no new example
            round_data["feedback_processed"] = resume_result.get("feedback_processed")

        rounds.append(round_data)

        if resume_result.get("status") == "completed":
            # For T3 with remaining rounds: start a fresh thread so the next
            # scripted round (e.g. FP) can be sent to a live workflow.
            # Each round after a completion is an independent agent decision test;
            # persisted state (patterns, insights) carries over via JSON files.
            if tier == "t3" and r < num_feedback_rounds:
                try:
                    fresh = manager.start_feedback_workflow(
                        user_id=user_id,
                        topic=topic,
                        provider=provider,
                        eval_mode=eval_mode,
                    )
                    if fresh.get("success"):
                        thread_id = fresh["thread_id"]
                    else:
                        break
                except Exception:
                    break
            else:
                break

        # For t0/t1/t2 — no real feedback loop, workflow completes after first resume
        if tier in ("t0", "t1", "t2") and r >= 1:
            break

    return {
        "tier": tier,
        "user_id": user_id,
        "topic": topic,
        "thread_id": thread_id,
        "initial_example": rounds[0]["example"] if rounds else "",
        "final_example": _get_final_example(rounds),
        "rounds": rounds,
        "context_instruction": start_result.get("context_instruction"),
        "error": None,
    }


def _get_final_example(rounds: List[Dict]) -> str:
    """Return the last generated example across all rounds."""
    for r in reversed(rounds):
        if r.get("example"):
            return r["example"]
    return ""


def run_tier0(profile: Dict[str, Any], topic: str, **kwargs) -> Dict[str, Any]:
    return run_tier("t0", profile, topic, num_feedback_rounds=1, **kwargs)


def run_tier1(profile: Dict[str, Any], topic: str, **kwargs) -> Dict[str, Any]:
    return run_tier("t1", profile, topic, num_feedback_rounds=1, **kwargs)


def run_tier2(profile: Dict[str, Any], topic: str, **kwargs) -> Dict[str, Any]:
    return run_tier("t2", profile, topic, num_feedback_rounds=1, **kwargs)


def run_tier3(profile: Dict[str, Any], topic: str, **kwargs) -> Dict[str, Any]:
    return run_tier("t3", profile, topic, num_feedback_rounds=3, **kwargs)


if __name__ == "__main__":
    # Quick smoke test on a single user/topic pair
    from eval.synthetic_profiles import SYNTHETIC_PROFILES, TOPICS
    profile = SYNTHETIC_PROFILES[0]
    topic = TOPICS[0]["topic"]
    print(f"Smoke test: {profile['user_id']} | {topic}")
    result = run_tier1(profile, topic, delay_seconds=0.5)
    print(f"  Error: {result.get('error')}")
    print(f"  Rounds: {len(result.get('rounds', []))}")
    example = result.get("initial_example", "")
    print(f"  Example preview: {example[:120]}...")
