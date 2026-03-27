"""
Seed Warm Start
Pre-seeds feedback history and learning patterns for warm-start users (eval_user_05–08).
Run ONCE before the main evaluation to establish warm-start state.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.feedback_store import (
    append_learning_pattern,
    append_accept_insight,
)
from eval.synthetic_profiles import SYNTHETIC_PROFILES

# Warm-start users: eval_user_05 to eval_user_08
WARM_USERS = [p for p in SYNTHETIC_PROFILES if p["start_mode"] == "warm"]


def seed_user(profile: dict) -> None:
    user_id = profile["user_id"]
    role = profile["role"]
    complexity = profile["complexity"]

    # Seed 2 learning patterns per user
    patterns = [
        {
            "pattern_type": "domain_preference",
            "observation": (
                f"User strongly prefers examples grounded in their professional domain "
                f"({profile['profession']}) with real-world scenarios from {profile['location']}."
            ),
        },
        {
            "pattern_type": "complexity_preference",
            "observation": (
                f"User consistently engages better with {complexity}-complexity examples. "
                f"Examples that are too abstract or too simple get negative feedback."
            ),
        },
    ]
    for pat in patterns:
        append_learning_pattern(
            user_id=user_id,
            pattern_type=pat["pattern_type"],
            observation=pat["observation"],
            example_id=f"seed_ex_{user_id}",
            source="seed",
        )

    # Seed 2 accept insights per user
    insights = [
        (
            f"Using {profile['name']}'s name and {profile['location']} location in the scenario "
            f"significantly improved engagement — the example felt personal and grounded."
        ),
        (
            f"Step-by-step breakdowns with labeled inputs and outputs worked well "
            f"for this {role} learner at {complexity} complexity."
        ),
    ]
    for insight in insights:
        append_accept_insight(
            user_id=user_id,
            insight=insight,
            example_id=f"seed_ex_{user_id}",
        )

    print(f"  Seeded {user_id} ({profile['name']}, {role}, {complexity})")


def seed_all_warm_users() -> None:
    print(f"Seeding {len(WARM_USERS)} warm-start users...")
    for profile in WARM_USERS:
        seed_user(profile)
    print("Done.")


if __name__ == "__main__":
    seed_all_warm_users()
