import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.schema import HumanMessage

# Load environment variables from .env file
load_dotenv()

class ExampleGenerator:
    def __init__(self, api_key: str):
        """Initialize the Example Generator with Gemini API key"""
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=api_key,
            temperature=0.7
        )
        
        # Create a prompt template for example generation
        self.prompt_template = PromptTemplate(
            input_variables=["topic"],
            template="""
            You are an expert example generator. Your task is to provide a clear, practical, and educational example for the given topic.
            
            Topic: {topic}
            
            Please provide:
            1. A brief explanation of the topic (1-2 sentences)
            2. A concrete, practical example
            3. Key points or takeaways from the example
            
            Make the example easy to understand and relevant to real-world applications.
            
            Example:
            """
        )
        
        # Create the chain
        self.chain = LLMChain(
            llm=self.llm,
            prompt=self.prompt_template,
            verbose=True
        )
    
    def generate_example(self, topic: str) -> str:
        """Generate an example for the given topic"""
        try:
            result = self.chain.run(topic=topic)
            return result
        except Exception as e:
            return f"Error generating example: {str(e)}"

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
    generator = ExampleGenerator(api_key)
    
    print("=== LangChain Example Generator ===")
    print("Enter a topic to generate an example for it.")
    print("Type 'quit' to exit.\n")
    
    while True:
        topic = input("Enter topic: ").strip()
        
        if topic.lower() in ['quit', 'exit', 'q']:
            print("Goodbye!")
            break
        
        if not topic:
            print("Please enter a valid topic.")
            continue
        
        print(f"\nGenerating example for: {topic}")
        print("-" * 50)
        
        example = generator.generate_example(topic)
        print(example)
        print("-" * 50)
        print()

if __name__ == "__main__":
    main()