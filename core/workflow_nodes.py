"""
Workflow Node Implementations
Individual node functions for LangGraph workflows.
"""

import time
import uuid
import os
from datetime import datetime
from typing import Dict
from langgraph.types import interrupt

from core.user_profile import UserProfile
from core.learning_context import LearningContext
from core.feedback_manager import FeedbackManager
from core.workflow_state import FeedbackGenerationState
from core.user_similarity import UserSimilarity
from core.example_history import ExampleHistory


def node_00_find_similar_users(state: FeedbackGenerationState) -> FeedbackGenerationState:
    """Node 0: Find similar users and retrieve effective examples (Collaborative Filtering)"""
    start_time = time.time()

    try:
        # Check if collaborative filtering is enabled
        use_cf = state.get("use_collaborative_filtering", False)

        if not use_cf:
            # Skip collaborative filtering
            state["similar_users"] = []
            state["source_examples"] = []
            state["collaborative_metadata"] = {
                "enabled": False,
                "reason": "Collaborative filtering not requested"
            }
        else:
            user_id = state["user_id"]
            topic = state["topic"]

            # Load user profile
            profile = UserProfile(user_id)
            profile_data = profile.profile_data
            state["user_profile_data"] = profile_data

            # Find similar users
            similarity_engine = UserSimilarity()
            all_profiles = similarity_engine.get_all_user_profiles()

            similar_users = similarity_engine.find_similar_users(
                target_user_id=user_id,
                target_profile=profile_data,
                all_profiles=all_profiles,
                top_k=5,
                min_similarity=0.3
            )

            # Get effective examples from similar users
            source_examples = []
            if similar_users:
                source_examples = ExampleHistory.get_similar_users_effective_examples(
                    similar_users=similar_users,
                    topic=topic,
                    min_score=0.5,
                    limit=3
                )

            # Store in state
            state["similar_users"] = [
                {"user_id": uid, "similarity": score}
                for uid, score in similar_users
            ]
            state["source_examples"] = source_examples
            state["collaborative_metadata"] = {
                "enabled": True,
                "num_similar_users": len(similar_users),
                "num_source_examples": len(source_examples),
                "total_users_analyzed": len(all_profiles)
            }

    except Exception as e:
        # Don't fail workflow if CF fails - fall back to standard generation
        state["similar_users"] = []
        state["source_examples"] = []
        state["collaborative_metadata"] = {
            "enabled": False,
            "error": str(e),
            "reason": "Collaborative filtering failed, using standard generation"
        }

    duration_ms = (time.time() - start_time) * 1000
    if "node_execution_times" not in state:
        state["node_execution_times"] = {}
    state["node_execution_times"]["node_00_find_similar_users"] = duration_ms

    return state


def node_01_generate_example(state: FeedbackGenerationState) -> FeedbackGenerationState:
    """Node 1: Generate personalized example"""
    start_time = time.time()

    try:
        from core.example_generator import ExampleGenerator
        from config.settings import DEFAULT_LLM_PROVIDER, LLM_API_KEYS

        # Get provider from state or use default
        provider = state.get("provider") or DEFAULT_LLM_PROVIDER
        api_key = LLM_API_KEYS.get(provider)

        if not api_key:
            raise ValueError(f"API key not configured for provider: {provider}")

        # Initialize generator with provider
        generator = ExampleGenerator(api_key=api_key, provider=provider)

        # Load user profile
        user_id = state["user_id"]
        topic = state["topic"]
        mode = state.get("mode", "adaptive")

        # Get profile and context summaries
        profile = UserProfile(user_id)
        profile_summary = profile.get_profile_summary()

        learning_context = LearningContext(user_id)
        context_summary = learning_context.get_learning_state_summary()

        # Get feedback history for influence tracking
        feedback_mgr = FeedbackManager(user_id)
        recent_feedback = feedback_mgr.get_feedback_patterns(topic=topic, limit=5)
        all_recent_feedback = feedback_mgr.get_feedback_patterns(limit=10)
        current_thresholds = feedback_mgr.get_current_thresholds()

        # Build feedback influence data
        feedback_influence = _build_feedback_influence(
            learning_context=learning_context,
            feedback_mgr=feedback_mgr,
            topic=topic,
            recent_feedback=recent_feedback,
            all_recent_feedback=all_recent_feedback,
            current_thresholds=current_thresholds
        )

        # Check if collaborative filtering data is available
        source_examples = state.get("source_examples", [])
        has_cf_context = len(source_examples) > 0

        # Generate example
        if has_cf_context:
            # Use collaborative filtering generation
            similar_users = state.get("similar_users", [])
            collaborative_context = generator._build_collaborative_context(
                source_examples=source_examples,
                similar_users=[(u["user_id"], u["similarity"]) for u in similar_users]
            )

            example = generator._generate_with_collaborative_context(
                topic=topic,
                user_profile=profile,
                learning_context=learning_context if mode == "adaptive" else None,
                collaborative_context=collaborative_context
            )
        elif mode == "adaptive":
            # Use the core generate_example method with UserProfile and LearningContext objects
            example = generator.generate_example(
                topic=topic,
                user_profile=profile,
                learning_context=learning_context
            )
        else:
            # Simple mode - use generate_example without learning context
            example = generator.generate_example(topic=topic, user_profile=profile)

        # Check for errors
        if example.startswith("Error generating example:"):
            state["error_occurred"] = True
            state["error_message"] = example
            state["generated_example"] = None
        else:
            state["generated_example"] = example
            state["user_profile_summary"] = profile_summary
            state["learning_context_summary"] = context_summary
            state["example_id"] = f"ex_{uuid.uuid4().hex[:12]}"
            state["confidence_score"] = 0.8
            state["error_occurred"] = False
            state["feedback_influence"] = feedback_influence

        # Record interaction in learning context
        learning_context.add_topic_interaction(topic)

    except Exception as e:
        state["error_occurred"] = True
        state["error_message"] = f"Error in generate_example node: {str(e)}"
        state["generated_example"] = None

    # Track execution time
    duration_ms = (time.time() - start_time) * 1000
    if "node_execution_times" not in state:
        state["node_execution_times"] = {}
    state["node_execution_times"]["node_01_generate_example"] = duration_ms

    return state


def _build_feedback_influence(
    learning_context: LearningContext,
    feedback_mgr: FeedbackManager,
    topic: str,
    recent_feedback: list,
    all_recent_feedback: list,
    current_thresholds: dict
) -> dict:
    """Build detailed feedback influence information"""

    influence = {
        "has_previous_feedback": len(all_recent_feedback) > 0,
        "topic_specific_feedback_count": len(recent_feedback),
        "total_feedback_count": len(all_recent_feedback),
        "adaptations_applied": [],
        "struggle_indicators": {},
        "mastery_indicators": {},
        "threshold_info": {},
        "recent_ratings_summary": {}
    }

    # Get struggle and mastery indicators from learning context
    struggles = learning_context.context_data.get("struggle_indicators", {})
    mastery = learning_context.context_data.get("mastery_indicators", {})

    # Check if current topic has struggle indicators
    if topic in struggles:
        struggle_info = struggles[topic]
        influence["struggle_indicators"] = {
            "is_struggling": True,
            "repeat_count": struggle_info.get("repeat_count", 0),
            "regeneration_count": struggle_info.get("regeneration_count", 0),
            "signal_type": struggle_info.get("signal_type", "unknown")
        }
        influence["adaptations_applied"].append({
            "type": "complexity_reduction",
            "reason": f"Detected struggle with '{topic}' ({struggle_info.get('repeat_count', 0)} repetitions, {struggle_info.get('regeneration_count', 0)} regenerations)",
            "action": "Simplified explanation, using more concrete examples"
        })

    # Check for mastery indicators
    if mastery:
        # Get the most recent mastery detection
        mastery_keys = sorted(mastery.keys(), reverse=True)
        if mastery_keys:
            latest_mastery = mastery[mastery_keys[0]]
            influence["mastery_indicators"] = {
                "showing_mastery": True,
                "progression_type": latest_mastery.get("type", "unknown"),
                "recent_topics": latest_mastery.get("topics", []),
                "unique_topic_count": latest_mastery.get("unique_topic_count", 0)
            }
            influence["adaptations_applied"].append({
                "type": "complexity_increase",
                "reason": f"Demonstrated mastery through {latest_mastery.get('unique_topic_count', 0)} diverse topics",
                "action": "Increased complexity, introducing advanced concepts"
            })

    # Summarize recent ratings
    if all_recent_feedback:
        avg_difficulty = sum(f.get("difficulty_rating", 3) for f in all_recent_feedback) / len(all_recent_feedback)
        avg_clarity = sum(f.get("clarity_rating", 3) for f in all_recent_feedback) / len(all_recent_feedback)
        avg_usefulness = sum(f.get("usefulness_rating", 3) for f in all_recent_feedback) / len(all_recent_feedback)

        influence["recent_ratings_summary"] = {
            "average_difficulty": round(avg_difficulty, 1),
            "average_clarity": round(avg_clarity, 1),
            "average_usefulness": round(avg_usefulness, 1),
            "sample_size": len(all_recent_feedback)
        }

        # Add adaptations based on ratings
        if avg_difficulty >= 4.0:
            influence["adaptations_applied"].append({
                "type": "difficulty_adjustment",
                "reason": f"Recent examples rated too difficult (avg: {avg_difficulty:.1f}/5)",
                "action": "Lowered complexity to match comfort level"
            })
        elif avg_difficulty <= 2.0:
            influence["adaptations_applied"].append({
                "type": "difficulty_adjustment",
                "reason": f"Recent examples rated too easy (avg: {avg_difficulty:.1f}/5)",
                "action": "Increased complexity for better challenge"
            })

        if avg_clarity < 3.0:
            influence["adaptations_applied"].append({
                "type": "clarity_improvement",
                "reason": f"Recent examples lacked clarity (avg: {avg_clarity:.1f}/5)",
                "action": "Using clearer explanations and simpler language"
            })

    # Include threshold information
    influence["threshold_info"] = {
        "struggle_threshold": current_thresholds.get("struggle_threshold", 3),
        "mastery_threshold": current_thresholds.get("mastery_threshold", 3),
        "last_calculated": current_thresholds.get("last_calculated", "Never")
    }

    # Add topic-specific feedback history
    if recent_feedback:
        influence["topic_feedback_history"] = [
            {
                "timestamp": f.get("timestamp", "unknown"),
                "difficulty": f.get("difficulty_rating"),
                "clarity": f.get("clarity_rating"),
                "usefulness": f.get("usefulness_rating")
            }
            for f in recent_feedback[:3]  # Last 3 feedback entries for this topic
        ]

    return influence


def node_02_prepare_display(state: FeedbackGenerationState) -> FeedbackGenerationState:
    """Node 2: Prepare example for display"""
    start_time = time.time()

    try:
        example = state.get("generated_example", "")
        formatted = example

        metadata = {
            "topic": state["topic"],
            "example_id": state.get("example_id", "unknown"),
            "generated_at": datetime.now().isoformat(),
            "mode": state.get("mode", "adaptive"),
            "profile_used": bool(state.get("user_profile_summary")),
            "context_used": bool(state.get("learning_context_summary"))
        }

        state["formatted_example"] = formatted
        state["display_metadata"] = metadata

    except Exception as e:
        state["error_occurred"] = True
        state["error_message"] = f"Error in prepare_display node: {str(e)}"

    duration_ms = (time.time() - start_time) * 1000
    if "node_execution_times" not in state:
        state["node_execution_times"] = {}
    state["node_execution_times"]["node_02_prepare_display"] = duration_ms

    return state


def node_03_interrupt_for_feedback(state: FeedbackGenerationState) -> FeedbackGenerationState:
    """Node 3: Interrupt workflow to collect user feedback"""
    start_time = time.time()

    # Check if feedback has already been provided (resume case)
    if state.get("difficulty_rating") is None:
        # Request feedback - this will pause the workflow
        interrupt({
            "message": "Please provide feedback",
            "example_id": state.get("example_id"),
            "formatted_example": state.get("formatted_example"),
            "awaiting": ["difficulty_rating", "clarity_rating", "usefulness_rating"]
        })

    duration_ms = (time.time() - start_time) * 1000
    if "node_execution_times" not in state:
        state["node_execution_times"] = {}
    state["node_execution_times"]["node_03_interrupt_for_feedback"] = duration_ms

    return state


def node_04_record_feedback(state: FeedbackGenerationState) -> FeedbackGenerationState:
    """Node 4: Record user feedback"""
    start_time = time.time()

    try:
        user_id = state["user_id"]
        example_id = state.get("example_id", "unknown")
        topic = state["topic"]

        difficulty = state.get("difficulty_rating")
        clarity = state.get("clarity_rating")
        usefulness = state.get("usefulness_rating")

        feedback_mgr = FeedbackManager(user_id)

        success = feedback_mgr.add_feedback(
            example_id=example_id,
            topic=topic,
            difficulty_rating=difficulty,
            clarity_rating=clarity,
            usefulness_rating=usefulness,
            example_text=state.get("generated_example")
        )

        state["feedback_recorded"] = success

    except Exception as e:
        state["error_occurred"] = True
        state["error_message"] = f"Error in record_feedback node: {str(e)}"
        state["feedback_recorded"] = False

    duration_ms = (time.time() - start_time) * 1000
    if "node_execution_times" not in state:
        state["node_execution_times"] = {}
    state["node_execution_times"]["node_04_record_feedback"] = duration_ms

    return state


def node_04b_record_example_history(state: FeedbackGenerationState) -> FeedbackGenerationState:
    """Node 4b: Record example in collaborative history"""
    start_time = time.time()

    try:
        user_id = state["user_id"]
        topic = state["topic"]
        example_text = state.get("generated_example")
        example_id = state.get("example_id")

        # Get ratings for effectiveness calculation
        difficulty = state.get("difficulty_rating")
        clarity = state.get("clarity_rating")
        usefulness = state.get("usefulness_rating")

        # Record in example history
        history = ExampleHistory(user_id=user_id)

        # Record the example with metadata
        history_example_id = history.record_example(
            topic=topic,
            example_text=example_text,
            profile_snapshot=state.get("user_profile_data"),
            learning_context_snapshot={},  # Could be added later
            similar_users=[(u["user_id"], u["similarity"]) for u in state.get("similar_users", [])]
        )

        # Determine if example was accepted based on ratings
        # Consider it accepted if all ratings are >= 3
        accepted = (
            difficulty is not None and
            clarity is not None and
            usefulness is not None and
            difficulty >= 3 and
            clarity >= 3 and
            usefulness >= 3
        )

        # Record feedback on the example
        if history_example_id:
            history.record_feedback(
                example_id=history_example_id,
                accepted=accepted,
                regeneration_requested=False  # Workflow doesn't track regenerations yet
            )

        state["example_history_recorded"] = True

    except Exception as e:
        # Don't fail workflow if history recording fails
        state["example_history_recorded"] = False
        print(f"Warning: Failed to record example history: {str(e)}")

    duration_ms = (time.time() - start_time) * 1000
    if "node_execution_times" not in state:
        state["node_execution_times"] = {}
    state["node_execution_times"]["node_04b_record_example_history"] = duration_ms

    return state


def node_05_update_learning_indicators(state: FeedbackGenerationState) -> FeedbackGenerationState:
    """Node 5: Update learning indicators based on feedback"""
    start_time = time.time()

    try:
        user_id = state["user_id"]
        topic = state["topic"]

        learning_context = LearningContext(user_id)

        # If difficulty was high (4-5), record struggle signal
        difficulty = state.get("difficulty_rating", 3)
        if difficulty >= 4:
            learning_context.record_session_struggle_signal(
                topic=topic,
                signal_type="difficulty_feedback"
            )

        state["indicators_updated"] = True

    except Exception as e:
        state["error_occurred"] = True
        state["error_message"] = f"Error in update_indicators node: {str(e)}"
        state["indicators_updated"] = False

    duration_ms = (time.time() - start_time) * 1000
    if "node_execution_times" not in state:
        state["node_execution_times"] = {}
    state["node_execution_times"]["node_05_update_learning_indicators"] = duration_ms

    return state


def node_06_calculate_adaptive_thresholds(state: FeedbackGenerationState) -> FeedbackGenerationState:
    """Node 6: Calculate new adaptive thresholds based on feedback history"""
    start_time = time.time()

    try:
        user_id = state["user_id"]
        feedback_mgr = FeedbackManager(user_id)
        new_thresholds = feedback_mgr.calculate_adaptive_thresholds()
        state["adaptive_thresholds"] = new_thresholds

    except Exception as e:
        state["error_occurred"] = True
        state["error_message"] = f"Error in calculate_thresholds node: {str(e)}"

    duration_ms = (time.time() - start_time) * 1000
    if "node_execution_times" not in state:
        state["node_execution_times"] = {}
    state["node_execution_times"]["node_06_calculate_adaptive_thresholds"] = duration_ms

    return state


def node_07_store_thresholds(state: FeedbackGenerationState) -> FeedbackGenerationState:
    """Node 7: Store adaptive thresholds (finalize workflow)"""
    start_time = time.time()

    # Thresholds already stored by FeedbackManager in node 6
    # This node marks the workflow as complete
    state["thresholds_adjusted"] = True
    state["workflow_completed_at"] = datetime.now().isoformat()

    duration_ms = (time.time() - start_time) * 1000
    if "node_execution_times" not in state:
        state["node_execution_times"] = {}
    state["node_execution_times"]["node_07_store_thresholds"] = duration_ms

    return state


def node_simple_generate(state: Dict) -> Dict:
    """Simple generation without feedback loop (backward compatibility)"""
    try:
        from core.example_generator import ExampleGenerator

        generator = ExampleGenerator(api_key=os.getenv("GEMINI_API_KEY"))
        profile = UserProfile(state["user_id"])

        example = generator.generate_example_simple(
            topic=state["topic"],
            user_profile=profile
        )

        if example.startswith("Error generating example:"):
            state["error_occurred"] = True
            state["error_message"] = example
            state["generated_example"] = None
        else:
            state["generated_example"] = example
            state["error_occurred"] = False

    except Exception as e:
        state["error_occurred"] = True
        state["error_message"] = f"Error in simple_generate node: {str(e)}"
        state["generated_example"] = None

    return state
