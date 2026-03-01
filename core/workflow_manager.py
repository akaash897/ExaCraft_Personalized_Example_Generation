"""
Workflow Manager
Orchestrates graph execution, thread management, and resumption.
"""

import uuid
from datetime import datetime
from typing import Dict, Optional, Any
from langgraph.checkpoint.memory import MemorySaver

from core.workflow_graphs import (
    build_feedback_generation_graph,
    build_simple_generation_graph
)
from core.workflow_state import FeedbackGenerationState, SimpleGenerationState


class WorkflowManager:
    """Manages workflow execution and thread lifecycle"""

    def __init__(self, checkpointer=None):
        """
        Initialize workflow manager

        Args:
            checkpointer: LangGraph checkpointer (MemorySaver, PostgresSaver, etc.)
        """
        self.checkpointer = checkpointer or MemorySaver()

        # Build graphs
        self.feedback_graph = build_feedback_generation_graph(self.checkpointer)
        self.simple_graph = build_simple_generation_graph(self.checkpointer)

        # Active threads tracking
        self.active_threads = {}

    def start_feedback_workflow(
        self,
        user_id: str,
        topic: str,
        mode: str = "adaptive",
        provider: str = None,
        use_collaborative_filtering: bool = True
    ) -> Dict[str, Any]:
        """
        Start a new feedback generation workflow with collaborative filtering

        Args:
            user_id: User identifier
            topic: Topic for example generation
            mode: "simple" or "adaptive"
            provider: LLM provider ("gemini" or "openai")
            use_collaborative_filtering: Enable collaborative filtering (default: True)

        Returns:
            Dict with thread_id, generated_example, example_id, status, CF metadata
        """

        # Generate thread ID
        thread_id = f"thread_{uuid.uuid4().hex[:16]}"

        # Initialize state
        initial_state: FeedbackGenerationState = {
            "user_id": user_id,
            "thread_id": thread_id,
            "topic": topic,
            "mode": mode,
            "provider": provider,  # Include provider in workflow state
            "use_collaborative_filtering": use_collaborative_filtering,
            "workflow_started_at": datetime.now().isoformat(),
            "error_occurred": False,
            "feedback_recorded": False,
            "example_history_recorded": False,
            "indicators_updated": False,
            "thresholds_adjusted": False,
            "node_execution_times": {},
            "checkpoints_created": []
        }

        # Configuration for this thread
        config = {"configurable": {"thread_id": thread_id}}

        # Invoke workflow (will run until interrupt)
        try:
            # Stream events until interrupt
            final_state = None
            for event in self.feedback_graph.stream(initial_state, config):
                final_state = event

            # Get current state after interrupt
            snapshot = self.feedback_graph.get_state(config)
            current_state = snapshot.values

            # Track active thread
            self.active_threads[thread_id] = {
                "user_id": user_id,
                "topic": topic,
                "status": "awaiting_feedback",
                "created_at": datetime.now().isoformat()
            }

            return {
                "success": True,
                "thread_id": thread_id,
                "generated_example": current_state.get("generated_example"),
                "example_id": current_state.get("example_id"),
                "formatted_example": current_state.get("formatted_example"),
                "display_metadata": current_state.get("display_metadata"),
                "feedback_influence": current_state.get("feedback_influence"),
                "similar_users": current_state.get("similar_users", []),
                "source_examples": current_state.get("source_examples", []),
                "collaborative_metadata": current_state.get("collaborative_metadata", {}),
                "status": "awaiting_feedback",
                "error_occurred": current_state.get("error_occurred", False),
                "error_message": current_state.get("error_message"),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Workflow execution failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }

    def resume_feedback_workflow(
        self,
        thread_id: str,
        difficulty_rating: int,
        clarity_rating: int,
        usefulness_rating: int
    ) -> Dict[str, Any]:
        """
        Resume interrupted feedback workflow with user feedback

        Args:
            thread_id: Thread identifier
            difficulty_rating: 1-5 rating
            clarity_rating: 1-5 rating
            usefulness_rating: 1-5 rating

        Returns:
            Dict with status, new_thresholds, completion info
        """

        config = {"configurable": {"thread_id": thread_id}}

        try:
            # Get current state
            snapshot = self.feedback_graph.get_state(config)
            current_state = snapshot.values

            # Update state with feedback
            current_state["difficulty_rating"] = difficulty_rating
            current_state["clarity_rating"] = clarity_rating
            current_state["usefulness_rating"] = usefulness_rating

            # Resume workflow from interrupt with updated state
            final_state = None
            for event in self.feedback_graph.stream(current_state, config):
                final_state = event

            # Get final state
            snapshot = self.feedback_graph.get_state(config)
            completed_state = snapshot.values

            # Update thread tracking
            if thread_id in self.active_threads:
                self.active_threads[thread_id]["status"] = "completed"

            return {
                "success": True,
                "status": "completed",
                "new_thresholds": completed_state.get("adaptive_thresholds"),
                "feedback_recorded": completed_state.get("feedback_recorded", False),
                "indicators_updated": completed_state.get("indicators_updated", False),
                "thresholds_adjusted": completed_state.get("thresholds_adjusted", False),
                "node_execution_times": completed_state.get("node_execution_times", {}),
                "message": "Feedback processed successfully",
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Resume failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }

    def get_workflow_state(self, thread_id: str) -> Dict[str, Any]:
        """
        Get current state of a workflow

        Args:
            thread_id: Thread identifier

        Returns:
            Dict with state, current_node, is_interrupted
        """

        config = {"configurable": {"thread_id": thread_id}}

        try:
            snapshot = self.feedback_graph.get_state(config)

            return {
                "success": True,
                "state": snapshot.values,
                "next": snapshot.next,
                "is_interrupted": len(snapshot.next) == 0,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get state: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }

    def invoke_simple_workflow(self, user_id: str, topic: str) -> Dict[str, Any]:
        """
        Invoke simple generation workflow (no feedback, no interrupt)

        Args:
            user_id: User identifier
            topic: Topic for example generation

        Returns:
            Dict with generated_example
        """

        initial_state: SimpleGenerationState = {
            "user_id": user_id,
            "topic": topic,
            "error_occurred": False
        }

        try:
            # Invoke graph (runs to completion)
            result = self.simple_graph.invoke(initial_state)

            return {
                "success": True,
                "generated_example": result.get("generated_example"),
                "error_occurred": result.get("error_occurred", False),
                "error_message": result.get("error_message"),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Simple workflow failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }

    def get_active_threads(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get list of active threads, optionally filtered by user_id

        Args:
            user_id: Optional user filter

        Returns:
            Dict with list of active threads
        """

        threads = self.active_threads

        if user_id:
            threads = {
                tid: info for tid, info in threads.items()
                if info.get("user_id") == user_id
            }

        return {
            "success": True,
            "active_threads": threads,
            "count": len(threads),
            "timestamp": datetime.now().isoformat()
        }

    def delete_workflow(self, thread_id: str) -> Dict[str, Any]:
        """
        Delete/cancel a workflow

        Args:
            thread_id: Thread identifier

        Returns:
            Dict with success status
        """

        try:
            # Remove from active threads
            if thread_id in self.active_threads:
                del self.active_threads[thread_id]

            # Note: Checkpointer cleanup would happen here
            # For MemorySaver, garbage collection handles it
            # For PostgresSaver, you'd delete from DB

            return {
                "success": True,
                "message": f"Workflow {thread_id} deleted",
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Delete failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
