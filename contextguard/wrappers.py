import openai
from typing import Any, Dict
from .guard import guard_messages, guard_gemini_contents

class _GuardedCompletions:
    """Wrapper around the Completions API to intercept 'create' calls."""
    
    def __init__(self, original_completions: Any):
        self._original_completions = original_completions
        
    def create(self, **kwargs) -> Any:
        if "messages" in kwargs:
            kwargs["messages"] = guard_messages(kwargs["messages"])
            
        return self._original_completions.create(**kwargs)

class _GuardedChat:
    """Wrapper around the Chat API namespace to intercept."""
    
    def __init__(self, original_chat: Any):
        self._original_chat = original_chat
        self.completions = _GuardedCompletions(self._original_chat.completions)

class GuardedOpenAI(openai.OpenAI):
    """
    A drop-in replacement for openai.OpenAI that intercepts messages
    and scans them for secrets before sending to the API.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Override the chat namespace with our wrapped version
        self.chat = _GuardedChat(super().chat)

# --- Anthropic Wrappers ---

try:
    import anthropic

    class _GuardedAnthropicMessages:
        def __init__(self, original_messages: Any):
            self._original_messages = original_messages
            
        def create(self, **kwargs) -> Any:
            if "messages" in kwargs:
                # Anthropic uses the exact same `role` and `content` structure
                # as OpenAI for the basic text case, so we can reuse `guard_messages`
                kwargs["messages"] = guard_messages(kwargs["messages"])
            return self._original_messages.create(**kwargs)
            
    class GuardedAnthropic(anthropic.Anthropic):
        """
        A drop-in replacement for anthropic.Anthropic that intercepts messages
        and scans them for secrets before sending to the API.
        """
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.messages = _GuardedAnthropicMessages(super().messages)

except ImportError:
    pass

# --- Gemini Wrappers ---

try:
    from google import genai
    
    class _GuardedGeminiModels:
        def __init__(self, original_models: Any):
            self._original_models = original_models
            
        def generate_content(self, **kwargs) -> Any:
            if "contents" in kwargs:
                kwargs["contents"] = guard_gemini_contents(kwargs["contents"])
            return self._original_models.generate_content(**kwargs)
            
    class GuardedGemini(genai.Client):
        """
        A drop-in replacement for google.genai.Client that intercepts contents
        and scans them for secrets before sending to the API.
        """
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.models = _GuardedGeminiModels(super().models)
            
except ImportError:
    pass
