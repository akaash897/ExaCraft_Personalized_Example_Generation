"""
CLI Application for AI Example Generator
Provides interactive command-line interface for generating personalized examples.
"""

import os
from core.example_generator import ExampleGenerator, UserProfile

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
    """Main CLI application"""
    # Check for API key
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("Error: GEMINI_API_KEY not found in environment variables.")
        print("Please create a .env file with your API key.")
        print("Example .env file content:")
        print("GEMINI_API_KEY=your_actual_api_key_here")
        return
    
    try:
        # Initialize the example generator
        generator = ExampleGenerator(api_key)
        print("✅ AI Example Generator initialized successfully!")
    except Exception as e:
        print(f"❌ Failed to initialize generator: {e}")
        return
    
    # Setup user profile
    user_profile = setup_user_profile()
    
    print("\n=== Personalized AI Example Generator ===")
    print("Enter a topic to generate a personalized example.")
    print("Commands:")
    print("  - Type any topic to generate an example")
    print("  - Type 'profile' to update your profile")
    print("  - Type 'help' to see this message again")
    print("  - Type 'quit' to exit")
    print()
    
    while True:
        try:
            topic = input("📝 Enter topic: ").strip()
            
            if topic.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            
            if topic.lower() == 'profile':
                user_profile = setup_user_profile()
                continue
            
            if topic.lower() == 'help':
                print("\n=== Commands ===")
                print("  - Any text: Generate an example for that topic")
                print("  - 'profile': Update your user profile")
                print("  - 'help': Show this help message")
                print("  - 'quit': Exit the application")
                print()
                continue
            
            if not topic:
                print("⚠️  Please enter a valid topic.")
                continue
            
            print(f"\n🤖 Generating personalized example for: {topic}")
            print("=" * 60)
            
            # Generate example
            example = generator.generate_example(topic, user_profile)
            
            # Display result
            if example.startswith("Error generating example:"):
                print(f"❌ {example}")
            else:
                print(example)
            
            print("=" * 60)
            print()
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ An error occurred: {e}")
            print("Please try again or type 'quit' to exit.\n")


if __name__ == "__main__":
    main()