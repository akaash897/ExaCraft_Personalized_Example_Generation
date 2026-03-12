"""
Learning Context Management Module
Tracks dynamic learning behavior, struggle indicators, and mastery patterns.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, Optional

class LearningContext:
    """Tracks dynamic learning context and behavior signals"""
    
    def __init__(self, user_id: str = None):
        self.user_id = user_id
        self.context_file = f"learning_contexts/{user_id}.json" if user_id else None
        self.context_data = self.load_context() if user_id else {}
    
    def load_context(self) -> Dict:
        """Load learning context from JSON file"""
        if not self.context_file:
            return self.create_default_context()
            
        try:
            os.makedirs("learning_contexts", exist_ok=True)
            
            if os.path.exists(self.context_file):
                with open(self.context_file, 'r') as f:
                    context = json.load(f)
                    # Clean old entries (older than 7 days)
                    context = self.clean_old_entries(context)
                    return context
            else:
                return self.create_default_context()
        except Exception as e:
            print(f"Error loading learning context: {e}")
            return self.create_default_context()
    
    def create_default_context(self) -> Dict:
        """Create default learning context structure"""
        return {
            "user_id": self.user_id or "default",
            "recent_topics": [],
            "struggle_indicators": {},
            "mastery_indicators": {},
            "session_history": [],
            "last_updated": datetime.now().isoformat()
        }
    
    def clean_old_entries(self, context: Dict) -> Dict:
        """Remove entries older than 7 days"""
        cutoff_date = datetime.now() - timedelta(days=7)
        
        # Clean session history
        if "session_history" in context:
            context["session_history"] = [
                session for session in context["session_history"]
                if datetime.fromisoformat(session.get("timestamp", "2000-01-01")) > cutoff_date
            ]
        
        # Clean recent topics
        if "recent_topics" in context:
            context["recent_topics"] = [
                topic for topic in context["recent_topics"]
                if datetime.fromisoformat(topic.get("timestamp", "2000-01-01")) > cutoff_date
            ]
        
        return context
    
    def add_topic_interaction(self, topic: str, success_indicators: Dict = None):
        """Record interaction with a topic"""
        timestamp = datetime.now().isoformat()
        
        # Add to recent topics
        topic_entry = {
            "topic": topic,
            "timestamp": timestamp,
            "success_signals": success_indicators or {},
            "session_id": self.get_current_session_id()
        }
        
        if "recent_topics" not in self.context_data:
            self.context_data["recent_topics"] = []
        
        self.context_data["recent_topics"].append(topic_entry)
        
        # Keep only last 20 topics
        self.context_data["recent_topics"] = self.context_data["recent_topics"][-20:]
        
        self.context_data["last_updated"] = timestamp
        self.save_context()
    
    def get_learning_state_summary(self) -> str:
        """Generate summary of current learning state for prompt"""
        recent_topics = self.context_data.get("recent_topics", [])[-5:]
        struggles = self.context_data.get("struggle_indicators", {})
        mastery = self.context_data.get("mastery_indicators", {})

        summary_parts = []

        if recent_topics:
            topics_list = [t.get("topic") for t in recent_topics]
            summary_parts.append(f"Recent topics explored: {', '.join(topics_list)}")

        if struggles:
            struggling_topics = list(struggles.keys())
            summary_parts.append(f"Currently struggling with: {', '.join(struggling_topics)}")

        # PRIORITY 2 FIX: Handle multiple mastery detections
        # PRIORITY 3 FIX: Enhanced summary with specific topic progression
        if mastery:
            # Get most recent mastery detection
            mastery_keys = sorted(mastery.keys(), reverse=True)
            if mastery_keys:
                latest_mastery = mastery[mastery_keys[0]]
                topics = latest_mastery.get("topics", [])
                if topics:
                    summary_parts.append(
                        f"Demonstrated mastery progression through {len(topics)} topics: "
                        f"{' -> '.join(topics)}. Ready for increased complexity."
                    )
                else:
                    summary_parts.append("Showing good learning momentum with quick progression")

        if not summary_parts:
            summary_parts.append("First time learning session")

        return "; ".join(summary_parts)
    
    def get_current_session_id(self) -> str:
        """Get or create current session ID"""
        if "current_session" not in self.context_data:
            # No active session
            return "no_session"
        return self.context_data["current_session"]["session_id"]
    
    def save_context(self):
        """Save learning context to file"""
        if not self.context_file:
            return False
            
        try:
            with open(self.context_file, 'w') as f:
                json.dump(self.context_data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving learning context: {e}")
            return False

