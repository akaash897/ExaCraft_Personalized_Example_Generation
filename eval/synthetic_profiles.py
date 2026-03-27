"""
Synthetic Profiles & Test Battery
4 profiles × 2 start modes (cold/warm) = 8 users
4 topics across 4 distinct domains
Scripted feedback battery: easy (cold users) + adversarial (warm users)
Round 3 adds FP (flag_pattern) stable-trait messages for all users.
"""

from typing import List, Dict, Any, Optional

# ── 4 Topics — 1 per domain ────────────────────────────────────────────────────

TOPICS = [
    {"topic": "Natural Selection",  "domain": "evolutionary_biology"},
    {"topic": "Cognitive Bias",     "domain": "psychology"},
    {"topic": "Compound Interest",  "domain": "mathematics_finance"},
    {"topic": "Plate Tectonics",    "domain": "earth_sciences"},
]

# ── 4 Profiles — globally diverse, 4 continents ───────────────────────────────

PROFESSIONS = [
    {
        "role": "student",
        "education_level": "high_school",
        "profession": "Student",
        "location": "Berlin, Germany",
        "cultural_background": "European",
        "name": "Lena",
    },
    {
        "role": "nurse",
        "education_level": "professional",
        "profession": "Nurse",
        "location": "Lagos, Nigeria",
        "cultural_background": "West African",
        "name": "Amara",
    },
    {
        "role": "humanities_researcher",
        "education_level": "phd",
        "profession": "Humanities Researcher",
        "location": "São Paulo, Brazil",
        "cultural_background": "Latin American",
        "name": "Carlos",
    },
    {
        "role": "engineer",
        "education_level": "undergraduate",
        "profession": "Software Engineer",
        "location": "Tokyo, Japan",
        "cultural_background": "East Asian",
        "name": "Kenji",
    },
]

# ── Build 8 Synthetic Users (4 cold + 4 warm, all medium complexity) ──────────

def _build_profiles() -> List[Dict[str, Any]]:
    profiles = []
    uid = 1
    # Cold-start users first (1–4), then warm-start (5–8)
    for start_mode in ("cold", "warm"):
        for prof in PROFESSIONS:
            profiles.append({
                "user_id": f"eval_user_{uid:02d}",
                "name": prof["name"],
                "role": prof["role"],
                "education_level": prof["education_level"],
                "profession": prof["profession"],
                "location": prof["location"],
                "cultural_background": prof["cultural_background"],
                "learning_style": "example-based",
                "complexity": "medium",
                "start_mode": start_mode,
            })
            uid += 1
    return profiles


SYNTHETIC_PROFILES: List[Dict[str, Any]] = _build_profiles()

# ── Scripted Feedback Battery ──────────────────────────────────────────────────
# T3 runs two feedback rounds per session:
#   Round 1 — critique (triggers regeneration decision by Adaptive Response Agent)
#   Round 2 — positive close F3 (triggers accept)
#
# Battery split:
#   Cold users  (start_mode="cold", users 1–4) → EASY battery (F1/F2)
#   Warm users  (start_mode="warm", users 5–8) → ADVERSARIAL battery (A1/A2/A4/A5)
#
# Easy battery — unambiguous, well-formed complaints
FEEDBACK_BATTERY = {
    "F1": "This is too complicated for me. Can you simplify it with a more basic example?",
    "F2": "This example doesn't feel relevant to my field. Can you use something from my domain instead?",
    "F3": "This is great! The example really helped me understand the concept.",  # positive close
}

# Adversarial battery — ambiguous, vague, contradictory, or minimal messages
ADVERSARIAL_BATTERY = {
    # A1: vague dissatisfaction — no actionable signal
    "A1": "I don't really get it.",
    # A2: contradictory — requests two incompatible changes simultaneously
    "A2": "Can you make it simpler, but also go into more depth on the technical side?",
    # A4: minimal / implicit — near-zero signal
    "A4": "Hmm.",
    # A5: mixed praise and hidden critique — positive framing conceals real complaint
    "A5": "I liked the example overall, but the main point wasn't really clear to me at the end.",
}

# FP battery — stable-trait statements that should trigger flag_pattern
# One message per user role; designed to reveal a persistent learning preference
FP_BATTERY = {
    "FP_student":    "I always connect better when examples use everyday scenarios from school life, like assignments or exams.",
    "FP_nurse":      "I find medical equipment analogies much more natural for understanding abstract ideas.",
    "FP_researcher": "I always prefer examples that draw on historical or cultural contexts rather than formulas.",
    "FP_engineer":   "Code-adjacent analogies always click better for me than abstract descriptions.",
}

# Feedback assignment per user (cold: F1/F2 alternating, warm: adversarial in difficulty order)
# uid 01 (Lena, cold)   → F1  (too complicated)
# uid 02 (Amara, cold)  → F2  (not relevant to field)
# uid 03 (Carlos, cold) → F1
# uid 04 (Kenji, cold)  → F2
# uid 05 (Lena, warm)   → A1  (vague)
# uid 06 (Amara, warm)  → A2  (contradictory)
# uid 07 (Carlos, warm) → A5  (hidden critique — hardest for researcher profile)
# uid 08 (Kenji, warm)  → A4  (minimal)

_COLD_SEQUENCE = ["F1", "F2", "F1", "F2"]      # positions 1–4
_WARM_SEQUENCE = ["A1", "A2", "A5", "A4"]      # positions 5–8 (warm_position 1–4)

# Role mapping: uid_num → role key for FP_BATTERY lookup
# Cold users 1–4 and warm users 5–8 share the same role ordering (student, nurse, researcher, engineer)
_UID_TO_ROLE = {
    1: "student", 2: "nurse", 3: "researcher", 4: "engineer",
    5: "student", 6: "nurse", 7: "researcher", 8: "engineer",
}


def get_feedback_for_round(user_id: str, round_num: int) -> str:
    """
    Return scripted feedback for a given round (1-indexed).

    Round 1: critique message (easy for cold users 1–4, adversarial for warm users 5–8)
    Round 2: positive close (F3) for all users
    Round 3: FP stable-trait message based on user's role (triggers flag_pattern)
    Round 4+: F3 fallback (positive close)
    """
    uid_num = int(user_id.split("_")[-1])  # 1–8

    # Round 3: stable-trait FP message — should trigger flag_pattern
    if round_num == 3:
        role = _UID_TO_ROLE.get(uid_num, "student")
        fp_key = f"FP_{role}"
        return FP_BATTERY[fp_key]

    # Round 2 and 4+: positive close
    if round_num >= 2:
        return FEEDBACK_BATTERY["F3"]

    # Round 1 — cold users: 1–4
    if uid_num <= 4:
        key = _COLD_SEQUENCE[uid_num - 1]
        return FEEDBACK_BATTERY[key]

    # Round 1 — warm users: 5–8
    warm_position = uid_num - 4  # 1–4
    key = _WARM_SEQUENCE[warm_position - 1]
    adv_or_easy = ADVERSARIAL_BATTERY if key.startswith("A") else FEEDBACK_BATTERY
    return adv_or_easy[key]


# ── Ground Truth Expected Agent Decisions ─────────────────────────────────────
# A2 is excluded (inherently ambiguous — either decision is defensible).
# Round 3 always expects "flag_pattern" for all users.
_EXPECTED_DECISIONS = {
    # Cold users, round 1
    ("eval_user_01", 1): "regenerate",   # F1
    ("eval_user_02", 1): "regenerate",   # F2
    ("eval_user_03", 1): "regenerate",   # F1
    ("eval_user_04", 1): "regenerate",   # F2
    # Warm users, round 1
    ("eval_user_05", 1): "regenerate",   # A1 — vague but still a complaint
    ("eval_user_06", 1): None,           # A2 — excluded (ambiguous)
    ("eval_user_07", 1): "regenerate",   # A5 — hidden critique
    ("eval_user_08", 1): "accept",       # A4 — minimal signal, should not regenerate
    # Round 2: all users → accept (F3 positive)
    **{(f"eval_user_{i:02d}", 2): "accept" for i in range(1, 9)},
    # Round 3: all users → flag_pattern (FP stable-trait)
    **{(f"eval_user_{i:02d}", 3): "flag_pattern" for i in range(1, 9)},
}


def get_expected_decision(user_id: str, round_num: int) -> Optional[str]:
    """
    Return the expected agent decision for a given user and round.
    Returns None if the round is excluded from accuracy evaluation (e.g. A2).
    """
    return _EXPECTED_DECISIONS.get((user_id, round_num))


def get_feedback_battery_type(feedback_text: str) -> str:
    """Classify a feedback string as 'easy' or 'adversarial'. Used by analysis.py."""
    if feedback_text in ADVERSARIAL_BATTERY.values():
        return "adversarial"
    return "easy"


def get_profile_by_id(user_id: str) -> Dict[str, Any]:
    for p in SYNTHETIC_PROFILES:
        if p["user_id"] == user_id:
            return p
    raise ValueError(f"Profile not found: {user_id}")


if __name__ == "__main__":
    print(f"Total profiles : {len(SYNTHETIC_PROFILES)}")
    print(f"Total topics   : {len(TOPICS)}")
    print(f"Total cells    : {len(SYNTHETIC_PROFILES) * len(TOPICS) * 4}  (all tiers)")
    cold = [p for p in SYNTHETIC_PROFILES if p["start_mode"] == "cold"]
    warm = [p for p in SYNTHETIC_PROFILES if p["start_mode"] == "warm"]
    print(f"Cold users: {len(cold)}, Warm users: {len(warm)}")
    for p in SYNTHETIC_PROFILES:
        fb = get_feedback_for_round(p["user_id"], 1)
        print(f"  {p['user_id']}  {p['start_mode']:5}  {p['profession']:<25}  {p['location']:<20}  R1: {fb[:50]}")
