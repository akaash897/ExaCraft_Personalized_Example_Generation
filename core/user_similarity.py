"""
User Similarity Module
Calculates similarity between users for collaborative filtering
"""

import os
import json
from typing import Dict, List, Tuple
from datetime import datetime


class UserSimilarity:
    """Calculate and manage user similarity scores for collaborative filtering"""

    # Weights for different profile dimensions
    SIMILARITY_WEIGHTS = {
        "education_level": 0.20,
        "profession": 0.15,
        "age_range": 0.10,
        "complexity_preference": 0.15,
        "learning_style": 0.15,
        "cultural_background": 0.10,
        "location": 0.10,
        "interests": 0.05
    }

    # Ordinal mappings for education and complexity
    EDUCATION_LEVELS = {
        "high_school": 1,
        "undergraduate": 2,
        "graduate": 3,
        "professional": 4
    }

    COMPLEXITY_LEVELS = {
        "simple": 1,
        "medium": 2,
        "advanced": 3
    }

    def __init__(self):
        self.similarity_cache_file = "data/similarity_cache.json"
        self.cache = self.load_cache()

    def load_cache(self) -> Dict:
        """Load similarity cache from file"""
        try:
            os.makedirs("data", exist_ok=True)
            if os.path.exists(self.similarity_cache_file):
                with open(self.similarity_cache_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"Error loading similarity cache: {e}")
            return {}

    def save_cache(self):
        """Save similarity cache to file"""
        try:
            with open(self.similarity_cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            print(f"Error saving similarity cache: {e}")

    def calculate_similarity(self, profile1: Dict, profile2: Dict) -> float:
        """
        Calculate similarity score between two user profiles
        Returns a score between 0 (completely different) and 1 (identical)
        """
        if not profile1 or not profile2:
            return 0.0

        similarity_scores = {}

        # 1. Education level similarity (ordinal)
        similarity_scores["education_level"] = self._calculate_education_similarity(profile1, profile2)

        # 2. Profession similarity (exact match or domain match)
        similarity_scores["profession"] = self._calculate_profession_similarity(profile1, profile2)

        # 3. Age range similarity (ordinal)
        similarity_scores["age_range"] = self._calculate_age_similarity(profile1, profile2)

        # 4. Complexity preference similarity (ordinal)
        similarity_scores["complexity_preference"] = self._calculate_complexity_similarity(profile1, profile2)

        # 5. Learning style similarity (exact match)
        similarity_scores["learning_style"] = self._calculate_learning_style_similarity(profile1, profile2)

        # 6. Cultural background similarity
        similarity_scores["cultural_background"] = self._calculate_cultural_similarity(profile1, profile2)

        # 7. Location similarity
        similarity_scores["location"] = self._calculate_location_similarity(profile1, profile2)

        # 8. Interests overlap
        similarity_scores["interests"] = self._calculate_interests_similarity(profile1, profile2)

        # Calculate weighted average
        total_score = 0.0
        total_weight = 0.0

        for dimension, score in similarity_scores.items():
            if score is not None:
                weight = self.SIMILARITY_WEIGHTS[dimension]
                total_score += score * weight
                total_weight += weight

        # Normalize by actual weights used
        final_score = total_score / total_weight if total_weight > 0 else 0.0
        return round(final_score, 3)

    def _calculate_education_similarity(self, profile1: Dict, profile2: Dict) -> float:
        """Calculate education level similarity (ordinal scale)"""
        try:
            edu1 = self._extract_education_level(profile1)
            edu2 = self._extract_education_level(profile2)

            if not edu1 or not edu2:
                return 0.0

            level1 = self.EDUCATION_LEVELS.get(edu1.lower(), 0)
            level2 = self.EDUCATION_LEVELS.get(edu2.lower(), 0)

            if level1 == 0 or level2 == 0:
                return 0.0

            # Distance-based similarity (max distance is 3)
            distance = abs(level1 - level2)
            return 1.0 - (distance / 3.0)
        except:
            return 0.0

    def _extract_education_level(self, profile: Dict) -> str:
        """Extract education level from profile"""
        education = profile.get("education", {})
        if isinstance(education, dict):
            return education.get("level", "")
        elif isinstance(education, str):
            return education
        return ""

    def _calculate_profession_similarity(self, profile1: Dict, profile2: Dict) -> float:
        """Calculate profession similarity"""
        try:
            prof1 = self._extract_profession(profile1).lower()
            prof2 = self._extract_profession(profile2).lower()

            if not prof1 or not prof2:
                return 0.0

            # Exact match
            if prof1 == prof2:
                return 1.0

            # Check for common domain keywords
            domains = ["engineer", "developer", "teacher", "doctor", "scientist",
                      "manager", "analyst", "designer", "consultant", "researcher"]

            for domain in domains:
                if domain in prof1 and domain in prof2:
                    return 0.7  # Partial match

            return 0.0
        except:
            return 0.0

    def _extract_profession(self, profile: Dict) -> str:
        """Extract profession from profile"""
        demographics = profile.get("demographics", {})
        if isinstance(demographics, dict):
            return demographics.get("profession", "")
        return profile.get("profession", "")

    def _calculate_age_similarity(self, profile1: Dict, profile2: Dict) -> float:
        """Calculate age range similarity"""
        try:
            age1 = self._extract_age_range(profile1).lower()
            age2 = self._extract_age_range(profile2).lower()

            if not age1 or not age2:
                return 0.0

            if age1 == age2:
                return 1.0

            # Adjacent age ranges get partial credit
            age_order = ["18-25", "26-35", "36-50", "50+"]
            if age1 in age_order and age2 in age_order:
                idx1 = age_order.index(age1)
                idx2 = age_order.index(age2)
                distance = abs(idx1 - idx2)
                return max(0.0, 1.0 - (distance * 0.3))

            return 0.0
        except:
            return 0.0

    def _extract_age_range(self, profile: Dict) -> str:
        """Extract age range from profile"""
        demographics = profile.get("demographics", {})
        if isinstance(demographics, dict):
            return demographics.get("age_range", "")
        return profile.get("age_range", "")

    def _calculate_complexity_similarity(self, profile1: Dict, profile2: Dict) -> float:
        """Calculate complexity preference similarity"""
        try:
            comp1 = self._extract_complexity(profile1).lower()
            comp2 = self._extract_complexity(profile2).lower()

            if not comp1 or not comp2:
                return 0.0

            level1 = self.COMPLEXITY_LEVELS.get(comp1, 0)
            level2 = self.COMPLEXITY_LEVELS.get(comp2, 0)

            if level1 == 0 or level2 == 0:
                return 0.0

            # Distance-based (max distance is 2)
            distance = abs(level1 - level2)
            return 1.0 - (distance / 2.0)
        except:
            return 0.0

    def _extract_complexity(self, profile: Dict) -> str:
        """Extract complexity preference from profile"""
        preferences = profile.get("preferences", {})
        if isinstance(preferences, dict):
            return preferences.get("example_complexity", "medium")
        return profile.get("complexity", "medium")

    def _calculate_learning_style_similarity(self, profile1: Dict, profile2: Dict) -> float:
        """Calculate learning style similarity"""
        try:
            style1 = self._extract_learning_style(profile1).lower()
            style2 = self._extract_learning_style(profile2).lower()

            if not style1 or not style2:
                return 0.0

            return 1.0 if style1 == style2 else 0.0
        except:
            return 0.0

    def _extract_learning_style(self, profile: Dict) -> str:
        """Extract learning style from profile"""
        preferences = profile.get("preferences", {})
        if isinstance(preferences, dict):
            return preferences.get("learning_style", "")
        return profile.get("learning_style", "")

    def _calculate_cultural_similarity(self, profile1: Dict, profile2: Dict) -> float:
        """Calculate cultural background similarity"""
        try:
            culture1 = self._extract_cultural_background(profile1).lower()
            culture2 = self._extract_cultural_background(profile2).lower()

            if not culture1 or not culture2:
                return 0.0

            return 1.0 if culture1 == culture2 else 0.0
        except:
            return 0.0

    def _extract_cultural_background(self, profile: Dict) -> str:
        """Extract cultural background from profile"""
        culture = profile.get("culture", {})
        if isinstance(culture, dict):
            return culture.get("cultural_background", "")
        return profile.get("cultural_background", "")

    def _calculate_location_similarity(self, profile1: Dict, profile2: Dict) -> float:
        """Calculate location similarity"""
        try:
            loc1 = self._extract_location(profile1)
            loc2 = self._extract_location(profile2)

            if not loc1 or not loc2:
                return 0.0

            country1 = loc1.get("country", "").lower()
            country2 = loc2.get("country", "").lower()
            city1 = loc1.get("city", "").lower()
            city2 = loc2.get("city", "").lower()

            if country1 and country2:
                if country1 == country2:
                    if city1 and city2 and city1 == city2:
                        return 1.0  # Same city
                    return 0.7  # Same country

            return 0.0
        except:
            return 0.0

    def _extract_location(self, profile: Dict) -> Dict:
        """Extract location from profile"""
        location = profile.get("location", {})
        if isinstance(location, dict):
            return location
        return {}

    def _calculate_interests_similarity(self, profile1: Dict, profile2: Dict) -> float:
        """Calculate interests overlap (Jaccard similarity)"""
        try:
            interests1 = set(self._extract_interests(profile1))
            interests2 = set(self._extract_interests(profile2))

            if not interests1 or not interests2:
                return 0.0

            intersection = len(interests1 & interests2)
            union = len(interests1 | interests2)

            return intersection / union if union > 0 else 0.0
        except:
            return 0.0

    def _extract_interests(self, profile: Dict) -> List:
        """Extract interests from profile"""
        demographics = profile.get("demographics", {})
        if isinstance(demographics, dict):
            interests = demographics.get("interests", [])
            if isinstance(interests, list):
                return [i.lower() for i in interests]
        return []

    def find_similar_users(self, target_user_id: str, target_profile: Dict,
                          all_profiles: Dict[str, Dict], top_k: int = 5,
                          min_similarity: float = 0.3) -> List[Tuple[str, float]]:
        """
        Find K most similar users to the target user

        Args:
            target_user_id: ID of the target user
            target_profile: Profile of the target user
            all_profiles: Dictionary of {user_id: profile_data}
            top_k: Number of similar users to return
            min_similarity: Minimum similarity threshold

        Returns:
            List of (user_id, similarity_score) tuples, sorted by score descending
        """
        similarities = []

        for user_id, profile in all_profiles.items():
            # Skip the target user
            if user_id == target_user_id:
                continue

            # Calculate similarity
            score = self.calculate_similarity(target_profile, profile)

            # Only include users above threshold
            if score >= min_similarity:
                similarities.append((user_id, score))

        # Sort by similarity score descending
        similarities.sort(key=lambda x: x[1], reverse=True)

        # Return top K
        return similarities[:top_k]

    def get_all_user_profiles(self) -> Dict[str, Dict]:
        """Load all user profiles from the user_profiles directory"""
        profiles = {}

        try:
            profile_dir = "user_profiles"
            if not os.path.exists(profile_dir):
                return profiles

            for filename in os.listdir(profile_dir):
                if filename.endswith(".json"):
                    user_id = filename[:-5]  # Remove .json extension
                    filepath = os.path.join(profile_dir, filename)

                    try:
                        with open(filepath, 'r') as f:
                            profile = json.load(f)
                            profiles[user_id] = profile
                    except Exception as e:
                        print(f"Error loading profile {filename}: {e}")

        except Exception as e:
            print(f"Error reading profiles directory: {e}")

        return profiles
