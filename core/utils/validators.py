"""
Input Validation Utilities
"""

from typing import Dict, Any, Optional


def validate_feedback_ratings(
    difficulty: Optional[int],
    clarity: Optional[int],
    usefulness: Optional[int]
) -> tuple[bool, Optional[str]]:
    """
    Validate feedback ratings are in range 1-5

    Returns:
        (is_valid, error_message)
    """

    if difficulty is None or clarity is None or usefulness is None:
        return False, "All ratings (difficulty, clarity, usefulness) are required"

    if not isinstance(difficulty, int) or not isinstance(clarity, int) or not isinstance(usefulness, int):
        return False, "Ratings must be integers"

    if not (1 <= difficulty <= 5):
        return False, "Difficulty rating must be between 1 and 5"

    if not (1 <= clarity <= 5):
        return False, "Clarity rating must be between 1 and 5"

    if not (1 <= usefulness <= 5):
        return False, "Usefulness rating must be between 1 and 5"

    return True, None


def validate_user_id(user_id: Optional[str]) -> tuple[bool, Optional[str]]:
    """
    Validate user_id format

    Returns:
        (is_valid, error_message)
    """

    if not user_id:
        return False, "user_id is required"

    if not isinstance(user_id, str):
        return False, "user_id must be a string"

    if len(user_id) < 1 or len(user_id) > 100:
        return False, "user_id must be between 1 and 100 characters"

    return True, None


def validate_topic(topic: Optional[str]) -> tuple[bool, Optional[str]]:
    """
    Validate topic format

    Returns:
        (is_valid, error_message)
    """

    if not topic:
        return False, "topic is required"

    if not isinstance(topic, str):
        return False, "topic must be a string"

    if len(topic) < 1 or len(topic) > 500:
        return False, "topic must be between 1 and 500 characters"

    return True, None


def validate_workflow_start_request(data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate request to start a workflow

    Returns:
        (is_valid, error_message)
    """

    # Check user_id
    is_valid, error = validate_user_id(data.get("user_id"))
    if not is_valid:
        return False, error

    # Check topic
    is_valid, error = validate_topic(data.get("topic"))
    if not is_valid:
        return False, error

    # Check mode (optional)
    mode = data.get("mode", "adaptive")
    if mode not in ["simple", "adaptive"]:
        return False, "mode must be 'simple' or 'adaptive'"

    return True, None


def validate_workflow_resume_request(data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate request to resume a workflow with feedback

    Returns:
        (is_valid, error_message)
    """

    # Check ratings
    is_valid, error = validate_feedback_ratings(
        data.get("difficulty_rating"),
        data.get("clarity_rating"),
        data.get("usefulness_rating")
    )

    return is_valid, error
