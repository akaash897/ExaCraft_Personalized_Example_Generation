"""
Adaptive Response Agent (formerly Subagent B: Feedback Processor)

Reads natural-language user feedback and autonomously decides what to do:
  - regenerate(instruction)   → example needs to change immediately
  - accept(insight)           → example was fine, store what worked
  - flag_pattern(type, obs)   → persistent learning trait detected

Uses LangChain bind_tools() — compatible with both Gemini and OpenAI.
"""

import json
import uuid
from datetime import datetime
from typing import Dict, Any, List

from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage

from core.llm_provider import LLMProviderFactory
from core.feedback_store import (
    save_nl_feedback_entry,
    append_accept_insight,
    append_learning_pattern,
    update_subject_tag_index,
    update_feedback_by_recency_index,
    update_subject_tag_statistics,
)
from core.subject_tag_metadata import load_subject_tag_metadata
from config.settings import DEFAULT_LLM_PROVIDER, LLM_API_KEYS


# ─── Tool Factory ─────────────────────────────────────────────────────────────

def _make_tools(user_id: str, example_id: str, topic: str, decisions: list):
    """
    Create the 3 agent tools with user context captured in closure.
    All parameters are str to ensure Gemini + OpenAI schema compatibility.

    decisions: mutable list — tools append to it so the caller can inspect
               which tools were actually called after agent invocation.
    """

    @tool
    def regenerate(instruction: str) -> str:
        """
        Call this when the example needs to be regenerated immediately.
        Use when the user says the example was too hard, too easy, confusing,
        off-topic, wrong domain, or explicitly asks for a different approach.
        instruction: specific instruction for how to improve the next example.
        """
        decisions.append({"tool": "regenerate", "instruction": instruction})
        return json.dumps({"action": "regenerate", "instruction": instruction})

    @tool
    def accept(insight: str) -> str:
        """
        Call this when the example was satisfactory or the feedback is positive or neutral.
        Also call this if the user skipped feedback with no text.
        insight: one sentence capturing what worked or was appreciated.
        """
        append_accept_insight(user_id, insight, example_id)
        decisions.append({"tool": "accept", "insight": insight})
        return json.dumps({"action": "accept", "insight": insight})

    @tool
    def flag_pattern(pattern_type: str, observation: str) -> str:
        """
        Call this when you detect a PERSISTENT learning trait that should
        influence ALL future example generations for this user — not just the next one.
        Use when the feedback reveals something recurring or fundamental about
        how this user learns.
        pattern_type: one of domain_preference, struggle_area, style_preference,
                      mastery_signal, complexity_preference.
        observation: specific evidence from the feedback, 1-2 sentences.
        """
        append_learning_pattern(user_id, pattern_type, observation, example_id)
        decisions.append({"tool": "flag_pattern", "pattern_type": pattern_type,
                          "observation": observation})
        return json.dumps({"action": "flag_pattern", "pattern_type": pattern_type})

    return [regenerate, accept, flag_pattern]


# ─── Subject Tagger (lightweight, separate LLM call) ─────────────────────────

def _assign_subject_tag(topic: str, example_text: str, provider: str, api_key: str) -> str:
    """Assign a semantic subject tag via LLM. Falls back to 'general_concept'."""
    try:
        tag_metadata = load_subject_tag_metadata()
        tag_list = "\n".join(
            f"- {tag}: {info['description']} (domain: {info['domain']})"
            for tag, info in tag_metadata.items()
        )
        llm = LLMProviderFactory.create_llm(provider, api_key, temperature=0.1)
        prompt = (
            f"You are an educational content classifier.\n\n"
            f"Available tags:\n{tag_list}\n\n"
            f"Topic: {topic}\nExample (truncated): {example_text[:600]}\n\n"
            f"Respond with ONLY the single best tag name from the list above. No explanation."
        )
        result = llm.invoke([HumanMessage(prompt)])
        tag = result.content.strip().lower().replace(" ", "_")
        return tag if tag in tag_metadata else "general_concept"
    except Exception:
        return "general_concept"


# ─── Main Agent Entry Point ───────────────────────────────────────────────────

def invoke_adaptive_response_agent(
    user_id: str,
    example_id: str,
    topic: str,
    example_text: str,
    user_feedback_text: str,
    user_profile: dict,
    pattern_history: dict,
    provider: str = None,
    api_key: str = None
) -> Dict[str, Any]:
    """
    Invoke the Adaptive Response Agent with natural-language user feedback.

    The agent reads the feedback and autonomously calls one or more tools:
      regenerate(instruction)     — triggers immediate re-generation
      accept(insight)             — logs positive/neutral signal
      flag_pattern(type, obs)     — stores persistent learning trait

    Returns:
        {
            regeneration_requested: bool,
            regeneration_instruction: str,
            agent_decisions: list,
            subject_tag: str,
            feedback_recorded: bool
        }
    """
    provider = provider or DEFAULT_LLM_PROVIDER
    api_key = api_key or LLM_API_KEYS.get(provider, "")

    # ── Short-circuit: user skipped (empty text) ──────────────────────────────
    if not user_feedback_text or not user_feedback_text.strip():
        subject_tag = _assign_subject_tag(topic, example_text, provider, api_key)
        entry = {
            "entry_id": f"fb_{uuid.uuid4().hex[:12]}",
            "example_id": example_id,
            "topic": topic,
            "subject_tag": subject_tag,
            "user_feedback_text": "",
            "agent_decision": "skipped",
            "regeneration_requested": False,
            "regeneration_instruction": "",
            "timestamp": datetime.now().isoformat()
        }
        save_nl_feedback_entry(user_id, entry)
        update_subject_tag_index(user_id, example_id, subject_tag)
        update_feedback_by_recency_index(user_id, example_id)
        update_subject_tag_statistics(user_id, subject_tag, "skipped")
        return {
            "regeneration_requested": False,
            "regeneration_instruction": "",
            "agent_decisions": [{"tool": "skipped"}],
            "subject_tag": subject_tag,
            "feedback_recorded": True
        }

    # ── Build context strings ─────────────────────────────────────────────────
    profile_lines = []
    if user_profile:
        profile_lines.append(f"Name: {user_profile.get('name', 'Unknown')}")
        profile_lines.append(f"Profession: {user_profile.get('profession', 'Unknown')}")
        profile_lines.append(f"Education: {user_profile.get('education', 'Unknown')}")
        profile_lines.append(f"Complexity preference: {user_profile.get('complexity', 'medium')}")
    profile_summary = "\n".join(profile_lines) if profile_lines else "No profile available."

    patterns = pattern_history.get("patterns", []) if pattern_history else []
    if patterns:
        pattern_lines = [f"- [{p['pattern_type']}] {p['observation']}" for p in patterns[-5:]]
        pattern_summary = "\n".join(pattern_lines)
    else:
        pattern_summary = "No prior patterns recorded."

    # ── System prompt ─────────────────────────────────────────────────────────
    system_prompt = f"""You are an adaptive learning agent for an educational AI tutor.
A student just received an example and gave natural language feedback.
Your job is to interpret the feedback and call the appropriate tool(s).

STUDENT PROFILE:
{profile_summary}

TOPIC: {topic}

EXAMPLE SHOWN TO STUDENT:
{example_text[:800]}

KNOWN LEARNING PATTERNS (from previous sessions):
{pattern_summary}

AVAILABLE TOOLS — you MUST call at least one:
- regenerate(instruction): call when the example needs to change RIGHT NOW.
  Use when feedback indicates confusion, wrong difficulty, wrong domain, or an explicit request for change.
  instruction should be a specific, actionable improvement directive.

- accept(insight): call when the example was fine or feedback is positive/neutral.
  insight should capture what worked or what the student appreciated.

- flag_pattern(pattern_type, observation): call when you detect a PERSISTENT trait
  that should influence ALL future generations — not just the next one.
  pattern_type: domain_preference | struggle_area | style_preference | mastery_signal | complexity_preference
  Can be combined with regenerate (e.g. regenerate + flag_pattern).

DECISION GUIDE:
- "too hard" / "confusing" / "I don't get it" → regenerate
- "use X domain" / "I'm a nurse/chef/engineer" → regenerate + flag_pattern(domain_preference)
- "too easy" / "I already know this" → regenerate + flag_pattern(mastery_signal)
- "got it" / "makes sense" / "helpful" → accept
- "a bit long" / "prefers shorter" → accept + flag_pattern(style_preference)
- Consistently struggling (patterns show repeated issues) → regenerate + flag_pattern(struggle_area)
"""

    # ── Invoke LLM with tools ─────────────────────────────────────────────────
    decisions: List[dict] = []
    tools = _make_tools(user_id, example_id, topic, decisions)

    try:
        llm = LLMProviderFactory.create_llm(provider, api_key, temperature=0.2)
        llm_with_tools = llm.bind_tools(tools)

        messages = [
            SystemMessage(system_prompt),
            HumanMessage(f'Student feedback: "{user_feedback_text}"')
        ]

        response = llm_with_tools.invoke(messages)

        # Execute tool calls from response
        if response.tool_calls:
            tool_map = {t.name: t for t in tools}
            for tc in response.tool_calls:
                tool_name = tc.get("name", "")
                tool_args = tc.get("args", {})
                if tool_name in tool_map:
                    tool_map[tool_name].invoke(tool_args)

        # If LLM made no tool calls, default to accept
        if not decisions:
            append_accept_insight(user_id, "No clear signal from feedback — logged as neutral.", example_id)
            decisions.append({"tool": "accept", "insight": "Neutral feedback, no action taken."})

    except Exception as e:
        print(f"Warning: Adaptive Response Agent LLM call failed: {e}")
        # Safe fallback: accept with error note
        decisions.append({"tool": "accept", "insight": f"Agent error, logged as neutral: {e}"})

    # ── Extract regeneration decision ─────────────────────────────────────────
    regeneration_requested = False
    regeneration_instruction = ""
    for d in decisions:
        if d.get("tool") == "regenerate":
            regeneration_requested = True
            regeneration_instruction = d.get("instruction", "")
            break

    # ── Determine primary agent_decision for storage ──────────────────────────
    if regeneration_requested:
        primary_decision = "regenerate"
    elif any(d.get("tool") == "flag_pattern" for d in decisions):
        primary_decision = "flag_pattern"
    else:
        primary_decision = "accept"

    # ── Assign subject tag ────────────────────────────────────────────────────
    subject_tag = _assign_subject_tag(topic, example_text, provider, api_key)

    # ── Persist feedback entry ────────────────────────────────────────────────
    entry = {
        "entry_id": f"fb_{uuid.uuid4().hex[:12]}",
        "example_id": example_id,
        "topic": topic,
        "subject_tag": subject_tag,
        "user_feedback_text": user_feedback_text,
        "agent_decision": primary_decision,
        "agent_decisions_log": decisions,
        "regeneration_requested": regeneration_requested,
        "regeneration_instruction": regeneration_instruction,
        "timestamp": datetime.now().isoformat()
    }
    saved = save_nl_feedback_entry(user_id, entry)
    update_subject_tag_index(user_id, example_id, subject_tag)
    update_feedback_by_recency_index(user_id, example_id)
    update_subject_tag_statistics(user_id, subject_tag, primary_decision)

    return {
        "regeneration_requested": regeneration_requested,
        "regeneration_instruction": regeneration_instruction,
        "agent_decisions": decisions,
        "subject_tag": subject_tag,
        "feedback_recorded": saved
    }
