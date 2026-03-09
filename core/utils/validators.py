"""
Input Validation Utilities
"""

from typing import Dict, Any, Optional, Tuple


def validate_user_id(user_id: Optional[str]) -> Tuple[bool, Optional[str]]:
    if not user_id:
        return False, "user_id is required"
    if not isinstance(user_id, str):
        return False, "user_id must be a string"
    if len(user_id) < 1 or len(user_id) > 100:
        return False, "user_id must be between 1 and 100 characters"
    return True, None


def validate_topic(topic: Optional[str]) -> Tuple[bool, Optional[str]]:
    if not topic:
        return False, "topic is required"
    if not isinstance(topic, str):
        return False, "topic must be a string"
    if len(topic) < 1 or len(topic) > 500:
        return False, "topic must be between 1 and 500 characters"
    return True, None


def validate_workflow_start_request(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    is_valid, error = validate_user_id(data.get("user_id"))
    if not is_valid:
        return False, error

    is_valid, error = validate_topic(data.get("topic"))
    if not is_valid:
        return False, error

    mode = data.get("mode", "adaptive")
    if mode not in ["simple", "adaptive"]:
        return False, "mode must be 'simple' or 'adaptive'"

    return True, None


def validate_workflow_resume_request(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate a workflow resume request.
    Accepts natural-language feedback text (empty string is valid — means user skipped).
    """
    if data is None:
        return False, "Request body is required"

    text = data.get("user_feedback_text")

    if text is None:
        return False, "user_feedback_text is required"

    if not isinstance(text, str):
        return False, "user_feedback_text must be a string"

    if len(text) > 2000:
        return False, "user_feedback_text must be 2000 characters or fewer"

    return True, None
