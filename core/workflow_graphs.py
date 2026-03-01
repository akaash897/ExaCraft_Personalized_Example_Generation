"""
Workflow Graph Definitions
Graph building logic for LangGraph workflows.
"""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from core.workflow_state import FeedbackGenerationState, SimpleGenerationState
from core.workflow_nodes import (
    node_00_find_similar_users,
    node_01_generate_example,
    node_02_prepare_display,
    node_03_interrupt_for_feedback,
    node_04_record_feedback,
    node_04b_record_example_history,
    node_05_update_learning_indicators,
    node_06_calculate_adaptive_thresholds,
    node_07_store_thresholds,
    node_simple_generate
)


def build_feedback_generation_graph(checkpointer=None):
    """
    Build the feedback generation workflow graph with collaborative filtering

    Workflow: find_similar → generate → prepare → interrupt → record_feedback →
              record_history → update → calculate → store
    """

    # Create graph builder
    builder = StateGraph(FeedbackGenerationState)

    # Add all nodes
    builder.add_node("node_00_find_similar_users", node_00_find_similar_users)
    builder.add_node("node_01_generate_example", node_01_generate_example)
    builder.add_node("node_02_prepare_display", node_02_prepare_display)
    builder.add_node("node_03_interrupt_for_feedback", node_03_interrupt_for_feedback)
    builder.add_node("node_04_record_feedback", node_04_record_feedback)
    builder.add_node("node_04b_record_example_history", node_04b_record_example_history)
    builder.add_node("node_05_update_indicators", node_05_update_learning_indicators)
    builder.add_node("node_06_calc_thresholds", node_06_calculate_adaptive_thresholds)
    builder.add_node("node_07_store_thresholds", node_07_store_thresholds)

    # Set entry point (start with collaborative filtering)
    builder.set_entry_point("node_00_find_similar_users")

    # Add edges (linear workflow with collaborative filtering)
    builder.add_edge("node_00_find_similar_users", "node_01_generate_example")
    builder.add_edge("node_01_generate_example", "node_02_prepare_display")
    builder.add_edge("node_02_prepare_display", "node_03_interrupt_for_feedback")
    builder.add_edge("node_03_interrupt_for_feedback", "node_04_record_feedback")
    builder.add_edge("node_04_record_feedback", "node_04b_record_example_history")
    builder.add_edge("node_04b_record_example_history", "node_05_update_indicators")
    builder.add_edge("node_05_update_indicators", "node_06_calc_thresholds")
    builder.add_edge("node_06_calc_thresholds", "node_07_store_thresholds")
    builder.add_edge("node_07_store_thresholds", END)

    # Compile with checkpointer
    if checkpointer is None:
        checkpointer = MemorySaver()

    return builder.compile(checkpointer=checkpointer)


def build_simple_generation_graph(checkpointer=None):
    """
    Build the simple generation workflow graph (no feedback loop)

    Workflow: generate → END
    """

    # Create graph builder
    builder = StateGraph(SimpleGenerationState)

    # Add node
    builder.add_node("node_simple_generate", node_simple_generate)

    # Set entry point
    builder.set_entry_point("node_simple_generate")

    # Add edge to END
    builder.add_edge("node_simple_generate", END)

    # Compile with checkpointer (optional for simple workflow)
    if checkpointer is None:
        checkpointer = MemorySaver()

    return builder.compile(checkpointer=checkpointer)


def build_extended_generation_graph(phases_enabled: dict, checkpointer=None):
    """
    Build extended workflow graph with Phase 2-4 features (future)

    Args:
        phases_enabled: Dict with keys like 'hallucination_detection', 'learning_stages', etc.
        checkpointer: Optional checkpointer
    """

    # This is a placeholder for Phase 2-4 implementation
    # For now, return the feedback generation graph
    return build_feedback_generation_graph(checkpointer)
