"""
AI Example Generator Core Module

This module contains the core business logic for generating personalized examples
using LangChain and Google's Gemini AI model.

Classes:
    - ExampleGenerator: Main class for generating examples
    - UserProfile: User profile management
    - ExampleGeneratorConfig: Configuration constants

Functions:
    - create_example_generator: Factory function for ExampleGenerator
    - validate_profile_data: Profile data validation utility
"""

from .example_generator import (
    ExampleGenerator,
    UserProfile, 
    ExampleGeneratorConfig,
    create_example_generator,
    validate_profile_data,
    PersonalizedExampleGenerator  # Backward compatibility alias
)

__version__ = "1.0.0"
__author__ = "AI Example Generator Team"

# Public API
__all__ = [
    "ExampleGenerator",
    "UserProfile",
    "ExampleGeneratorConfig", 
    "create_example_generator",
    "validate_profile_data",
    "PersonalizedExampleGenerator"
]