"""
Centralized Configuration and Settings
"""

import os
from pathlib import Path
from enum import Enum
from dotenv import load_dotenv

load_dotenv()


class Environment(Enum):
    DEV = "development"
    STAGING = "staging"
    PROD = "production"


# Environment
ENV = Environment(os.getenv('ENVIRONMENT', 'development'))
DEBUG = ENV == Environment.DEV

# Paths
ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / 'data'
LOGS_DIR = ROOT_DIR / 'logs'

# LangGraph Checkpointing
CHECKPOINT_TYPE = os.getenv('CHECKPOINT_TYPE', 'memory')  # 'memory', 'postgres', 'sqlite'
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://user:pass@localhost/exacraft')
CHECKPOINT_TTL_HOURS = int(os.getenv('CHECKPOINT_TTL_HOURS', '24'))
CHECKPOINT_CLEANUP_INTERVAL_HOURS = 6

# Max concurrent workflows per user
MAX_WORKFLOWS_PER_USER = 5

# Workflow timeouts
WORKFLOW_NODE_TIMEOUT_SECONDS = 30
WORKFLOW_INTERRUPT_TIMEOUT_HOURS = 24

# API Configuration
API_HOST = os.getenv('API_HOST', '0.0.0.0')
API_PORT = int(os.getenv('API_PORT', '8000'))
API_DEBUG = DEBUG

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG' if DEBUG else 'INFO')

# LLM Configuration - Multi-Provider Support
DEFAULT_LLM_PROVIDER = os.getenv('DEFAULT_LLM_PROVIDER', 'gemini')

# Provider-specific API Keys
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Provider-specific Models
GEMINI_DEFAULT_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
OPENAI_DEFAULT_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')

# Shared LLM Settings
LLM_TEMPERATURE = float(os.getenv('LLM_TEMPERATURE', '0.3'))
LLM_MAX_TOKENS = int(os.getenv('LLM_MAX_TOKENS', '2048'))

# Provider API Key Mapping
LLM_API_KEYS = {
    'gemini': GEMINI_API_KEY,
    'openai': OPENAI_API_KEY
}

# File Storage
USER_PROFILES_DIR = Path('user_profiles')
LEARNING_CONTEXTS_DIR = Path('learning_contexts')
FEEDBACK_HISTORY_DIR = DATA_DIR / 'feedback_history'
CHECKPOINTS_DIR = DATA_DIR / 'checkpoints'

# Create directories if not exist
for directory in [USER_PROFILES_DIR, LEARNING_CONTEXTS_DIR, FEEDBACK_HISTORY_DIR,
                  CHECKPOINTS_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)


def get_checkpointer():
    """
    Get appropriate checkpointer based on configuration

    Returns:
        LangGraph checkpointer instance
    """
    from langgraph.checkpoint.memory import MemorySaver

    if CHECKPOINT_TYPE == 'memory':
        return MemorySaver()
    elif CHECKPOINT_TYPE == 'postgres':
        try:
            from langgraph.checkpoint.postgres import PostgresSaver
            return PostgresSaver.from_conn_string(DATABASE_URL)
        except ImportError:
            print("Warning: langgraph[postgres] not installed, falling back to MemorySaver")
            return MemorySaver()
    elif CHECKPOINT_TYPE == 'sqlite':
        try:
            from langgraph.checkpoint.sqlite import SqliteSaver
            return SqliteSaver.from_conn_string(str(CHECKPOINTS_DIR / 'checkpoints.db'))
        except ImportError:
            print("Warning: langgraph[sqlite] not installed, falling back to MemorySaver")
            return MemorySaver()
    else:
        print(f"Warning: Unknown CHECKPOINT_TYPE '{CHECKPOINT_TYPE}', using MemorySaver")
        return MemorySaver()
