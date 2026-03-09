import re
import math
from typing import Dict, List, Tuple

# Detection patterns currently implemented
PATTERNS = {
    "OPENAI_API_KEY": re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    "ANTHROPIC_API_KEY": re.compile(r"sk-ant-[a-zA-Z0-9-_]{20,}"),
    "OPENROUTER_KEY": re.compile(r"sk-or-[a-zA-Z0-9-_]{20,}"),
    "GITHUB_TOKEN": re.compile(r"gh[ps]_[a-zA-Z0-9]{36}"),
    "AWS_ACCESS_KEY": re.compile(r"AKIA[0-9A-Z]{16}"),
    "JWT": re.compile(r"eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+"),
    "BEARER_TOKEN": re.compile(r"Bearer\s+([A-Za-z0-9\-\._~\+\/]+=*)"),
    "PRIVATE_KEY": re.compile(r"-----BEGIN(?:[A-Z\s]+)?PRIVATE KEY-----.*?-----END(?:[A-Z\s]+)?PRIVATE KEY-----", re.DOTALL)
}

HIGH_ENTROPY_THRESHOLD = 4.2
MIN_ENTROPY_LENGTH = 20

def calculate_shannon_entropy(string: str) -> float:
    """Calculates the Shannon entropy of a string."""
    if not string:
        return 0.0

    entropy = 0.0
    length = len(string)
    
    # Calculate character frequencies map
    freqs = {}
    for char in string:
        freqs[char] = freqs.get(char, 0) + 1
        
    for count in freqs.values():
        p_x = float(count) / length
        if p_x > 0:
            entropy += - p_x * math.log2(p_x)
            
    return entropy

def find_secrets(text: str) -> List[Tuple[str, str]]:
    """
    Scans text for secrets based on regex patterns and entropy.
    Returns a list of tuples: (label, matching_string).
    """
    secrets = []
    
    # Check regex patterns
    for label, pattern in PATTERNS.items():
        for match in pattern.finditer(text):
            secret_string = match.group(0)
            secrets.append((label, secret_string))
            
    # Check entropy (split by whitespace to find candidate tokens)
    tokens = re.split(r'\s+', text)
    for token in tokens:
        # Strip basic punctuation that might be attached
        clean_token = token.strip('.,;:!?()[]{}"\'')
        
        # We only check long enough tokens to avoid false positives on normal words
        if len(clean_token) >= MIN_ENTROPY_LENGTH:
            entropy = calculate_shannon_entropy(clean_token)
            if entropy >= HIGH_ENTROPY_THRESHOLD:
                # Avoid flagging if it was already caught by a regex
                already_caught = any(clean_token in s_match for _, s_match in secrets)
                if not already_caught:
                    secrets.append(("HIGH_ENTROPY_SECRET", clean_token))
                    
    return secrets

def redact_secrets(text: str, secrets: List[Tuple[str, str]]) -> str:
    """Replaces exact secret strings with generic labels."""
    redacted_text = text
    for label, secret in secrets:
        redacted_text = redacted_text.replace(secret, f"[{label}_REDACTED]")
    return redacted_text
