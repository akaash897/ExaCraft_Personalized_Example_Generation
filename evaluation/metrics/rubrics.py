"""
Evaluation Rubrics for Educational Example Quality

Seven dimensions based on:
  - Bloom's Revised Taxonomy (Anderson et al., 2001) for pedagogical quality
  - Cognitive Load Theory (Sweller, 1988) for clarity
  - Culturally Responsive Teaching (Gay, 2000) for cultural appropriateness
  - G-Eval style: explicit per-score anchors eliminate scale inconsistency
    (Liu et al., 2023 — rubric-anchored scoring vs. open-ended rating)

Each rubric provides:
  - Dimension name and weight in final composite score
  - Chain-of-thought prompt (G-Eval style) — judge reasons before scoring
  - Score anchors (1–5) with explicit behavioral descriptions
"""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Rubric:
    name: str
    key: str                    # snake_case identifier used in JSON output
    weight: float               # proportion of composite score (must sum to 1.0)
    description: str            # one-line description for reports
    cot_prompt: str             # chain-of-thought instructions for the judge
    score_anchors: Dict[int, str]  # 1–5 anchor descriptions


# ──────────────────────────────────────────────────────────────────────────────
# DIMENSION 1 — Factual Accuracy                                    weight 0.20
# ──────────────────────────────────────────────────────────────────────────────
FACTUAL_ACCURACY = Rubric(
    name="Factual Accuracy",
    key="factual_accuracy",
    weight=0.20,
    description="Is every factual claim in the example correct?",
    cot_prompt=(
        "Carefully examine every factual claim, figure, name, relationship, "
        "or causal statement in the example. Identify any errors or "
        "misleading statements. Consider whether domain-specific details "
        "(scientific, historical, technical) are correct."
    ),
    score_anchors={
        1: "Contains multiple clear factual errors that would actively mislead a learner.",
        2: "Contains at least one notable factual error that affects understanding.",
        3: "Mostly accurate but includes minor imprecision or oversimplification that does not actively mislead.",
        4: "Accurate with trivial simplifications acceptable for educational purposes.",
        5: "Completely accurate; every factual claim is verifiably correct.",
    },
)

# ──────────────────────────────────────────────────────────────────────────────
# DIMENSION 2 — Concept Relevance                                   weight 0.20
# ──────────────────────────────────────────────────────────────────────────────
CONCEPT_RELEVANCE = Rubric(
    name="Concept Relevance",
    key="concept_relevance",
    weight=0.20,
    description="Does the example clearly and correctly illustrate the target concept?",
    cot_prompt=(
        "Check whether the core mechanism of the target concept is accurately "
        "demonstrated through the scenario. Ask: Would a student who only reads "
        "this example correctly understand the concept? Is the conceptual mapping "
        "tight, or does the analogy break down?"
    ),
    score_anchors={
        1: "The example is unrelated to or actively contradicts the target concept.",
        2: "The example only tangentially relates to the concept; the link is unclear.",
        3: "The example captures the concept partially but misses key aspects.",
        4: "The example clearly illustrates the concept with minor omissions.",
        5: "The example perfectly illustrates the concept; the conceptual mapping is tight and complete.",
    },
)

# ──────────────────────────────────────────────────────────────────────────────
# DIMENSION 3 — Personalization Fidelity                            weight 0.20
# ──────────────────────────────────────────────────────────────────────────────
PERSONALIZATION_FIDELITY = Rubric(
    name="Personalization Fidelity",
    key="personalization_fidelity",
    weight=0.20,
    description="How faithfully does the example reflect the user's profile attributes?",
    cot_prompt=(
        "Compare the example against the provided user profile. Check whether "
        "location, profession, education level, cultural background, interests, "
        "learning style, and complexity preference are genuinely reflected — not "
        "just superficially mentioned. A high-scoring example integrates profile "
        "attributes into the scenario naturally, not as a forced add-on."
    ),
    score_anchors={
        1: "The example ignores the user profile entirely; it is generic or mismatched.",
        2: "One profile attribute is superficially mentioned but most are ignored.",
        3: "Several attributes are reflected but integration feels forced or incomplete.",
        4: "Most key profile attributes are naturally integrated into the scenario.",
        5: "All major profile attributes are seamlessly woven into a coherent, tailored scenario.",
    },
)

# ──────────────────────────────────────────────────────────────────────────────
# DIMENSION 4 — Pedagogical Soundness                               weight 0.15
# ──────────────────────────────────────────────────────────────────────────────
# Grounded in Bloom's Revised Taxonomy (Anderson et al., 2001):
# appropriate cognitive level, scaffolding, and knowledge construction.
PEDAGOGICAL_SOUNDNESS = Rubric(
    name="Pedagogical Soundness",
    key="pedagogical_soundness",
    weight=0.15,
    description="Is this a well-designed teaching example for the learner's level?",
    cot_prompt=(
        "Evaluate this as an educational designer would. Consider: "
        "(a) Is the complexity appropriate for the learner's education level? "
        "(b) Does it build on what the learner likely already knows (scaffolding)? "
        "(c) Is the concept presented at the right cognitive level per Bloom's Taxonomy "
        "(remember, understand, apply, analyze)? "
        "(d) Does it avoid cognitive overload while still being substantive?"
    ),
    score_anchors={
        1: "Completely mismatched to learner level (either trivially simple or incomprehensibly complex); poor pedagogical design.",
        2: "Noticeably too simple or too complex; limited educational value.",
        3: "Acceptable difficulty level but misses scaffolding opportunities or cognitive engagement.",
        4: "Well-matched to learner level with good scaffolding; minor missed opportunities.",
        5: "Excellently calibrated to the learner; builds appropriately on prior knowledge and challenges growth.",
    },
)

# ──────────────────────────────────────────────────────────────────────────────
# DIMENSION 5 — Clarity & Coherence                                 weight 0.15
# ──────────────────────────────────────────────────────────────────────────────
# Grounded in Cognitive Load Theory (Sweller, 1988):
# minimize extraneous load; maximize germane cognitive processing.
CLARITY_COHERENCE = Rubric(
    name="Clarity & Coherence",
    key="clarity_coherence",
    weight=0.15,
    description="Is the example clear, well-written, and easy to follow?",
    cot_prompt=(
        "Evaluate grammatical correctness, sentence structure, and readability. "
        "Does the scenario flow logically? Are pronouns, referents, and causal "
        "relationships clear? Is the language appropriate for the learner's "
        "education level? Identify any confusing passages, ambiguous pronoun "
        "references, or awkward phrasing."
    ),
    score_anchors={
        1: "The example is confusing, grammatically broken, or incoherent.",
        2: "The example is understandable but has significant clarity issues.",
        3: "Mostly clear with some awkward phrasing or minor ambiguities.",
        4: "Clear and well-written with only trivial stylistic issues.",
        5: "Exceptionally clear; reads naturally and is immediately comprehensible.",
    },
)

# ──────────────────────────────────────────────────────────────────────────────
# DIMENSION 6 — Cultural Appropriateness                            weight 0.05
# ──────────────────────────────────────────────────────────────────────────────
# Grounded in Culturally Responsive Teaching (Gay, 2000):
# examples should respect, reflect, and leverage the learner's cultural context.
CULTURAL_APPROPRIATENESS = Rubric(
    name="Cultural Appropriateness",
    key="cultural_appropriateness",
    weight=0.05,
    description="Is the cultural context respectful, accurate, and fitting?",
    cot_prompt=(
        "Assess whether cultural references, names, locations, and practices "
        "are used respectfully and accurately. Check for stereotyping, cultural "
        "insensitivity, or factual errors about the user's cultural context. "
        "Also check whether the cultural framing genuinely helps connect the "
        "concept to the user's lived experience."
    ),
    score_anchors={
        1: "Contains offensive, stereotyping, or clearly inaccurate cultural content.",
        2: "Cultural references are present but feel tokenistic or slightly inaccurate.",
        3: "Culturally neutral or acceptable; no glaring issues but limited cultural value.",
        4: "Cultural references are respectful, accurate, and meaningfully integrated.",
        5: "Culturally rich, accurate, and genuinely enhances the learning experience for this user.",
    },
)

# ──────────────────────────────────────────────────────────────────────────────
# DIMENSION 7 — Engagement & Relatability                           weight 0.05
# ──────────────────────────────────────────────────────────────────────────────
ENGAGEMENT_RELATABILITY = Rubric(
    name="Engagement & Relatability",
    key="engagement_relatability",
    weight=0.05,
    description="Would the target user find this example engaging and relatable?",
    cot_prompt=(
        "Imagine you are this specific user (with the given profession, interests, "
        "background, and age range). Would this example capture your attention? "
        "Does the scenario feel real and relevant to your life? Is there a "
        "memorable narrative element that aids retention?"
    ),
    score_anchors={
        1: "The example is dry, abstract, and entirely disconnected from the user's world.",
        2: "Minimally engaging; the user would likely skim past it.",
        3: "Moderately engaging; has some relatable elements but lacks vividness.",
        4: "Engaging and relatable; would hold the user's attention.",
        5: "Highly engaging; vivid, memorable scenario that directly resonates with the user.",
    },
)

# ──────────────────────────────────────────────────────────────────────────────
# Master registry
# ──────────────────────────────────────────────────────────────────────────────
ALL_RUBRICS: List[Rubric] = [
    FACTUAL_ACCURACY,
    CONCEPT_RELEVANCE,
    PERSONALIZATION_FIDELITY,
    PEDAGOGICAL_SOUNDNESS,
    CLARITY_COHERENCE,
    CULTURAL_APPROPRIATENESS,
    ENGAGEMENT_RELATABILITY,
]

# Validate weights sum to 1.0
_total_weight = sum(r.weight for r in ALL_RUBRICS)
assert abs(_total_weight - 1.0) < 1e-6, f"Rubric weights must sum to 1.0, got {_total_weight}"

RUBRIC_BY_KEY: Dict[str, Rubric] = {r.key: r for r in ALL_RUBRICS}


def build_judge_prompt(
    topic: str,
    user_profile_summary: str,
    learning_context_summary: str,
    example_text: str,
    rubric: Rubric,
) -> str:
    """
    Construct the G-Eval style prompt for a single rubric dimension.

    G-Eval approach (Liu et al., 2023):
      Step 1 — Provide evaluation context and criteria
      Step 2 — Ask the judge to reason through the criteria (CoT)
      Step 3 — Ask for a structured JSON score with justification

    This two-step structure significantly improves alignment with human judgment
    compared to direct scoring requests.
    """
    anchor_text = "\n".join(
        f"  {score}: {desc}" for score, desc in rubric.score_anchors.items()
    )

    return f"""You are an expert educational content evaluator. Your task is to evaluate a single dimension of a personalized learning example.

## Context

**Target Concept:** {topic}

**User Profile:**
{user_profile_summary}

**User's Learning Context:**
{learning_context_summary}

**Example to Evaluate:**
{example_text}

---

## Evaluation Dimension: {rubric.name}

**What to assess:** {rubric.description}

**Evaluation instructions:**
{rubric.cot_prompt}

**Score anchors:**
{anchor_text}

---

## Instructions

1. Think step-by-step about the evaluation criteria above. Write your reasoning in 2–4 sentences.
2. Assign a score from 1 to 5 using the anchors above.
3. Respond with ONLY valid JSON in this exact format:

{{
  "dimension": "{rubric.key}",
  "reasoning": "<your 2-4 sentence reasoning here>",
  "score": <integer 1-5>
}}

Do not add any text outside the JSON object."""


def build_full_evaluation_prompt(
    topic: str,
    user_profile_summary: str,
    learning_context_summary: str,
    example_text: str,
) -> str:
    """
    Single-call prompt that evaluates all dimensions at once.
    Used for judges that perform better with complete context.
    Less calibrated than per-dimension prompting but faster.
    """
    dimensions_block = ""
    for r in ALL_RUBRICS:
        anchor_text = "\n".join(
            f"      {score}: {desc}" for score, desc in r.score_anchors.items()
        )
        dimensions_block += f"""
  **{r.name}** (`{r.key}`)
  {r.description}
  Evaluation instructions: {r.cot_prompt}
  Score anchors:
{anchor_text}
"""

    keys_list = [r.key for r in ALL_RUBRICS]
    json_template = "{\n" + "\n".join(
        f'  "{k}": {{"reasoning": "<reasoning>", "score": <1-5>}},'
        for k in keys_list
    ) + "\n}"

    return f"""You are an expert educational content evaluator. Evaluate the following personalized learning example across {len(ALL_RUBRICS)} dimensions.

## Context

**Target Concept:** {topic}

**User Profile:**
{user_profile_summary}

**User's Learning Context:**
{learning_context_summary}

**Example to Evaluate:**
{example_text}

---

## Evaluation Dimensions
{dimensions_block}

---

## Instructions

For each dimension:
1. Reason through the criteria (2–3 sentences of analysis)
2. Assign a score from 1 to 5 using the anchors provided

Respond with ONLY valid JSON in this exact format:
{json_template}

Do not include any text outside the JSON object."""
