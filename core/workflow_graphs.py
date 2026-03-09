"""
Workflow Graph Definitions
Graph building logic for the Primary Agent (Adaptive Example Generation).

Flow:
  load_profile → build_context → generate → format_and_save
  → user_review (⏸ interrupt) → process_feedback
  → [conditional] regenerate? → generate (loop, max 3)
                  done?       → END
"""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from core.workflow_state import PersonalizedGenerationState
from core.workflow_nodes import (
    node_load_profile,
    node_build_context,
    node_generate,
    node_format_and_save,
    node_user_review,
    node_process_feedback,
)

MAX_REGENERATION_LOOPS = 3


def _route_after_feedback(state: PersonalizedGenerationState) -> str:
    """
    Conditional edge after node_process_feedback.
    Loops back to node_generate if the Adaptive Response Agent requested regeneration,
    subject to a max-loop guard to prevent infinite cycles.
    """
    if (state.get("regeneration_requested") and
            state.get("loop_count", 0) < MAX_REGENERATION_LOOPS):
        return "regenerate"
    return "end"


def build_primary_agent_graph(checkpointer=None):
    """
    Build the Primary Agent graph: Adaptive Example Generation with
    natural-language feedback loop.

    A checkpointer is required for the interrupt in node_user_review.
    """
    graph = StateGraph(PersonalizedGenerationState)

    graph.add_node("node_load_profile",     node_load_profile)
    graph.add_node("node_build_context",    node_build_context)
    graph.add_node("node_generate",         node_generate)
    graph.add_node("node_format_and_save",  node_format_and_save)
    graph.add_node("node_user_review",      node_user_review)
    graph.add_node("node_process_feedback", node_process_feedback)

    graph.set_entry_point("node_load_profile")

    graph.add_edge("node_load_profile",     "node_build_context")
    graph.add_edge("node_build_context",    "node_generate")
    graph.add_edge("node_generate",         "node_format_and_save")
    graph.add_edge("node_format_and_save",  "node_user_review")
    graph.add_edge("node_user_review",      "node_process_feedback")

    # Conditional: loop back to generate OR end
    graph.add_conditional_edges(
        "node_process_feedback",
        _route_after_feedback,
        {
            "regenerate": "node_generate",   # loop — skips build_context intentionally
            "end": END
        }
    )

    if checkpointer is None:
        checkpointer = MemorySaver()

    return graph.compile(checkpointer=checkpointer)


# Backward-compatibility alias
def build_feedback_generation_graph(checkpointer=None):
    return build_primary_agent_graph(checkpointer=checkpointer)
