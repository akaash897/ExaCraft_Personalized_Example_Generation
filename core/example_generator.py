"""
Core Example Generator Module
Contains the main business logic for generating personalized examples.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate

# Load environment variables
load_dotenv()


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
        
        # Count topic repetitions (struggle indicator)
        topic_count = sum(1 for t in self.context_data.get("recent_topics", []) 
                         if t.get("topic") == topic)
        
        if topic_count >= 3:  # Repeated requests indicate struggle
            if "struggle_indicators" not in self.context_data:
                self.context_data["struggle_indicators"] = {}
            self.context_data["struggle_indicators"][topic] = {
                "repeat_count": topic_count,
                "last_seen": datetime.now().isoformat()
            }
        
        # Quick successive different topics (mastery indicator)
        recent_topics = self.context_data.get("recent_topics", [])[-5:]
        if len(recent_topics) >= 3:
            unique_topics = len(set(t.get("topic") for t in recent_topics))
            if unique_topics >= 3:  # Quick progression through different topics
                if "mastery_indicators" not in self.context_data:
                    self.context_data["mastery_indicators"] = {}
                self.context_data["mastery_indicators"]["quick_progression"] = {
                    "recent_topics": [t.get("topic") for t in recent_topics],
                    "timestamp": datetime.now().isoformat()
                }
    
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
        
        if mastery.get("quick_progression"):
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


class UserProfile:
    """User profile management class"""
    
    def __init__(self, user_id: str = None, profile_data: Dict = None):
        self.user_id = user_id
        if profile_data:
            # Initialize from provided data (API mode)
            self.profile_data = profile_data
            self.profile_file = None
        else:
            # Initialize from file (CLI mode)
            self.profile_file = f"user_profiles/{user_id}.json" if user_id else None
            self.profile_data = self.load_profile() if user_id else {}
    
    def load_profile(self) -> Dict:
        """Load user profile from JSON file"""
        if not self.profile_file:
            return self.create_default_profile()
            
        try:
            # Create directory if it doesn't exist
            os.makedirs("user_profiles", exist_ok=True)
            
            if os.path.exists(self.profile_file):
                with open(self.profile_file, 'r') as f:
                    return json.load(f)
            else:
                return self.create_default_profile()
        except Exception as e:
            print(f"Error loading profile: {e}")
            return self.create_default_profile()
    
    def create_default_profile(self) -> Dict:
        """Create a default profile structure"""
        return {
            "user_id": self.user_id or "default",
            "name": "",
            "location": {
                "country": "",
                "city": "",
                "region": ""
            },
            "education": {
                "level": "",  # high_school, undergraduate, graduate, professional
                "field": "",
                "background": ""
            },
            "culture": {
                "language": "English",
                "cultural_background": "",
                "religion": "",
                "traditions": []
            },
            "demographics": {
                "age_range": "",  # 18-25, 26-35, 36-50, 50+
                "profession": "",
                "interests": []
            },
            "preferences": {
                "example_complexity": "medium",  # simple, medium, advanced
                "preferred_domains": [],  # tech, business, science, arts, etc.
                "learning_style": "practical"  # theoretical, practical, visual
            },
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
    
    def save_profile(self):
        """Save profile to JSON file"""
        if not self.profile_file:
            return False
            
        try:
            self.profile_data["updated_at"] = datetime.now().isoformat()
            with open(self.profile_file, 'w') as f:
                json.dump(self.profile_data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving profile: {e}")
            return False
    
    def update_profile(self, updates: Dict):
        """Update profile with new information"""
        def deep_update(original, updates):
            for key, value in updates.items():
                if isinstance(value, dict) and key in original:
                    deep_update(original[key], value)
                else:
                    original[key] = value
        
        deep_update(self.profile_data, updates)
        if self.profile_file:
            self.save_profile()
    
    def get_profile_summary(self) -> str:
        """Get a formatted summary of user profile for prompt"""
        profile = self.profile_data
        
        summary_parts = []
        
        if profile.get("name"):
            summary_parts.append(f"Name: {profile['name']}")
        
        # Location context (handle both dict and string formats)
        location = profile.get("location", {})
        if isinstance(location, dict):
            if location.get("country") or location.get("city"):
                loc_str = f"{location.get('city', '')}, {location.get('country', '')}".strip(", ")
                if loc_str:
                    summary_parts.append(f"Location: {loc_str}")
        elif isinstance(location, str) and location:
            summary_parts.append(f"Location: {location}")
        
        # Education context (handle both dict and string formats)
        education = profile.get("education", {})
        if isinstance(education, dict):
            if education.get("level") or education.get("field"):
                edu_str = f"{education.get('level', '')} in {education.get('field', '')}".strip(" in ")
                if edu_str:
                    summary_parts.append(f"Education: {edu_str}")
        elif isinstance(education, str) and education:
            summary_parts.append(f"Education: {education}")
        
        # Cultural context (handle both dict and string formats)
        culture = profile.get("culture", {})
        if isinstance(culture, dict):
            if culture.get("cultural_background"):
                summary_parts.append(f"Cultural Background: {culture['cultural_background']}")
        
        # Professional context (handle both dict and string formats)
        demographics = profile.get("demographics", {})
        profession = None
        if isinstance(demographics, dict):
            profession = demographics.get("profession")
        elif profile.get("profession"):  # Direct profession field
            profession = profile.get("profession")
        
        if profession:
            summary_parts.append(f"Profession: {profession}")
        
        # Preferences (handle both dict and string formats)
        preferences = profile.get("preferences", {})
        complexity = None
        learning_style = None
        
        if isinstance(preferences, dict):
            complexity = preferences.get("example_complexity")
            learning_style = preferences.get("learning_style")
        elif profile.get("complexity"):  # Direct complexity field
            complexity = profile.get("complexity")
        
        if complexity:
            summary_parts.append(f"Preferred Complexity: {complexity}")
        
        if learning_style:
            summary_parts.append(f"Learning Style: {learning_style}")
        
        return "\n".join(summary_parts) if summary_parts else "No specific profile information available"


class ExampleGenerator:
    """Core example generation logic"""
    
    def __init__(self, api_key: str = None):
        """Initialize the Example Generator with Gemini API key"""
        if not api_key:
            api_key = os.getenv("GEMINI_API_KEY")
        
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found. Please set it in environment variables or pass it directly.")
        
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=api_key,
            temperature=0.3
        )
        
        # Create a personalized prompt template with dynamic learning context
        self.prompt_template = PromptTemplate(
        input_variables=["topic", "user_profile", "learning_context"],
        template="""
        You are an adaptive AI tutor that personalizes examples based on both static user profile and dynamic learning context.

        STATIC USER PROFILE:
        {user_profile}

        DYNAMIC LEARNING CONTEXT:
        {learning_context}

        TARGET TOPIC: {topic}

        DYNAMIC ADAPTATION RULES:

        If learning context shows STRUGGLE INDICATORS (repeated requests, stuck on topics):
        - Simplify complexity regardless of profile education level
        - Use more concrete, visual analogies
        - Build confidence with encouraging tone
        - Connect to topics they've already mastered
        - Break down complex concepts into smaller steps

        If learning context shows MASTERY INDICATORS (quick progression, diverse topics):
        - Increase complexity and introduce nuanced concepts
        - Make connections between multiple topics
        - Use their learning momentum to explore advanced applications
        - Challenge them appropriately with sophisticated examples

        If learning context shows RECENT TOPIC CONNECTIONS:
        - Build directly on their recently explored topics
        - Make explicit connections to what they just learned
        - Use their current learning journey as a foundation

        If this is a FIRST TIME SESSION (no learning context):
        - Use standard personalization based on static profile
        - Focus on cultural and professional relevance
        - Establish baseline complexity appropriate to education level

        PERSONALIZATION HIERARCHY:
        1. First adapt for learning context (struggle/mastery/connections)
        2. Then apply cultural personalization (location, background)
        3. Finally adjust for professional relevance

        EXAMPLE GENERATION:
        Generate a contextually adaptive example as a vivid scenario in 2-4 sentences.
        Use specific characters, locations, and situations that match their profile and learning state.

        Output ONLY the example scenario - no explanations or analysis.
        """
    )
        # Create the chain using modern syntax
        self.chain = self.prompt_template | self.llm
    
    def generate_example(self, topic: str, user_profile: UserProfile, learning_context: LearningContext = None) -> str:
        """Generate a dynamically personalized example for the given topic"""
        try:
            profile_summary = user_profile.get_profile_summary()
            
            # Get learning context summary
            if learning_context:
                context_summary = learning_context.get_learning_state_summary()
                # Record this topic interaction
                learning_context.add_topic_interaction(topic)
            else:
                context_summary = "First time learning session - no previous learning context available"
            
            result = self.chain.invoke({
                "topic": topic, 
                "user_profile": profile_summary,
                "learning_context": context_summary
            })
            return result.content
        except Exception as e:
            return f"Error generating example: {str(e)}"
    
    def generate_example_simple(self, topic: str, profile_data: Dict = None) -> str:
        """
        Simplified method for API usage without learning context
        Args:
            topic: The topic to generate an example for
            profile_data: Dictionary containing user profile information
        Returns:
            Generated example as string
        """
        user_profile = UserProfile(profile_data=profile_data or {})
        return self.generate_example(topic, user_profile)
    
    def generate_adaptive_example(self, topic: str, profile_data: Dict = None, user_id: str = None) -> str:
        """
        Generate example with dynamic learning context
        Args:
            topic: The topic to generate an example for
            profile_data: Dictionary containing user profile information
            user_id: User identifier for learning context tracking
        Returns:
            Generated example as string
        """
        user_profile = UserProfile(profile_data=profile_data or {})
        learning_context = LearningContext(user_id=user_id) if user_id else None
        return self.generate_example(topic, user_profile, learning_context)


class ExampleGeneratorConfig:
    """Configuration settings for the example generator"""
    
    # Default model settings
    DEFAULT_MODEL = "gemini-2.5-flash"
    DEFAULT_TEMPERATURE = 0.3
    
    # Complexity levels
    COMPLEXITY_LEVELS = ["simple", "medium", "advanced"]
    
    # Education levels
    EDUCATION_LEVELS = ["high_school", "undergraduate", "graduate", "professional"]
    
    # Learning styles
    LEARNING_STYLES = ["theoretical", "practical", "visual"]
    
    # Default profile structure for validation
    PROFILE_SCHEMA = {
        "name": str,
        "location": [str, dict],
        "education": [str, dict],
        "profession": str,
        "complexity": str,
        "cultural_background": str,
        "age_range": str,
        "interests": list,
        "preferred_domains": list,
        "learning_style": str
    }


# Utility functions
def create_example_generator(api_key: str = None) -> ExampleGenerator:
    """Factory function to create an ExampleGenerator instance"""
    return ExampleGenerator(api_key)


def validate_profile_data(profile_data: Dict) -> bool:
    """Validate profile data structure"""
    try:
        # Basic validation - ensure it's a dictionary
        if not isinstance(profile_data, dict):
            return False
        
        # Check for required fields (flexible validation)
        # Allow empty values but check types if present
        for key, expected_types in ExampleGeneratorConfig.PROFILE_SCHEMA.items():
            if key in profile_data:
                value = profile_data[key]
                if value is not None and value != "":
                    if isinstance(expected_types, list):
                        if not any(isinstance(value, t) for t in expected_types):
                            return False
                    else:
                        if not isinstance(value, expected_types):
                            return False
        
        return True
    except Exception:
        return False


# For backward compatibility
PersonalizedExampleGenerator = ExampleGenerator