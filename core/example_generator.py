"""
Core Example Generator Module
Contains the main business logic for generating personalized examples.
"""

import os
import json
from datetime import datetime
from typing import Dict, Optional
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate

# Load environment variables
load_dotenv()


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
            model="gemini-1.5-flash",
            google_api_key=api_key,
            temperature=0.7
        )
        
        # Create a personalized prompt template
        self.prompt_template = PromptTemplate(
            input_variables=["topic", "user_profile"],
            template="""
            You are an expert example generator who creates personalized, culturally-aware examples.
            
            User Profile:
            {user_profile}
            
            Topic: {topic}
            
            Based on the user's background, location, education level, and cultural context, provide:
            1. A brief explanation of the topic (1-2 sentences) - adjusted for their education level
            2. A concrete, practical example that relates to their cultural background, location, or profession
            3. Key points or takeaways that are relevant to their context
            
            Guidelines:
            - Use references, analogies, and examples that would be familiar to someone from their background
            - Consider their education level when explaining concepts
            - Include cultural context when relevant (local customs, businesses, landmarks, etc.)
            - If they have a profession, try to relate examples to their field when possible
            - Match the complexity to their preferred level
            - Keep the response concise and focused (under 300 words for API usage)
            
            Make the example personally relevant and engaging for this specific user.
            
            Personalized Example:
            """
        )
        
        # Create the chain using modern syntax
        self.chain = self.prompt_template | self.llm
    
    def generate_example(self, topic: str, user_profile: UserProfile) -> str:
        """Generate a personalized example for the given topic"""
        try:
            profile_summary = user_profile.get_profile_summary()
            result = self.chain.invoke({"topic": topic, "user_profile": profile_summary})
            return result.content
        except Exception as e:
            return f"Error generating example: {str(e)}"
    
    def generate_example_simple(self, topic: str, profile_data: Dict = None) -> str:
        """
        Simplified method for API usage
        Args:
            topic: The topic to generate an example for
            profile_data: Dictionary containing user profile information
        Returns:
            Generated example as string
        """
        user_profile = UserProfile(profile_data=profile_data or {})
        return self.generate_example(topic, user_profile)


class ExampleGeneratorConfig:
    """Configuration settings for the example generator"""
    
    # Default model settings
    DEFAULT_MODEL = "gemini-2.5-flash"
    DEFAULT_TEMPERATURE = 0.7
    
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