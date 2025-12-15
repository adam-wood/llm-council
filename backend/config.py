"""Configuration for the LLM Council."""

import os
from dotenv import load_dotenv

load_dotenv()

# OpenRouter API key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Council members - list of OpenRouter model identifiers
COUNCIL_MODELS = [
    "openai/gpt-5.1",
    "google/gemini-3-pro-preview",
    "anthropic/claude-sonnet-4.5",
    "x-ai/grok-4",
]

# Chairman model - synthesizes final response
CHAIRMAN_MODEL = "google/gemini-3-pro-preview"

# OpenRouter API endpoint
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Base data directory
DATA_BASE_DIR = "data"


def get_user_data_dir(user_id: str) -> str:
    """Get the data directory for a specific user."""
    return f"{DATA_BASE_DIR}/users/{user_id}"


def get_user_conversations_dir(user_id: str) -> str:
    """Get the conversations directory for a specific user."""
    return f"{get_user_data_dir(user_id)}/conversations"


def get_user_agents_file(user_id: str) -> str:
    """Get the agents file path for a specific user."""
    return f"{get_user_data_dir(user_id)}/agents.json"


def get_user_prompts_file(user_id: str) -> str:
    """Get the prompts file path for a specific user."""
    return f"{get_user_data_dir(user_id)}/prompts.json"
