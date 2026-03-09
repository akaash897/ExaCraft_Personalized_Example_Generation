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
    Synthesize the user's accumulated learning patterns and accept insights
    into a single context_instruction string for the generator.

    Reads:
        data/learning_patterns/{user_id}.json
        data/accept_insights/{user_id}.json

    Writes:
        state["context_instruction"]  — empty string on cold start (no LLM call)
    """
    user_id = state["user_id"]
    topic = state["topic"]
    provider, api_key = _get_provider_and_key(state)

    try:
        patterns_data = load_learning_patterns(user_id)
        insights_data = load_accept_insights(user_id)

        patterns = patterns_data.get("patterns", [])
        insights = insights_data.get("insights", [])

        # Cold start — nothing to synthesize
        if not patterns and not insights:
            state["context_instruction"] = ""
            return state

        # Build summary strings for LLM
        pattern_lines = "\n".join(
            f"- [{p['pattern_type']}] {p['observation']}"
            for p in patterns[-8:]  # last 8 patterns
        )
        insight_lines = "\n".join(
            f"- {i['insight']}"
            for i in insights[-8:]  # last 8 insights
        )

        llm = LLMProviderFactory.create_llm(provider, api_key, temperature=0.2)
        prompt_text = (
            "You are summarizing a student's learning history for an AI tutor.\n\n"
            f"Persistent learning patterns flagged over time:\n{pattern_lines or 'None'}\n\n"
            f"Recent positive feedback insights (what has worked):\n{insight_lines or 'None'}\n\n"
            f"Target topic for next example: {topic}\n\n"
            "In 2-3 sentences, write a specific and actionable instruction for the AI tutor "
            "about how to tailor the next example for this student. "
            "Be concrete. Output ONLY the instruction text — no labels, no preamble."
        )

        result = llm.invoke([HumanMessage(prompt_text)])
        state["context_instruction"] = result.content.strip()

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

        # Compose enriched context
        enriched_context = base_context
        if context_instruction:
            enriched_context += f"\n\nPERSONALIZATION INSTRUCTION (from learning history):\n{context_instruction}"
        if regeneration_instruction:
            enriched_context += (
                f"\n\nREGENERATION REQUEST (apply this change):\n{regeneration_instruction}"
            )

        # Clear regeneration instruction after consuming it
        state["regeneration_instruction"] = ""

        llm = LLMProviderFactory.create_llm(provider, api_key, temperature=0.3)

        prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are an adaptive AI tutor that personalizes examples based on the student's "
             "profile and learning history.\n\n"
             "STUDENT PROFILE:\n{user_profile}\n\n"
             "LEARNING CONTEXT:\n{learning_context}\n\n"
             "Generate a contextually adaptive example as a vivid scenario in 2-4 sentences. "
             "Use specific characters, locations, and situations that match the student's profile "
             "and learning history instructions. "
             "Output ONLY the example scenario — no explanations, no labels."),
            ("human", "Generate an example for the topic: {topic}")
        ])

        chain = prompt | llm
        result = chain.invoke({
            "user_profile": profile_summary,
            "learning_context": enriched_context,
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
        history = ExampleHistory(user_id=user_id)
        example_id = history.record_example(
            topic=topic,
            example_text=generated_example,
            profile_snapshot=profile_data,
            learning_context_snapshot=example_metadata,
            similar_users=[]
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
