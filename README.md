# ContextGuard

A Python library that acts as a middleware layer between user/agent context and the LLM API. It intercepts the messages payload just before it's sent to the LLM, scans for secrets, and either prompts the user or silently redacts depending on whether a human is at the terminal.
