import openai
from typing import Any, Dict
from .guard import guard_messages

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
