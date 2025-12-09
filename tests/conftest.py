"""Shared pytest fixtures for all tests."""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def temp_data_dir(monkeypatch):
    """Create a temporary directory for test data storage."""
    temp_dir = tempfile.mkdtemp()

    # Monkey-patch the data directories
    monkeypatch.setattr("backend.storage.DATA_DIR", temp_dir)
    monkeypatch.setattr("backend.agent_storage.AGENTS_FILE", Path(temp_dir) / "agents.json")
    monkeypatch.setattr("backend.prompt_storage.PROMPTS_FILE", Path(temp_dir) / "prompts.json")

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_agent():
    """Sample agent configuration."""
    return {
        "id": "test-agent-1",
        "title": "Test Agent",
        "role": "Test role description",
        "model": "test/model-1",
        "prompts": {
            "stage1": "Test stage 1 prompt: {user_query}",
            "stage2": "Test stage 2 prompt: {responses_text}"
        },
        "active": True,
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00"
    }


@pytest.fixture
def sample_agents():
    """Multiple sample agents."""
    return [
        {
            "id": "agent-1",
            "title": "Agent One",
            "role": "First agent",
            "model": "test/model-1",
            "prompts": {},
            "active": True,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00"
        },
        {
            "id": "agent-2",
            "title": "Agent Two",
            "role": "Second agent",
            "model": "test/model-2",
            "prompts": {},
            "active": True,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00"
        },
        {
            "id": "agent-3",
            "title": "Agent Three",
            "role": "Third agent",
            "model": "test/model-3",
            "prompts": {},
            "active": False,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00"
        }
    ]


@pytest.fixture
def sample_conversation():
    """Sample conversation."""
    return {
        "id": "test-conv-1",
        "created_at": "2024-01-01T00:00:00",
        "title": "Test Conversation",
        "messages": [
            {"role": "user", "content": "Test question?"},
            {
                "role": "assistant",
                "stage1": [
                    {
                        "agent_id": "agent-1",
                        "agent_title": "Agent One",
                        "model": "test/model-1",
                        "response": "Response from agent 1"
                    }
                ],
                "stage2": [
                    {
                        "agent_id": "agent-1",
                        "agent_title": "Agent One",
                        "model": "test/model-1",
                        "ranking": "FINAL RANKING:\n1. Response A",
                        "parsed_ranking": ["Response A"]
                    }
                ],
                "stage3": {
                    "agent_title": "Chairman",
                    "model": "test/chairman",
                    "response": "Final synthesis"
                }
            }
        ]
    }


@pytest.fixture
def mock_openrouter_response():
    """Mock OpenRouter API response."""
    return {
        "choices": [
            {
                "message": {
                    "content": "This is a test response from the model.",
                    "reasoning_details": None
                }
            }
        ]
    }


@pytest.fixture
def mock_openrouter_client(mock_openrouter_response):
    """Mock httpx.AsyncClient for OpenRouter API calls."""
    mock_response = MagicMock()
    mock_response.json.return_value = mock_openrouter_response
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    return mock_client


@pytest.fixture
def sample_stage1_results():
    """Sample stage 1 results."""
    return [
        {
            "agent_id": "agent-1",
            "agent_title": "Agent One",
            "model": "test/model-1",
            "response": "This is response A with detailed analysis."
        },
        {
            "agent_id": "agent-2",
            "agent_title": "Agent Two",
            "model": "test/model-2",
            "response": "This is response B with alternative perspective."
        },
        {
            "agent_id": "agent-3",
            "agent_title": "Agent Three",
            "model": "test/model-3",
            "response": "This is response C with additional insights."
        }
    ]


@pytest.fixture
def sample_ranking_text_numbered():
    """Sample ranking text in numbered format."""
    return """I have evaluated all responses carefully.

FINAL RANKING:
1. Response C
2. Response A
3. Response B

This ranking is based on depth of analysis."""


@pytest.fixture
def sample_ranking_text_plain():
    """Sample ranking text without numbers."""
    return """After careful consideration.

FINAL RANKING:
Response B
Response C
Response A"""


@pytest.fixture
def sample_label_to_model():
    """Sample label to model mapping."""
    return {
        "Response A": {
            "agent_title": "Agent One",
            "model": "test/model-1"
        },
        "Response B": {
            "agent_title": "Agent Two",
            "model": "test/model-2"
        },
        "Response C": {
            "agent_title": "Agent Three",
            "model": "test/model-3"
        }
    }
