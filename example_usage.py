import os
from contextguard import GuardedOpenAI as OpenAI

from contextguard.guard import guard_messages

# -------------------------------------------------------------
# ContextGuard Usage Example
# -------------------------------------------------------------
# This script demonstrates how to use ContextGuard for a normal,
# safe message. It acts as a drop-in replacement for the
# standard openai.OpenAI client.
# -------------------------------------------------------------

def main():
    # 1. Initialize the client exactly as you normally would.
    # Note: We are using a dummy key and base_url so this script 
    # runs without charging you money.
    client = OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY", "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"),
        # Using openrouter for testing purposes
        base_url="https://openrouter.ai/api/v1" 
    )

    # 2. Add your messages. 
    # This message is perfectly safe and contains no secrets.
    messages = [
        {"role": "user", "content": f"Hello! What is this code {client.api_key}?"}
    ]
    
    try:
        # 3. Create the completion using the original messages.
        # GuardedOpenAI will automatically intercept this call and scan it!
        response = client.chat.completions.create(
            model="openai/gpt-4o-mini", 
            messages=messages
        )
        
        print("\n--- LLM RESPONSE ---")
        print(response.choices[0].message.content)

    except Exception as e:
        # This will catch the 401 Authentication error if you run this 
        # script without a real valid API key in your environment.
        print(f"\nAPI Error (Expected if using a dummy key):\n{e}")

if __name__ == "__main__":
    main()
