"""
Workflow State Schemas
TypedDict definitions for LangGraph workflow states.
"""

from typing import TypedDict, Optional, Dict, List


class FeedbackGenerationState(TypedDict, total=False):
    """State for feedback generation workflow"""

    # Identifiers
    user_id: str
    thread_id: str
    example_id: str

    # Request parameters
    topic: str
    mode: str  # "simple" or "adaptive"
    provider: Optional[str]  # LLM provider ("gemini" or "openai")
    use_collaborative_filtering: bool  # Enable collaborative filtering

    # Generation phase outputs
    user_profile_summary: Optional[str]
    learning_context_summary: Optional[str]
    generated_example: Optional[str]
    confidence_score: Optional[float]

    # Collaborative filtering outputs
    user_profile_data: Optional[Dict]  # Full profile for similarity matching
    similar_users: Optional[List[Dict]]  # [{user_id, similarity_score}]
    source_examples: Optional[List[Dict]]  # Examples from similar users
    collaborative_metadata: Optional[Dict]  # CF metadata

    # Display phase outputs
    formatted_example: Optional[str]
    display_metadata: Optional[Dict]

    # Feedback phase inputs (from interrupt resume)
    difficulty_rating: Optional[int]  # 1-5
    clarity_rating: Optional[int]      # 1-5
    usefulness_rating: Optional[int]   # 1-5

    # Processing phase outputs
    feedback_recorded: bool
    example_history_recorded: bool  # Track if added to collaborative history
    indicators_updated: bool
    thresholds_adjusted: bool
    adaptive_thresholds: Optional[Dict]  # Calculated thresholds from node_06

    # Feedback influence data
    feedback_influence: Optional[Dict]  # Detailed influence tracking

    # Metadata
    workflow_started_at: str
    workflow_completed_at: Optional[str]
    error_occurred: bool
    error_message: Optional[str]

    # Tracking
    node_execution_times: Dict[str, float]  # {node_name: duration_ms}
    checkpoints_created: List[str]   # [checkpoint_ids]


class SimpleGenerationState(TypedDict, total=False):
    """Minimal state for backward compatible simple generation"""
    
    user_id: str
    topic: str
    generated_example: Optional[str]
    error_occurred: bool
    error_message: Optional[str]


class ExtendedGenerationState(FeedbackGenerationState, total=False):
    """Extended state for Phase 2+ features (future)"""
    
    # Phase 2 fields
    hallucination_detected: Optional[bool]
    hallucination_confidence: Optional[float]
    hallucination_details: Optional[Dict]
    
    # Phase 3 fields
    creativity_score: Optional[float]
    learning_stage: Optional[str]  # "novice", "developing", "proficient", "mastery"
    pedagogical_template_used: Optional[str]
    
    # Additional
    processing_trace: List[Dict]  # {node, status, output}
