"""
Workflow Manager
Orchestrates Primary Agent graph execution, thread management, and resumption.
"""

import uuid
from datetime import datetime
from typing import Dict, Optional, Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from core.workflow_graphs import build_primary_agent_graph
from core.workflow_state import PersonalizedGenerationState
from config.settings import DEFAULT_LLM_PROVIDER


class WorkflowManager:
    """Manages workflow execution and thread lifecycle."""

    def __init__(self, checkpointer=None):
        self.checkpointer = checkpointer or MemorySaver()
        self.primary_graph = build_primary_agent_graph(self.checkpointer)
        self.active_threads: Dict[str, Dict] = {}

    # ── Start ──────────────────────────────────────────────────────────────────

    def start_feedback_workflow(
        self,
        user_id: str,
        topic: str,
        mode: str = "adaptive",
        provider: str = None,
    ) -> Dict[str, Any]:
        """
        Start a new feedback generation workflow.

        Runs until the interrupt in node_user_review, then returns the generated
        example and thread_id so the caller can collect feedback and resume.
        """
        thread_id = f"thread_{uuid.uuid4().hex[:16]}"

        initial_state: PersonalizedGenerationState = {
            "user_id": user_id,
            "topic": topic,
            "thread_id": thread_id,
            "provider": provider or DEFAULT_LLM_PROVIDER,
            "loop_count": 0,
            "feedback_processed": False,
            "error_occurred": False,
            "workflow_started_at": datetime.now().isoformat()
        }

        config = {"configurable": {"thread_id": thread_id}}

        try:
            for _ in self.primary_graph.stream(initial_state, config):
                pass  # stream pauses automatically at interrupt

            snapshot = self.primary_graph.get_state(config)
            current_state = snapshot.values

            self.active_threads[thread_id] = {
                "user_id": user_id,
                "topic": topic,
                "status": "awaiting_feedback",
                "created_at": datetime.now().isoformat()
            }

            error_occurred = current_state.get("error_occurred", False)
            return {
                "success": not error_occurred,
                "thread_id": thread_id,
                "generated_example": current_state.get("generated_example"),
                "example_id": current_state.get("example_id"),
                "formatted_example": current_state.get("formatted_example"),
                "display_metadata": current_state.get("display_metadata"),
                "status": "awaiting_feedback",
                "error_occurred": error_occurred,
                "error_message": current_state.get("error_message"),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Workflow execution failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }

    # ── Resume ─────────────────────────────────────────────────────────────────

    def resume_feedback_workflow(
        self,
        thread_id: str,
        user_feedback_text: str = ""
    ) -> Dict[str, Any]:
        """
        Resume an interrupted workflow with the user's natural-language feedback.

        If the Adaptive Response Agent decides to regenerate, the graph loops back
        to node_generate and pauses again at node_user_review with the new example.
        In that case the response includes status: "awaiting_feedback" and the
        new example so the extension can display it and ask for feedback again.
        """
        config = {"configurable": {"thread_id": thread_id}}
        feedback_data = {"user_feedback_text": user_feedback_text}

        try:
            for _ in self.primary_graph.stream(Command(resume=feedback_data), config):
                pass

            snapshot = self.primary_graph.get_state(config)
            completed_state = snapshot.values

            # Check if still interrupted (regeneration loop caused a new interrupt)
            still_interrupted = bool(snapshot.next)

            if still_interrupted:
                # Adaptive Response Agent triggered regeneration — new example ready
                if thread_id in self.active_threads:
                    self.active_threads[thread_id]["status"] = "awaiting_feedback"

                return {
                    "success": True,
                    "status": "awaiting_feedback",
                    "regeneration_requested": True,
                    "generated_example": completed_state.get("generated_example"),
                    "example_id": completed_state.get("example_id"),
                    "formatted_example": completed_state.get("formatted_example"),
                    "display_metadata": completed_state.get("display_metadata"),
                    "loop_count": completed_state.get("loop_count", 0),
                    "thread_id": thread_id,
                    "message": "Example regenerated based on your feedback.",
                    "timestamp": datetime.now().isoformat()
                }
            else:
                # Workflow completed normally
                if thread_id in self.active_threads:
                    self.active_threads[thread_id]["status"] = "completed"

                error_occurred = completed_state.get("error_occurred", False)
                return {
                    "success": not error_occurred,
                    "status": "completed",
                    "feedback_processed": completed_state.get("feedback_processed", False),
                    "workflow_completed_at": completed_state.get("workflow_completed_at"),
                    "error_occurred": error_occurred,
                    "error_message": completed_state.get("error_message"),
                    "message": "Feedback recorded. Thanks!",
                    "timestamp": datetime.now().isoformat()
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"Resume failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }

    # ── Utilities ──────────────────────────────────────────────────────────────

    def get_workflow_state(self, thread_id: str) -> Dict[str, Any]:
        config = {"configurable": {"thread_id": thread_id}}
        try:
            snapshot = self.primary_graph.get_state(config)
            return {
                "success": True,
                "state": snapshot.values,
                "next": list(snapshot.next) if snapshot.next else [],
                "is_interrupted": bool(snapshot.next),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get state: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }

    def get_active_threads(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        threads = self.active_threads
        if user_id:
            threads = {tid: info for tid, info in threads.items()
                       if info.get("user_id") == user_id}
        return {
            "success": True,
            "active_threads": threads,
            "count": len(threads),
            "timestamp": datetime.now().isoformat()
        }

    def delete_workflow(self, thread_id: str) -> Dict[str, Any]:
        try:
            self.active_threads.pop(thread_id, None)
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
