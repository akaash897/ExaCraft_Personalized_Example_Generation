"""
Core Example Generator Module
Contains profile validation logic for the API endpoints.
"""

from typing import Dict


_PROFILE_SCHEMA = {
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


def validate_profile_data(profile_data: Dict) -> bool:
    """Validate profile data structure"""
    try:
        # Basic validation - ensure it's a dictionary
        if not isinstance(profile_data, dict):
            return False

        # Check for required fields (flexible validation)
        # Allow empty values but check types if present
        for key, expected_types in _PROFILE_SCHEMA.items():
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
