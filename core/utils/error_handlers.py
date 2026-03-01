"""
Custom Error Handlers and Exceptions
"""


class WorkflowException(Exception):
    """Base exception for workflow errors"""
    pass


class NodeExecutionError(WorkflowException):
    """Node failed during execution"""

    def __init__(self, node_name: str, original_error: Exception):
        self.node_name = node_name
        self.original_error = original_error
        super().__init__(f"Node '{node_name}' failed: {str(original_error)}")


class CheckpointError(WorkflowException):
    """Checkpointing failed"""
    pass


class ThreadNotFoundError(WorkflowException):
    """Thread ID not found in checkpoint store"""
    pass


class ValidationError(WorkflowException):
    """Input validation failed"""
    pass


def handle_workflow_error(error: Exception, context: str = "") -> dict:
    """
    Convert exceptions to API-friendly error responses

    Args:
        error: The exception
        context: Optional context string

    Returns:
        Dict with error information
    """

    error_type = type(error).__name__

    if isinstance(error, ValidationError):
        status_code = 400
    elif isinstance(error, ThreadNotFoundError):
        status_code = 404
    elif isinstance(error, NodeExecutionError):
        status_code = 500
    else:
        status_code = 500

    return {
        "success": False,
        "error": str(error),
        "error_type": error_type,
        "context": context,
        "status_code": status_code
    }
