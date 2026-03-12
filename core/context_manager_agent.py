"""
ContextManager Agent
ReAct agent that reasons over a user's example history and feedback signals
to build a targeted context_instruction for the LLM tutor in node_generate.

Tools:
  get_examples_by_tag(tag)        — filter ExampleHistory by canonical tag
  get_linked_feedback(example_id) — load patterns+insights linked to an example
  get_global_signals(reason)      — load all patterns+insights (global fallback)
  emit_instruction(text)          — set final context_instruction and stop
"""

import json
from typing import List

from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage

from core.example_history import ExampleHistory
from core.feedback_store import load_learning_patterns, load_accept_insights
from core.subject_tag_metadata import load_subject_tag_metadata
from core.llm_provider import LLMProviderFactory
from config.settings import DEFAULT_LLM_PROVIDER, LLM_API_KEYS


# ─── Tag Resolution ────────────────────────────────────────────────────────────

def resolve_topic_tags(topic: str, provider: str, api_key: str) -> List[str]:
    """
    Use LLM to assign 1-3 canonical subject tags from the taxonomy for a topic.
    Called in both node_build_context (for agent reasoning) and node_format_and_save
    (to tag the saved example). Returns ['general_concept'] on any failure.
    """
    try:
        tag_metadata = load_subject_tag_metadata()
        tag_list_text = "\n".join(
            f"- {tag}: {info['description']}"
            for tag, info in tag_metadata.items()
        )
        llm = LLMProviderFactory.create_llm(provider, api_key, temperature=0.1)
        prompt = (
            f"You are an educational content classifier.\n\n"
            f"Available tags:\n{tag_list_text}\n\n"
            f"Topic: {topic}\n\n"
            f"Assign 1 to 3 tags from the list above that best match this topic. "
            f"Respond with ONLY a comma-separated list of tag names. No explanation."
        )
        result = llm.invoke([HumanMessage(prompt)])
        raw = result.content.strip().lower()
        tags = [t.strip().replace(" ", "_") for t in raw.split(",")]
        valid = [t for t in tags if t in tag_metadata]
        return valid if valid else ["general_concept"]
    except Exception:
        return ["general_concept"]


# ─── Tool Factory ──────────────────────────────────────────────────────────────

def _make_context_tools(user_id: str, result_holder: dict) -> list:
    """
    Create the 4 ContextManager tools with user_id captured in closure.
    result_holder: mutable dict — emit_instruction writes the final output here.
    """

    @tool
    def get_examples_by_tag(tag: str) -> str:
        """
        Return a JSON list of past examples whose tags include the given tag.
        Each entry includes: example_id, topic, text_snippet (200 chars), tags, timestamp,
        and the feedback outcome (accepted / regeneration_requested).
        tag: a canonical subject tag name (e.g. 'machine_learning', 'algorithms').
        """
        history = ExampleHistory(user_id=user_id)
        matches = history.get_examples_by_tag(tag)
        summary = [
            {
                "example_id": ex["example_id"],
                "topic": ex["topic"],
                "text_snippet": ex["example_text"][:200],
                "tags": ex.get("tags", []),
                "timestamp": ex["timestamp"],
                "feedback": ex.get("feedback", {})
            }
            for ex in matches[-10:]
        ]
        return json.dumps(summary)

    @tool
    def get_linked_feedback(example_id: str) -> str:
        """
        Return all learning patterns and accept insights linked to a specific example_id.
        Use this after get_examples_by_tag to retrieve the feedback signals for a specific example.
        example_id: the example_id string returned by get_examples_by_tag.
        """
        patterns_data = load_learning_patterns(user_id)
        insights_data = load_accept_insights(user_id)

        linked_patterns = [
            p for p in patterns_data.get("patterns", [])
            if p.get("example_id") == example_id
        ]
        linked_insights = [
            i for i in insights_data.get("insights", [])
            if i.get("example_id") == example_id
        ]
        return json.dumps({
            "example_id": example_id,
            "linked_patterns": linked_patterns,
            "linked_insights": linked_insights
        })

    @tool
    def get_global_signals(reason: str = "") -> str:
        """
        Return all learning patterns and recent accept insights for this user globally.
        Use this as a fallback when no tag-matched examples exist (cold start for this topic),
        or to supplement tag-specific findings with broader user traits.
        reason: optional note explaining why you are calling this (ignored, for reasoning trace).
        """
        patterns_data = load_learning_patterns(user_id)
        insights_data = load_accept_insights(user_id)
        return json.dumps({
            "global_patterns": patterns_data.get("patterns", [])[-10:],
            "recent_insights": insights_data.get("insights", [])[-10:]
        })

    @tool
    def emit_instruction(text: str) -> str:
        """
        Set the final context_instruction for the LLM tutor and finish reasoning.
        Call this ONCE as your last action after reasoning over all signals you gathered.
        text: 2-3 sentence actionable instruction for how to tailor the next example.
              If you found nothing useful, pass an empty string.
        """
        result_holder["context_instruction"] = text
        result_holder["_emit_called"] = True
        return json.dumps({"status": "instruction_set"})

    return [get_examples_by_tag, get_linked_feedback, get_global_signals, emit_instruction]


# ─── Main Agent Entry Point ────────────────────────────────────────────────────

def invoke_context_manager_agent(
    user_id: str,
    topic: str,
    topic_tags: List[str],
    provider: str = None,
    api_key: str = None
) -> str:
    """
    Invoke the ContextManager ReAct Agent.

    The agent:
    1. Calls get_examples_by_tag for each topic tag to find relevant past examples.
    2. Calls get_linked_feedback for relevant examples to retrieve associated patterns/insights.
    3. Falls back to get_global_signals if no tag-matched examples exist.
    4. Calls emit_instruction with a 2-3 sentence actionable tutor directive.

    Returns:
        context_instruction string (empty string on failure or nothing found).
    """
    provider = provider or DEFAULT_LLM_PROVIDER
    api_key = api_key or LLM_API_KEYS.get(provider, "")
    topic_tags = topic_tags or ["general_concept"]

    result_holder = {"context_instruction": "", "_emit_called": False}
    tools = _make_context_tools(user_id, result_holder)
    tool_map = {t.name: t for t in tools}

    system_prompt = f"""You are the ContextManager for an adaptive AI tutor system.
Your job is to examine this student's past example history and feedback signals,
then produce a precise, actionable instruction for the tutor LLM.

STUDENT: {user_id}
TOPIC FOR NEXT EXAMPLE: {topic}
TOPIC TAGS DETECTED: {', '.join(topic_tags)}

STEP-BY-STEP INSTRUCTIONS:
1. Call get_examples_by_tag for each of the detected topic tags to find relevant past examples.
2. For any relevant examples found, call get_linked_feedback to see what patterns
   and insights were recorded specifically for that example.
3. If no tag-matched examples exist, call get_global_signals to get the student's
   overall learning traits as a fallback.
4. Reason over everything you found: what has worked, what has failed, what this
   student struggles with or prefers.
5. Call emit_instruction ONCE with a specific, actionable instruction (2-3 sentences)
   telling the tutor how to tailor the next example. Reference specific findings.
   If you found nothing useful, call emit_instruction with an empty string.

CRITICAL RULES for emit_instruction:
- Your instruction must be relevant to the topic domain: {topic}.
- Do NOT carry over style preferences from a different domain.
  e.g. if the student's history is CS/coding but the topic is Fishing, Biology, or History —
  do NOT instruct the tutor to use code or programming analogies.
  Instead, focus on tone, complexity, analogy type, and depth appropriate for the topic.
- If the student's prior signals are domain-specific (e.g. "use Python code") and the
  current topic is unrelated to that domain, emit an empty string instead.

IMPORTANT: Always end with exactly one call to emit_instruction.
"""

    try:
        llm = LLMProviderFactory.create_llm(provider, api_key, temperature=0.2)
        llm_with_tools = llm.bind_tools(tools)

        messages = [
            SystemMessage(system_prompt),
            HumanMessage(f"Build a context instruction for topic: {topic}")
        ]

        MAX_ITERATIONS = 8
        for _ in range(MAX_ITERATIONS):
            response = llm_with_tools.invoke(messages)
            messages.append(response)

            if not response.tool_calls:
                break

            for tc in response.tool_calls:
                tool_name = tc.get("name", "")
                tool_args = tc.get("args", {})
                if tool_name in tool_map:
                    tool_result = tool_map[tool_name].invoke(tool_args)
                    messages.append(ToolMessage(
                        content=str(tool_result),
                        tool_call_id=tc.get("id", tool_name)
                    ))

            # Stop as soon as emit_instruction has been called
            if result_holder.get("_emit_called"):
                break

    except Exception as e:
        print(f"Warning: ContextManager Agent failed: {e}")
        return ""

    return result_holder.get("context_instruction", "")
