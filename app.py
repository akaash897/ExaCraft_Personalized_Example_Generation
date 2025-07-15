import os
import json
from datetime import datetime
from typing import Dict, Optional
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage

# Load environment variables from .env file
load_dotenv()

class UserProfile:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.profile_file = f"user_profiles/{user_id}.json"
        self.profile_data = self.load_profile()
    
    def load_profile(self) -> Dict:
        """Load user profile from JSON file"""
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
            "user_id": self.user_id,
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
        self.save_profile()
    
    def get_profile_summary(self) -> str:
        """Get a formatted summary of user profile for prompt"""
        profile = self.profile_data
        
        summary_parts = []
        
        if profile.get("name"):
            summary_parts.append(f"Name: {profile['name']}")
        
        # Location context
        location = profile.get("location", {})
        if location.get("country") or location.get("city"):
            loc_str = f"{location.get('city', '')}, {location.get('country', '')}".strip(", ")
            summary_parts.append(f"Location: {loc_str}")
        
        # Education context
        education = profile.get("education", {})
        if education.get("level") or education.get("field"):
            edu_str = f"{education.get('level', '')} in {education.get('field', '')}".strip(" in ")
            summary_parts.append(f"Education: {edu_str}")
        
        # Cultural context
        culture = profile.get("culture", {})
        if culture.get("cultural_background"):
            summary_parts.append(f"Cultural Background: {culture['cultural_background']}")
        
        # Professional context
        demographics = profile.get("demographics", {})
        if demographics.get("profession"):
            summary_parts.append(f"Profession: {demographics['profession']}")
        
        # Preferences
        preferences = profile.get("preferences", {})
        if preferences.get("example_complexity"):
            summary_parts.append(f"Preferred Complexity: {preferences['example_complexity']}")
        
        if preferences.get("learning_style"):
            summary_parts.append(f"Learning Style: {preferences['learning_style']}")
        
        return "\n".join(summary_parts) if summary_parts else "No specific profile information available"

class PersonalizedExampleGenerator:
    def __init__(self, api_key: str):
        """Initialize the Personalized Example Generator with Gemini API key"""
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
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
            
            Make the example personally relevant and engaging for this specific user.
            
            Personalized Example:
            """
        )
        
        # Create the chain using modern RunnableSequence syntax
        self.chain = self.prompt_template | self.llm
    
    def generate_example(self, topic: str, user_profile: UserProfile) -> str:
        """Generate a personalized example for the given topic"""
        try:
            profile_summary = user_profile.get_profile_summary()
            result = self.chain.invoke({"topic": topic, "user_profile": profile_summary})
            # Extract content from the AIMessage response
            return result.content
        except Exception as e:
            return f"Error generating example: {str(e)}"

def setup_user_profile() -> UserProfile:
    """Interactive setup for user profile"""
    print("=== User Profile Setup ===")
    print("Let's personalize your examples by setting up your profile.")
    print("You can skip any question by pressing Enter.\n")
    
    user_id = input("Enter your name or user ID: ").strip() or "default_user"
    profile = UserProfile(user_id)
    
    # Check if profile exists
    if profile.profile_data.get("name"):
        print(f"Welcome back, {profile.profile_data['name']}!")
        update = input("Would you like to update your profile? (y/n): ").strip().lower()
        if update != 'y':
            return profile
    
    # Collect profile information
    updates = {}
    
    name = input("Full name: ").strip()
    if name:
        updates["name"] = name
    
    # Location
    country = input("Country: ").strip()
    city = input("City: ").strip()
    if country or city:
        updates["location"] = {"country": country, "city": city}
    
    # Education
    print("\nEducation Level Options: high_school, undergraduate, graduate, professional")
    edu_level = input("Education level: ").strip()
    edu_field = input("Field of study: ").strip()
    if edu_level or edu_field:
        updates["education"] = {"level": edu_level, "field": edu_field}
    
    # Culture
    cultural_bg = input("Cultural background: ").strip()
    if cultural_bg:
        updates["culture"] = {"cultural_background": cultural_bg}
    
    # Demographics
    profession = input("Profession: ").strip()
    if profession:
        updates["demographics"] = {"profession": profession}
    
    # Preferences
    print("\nComplexity Options: simple, medium, advanced")
    complexity = input("Preferred example complexity: ").strip()
    print("Learning Style Options: theoretical, practical, visual")
    learning_style = input("Learning style: ").strip()
    
    if complexity or learning_style:
        updates["preferences"] = {}
        if complexity:
            updates["preferences"]["example_complexity"] = complexity
        if learning_style:
            updates["preferences"]["learning_style"] = learning_style
    
    # Update profile
    if updates:
        profile.update_profile(updates)
        print("\nProfile updated successfully!")
    
    return profile

def main():
    # Load API key from environment variables
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("Error: GEMINI_API_KEY not found in environment variables.")
        print("Please create a .env file with your API key.")
        print("Example .env file content:")
        print("GEMINI_API_KEY=your_actual_api_key_here")
        return
    
    # Initialize the example generator
    generator = PersonalizedExampleGenerator(api_key)
    
    # Setup user profile
    user_profile = setup_user_profile()
    
    print("\n=== Personalized LangChain Example Generator ===")
    print("Enter a topic to generate a personalized example.")
    print("Type 'profile' to update your profile.")
    print("Type 'quit' to exit.\n")
    
    while True:
        topic = input("Enter topic: ").strip()
        
        if topic.lower() in ['quit', 'exit', 'q']:
            print("Goodbye!")
            break
        
        if topic.lower() == 'profile':
            user_profile = setup_user_profile()
            continue
        
        if not topic:
            print("Please enter a valid topic.")
            continue
        
        print(f"\nGenerating personalized example for: {topic}")
        print("-" * 50)
        
        example = generator.generate_example(topic, user_profile)
        print(example)
        print("-" * 50)
        print()

if __name__ == "__main__":
    main()