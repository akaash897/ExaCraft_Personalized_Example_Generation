"""
Logging Configuration
"""

import logging
import json
from datetime import datetime
from pathlib import Path


class WorkflowLogger:
    """Structured logging for workflow events"""

    def __init__(self, user_id: str, thread_id: str):
        self.user_id = user_id
        self.thread_id = thread_id
        self.logger = logging.getLogger(f"workflow.{thread_id}")

        # Configure logger if not already configured
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def log_event(self, event_type: str, node_name: str, duration_ms: float, data: dict = None):
        """Structured logging for workflow events"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'thread_id': self.thread_id,
            'user_id': self.user_id,
            'event_type': event_type,  # 'node_start', 'node_complete', 'node_error', etc.
            'node_name': node_name,
            'duration_ms': duration_ms,
            'data': data or {}
        }
        self.logger.info(json.dumps(log_entry))

    def log_error(self, error: Exception, context: str = ""):
        """Log error with context"""
        self.logger.error(f"Error in {context}: {str(error)}", exc_info=True)


def setup_logging(log_level: str = "INFO"):
    """Setup application-wide logging"""

    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / "exacraft.log"),
            logging.StreamHandler()
        ]
    )
