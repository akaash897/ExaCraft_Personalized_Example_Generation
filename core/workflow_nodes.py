"""
Workflow Node Implementations
Primary Agent nodes for Adaptive Example Generation (6 nodes).

node_load_profile          → load user profile from storage
node_build_context         → synthesize learning patterns + insights into context_instruction
node_generate              → call LLM with profile + context + optional regeneration_instruction
node_format_and_save       → save example to history, set example_id
node_user_review           → ⏸ interrupt for natural-language user feedback
node_process_feedback      → invoke Adaptive Response Agent, set regeneration flags
"""

import uuid
from datetime import datetime
from typing import Dict, Any

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.types import interrupt

from core.user_profile import UserProfile
from core.learning_context import LearningContext
from core.workflow_state import PersonalizedGenerationState
from core.adaptive_response_agent import invoke_adaptive_response_agent
from core.example_history import ExampleHistory
from core.feedback_store import load_learning_patterns, load_accept_insights
from core.context_manager_agent import resolve_topic_tags, invoke_context_manager_agent
from core.llm_provider import LLMProviderFactory
from config.settings import DEFAULT_LLM_PROVIDER, LLM_API_KEYS


def _get_provider_and_key(state: PersonalizedGenerationState):
    provider = state.get("provider") or DEFAULT_LLM_PROVIDER
    api_key = LLM_API_KEYS.get(provider, "")
    return provider, api_key


# ─── Node 1: Load Profile ─────────────────────────────────────────────────────

def node_load_profile(state: PersonalizedGenerationState) -> PersonalizedGenerationState:
    """Load user profile via UserProfile class."""
    user_id = state["user_id"]
    try:
        profile = UserProfile(user_id=user_id)
        state["user_profile"] = profile.profile_data
        state["profile_summary"] = profile.get_profile_summary()
        state["error_occurred"] = False
    except Exception as e:
        state["user_profile"] = {}
        state["profile_summary"] = "Profile unavailable."
        state["error_occurred"] = True
        state["error_message"] = f"node_load_profile error: {e}"
    return state


# ─── Node 2: Build Context ────────────────────────────────────────────────────

def node_build_context(state: PersonalizedGenerationState) -> PersonalizedGenerationState:
    """
    Build a targeted context_instruction using the ContextManager Agent.

    1. Resolve 1-3 canonical topic tags for the current topic (LLM call).
    2. Cold start guard: if no patterns and no insights exist, skip agent.
    3. Invoke ContextManager Agent — it queries example history by tag,
       retrieves linked feedback, reasons over global signals as fallback,
       and emits a 2-3 sentence actionable instruction.
    """
    user_id = state["user_id"]
    topic = state["topic"]
    provider, api_key = _get_provider_and_key(state)

    try:
        # Step 1: Resolve topic tags
        topic_tags = resolve_topic_tags(topic, provider, api_key)
        state["topic_tags"] = topic_tags

        # Step 2: Cold start guard
        patterns_data = load_learning_patterns(user_id)
        insights_data = load_accept_insights(user_id)
        if not patterns_data.get("patterns") and not insights_data.get("insights"):
            state["context_instruction"] = ""
            return state

        # Step 3: Invoke ContextManager Agent
        context_instruction = invoke_context_manager_agent(
            user_id=user_id,
            topic=topic,
            topic_tags=topic_tags,
            provider=provider,
            api_key=api_key
        )
        state["context_instruction"] = context_instruction

    except Exception as e:
        state["context_instruction"] = ""
        state["error_message"] = f"node_build_context warning: {e}"

    return state


# ─── Node 3: Generate ─────────────────────────────────────────────────────────

def node_generate(state: PersonalizedGenerationState) -> PersonalizedGenerationState:
    """
    Generate a personalized example using the LLM.

    Reads from state:
        profile_summary          — who the user is
        context_instruction      — synthesized from learning history (node_build_context)
        regeneration_instruction — specific fix requested by Adaptive Response Agent (if looping)

    Clears regeneration_instruction after use so it doesn't leak into further loops.
    """
    user_id = state["user_id"]
    topic = state["topic"]
    profile_summary = state.get("profile_summary", "No profile available.")
    context_instruction = state.get("context_instruction", "")
    regeneration_instruction = state.get("regeneration_instruction", "")
    provider, api_key = _get_provider_and_key(state)

    try:
        if not api_key:
            raise ValueError(f"API key not configured for provider: {provider}")

        # Build learning context base
        learning_context = LearningContext(user_id=user_id)
        base_context = learning_context.get_learning_state_summary()

        # Compose enriched context (personalization only — no regen here)
        enriched_context = base_context
        if context_instruction:
            enriched_context += f"\n\nPERSONALIZATION INSTRUCTION (from learning history):\n{context_instruction}"

        # Clear regeneration instruction after consuming it
        state["regeneration_instruction"] = ""

        llm = LLMProviderFactory.create_llm(provider, api_key, temperature=0.3)

        prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are an adaptive AI tutor that generates structured, personalized examples.\n\n"
             "WHAT TO GENERATE (non-negotiable):\n"
             "  - An example that EXPLAINS the topic to the student. The topic is the concept to teach.\n"
             "  - Do NOT reframe the topic as a project to build or a task to automate.\n"
             "    e.g. topic='Fishing' → explain what fishing is, not how to code a fishing log.\n"
             "    e.g. topic='Supply and Demand' → explain the concept, not how to model it in Python.\n"
             "  - Topic accuracy comes first — never sacrifice it.\n"
             "  - Complexity MUST strictly match the student's preferred level:\n"
             "      simple   → 1 scenario, plain English, no jargon, no formulas unless trivial, max 6 structured lines\n"
             "      medium   → 1 scenario, one numeric example or formula, moderate depth\n"
             "      advanced → full depth, formulas, complexity analysis, edge cases welcome\n\n"
             "HOW TO PERSONALIZE (style guidance):\n"
             "  - Use the student's name, location, and profession to ground the scenario.\n"
             "  - Apply the context instruction only if it is relevant to the topic domain.\n"
             "    e.g. 'use Python code' is relevant for programming topics, NOT for fishing, history, or biology.\n"
             "  - If the context instruction conflicts with the topic domain, ignore it and infer from the profile.\n\n"
             "OUTPUT FORMAT:\n"
             "  Always use a structured format appropriate for the topic domain.\n"
             "  Adapt the field labels to fit the topic — do not force fixed labels.\n"
             "  Begin with 'Concept:' and 'Example:' then add relevant structured fields.\n\n"
             "EXAMPLES OF GOOD OUTPUT:\n\n"
             "---\n"
             "Profile: Student | high_school | Benares | medium complexity\n"
             "Context: Student prefers cricket analogies.\n"
             "Topic: Machine Learning\n\n"
             "Concept: Machine Learning\n\n"
             "Example:\n"
             "Akaash builds a model in Benares that predicts whether a cricket\n"
             "batsman will score a half-century based on past match data.\n\n"
             "Input:\n"
             "  - Batsman's recent average\n"
             "  - Pitch condition\n"
             "  - Opposition bowling strength\n\n"
             "Output:\n"
             "  Prediction → Score 50+ / Won't Score 50+\n\n"
             "How it learns:\n"
             "  The model is shown hundreds of past matches with known outcomes\n"
             "  and adjusts its internal weights until its predictions are accurate.\n\n"
             "---\n"
             "Profile: Student | high_school | Kolkata | simple complexity\n"
             "Context: No strong prior signals. Generate from profile.\n"
             "Topic: Photosynthesis\n\n"
             "Concept: Photosynthesis\n\n"
             "Example:\n"
             "In a garden in Kolkata, Meera's sunflower absorbs morning sunlight\n"
             "to produce its own food for the day.\n\n"
             "Inputs:\n"
             "  - Sunlight (energy source)\n"
             "  - CO₂ (from air via stomata)\n"
             "  - H₂O (from soil via roots)\n\n"
             "Output:\n"
             "  - Glucose (food for the plant)\n"
             "  - O₂ (released into air)\n\n"
             "Location:\n"
             "  Chloroplasts inside leaf cells\n\n"
             "Equation:\n"
             "  6CO₂ + 6H₂O + light → C₆H₁₂O₆ + 6O₂\n\n"
             "---\n"
             "Profile: Nurse | professional | Mumbai | advanced complexity\n"
             "Context: Student is a nurse. Medical domain analogies work well.\n"
             "Topic: Newton's Second Law\n\n"
             "Concept: Newton's Second Law (F = ma)\n\n"
             "Example:\n"
             "Sara is pushing a patient gurney down a corridor in a Mumbai hospital.\n"
             "A heavier patient requires more force to reach the same speed.\n\n"
             "Given:\n"
             "  - Force applied: 100 N\n"
             "  - Gurney + patient mass: 50 kg\n\n"
             "Formula:\n"
             "  F = m × a\n"
             "  a = F / m = 100 / 50 = 2 m/s²\n\n"
             "Result:\n"
             "  The gurney accelerates at 2 m/s²\n\n"
             "Key Insight:\n"
             "  Double the mass → half the acceleration for the same push.\n"
             "  This is why moving a bariatric patient requires significantly\n"
             "  more effort than a lightweight gurney.\n\n"
             "---\n"
             "Profile: Engineering Student | undergraduate | Kolkata | medium complexity\n"
             "Context: No strong prior signals. Generate based on profile only.\n"
             "Topic: Ohm's Law\n\n"
             "Concept: Ohm's Law\n\n"
             "Example:\n"
             "In Meera's electronics lab in Kolkata, she connects a 9V battery to\n"
             "a resistor and measures the current flowing through the circuit.\n\n"
             "Given:\n"
             "  - Voltage (V): 9V\n"
             "  - Resistor A: 3Ω → Current = 3A\n"
             "  - Resistor B: 9Ω → Current = 1A\n\n"
             "Formula:\n"
             "  V = I × R\n"
             "  I = V / R\n\n"
             "Results:\n"
             "  9V / 3Ω = 3A   ← less resistance, more current flows\n"
             "  9V / 9Ω = 1A   ← more resistance, less current flows\n\n"
             "Key Insight:\n"
             "  Voltage is the pressure pushing current through the wire.\n"
             "  Resistance fights it. Double the resistance, halve the current —\n"
             "  the battery's push stays the same.\n\n"
             "---\n\n"
             "STUDENT PROFILE:\n{user_profile}\n\n"
             "LEARNING CONTEXT:\n{learning_context}\n\n"
             "{regeneration_override}"
             "Now generate a structured example following the pattern above.\n"
             "Adapt the field labels to suit the topic — do not copy the example fields blindly.\n"
             "Output ONLY the structured example. No meta-commentary."),
            ("human", "Generate an example for the topic: {topic}")
        ])

        # Regeneration instruction overrides profile complexity — student feedback takes priority
        if regeneration_instruction:
            regeneration_override = (
                "STUDENT FEEDBACK OVERRIDE (highest priority — supersedes profile complexity):\n"
                f"{regeneration_instruction}\n"
                "Apply this change exactly. Ignore the complexity level in the profile if it conflicts.\n\n"
            )
        else:
            regeneration_override = ""

        chain = prompt | llm
        result = chain.invoke({
            "user_profile": profile_summary,
            "learning_context": enriched_context,
            "regeneration_override": regeneration_override,
            "topic": topic
        })

        example_text = result.content.strip()

        if example_text.startswith("Error generating example:"):
            state["error_occurred"] = True
            state["error_message"] = example_text
            state["generated_example"] = None
        else:
            state["generated_example"] = example_text
            state["example_metadata"] = {
                "topic": topic,
                "provider": provider,
                "had_context_instruction": bool(context_instruction),
                "was_regeneration": bool(regeneration_instruction),
                "generation_timestamp": datetime.now().isoformat()
            }
            state["error_occurred"] = False

        # Record topic interaction in learning context
        learning_context.add_topic_interaction(topic)

    except Exception as e:
        state["error_occurred"] = True
        state["error_message"] = f"node_generate error: {e}"
        state["generated_example"] = None

    return state


# ─── Node 4: Format and Save ──────────────────────────────────────────────────

def node_format_and_save(state: PersonalizedGenerationState) -> PersonalizedGenerationState:
    """Save example to ExampleHistory and populate display fields."""
    user_id = state["user_id"]
    topic = state["topic"]
    generated_example = state.get("generated_example", "")
    example_metadata = state.get("example_metadata", {})
    profile_data = state.get("user_profile", {})

    try:
        # Reuse tags resolved in node_build_context; resolve fresh only if missing
        tags = state.get("topic_tags")
        if not tags:
            try:
                provider_fs, api_key_fs = _get_provider_and_key(state)
                tags = resolve_topic_tags(topic, provider_fs, api_key_fs)
                state["topic_tags"] = tags
            except Exception:
                tags = ["general_concept"]

        history = ExampleHistory(user_id=user_id)
        example_id = history.record_example(
            topic=topic,
            example_text=generated_example,
            profile_snapshot=profile_data,
            learning_context_snapshot=example_metadata,
            similar_users=[],
            tags=tags
        )

        state["example_id"] = example_id
        state["example_record"] = {
            "example_id": example_id,
            "topic": topic,
            "example_text": generated_example,
            "metadata": example_metadata,
            "timestamp": datetime.now().isoformat()
        }
        state["formatted_example"] = {
            "example_id": example_id,
            "topic": topic,
            "text": generated_example
        }
        state["display_metadata"] = {
            "topic": topic,
            "example_id": example_id,
            "generated_at": datetime.now().isoformat(),
            "provider": example_metadata.get("provider", "unknown"),
            "loop_count": state.get("loop_count", 0)
        }

    except Exception as e:
        fallback_id = f"ex_{uuid.uuid4().hex[:12]}"
        state["example_id"] = fallback_id
        state["formatted_example"] = {
            "example_id": fallback_id,
            "topic": topic,
            "text": generated_example
        }
        state["display_metadata"] = {
            "topic": topic,
            "example_id": fallback_id,
            "generated_at": datetime.now().isoformat()
        }
        state["error_message"] = f"node_format_and_save warning: {e}"

    return state


# ─── Node 5: User Review (Interrupt) ─────────────────────────────────────────

def node_user_review(state: PersonalizedGenerationState) -> PersonalizedGenerationState:
    """
    Interrupt workflow to collect natural-language user feedback.
    LangGraph pauses here and returns thread_id + example to the caller.
    Resumes when POST /workflows/{thread_id}/resume is called with user_feedback_text.
    """
    feedback = interrupt({
        "example": state.get("formatted_example"),
        "metadata": state.get("display_metadata"),
        "prompt": "What did you think of this example?"
    })

    return {
        "user_feedback_text": feedback.get("user_feedback_text", ""),
    }


# ─── Node 6: Process Feedback ─────────────────────────────────────────────────

def node_process_feedback(state: PersonalizedGenerationState) -> PersonalizedGenerationState:
    """
    Invoke the Adaptive Response Agent with the user's natural-language feedback.
    The agent autonomously decides to call regenerate / accept / flag_pattern.
    Writes regeneration_requested + regeneration_instruction back into state.
    """
    user_id = state["user_id"]
    example_id = state.get("example_id", "")
    topic = state["topic"]
    generated_example = state.get("generated_example") or ""
    user_feedback_text = state.get("user_feedback_text") or ""
    provider, api_key = _get_provider_and_key(state)

    # If generation failed upstream, skip feedback processing
    if state.get("error_occurred") and not generated_example:
        state["regeneration_requested"] = False
        state["regeneration_instruction"] = ""
        state["feedback_processed"] = False
        state["workflow_completed_at"] = datetime.now().isoformat()
        return state

    try:
        patterns = load_learning_patterns(user_id)

        result = invoke_adaptive_response_agent(
            user_id=user_id,
            example_id=example_id,
            topic=topic,
            example_text=generated_example,
            user_feedback_text=user_feedback_text,
            user_profile=state.get("user_profile", {}),
            pattern_history=patterns,
            provider=provider,
            api_key=api_key
        )

        state["regeneration_requested"] = result.get("regeneration_requested", False)
        state["regeneration_instruction"] = result.get("regeneration_instruction", "")
        state["feedback_processed"] = result.get("feedback_recorded", False)
        state["loop_count"] = state.get("loop_count", 0) + 1
        state["workflow_completed_at"] = datetime.now().isoformat()

    except Exception as e:
        state["regeneration_requested"] = False
        state["regeneration_instruction"] = ""
        state["feedback_processed"] = False
        state["error_occurred"] = True
        state["error_message"] = f"node_process_feedback error: {e}"
        state["workflow_completed_at"] = datetime.now().isoformat()

    return state
