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
        
        # Update current session
        self.update_current_session(topic, timestamp)
        
        # Update struggle/mastery indicators
        self.update_learning_indicators(topic, success_indicators or {})
        
        self.context_data["last_updated"] = timestamp
        self.save_context()
    
    def update_learning_indicators(self, topic: str, signals: Dict):
        """Update struggle and mastery indicators"""

        # PRIORITY 1 FIX: Check regeneration signals from current session
        regeneration_count = 0
        if "current_session" in self.context_data:
            session = self.context_data["current_session"]
            regeneration_count = sum(1 for s in session.get("struggle_signals", [])
                                   if s.get("signal_type") == "regeneration_requested"
                                   and s.get("topic") == topic)

        # Count topic repetitions (struggle indicator)
        topic_count = sum(1 for t in self.context_data.get("recent_topics", [])
                         if t.get("topic") == topic)

        # PRIORITY 1 FIX: Detect struggle from EITHER topic repetition OR regeneration requests
        # Threshold: 3+ repetitions OR 2+ regenerations = struggle
        is_struggling = (topic_count >= 3) or (regeneration_count >= 2)

        if is_struggling:
            if "struggle_indicators" not in self.context_data:
                self.context_data["struggle_indicators"] = {}
            self.context_data["struggle_indicators"][topic] = {
                "repeat_count": topic_count,
                "regeneration_count": regeneration_count,
                "last_seen": datetime.now().isoformat(),
                "signal_type": "regeneration" if regeneration_count >= 2 else "repetition"
            }

        # Quick successive different topics (mastery indicator)
        # PRIORITY 2 FIX: Track multiple mastery moments with unique identifiers
        recent_topics = self.context_data.get("recent_topics", [])[-5:]
        if len(recent_topics) >= 3:
            unique_topics = len(set(t.get("topic") for t in recent_topics))
            if unique_topics >= 3:  # Quick progression through different topics
                if "mastery_indicators" not in self.context_data:
                    self.context_data["mastery_indicators"] = {}

                # Create unique mastery ID using timestamp with microseconds + counter
                # to ensure uniqueness even for rapid successive detections
                base_id = f"mastery_{int(datetime.now().timestamp())}"
                counter = 0
                mastery_id = base_id
                while mastery_id in self.context_data["mastery_indicators"]:
                    counter += 1
                    mastery_id = f"{base_id}_{counter}"

                topic_list = [t.get("topic") for t in recent_topics]

                self.context_data["mastery_indicators"][mastery_id] = {
                    "type": "quick_progression",
                    "topics": topic_list,
                    "unique_topic_count": unique_topics,
                    "timestamp": datetime.now().isoformat()
                }

                # Keep only last 5 mastery detections to prevent unbounded growth
                mastery_keys = sorted(self.context_data["mastery_indicators"].keys())
                if len(mastery_keys) > 5:
                    for old_key in mastery_keys[:-5]:
                        del self.context_data["mastery_indicators"][old_key]
    
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
    
    def start_learning_session(self) -> str:
        """Start a new learning session"""
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        timestamp = datetime.now().isoformat()
        
        # End previous session if exists
        if "current_session" in self.context_data:
            self.end_learning_session()
        
        # Start new session
        self.context_data["current_session"] = {
            "session_id": session_id,
            "start_time": timestamp,
            "topics_in_session": [],
            "struggle_signals": [],
            "session_active": True
        }
        
        self.context_data["last_updated"] = timestamp
        self.save_context()
        return session_id
    
    def end_learning_session(self):
        """End the current learning session"""
        if "current_session" not in self.context_data:
            return False
        
        timestamp = datetime.now().isoformat()
        current_session = self.context_data["current_session"]
        
        # Create session summary
        session_summary = {
            "session_id": current_session["session_id"],
            "start_time": current_session["start_time"],
            "end_time": timestamp,
            "duration_minutes": self.calculate_session_duration(current_session["start_time"], timestamp),
            "topics_explored": current_session.get("topics_in_session", []),
            "struggle_signals": current_session.get("struggle_signals", []),
            "total_topics": len(current_session.get("topics_in_session", [])),
            "session_active": False
        }
        
        # Add to session history
        if "session_history" not in self.context_data:
            self.context_data["session_history"] = []
        
        self.context_data["session_history"].append(session_summary)
        
        # Keep only last 10 sessions
        self.context_data["session_history"] = self.context_data["session_history"][-10:]
        
        # Remove current session
        del self.context_data["current_session"]
        
        self.context_data["last_updated"] = timestamp
        self.save_context()
        return True
    
    def update_current_session(self, topic: str, timestamp: str):
        """Update current session with topic interaction"""
        if "current_session" not in self.context_data:
            return
        
        current_session = self.context_data["current_session"]
        
        # Add topic to session
        if "topics_in_session" not in current_session:
            current_session["topics_in_session"] = []
        
        current_session["topics_in_session"].append({
            "topic": topic,
            "timestamp": timestamp
        })
    
    def record_session_struggle_signal(self, topic: str, signal_type: str):
        """Record struggle signal within current session"""
        if "current_session" not in self.context_data:
            return
        
        timestamp = datetime.now().isoformat()
        current_session = self.context_data["current_session"]
        
        if "struggle_signals" not in current_session:
            current_session["struggle_signals"] = []
        
        current_session["struggle_signals"].append({
            "topic": topic,
            "signal_type": signal_type,
            "timestamp": timestamp
        })
        
        self.save_context()
    
    def calculate_session_duration(self, start_time: str, end_time: str) -> int:
        """Calculate session duration in minutes"""
        try:
            start = datetime.fromisoformat(start_time)
            end = datetime.fromisoformat(end_time)
            duration = end - start
            return int(duration.total_seconds() / 60)
        except:
            return 0
    
    def get_session_duration_minutes(self) -> int:
        """Get current session duration in minutes"""
        if "current_session" not in self.context_data:
            return 0
        
        current_session = self.context_data["current_session"]
        start_time = current_session.get("start_time")
        if not start_time:
            return 0
        
        return self.calculate_session_duration(start_time, datetime.now().isoformat())
    
    def get_session_summary(self) -> str:
        """Get current session summary for prompt"""
        if "current_session" not in self.context_data:
            return "No active learning session"
        
        current_session = self.context_data["current_session"]
        topics_count = len(current_session.get("topics_in_session", []))
        signals_count = len(current_session.get("struggle_signals", []))
        
        summary_parts = []
        summary_parts.append(f"Active learning session with {topics_count} topics explored")
        
        if signals_count > 0:
            summary_parts.append(f"{signals_count} struggle signals recorded")
        
        return "; ".join(summary_parts)
    
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

