import pytest
from unittest.mock import patch
from contextguard.patterns import find_secrets, redact_secrets, calculate_shannon_entropy
from contextguard.guard import guard_messages, SecretLeakError

# Dummy secrets for testing
MOCK_SECRETS = {
    "OPENAI_API_KEY": "sk-1234567890abcdef1234567890abcdef",
    "ANTHROPIC_API_KEY": "sk-ant-1234567890abcdef1234567890abcdef",
    "OPENROUTER_KEY": "sk-or-1234567890abcdef1234567890abcdef",
    "GITHUB_TOKEN": "ghp_123456789012345678901234567890123456",
    "AWS_ACCESS_KEY": "AKIA1234567890ABCDEF",
    "JWT": "eyJhbGciOiJIUzI1NiIsInR5cCI.eyJzdWIiOiIxMjM.SflKxwRJSMeKKF",
}

def test_regex_patterns():
    for label, secret in MOCK_SECRETS.items():
        text = f"Here is my key: {secret} do not share it."
        secrets_found = find_secrets(text)
        assert len(secrets_found) >= 1
        assert any(s[0] == label and s[1] == secret for s in secrets_found)

def test_entropy_detection():
    # A string of random characters that should trigger the entropy detector
    high_entropy_string = "aB3cD4eF5gH6iJ7kL8mN9oP0qR1sT2uV3wX4yZ5"
    assert len(high_entropy_string) >= 20
    assert calculate_shannon_entropy(high_entropy_string) >= 4.2
    
    text = f"My password is {high_entropy_string}"
    secrets_found = find_secrets(text)
    assert len(secrets_found) == 1
    assert secrets_found[0][0] == "HIGH_ENTROPY_SECRET"
    assert secrets_found[0][1] == high_entropy_string

def test_clean_text_passes():
    text = "Hello, what is the weather today? No secrets here."
    secrets_found = find_secrets(text)
    assert len(secrets_found) == 0

def test_redaction_works():
    text = f"Key: {MOCK_SECRETS['OPENAI_API_KEY']} and {MOCK_SECRETS['AWS_ACCESS_KEY']}."
    secrets = find_secrets(text)
    redacted = redact_secrets(text, secrets)
    assert redacted == "Key: <OPENAI_API_KEY_REDACTED> and <AWS_ACCESS_KEY_REDACTED>."

@patch('sys.stdin.isatty', return_value=False)
def test_unattended_pipeline_silently_redacts(mock_isatty):
    messages = [
        {"role": "user", "content": f"Use key {MOCK_SECRETS['OPENAI_API_KEY']}"}
    ]
    
    with patch('sys.stderr.write') as mock_stderr:
        result = guard_messages(messages)
    
        # Should be redacted
        assert "<OPENAI_API_KEY_REDACTED>" in result[0]["content"]
        assert MOCK_SECRETS['OPENAI_API_KEY'] not in result[0]["content"]
        
        # Original message should NOT be mutated
        assert MOCK_SECRETS['OPENAI_API_KEY'] in messages[0]["content"]

@patch('sys.stdin.isatty', return_value=True)
@patch('builtins.input', return_value='r')
def test_interactive_redact(mock_input, mock_isatty):
    messages = [{"role": "user", "content": f"Key: {MOCK_SECRETS['GITHUB_TOKEN']}"}]
    result = guard_messages(messages)
    assert "<GITHUB_TOKEN_REDACTED>" in result[0]["content"]

@patch('sys.stdin.isatty', return_value=True)
@patch('builtins.input', return_value='s')
def test_interactive_send(mock_input, mock_isatty):
    messages = [{"role": "user", "content": f"Key: {MOCK_SECRETS['GITHUB_TOKEN']}"}]
    result = guard_messages(messages)
    # Should be returned untouched
    assert MOCK_SECRETS['GITHUB_TOKEN'] in result[0]["content"]

@patch('sys.stdin.isatty', return_value=True)
@patch('builtins.input', return_value='b')
def test_interactive_block(mock_input, mock_isatty):
    messages = [{"role": "user", "content": f"Key: {MOCK_SECRETS['GITHUB_TOKEN']}"}]
    with pytest.raises(SecretLeakError):
        guard_messages(messages)

def test_nested_content_blocks():
    # Simulate a complicated message structure (like Anthropic uses sometimes, or OpenAI Vision)
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Describe this code:"},
                {"type": "text", "text": f"API_KEY = '{MOCK_SECRETS['OPENAI_API_KEY']}'"}
            ]
        }
    ]
    
    with patch('sys.stdin.isatty', return_value=False):
        result = guard_messages(messages)
        content = result[0]["content"]
        assert "<OPENAI_API_KEY_REDACTED>" in content[1]["text"]
        assert MOCK_SECRETS['OPENAI_API_KEY'] not in content[1]["text"]
