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
from langchain_core.prompts import PromptTemplate
from core.llm_provider import LLMProviderFactory

# Import from new module locations
from core.user_profile import UserProfile
from core.learning_context import LearningContext

# Load environment variables
load_dotenv()


# LearningContext and UserProfile have been moved to separate modules
# Kept here as comment for reference - they are now imported from:
# - core.learning_context.LearningContext
# - core.user_profile.UserProfile

# Skip to ExampleGenerator class (LearningContext and UserProfile now in separate files)
class ExampleGenerator:
    """Core example generation logic"""
    
    def __init__(self, api_key: str = None, provider: str = None, model: str = None):
        """
        Initialize the Example Generator with LLM provider support

        Args:
            api_key: API key for the provider (auto-detected if None)
            provider: "gemini" or "openai" (default from config)
            model: Model name (uses provider default if None)
        """
        from config.settings import DEFAULT_LLM_PROVIDER, LLM_API_KEYS, LLM_TEMPERATURE

        # Set provider (request > config default > fallback to gemini)
        self.provider = provider or DEFAULT_LLM_PROVIDER

        # Get API key (parameter > env > config)
        if not api_key:
            api_key = LLM_API_KEYS.get(self.provider)

        if not api_key:
            raise ValueError(
                f"{self.provider.upper()}_API_KEY not found. "
                f"Please set it in .env or pass it directly."
            )

        # Create LLM instance using factory
        self.llm = LLMProviderFactory.create_llm(
            provider=self.provider,
            api_key=api_key,
            model=model,
            temperature=LLM_TEMPERATURE
        )

        # Store configuration for debugging
        self.model_config = {
            "provider": self.provider,
            "model": model or LLMProviderFactory.get_default_model(self.provider),
            "temperature": LLM_TEMPERATURE
        }
        
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
def create_example_generator(api_key: str = None, provider: str = None, model: str = None) -> ExampleGenerator:
    """
    Factory function to create an ExampleGenerator instance

    Args:
        api_key: API key for the provider
        provider: "gemini" or "openai"
        model: Model name (optional)

    Returns:
        ExampleGenerator instance
    """
    return ExampleGenerator(api_key=api_key, provider=provider, model=model)


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


