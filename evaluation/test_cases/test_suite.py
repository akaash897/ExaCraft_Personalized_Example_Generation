"""
Test Scenarios

Each scenario combines a topic + profile + generation mode, forming one
end-to-end test case: generate an example → evaluate it.

Topic selection rationale:
  Topics are drawn from six domains that map to different abstraction levels:
    1. Abstract/mathematical  (recursion, probability)
    2. Physical sciences      (photosynthesis, Newton's laws)
    3. Economics/social       (supply and demand, inflation)
    4. Computer science       (APIs, databases)
    5. Biology/medicine       (DNA replication, immune response)
    6. Philosophy/logic       (Occam's Razor, logical fallacies)

  Abstract topics stress Concept Relevance and Personalization Fidelity most
  heavily — they are hardest to make concrete and personalized simultaneously.
  Concrete domain topics stress Factual Accuracy and Pedagogical Soundness.

  Covering both categories prevents evaluation from only assessing "easy" cases
  where generic examples could score well.

Generation mode coverage:
  Each topic × profile is tested in all three ExaCraft modes:
    - simple      : no learning context, baseline personalization
    - adaptive    : with simulated learning context (neutral / struggling / mastering)
    - collaborative: with collaborative filtering context

  This lets the evaluation measure whether adaptive and collaborative modes
  genuinely improve over baseline, which is the core research claim.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class LearningContextSimulation:
    """Simulated learning context state for adaptive mode testing."""
    scenario_name: str        # "neutral" | "struggling" | "mastering"
    recent_topics: List[str]
    struggle_topics: List[str]
    mastery_topics: List[str]
    description: str          # human-readable description for reports

    def to_context_summary(self) -> str:
        """Render as the learning context summary string fed to the generator."""
        parts = []
        if self.recent_topics:
            parts.append(f"Recent topics explored: {', '.join(self.recent_topics)}")
        if self.struggle_topics:
            parts.append(f"Currently struggling with: {', '.join(self.struggle_topics)}")
        if self.mastery_topics:
            parts.append(
                f"Demonstrated mastery progression through {len(self.mastery_topics)} topics: "
                f"{' -> '.join(self.mastery_topics)}. Ready for increased complexity."
            )
        if not parts:
            parts.append("First time learning session")
        return "; ".join(parts)


# Simulated learning contexts — three canonical states
NEUTRAL_CONTEXT = LearningContextSimulation(
    scenario_name="neutral",
    recent_topics=[],
    struggle_topics=[],
    mastery_topics=[],
    description="First-time session, no learning history",
)

STRUGGLING_CONTEXT = LearningContextSimulation(
    scenario_name="struggling",
    recent_topics=["recursion", "recursion", "recursion"],
    struggle_topics=["recursion"],
    mastery_topics=[],
    description="Learner is stuck — repeated the same topic 3 times",
)

MASTERING_CONTEXT = LearningContextSimulation(
    scenario_name="mastering",
    recent_topics=["variables", "loops", "functions", "classes", "recursion"],
    struggle_topics=[],
    mastery_topics=["variables", "loops", "functions", "classes", "recursion"],
    description="Learner is progressing rapidly through diverse topics",
)


@dataclass
class TestScenario:
    """One complete test scenario: profile × topic × mode × learning context."""
    scenario_id: str
    topic: str
    profile_key: str          # key into TEST_PROFILES dict
    generation_mode: str      # "simple" | "adaptive" | "collaborative"
    learning_context: LearningContextSimulation = field(default_factory=lambda: NEUTRAL_CONTEXT)
    description: str = ""     # human-readable note for reports
    expected_personalization_elements: List[str] = field(default_factory=list)
    # expected_personalization_elements: hints for manual review
    # (not used in automated scoring, but useful for human audits)


# ──────────────────────────────────────────────────────────────────────────────
# Core topic × profile × mode combinations
# ──────────────────────────────────────────────────────────────────────────────

TEST_SCENARIOS: List[TestScenario] = [

    # ── ABSTRACT / CS TOPICS ──────────────────────────────────────────────

    TestScenario(
        scenario_id="T01_recursion_engineer_simple",
        topic="Recursion in programming",
        profile_key="software_engineer_india",
        generation_mode="simple",
        description="CS topic, technical profile, baseline mode",
        expected_personalization_elements=["software", "code", "India or Bengaluru"],
    ),
    TestScenario(
        scenario_id="T02_recursion_engineer_adaptive_struggling",
        topic="Recursion in programming",
        profile_key="software_engineer_india",
        generation_mode="adaptive",
        learning_context=STRUGGLING_CONTEXT,
        description="Same topic but learner is struggling — should simplify",
        expected_personalization_elements=["simple analogy", "encouraging tone"],
    ),
    TestScenario(
        scenario_id="T03_recursion_engineer_adaptive_mastering",
        topic="Recursion in programming",
        profile_key="software_engineer_india",
        generation_mode="adaptive",
        learning_context=MASTERING_CONTEXT,
        description="Same topic but learner is mastering — should increase complexity",
        expected_personalization_elements=["advanced", "tail recursion or memoization"],
    ),
    TestScenario(
        scenario_id="T04_recursion_highschool_simple",
        topic="Recursion in programming",
        profile_key="high_school_nigeria",
        generation_mode="simple",
        description="Abstract CS topic for high-school student — should simplify significantly",
        expected_personalization_elements=["Lagos or Nigeria", "football or music"],
    ),
    TestScenario(
        scenario_id="T05_recursion_artstudent_simple",
        topic="Recursion in programming",
        profile_key="art_student_mexico",
        generation_mode="simple",
        description="Abstract topic for non-technical profile — personalization challenge",
        expected_personalization_elements=["painting or art", "Mexico City"],
    ),

    # ── ECONOMICS TOPICS ──────────────────────────────────────────────────

    TestScenario(
        scenario_id="T06_supply_demand_econ_grad",
        topic="Supply and demand equilibrium",
        profile_key="econ_grad_germany",
        generation_mode="simple",
        description="Domain-expert for this topic — should use advanced framing",
        expected_personalization_elements=["Berlin or Germany", "advanced economic framing"],
    ),
    TestScenario(
        scenario_id="T07_supply_demand_highschool",
        topic="Supply and demand equilibrium",
        profile_key="high_school_nigeria",
        generation_mode="simple",
        description="Economics concept for high-school student",
        expected_personalization_elements=["Nigeria market", "local goods"],
    ),
    TestScenario(
        scenario_id="T08_inflation_nurse",
        topic="Inflation and purchasing power",
        profile_key="nurse_brazil",
        generation_mode="adaptive",
        learning_context=NEUTRAL_CONTEXT,
        description="Economics topic for healthcare professional",
        expected_personalization_elements=["medical supplies or healthcare costs", "Brazil"],
    ),

    # ── BIOLOGY / MEDICINE ────────────────────────────────────────────────

    TestScenario(
        scenario_id="T09_dna_replication_nurse",
        topic="DNA replication",
        profile_key="nurse_brazil",
        generation_mode="simple",
        description="Biology concept for a nurse — should connect to clinical context",
        expected_personalization_elements=["healthcare or nursing", "cell biology"],
    ),
    TestScenario(
        scenario_id="T10_immune_response_teacher",
        topic="Immune response and antibodies",
        profile_key="retired_teacher_japan",
        generation_mode="simple",
        description="Biology topic for retired teacher — clear, educational framing",
        expected_personalization_elements=["Japan or Kyoto", "teaching analogy"],
    ),

    # ── MATHEMATICS ───────────────────────────────────────────────────────

    TestScenario(
        scenario_id="T11_probability_data_scientist",
        topic="Conditional probability (Bayes' theorem)",
        profile_key="data_scientist_egypt",
        generation_mode="simple",
        description="Math topic for expert data scientist — advanced level expected",
        expected_personalization_elements=["statistics or ML", "Egypt or Cairo"],
    ),
    TestScenario(
        scenario_id="T12_probability_highschool",
        topic="Basic probability",
        profile_key="high_school_nigeria",
        generation_mode="simple",
        description="Math topic for high-schooler — concrete and simple",
        expected_personalization_elements=["football or music", "relatable scenario"],
    ),
    TestScenario(
        scenario_id="T13_probability_business_student",
        topic="Expected value in decision-making",
        profile_key="business_student_usa",
        generation_mode="adaptive",
        learning_context=NEUTRAL_CONTEXT,
        description="Probability applied to business decisions",
        expected_personalization_elements=["business or entrepreneurship", "Atlanta or USA"],
    ),

    # ── PHILOSOPHY / LOGIC ────────────────────────────────────────────────

    TestScenario(
        scenario_id="T14_occams_razor_econ_grad",
        topic="Occam's Razor (parsimony principle)",
        profile_key="econ_grad_germany",
        generation_mode="simple",
        description="Abstract concept for philosophy-interested economist",
        expected_personalization_elements=["economics or model selection", "philosophy"],
    ),
    TestScenario(
        scenario_id="T15_confirmation_bias_data_scientist",
        topic="Confirmation bias in research",
        profile_key="data_scientist_egypt",
        generation_mode="adaptive",
        learning_context=MASTERING_CONTEXT,
        description="Cognitive bias topic for advanced data scientist",
        expected_personalization_elements=["data analysis or ML experiments", "research"],
    ),

    # ── CROSS-MODE COMPARISON (same topic × same profile × all 3 modes) ──
    # These three form a controlled comparison group for the research analysis.

    TestScenario(
        scenario_id="T16_newton_business_simple",
        topic="Newton's third law of motion",
        profile_key="business_student_usa",
        generation_mode="simple",
        description="[COMPARISON GROUP] Physics topic, business student, simple mode",
    ),
    TestScenario(
        scenario_id="T17_newton_business_adaptive",
        topic="Newton's third law of motion",
        profile_key="business_student_usa",
        generation_mode="adaptive",
        learning_context=NEUTRAL_CONTEXT,
        description="[COMPARISON GROUP] Same as T16 but adaptive mode",
    ),
    TestScenario(
        scenario_id="T18_newton_business_collaborative",
        topic="Newton's third law of motion",
        profile_key="business_student_usa",
        generation_mode="collaborative",
        description="[COMPARISON GROUP] Same as T16 but collaborative mode",
    ),
]

# Quick lookup by scenario_id
SCENARIO_BY_ID = {s.scenario_id: s for s in TEST_SCENARIOS}
