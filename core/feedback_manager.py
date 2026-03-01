"""
Feedback Management Module
Handles user feedback collection, pattern analysis, and adaptive threshold calculation.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


class FeedbackManager:
    """Manages feedback collection and adaptive threshold calculation"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.feedback_file = f"data/feedback_history/{user_id}.json"
        self.feedback_data = self.load_feedback()
    
    def load_feedback(self) -> Dict:
        """Load feedback history from JSON file"""
        try:
            os.makedirs("data/feedback_history", exist_ok=True)
            
            if os.path.exists(self.feedback_file):
                with open(self.feedback_file, 'r') as f:
                    return json.load(f)
            else:
                return self.create_default_feedback_structure()
        except Exception as e:
            print(f"Error loading feedback: {e}")
            return self.create_default_feedback_structure()
    
    def create_default_feedback_structure(self) -> Dict:
        """Create default feedback data structure"""
        return {
            "user_id": self.user_id,
            "feedback_entries": [],
            "adaptive_thresholds": {
                "struggle_threshold": 3,  # Default: 3 repetitions
                "mastery_threshold": 3,   # Default: 3 unique topics in 5 interactions
                "last_calculated": datetime.now().isoformat()
            },
            "created_at": datetime.now().isoformat()
        }
    
    def add_feedback(
        self,
        example_id: str,
        topic: str,
        difficulty_rating: int,
        clarity_rating: int,
        usefulness_rating: int,
        example_text: Optional[str] = None
    ) -> bool:
        """
        Add feedback entry
        
        Args:
            example_id: Unique example identifier
            topic: Topic of the example
            difficulty_rating: 1-5 (1=too easy, 5=too hard)
            clarity_rating: 1-5 (1=unclear, 5=very clear)
            usefulness_rating: 1-5 (1=not useful, 5=very useful)
            example_text: Optional example content
        """
        feedback_entry = {
            "example_id": example_id,
            "topic": topic,
            "difficulty_rating": difficulty_rating,
            "clarity_rating": clarity_rating,
            "usefulness_rating": usefulness_rating,
            "example_text": example_text,
            "timestamp": datetime.now().isoformat()
        }
        
        self.feedback_data["feedback_entries"].append(feedback_entry)
        self.save_feedback()
        return True
    
    def get_feedback_patterns(self, topic: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """Get recent feedback entries, optionally filtered by topic"""
        entries = self.feedback_data.get("feedback_entries", [])
        
        if topic:
            entries = [e for e in entries if e.get("topic") == topic]
        
        # Sort by timestamp (most recent first)
        entries = sorted(
            entries,
            key=lambda x: x.get("timestamp", ""),
            reverse=True
        )
        
        return entries[:limit]
    
    def calculate_adaptive_thresholds(self) -> Dict[str, float]:
        """
        Calculate adaptive thresholds based on feedback history
        
        Logic:
        - If users consistently rate difficulty high (4-5): Lower struggle threshold (make it easier to detect struggle)
        - If users consistently rate difficulty low (1-2): Raise mastery threshold (expect more progression for mastery)
        - If clarity is low: Lower both thresholds (provide more support)
        """
        entries = self.feedback_data.get("feedback_entries", [])
        
        # Need at least 5 feedback entries to calculate
        if len(entries) < 5:
            return self.feedback_data.get("adaptive_thresholds", {
                "struggle_threshold": 3,
                "mastery_threshold": 3,
                "last_calculated": datetime.now().isoformat()
            })
        
        # Get recent 20 entries
        recent_entries = sorted(
            entries,
            key=lambda x: x.get("timestamp", ""),
            reverse=True
        )[:20]
        
        # Calculate averages
        avg_difficulty = sum(e.get("difficulty_rating", 3) for e in recent_entries) / len(recent_entries)
        avg_clarity = sum(e.get("clarity_rating", 3) for e in recent_entries) / len(recent_entries)
        avg_usefulness = sum(e.get("usefulness_rating", 3) for e in recent_entries) / len(recent_entries)
        
        # Default thresholds
        struggle_threshold = 3.0
        mastery_threshold = 3.0
        
        # Adjust based on difficulty ratings
        if avg_difficulty >= 4.0:
            # User finds examples too hard → lower struggle threshold (detect struggle earlier)
            struggle_threshold = 2.0
        elif avg_difficulty >= 3.5:
            struggle_threshold = 2.5
        elif avg_difficulty <= 2.0:
            # User finds examples too easy → raise mastery threshold (expect more progression)
            mastery_threshold = 4.0
        elif avg_difficulty <= 2.5:
            mastery_threshold = 3.5
        
        # Adjust based on clarity
        if avg_clarity < 3.0:
            # Low clarity → provide more support (lower both thresholds)
            struggle_threshold = max(2.0, struggle_threshold - 0.5)
            mastery_threshold = max(3.0, mastery_threshold - 0.5)
        
        thresholds = {
            "struggle_threshold": round(struggle_threshold, 1),
            "mastery_threshold": round(mastery_threshold, 1),
            "avg_difficulty": round(avg_difficulty, 2),
            "avg_clarity": round(avg_clarity, 2),
            "avg_usefulness": round(avg_usefulness, 2),
            "sample_size": len(recent_entries),
            "last_calculated": datetime.now().isoformat()
        }
        
        # Update stored thresholds
        self.feedback_data["adaptive_thresholds"] = thresholds
        self.save_feedback()
        
        return thresholds
    
    def get_current_thresholds(self) -> Dict[str, float]:
        """Get current adaptive thresholds"""
        return self.feedback_data.get("adaptive_thresholds", {
            "struggle_threshold": 3,
            "mastery_threshold": 3,
            "last_calculated": datetime.now().isoformat()
        })
    
    def get_feedback_summary(self) -> Dict:
        """Get summary statistics of feedback"""
        entries = self.feedback_data.get("feedback_entries", [])
        
        if not entries:
            return {
                "total_feedback": 0,
                "avg_difficulty": 0,
                "avg_clarity": 0,
                "avg_usefulness": 0
            }
        
        return {
            "total_feedback": len(entries),
            "avg_difficulty": round(sum(e.get("difficulty_rating", 0) for e in entries) / len(entries), 2),
            "avg_clarity": round(sum(e.get("clarity_rating", 0) for e in entries) / len(entries), 2),
            "avg_usefulness": round(sum(e.get("usefulness_rating", 0) for e in entries) / len(entries), 2),
            "recent_topics": list(set(e.get("topic") for e in entries[-10:]))
        }
    
    def save_feedback(self) -> bool:
        """Save feedback to file"""
        try:
            os.makedirs(os.path.dirname(self.feedback_file), exist_ok=True)
            with open(self.feedback_file, 'w') as f:
                json.dump(self.feedback_data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving feedback: {e}")
            return False
