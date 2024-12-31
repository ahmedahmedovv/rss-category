from together import Together
import os
from dotenv import load_dotenv

def main():
    # Load environment variables
    load_dotenv()
    
    # Initialize the Together client
    client = Together()
    
    print("Welcome to the AI Chat Assistant!")
    print("Type 'quit' to exit the conversation")
    print("-" * 50)
    
    while True:
        # Get user input
        user_input = input("\nYou: ").strip()
        
        # Check if user wants to quit
        if user_input.lower() == 'quit':
            print("\nGoodbye!")
            break
        
        try:
            # Send request to Together AI
            response = client.chat.completions.create(
                model="Qwen/QwQ-32B-Preview",
                messages=[{"role": "user", "content": user_input}],
            )
            
            # Extract and print the AI's response
            ai_response = response.choices[0].message.content
            print("\nAI:", ai_response)
            
        except Exception as e:
            print(f"\nError: {str(e)}")

if __name__ == "__main__":
    main()