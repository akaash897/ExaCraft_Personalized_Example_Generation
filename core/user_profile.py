"""
User Profile Management Module
Handles static user profile data with file-based and in-memory persistence.
"""

import os
import json
from datetime import datetime
from typing import Dict, Optional


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
        cultural_background = None
        if isinstance(culture, dict):
            cultural_background = culture.get("cultural_background")
        if not cultural_background:
            cultural_background = profile.get("cultural_background")  # Flat field fallback
        if cultural_background:
            summary_parts.append(f"Cultural Background: {cultural_background}")
        
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

        # Flat field fallbacks (extension format)
        if not complexity and profile.get("complexity"):
            complexity = profile.get("complexity")
        if not learning_style and profile.get("learning_style"):
            learning_style = profile.get("learning_style")
        
        if complexity:
            summary_parts.append(f"Preferred Complexity: {complexity}")
        
        if learning_style:
            summary_parts.append(f"Learning Style: {learning_style}")
        
        return "\n".join(summary_parts) if summary_parts else "No specific profile information available"
