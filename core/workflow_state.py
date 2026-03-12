"""
Workflow State Schemas
TypedDict definitions for LangGraph workflow states.
"""

from typing import TypedDict, Optional, Dict, Any


class PersonalizedGenerationState(TypedDict, total=False):
    """State for the Primary Agent: Adaptive Example Generation"""

    # Input
    user_id: str
    topic: str
    thread_id: str
    provider: Optional[str]           # "gemini" | "openai" — flows through all LLM calls

    # Profile
    user_profile: Optional[Dict[str, Any]]
    profile_summary: Optional[str]

    # Context (from node_build_context — synthesized from patterns + insights)
    context_instruction: Optional[str]

    # Generation
    generated_example: Optional[str]
    example_metadata: Optional[Dict[str, Any]]

    # Save
    example_id: Optional[str]
    example_record: Optional[Dict[str, Any]]

    # Display
    formatted_example: Optional[Dict[str, Any]]
    display_metadata: Optional[Dict[str, Any]]

    # User feedback (post-interrupt) — natural language only
    user_feedback_text: Optional[str]

    # Adaptive Response Agent decisions
    regeneration_requested: Optional[bool]
    regeneration_instruction: Optional[str]   # cleared after use in node_generate

    # Loop guard — max 3 regeneration cycles per thread
    loop_count: Optional[int]

    # Processing
    feedback_processed: bool

    # Error tracking
    error_occurred: bool
    error_message: Optional[str]

    # Timestamps
    workflow_started_at: Optional[str]
    workflow_completed_at: Optional[str]

