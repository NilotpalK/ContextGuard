<p align="center">
  <img src="img/image.png" alt="ContextGuard Logo" width="80%">
</p>

# ContextGuard

**ContextGuard** is a Python library that acts as a middleware layer between user/agent context and the LLM API. It intercepts the payload just before it's sent to the LLM and scans for secrets to prevent accidental data leaks.

## Problem it solves

When users or agents accidentally include secrets (API keys, JWTs, tokens) in messages to an LLM — whether by pasting them manually or an agent reading an environment file — this library catches and redacts them *before* they leave the machine.

## How it works

1. It acts as a drop-in replacement for the official `openai` Python SDK.
2. It wraps the `chat.completions.create` method.
3. It recursively scans all text in your `messages` array payload.
4. If secrets are found, it triggers based on your environment:
   * **Interactive Mode (Terminal attached)**: Shows a warning prompt giving you the option to `[r] Redact`, `[s] Send anyway`, or `[b] Block`.
   * **Unattended Mode (CI/CD, Agents)**: Silently redacts the secrets to prevent the pipeline from breaking, but logs a warning to `stderr`.

---

## Installation

ContextGuard is available via pip (requires `openai >= 1.0.0`):
```bash
pip install contextguard
```

*(Note: If installing locally from this repository during development, use `pip install -e .`)*

---

## Usage

ContextGuard is designed to be a one-line change to your existing codebase. You use it exactly the same way you use the official OpenAI SDK.

### Standard OpenAI Client

```python
# Before
from openai import OpenAI

# After
from contextguard import GuardedOpenAI as OpenAI

client = OpenAI(api_key="sk-your-real-key")

# Any secrets in this array will be flagged!
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "user", "content": "Here is my code for review: sk-1234567890..."}
    ]
)
```

### With OpenRouter

Because OpenRouter uses the exact same SDK pattern, it is also supported natively!

```python
from contextguard import GuardedOpenAI as OpenAI

client = OpenAI(
    api_key="sk-or-your-real-key",
    base_url="https://openrouter.ai/api/v1"
)
```

---

## Supported Operators (Detection Patterns)

ContextGuard uses a two-layer detection approach: **Known Signatures (Regex)** and **Generic Detection (Shannon Entropy)**.

Currently, it natively detects and protects against the leak of the following tokens:

| Label | Pattern Description |
|---|---|
| `OPENAI_API_KEY` | OpenAI standard API keys (`sk-...`) |
| `ANTHROPIC_API_KEY` | Anthropic Claude API keys (`sk-ant-...`) |
| `OPENROUTER_KEY` | OpenRouter API keys (`sk-or-...`) |
| `GITHUB_TOKEN` | GitHub Personal Access Tokens (`ghp_...` / `ghs_...`) |
| `AWS_ACCESS_KEY` | AWS IAM Access Keys (`AKIA...`) |
| `JWT` | Standard JSON Web Tokens (`eyJ...`) |
| `BEARER_TOKEN` | Generic Bearer Tokens (`Bearer <token>`) |
| `PRIVATE_KEY` | PEM Encoded Private Keys (`-----BEGIN PRIVATE KEY-----`) |
| `HIGH_ENTROPY_SECRET` | Any unknown 20+ character string with a Shannon Entropy ≥ 4.2 |

The entropy analysis acts as a powerful catch-all for unknown API keys, base64 encoded passwords, or database connection strings that don't match standard vendor prefixes.

---

## Architectural Decisions

* **Not a network proxy**: Wraps the SDK directly, meaning no TLS/certificate proxy complexity.
* **User-side only**: Protects against accidental developer leaks locally, not a server-side enterprise gateway.
* **Fail-Safe**: Default action is to redact and send so autonomous agents don't silently break and hang forever when encountering a secret.
