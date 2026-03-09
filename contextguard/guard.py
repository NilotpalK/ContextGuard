import sys
import copy
from typing import List, Dict, Any
from .patterns import find_secrets, redact_secrets

class SecretLeakError(Exception):
    """Raised when a user explicitly blocks a detected secret from being sent."""
    pass

def _get_interactive_choice(secrets_found: List[tuple]) -> str:
    """Prompts the user on the TTY when secrets are detected."""
    print("============================================================")
    print("⚠️  CONTEXTGUARD: Secret detected in message to LLM")
    print("============================================================")
    
    for label, secret in secrets_found:
        # Show only prefix to avoid printing the whole secret cleanly
        preview = secret[:8] + "..." if len(secret) > 8 else "***"
        print(f"  → {label}: {preview}")
        
    print("============================================================")
    print("  [r] Redact and send (default)")
    print("  [s] Send anyway")
    print("  [b] Block — raise an error")
    print("============================================================")
    
    while True:
        try:
            choice = input("Your choice (r/s/b) [r]: ").strip().lower()
            if not choice:
                return 'r'
            if choice in ['r', 's', 'b']:
                return choice
            print("Invalid choice. Please enter r, s, or b.")
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.")
            return 'b'

def guard_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Scans the OpenAI messages array for secrets.
    Depending on TTY presence and user choice, either redacts, passes through, or blocks.
    Returns the (potentially redacted) messages array.
    """
    # Create a deep copy to avoid mutating the user's data
    guarded_messages = copy.deepcopy(messages)
    
    all_secrets_found = []
    
    # First pass: find all secrets
    for message in guarded_messages:
        content = message.get("content")
        if not content:
            continue
            
        if isinstance(content, str):
            secrets = find_secrets(content)
            all_secrets_found.extend(secrets)
            
        elif isinstance(content, list):
            # Handle multi-part content (e.g., Vision API or tool calls arrays)
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    text = part.get("text", "")
                    secrets = find_secrets(text)
                    all_secrets_found.extend(secrets)
    
    if not all_secrets_found:
        return guarded_messages
        
    # Secrets were found, decide on action
    action = 'r' # default
    
    if sys.stdin.isatty():
        # Interactive mode
        action = _get_interactive_choice(all_secrets_found)
    else:
        # Unattended mode
        print(f"⚠️ CONTEXTGUARD: Secrets detected and redacted in unattended mode: {', '.join([l for l, _ in all_secrets_found])}", file=sys.stderr)
        action = 'r'
        
    if action == 'b':
        raise SecretLeakError("Message blocked by user due to detected secrets.")
    elif action == 's':
        # Send anyway, return original messages
        return messages
    elif action == 'r':
        # Second pass: apply redaction
        for message in guarded_messages:
            content = message.get("content")
            if not content:
                continue
                
            if isinstance(content, str):
                secrets = find_secrets(content)
                if secrets:
                    message["content"] = redact_secrets(content, secrets)
                    
            elif isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        text = part.get("text", "")
                        secrets = find_secrets(text)
                        if secrets:
                            part["text"] = redact_secrets(text, secrets)
                            
        return guarded_messages

def guard_gemini_contents(contents: Any) -> Any:
    """
    Scans the Gemini contents array (or string/Content objects) for secrets.
    Depending on TTY presence and user choice, either redacts, passes through, or blocks.
    Returns the (potentially redacted) contents.
    """
    try:
        from google import genai
    except ImportError:
        pass # Handle when used without standard type checking available
        
    # We must operate on a deep copy
    guarded_contents = copy.deepcopy(contents)
    
    all_secrets_found = []
    
    # helper for recursion into Gemini's format
    def extract_secrets_from_part(part: Any):
        if hasattr(part, "text") and getattr(part, "text"):
            all_secrets_found.extend(find_secrets(part.text))
            
    def scan_content(c: Any):
        if isinstance(c, str):
            all_secrets_found.extend(find_secrets(c))
        elif isinstance(c, dict) and "parts" in c:
            for p in c["parts"]:
                if isinstance(p, dict) and "text" in p:
                    all_secrets_found.extend(find_secrets(p["text"]))
        elif hasattr(c, "parts"):
            for p in c.parts:
                extract_secrets_from_part(p)
                
    # Initial scan
    if isinstance(guarded_contents, list):
        for item in guarded_contents:
            scan_content(item)
    else:
        scan_content(guarded_contents)
        
    if not all_secrets_found:
        return guarded_contents
        
    # Secrets were found, decide on action
    action = 'r' # default
    
    if sys.stdin.isatty():
        action = _get_interactive_choice(all_secrets_found)
    else:
        print(f"⚠️ CONTEXTGUARD: Secrets detected and redacted in unattended mode: {', '.join([l for l, _ in all_secrets_found])}", file=sys.stderr)
        action = 'r'
        
    if action == 'b':
        raise SecretLeakError("Message blocked by user due to detected secrets.")
    elif action == 's':
        return contents
    elif action == 'r':
        # Apply redaction
        def redact_part(part: Any):
            if hasattr(part, "text") and getattr(part, "text"):
                sec = find_secrets(part.text)
                if sec:
                    part.text = redact_secrets(part.text, sec)
                    
        def redact_c(c: Any):
            if isinstance(c, str):
                sec = find_secrets(c)
                if sec:
                    return redact_secrets(c, sec)
            elif isinstance(c, dict) and "parts" in c:
                for p in c["parts"]:
                    if isinstance(p, dict) and "text" in p:
                        sec = find_secrets(p["text"])
                        if sec:
                            p["text"] = redact_secrets(p["text"], sec)
            elif hasattr(c, "parts"):
                for p in c.parts:
                    redact_part(p)
            return c
            
        if isinstance(guarded_contents, list):
            for i in range(len(guarded_contents)):
                guarded_contents[i] = redact_c(guarded_contents[i])
        else:
            guarded_contents = redact_c(guarded_contents)
            
        return guarded_contents
