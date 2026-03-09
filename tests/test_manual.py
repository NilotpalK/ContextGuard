import os
import sys

# Add the parent directory to sys.path so we can import contextguard
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from contextguard import GuardedOpenAI, SecretLeakError

# This script is meant to be run manually by a human to test the interactive prompt.

# We'll initialize the wrapper. 
# We don't need a real API key to test the interception layer!
client = GuardedOpenAI(
    api_key="sk-or-dummykey",
    base_url="https://openrouter.ai/api/v1"
)

def main():
    print("Testing ContextGuard Interception")
    print("-" * 40)
    
    fake_secret = "sk-1234567890abcdef1234567890abcdef"
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": f"Here is my API key, please use it: {fake_secret}"}
    ]
    
    print("\nAttempting to send message with fake secret...")
    try:
        # Wrap this in a try/except because if 's' or 'r' is chosen, 
        # it will actually try to hit the API with the dummy key and likely get a 401,
        # but that's fine, it means it got past our guard.
        response = client.chat.completions.create(
            model="openai/gpt-3.5-turbo",
            messages=messages
        )
        print("\nRequest completed successfully! (Secret was sent or redacted)")
        print(f"API Response (might be an error due to fake key): {response}")
    except SecretLeakError as e:
        print(f"\nCaught SecretLeakError: {e}")
        print("The request was blocked as expected.")
    except Exception as e:
        # We let other exceptions bubble up so you can see the normal API behavior
        raise

if __name__ == "__main__":
    main()
