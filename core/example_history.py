"""
Example History Module
Tracks generated examples and their effectiveness per user for collaborative filtering
"""

import os
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List


class ExampleHistory:
    """Tracks example generation history and effectiveness metrics"""

    def __init__(self, user_id: str = None):
        self.user_id = user_id
        self.history_file = f"data/example_history/{user_id}.json" if user_id else None
        self.history_data = self.load_history() if user_id else {}

    def load_history(self) -> Dict:
        """Load example history from JSON file"""
        if not self.history_file:
            return self.create_default_history()

        try:
            os.makedirs("data/example_history", exist_ok=True)

            if os.path.exists(self.history_file):
                with open(self.history_file, 'r') as f:
                    history = json.load(f)
                    # Clean old entries (older than 30 days)
                    history = self.clean_old_entries(history)
                    return history
            else:
                return self.create_default_history()
        except Exception as e:
            print(f"Error loading example history: {e}")
            return self.create_default_history()

    def create_default_history(self) -> Dict:
        """Create default history structure"""
        return {
            "user_id": self.user_id or "default",
            "examples": [],
            "topic_examples": {},  # topic -> list of example IDs
            "effectiveness_scores": {},  # example_id -> score
            "last_updated": datetime.now().isoformat()
        }

    def clean_old_entries(self, history: Dict) -> Dict:
        """Remove entries older than 30 days"""
        cutoff_date = datetime.now() - timedelta(days=30)

        if "examples" in history:
            history["examples"] = [
                ex for ex in history["examples"]
                if datetime.fromisoformat(ex.get("timestamp", "2000-01-01")) > cutoff_date
            ]

            # Rebuild topic_examples index
            topic_examples = {}
            for ex in history["examples"]:
                topic = ex.get("topic")
                example_id = ex.get("example_id")
                if topic and example_id:
                    if topic not in topic_examples:
                        topic_examples[topic] = []
                    topic_examples[topic].append(example_id)

            history["topic_examples"] = topic_examples

        return history

    def record_example(self, topic: str, example_text: str, profile_snapshot: Dict = None,
                      learning_context_snapshot: Dict = None, similar_users: List = None) -> str:
        """
        Record a generated example

        Args:
            topic: The topic of the example
            example_text: The generated example text
            profile_snapshot: Snapshot of user profile at generation time
            learning_context_snapshot: Snapshot of learning context at generation time
            similar_users: List of (user_id, similarity_score) that influenced this example

        Returns:
            example_id: Unique ID for this example
        """
        timestamp = datetime.now().isoformat()
        example_id = f"ex_{uuid.uuid4().hex[:16]}"

        example_entry = {
            "example_id": example_id,
            "topic": topic,
            "example_text": example_text,
            "timestamp": timestamp,
            "profile_snapshot": profile_snapshot or {},
            "learning_context_snapshot": learning_context_snapshot or {},
            "similar_users_used": similar_users or [],
            "feedback": {
                "accepted": None,  # True if kept, False if regenerated
                "regeneration_requested": False,
                "time_to_action_seconds": None
            },
            "effectiveness_score": None  # Will be calculated later
        }

        if "examples" not in self.history_data:
            self.history_data["examples"] = []

        self.history_data["examples"].append(example_entry)

        # Update topic index
        if "topic_examples" not in self.history_data:
            self.history_data["topic_examples"] = {}

        if topic not in self.history_data["topic_examples"]:
            self.history_data["topic_examples"][topic] = []

        self.history_data["topic_examples"][topic].append(example_id)

        # Keep only last 100 examples
        self.history_data["examples"] = self.history_data["examples"][-100:]

        self.history_data["last_updated"] = timestamp
        self.save_history()

        return example_id

    def save_history(self):
        """Save history to file"""
        if not self.history_file:
            return False

        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.history_data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving example history: {e}")
            return False

