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
            "location": "",
            "education": "",   # high_school, undergraduate, graduate, professional
            "profession": "",
            "complexity": "medium",  # simple, medium, advanced
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
        parts = []

        if profile.get("name"):
            parts.append(f"Name: {profile['name']}")
        if profile.get("location"):
            parts.append(f"Location: {profile['location']}")
        if profile.get("education"):
            parts.append(f"Education: {profile['education']}")
        if profile.get("profession"):
            parts.append(f"Profession: {profile['profession']}")
        if profile.get("complexity"):
            parts.append(f"Preferred Complexity: {profile['complexity']}")

        return "\n".join(parts) if parts else "No specific profile information available"
