"""Storage and management for agent configurations with user scoping."""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from .config import get_user_agents_file, get_user_data_dir


def ensure_user_directory(user_id: str):
    """Ensure the user's data directory exists."""
    Path(get_user_data_dir(user_id)).mkdir(parents=True, exist_ok=True)


def load_agents(user_id: str) -> Dict[str, Any]:
    """
    Load agent configurations from storage for a user.

    Args:
        user_id: The user's identifier

    Returns:
        Dict with 'agents' list and 'chairman' id
    """
    ensure_user_directory(user_id)
    agents_file = Path(get_user_agents_file(user_id))

    if not agents_file.exists():
        # Initialize with defaults for new users
        return initialize_default_agents_data()

    try:
        with open(agents_file, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return initialize_default_agents_data()


def save_agents(user_id: str, agents_data: Dict[str, Any]) -> None:
    """
    Save agent configurations to storage for a user.

    Args:
        user_id: The user's identifier
        agents_data: Dict with 'agents' list and 'chairman' id
    """
    ensure_user_directory(user_id)
    agents_file = Path(get_user_agents_file(user_id))

    with open(agents_file, 'w') as f:
        json.dump(agents_data, f, indent=2)


def get_all_agents(user_id: str) -> List[Dict[str, Any]]:
    """
    Get all agent configurations for a user.

    Args:
        user_id: The user's identifier

    Returns:
        List of agent configurations
    """
    data = load_agents(user_id)
    return data["agents"]


def get_active_agents(user_id: str) -> List[Dict[str, Any]]:
    """
    Get only active agent configurations for a user.

    Args:
        user_id: The user's identifier

    Returns:
        List of active agent configurations
    """
    agents = get_all_agents(user_id)
    return [agent for agent in agents if agent.get("active", True)]


def get_agent_by_id(user_id: str, agent_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific agent by ID for a user.

    Args:
        user_id: The user's identifier
        agent_id: The agent's unique identifier

    Returns:
        Agent configuration or None if not found
    """
    agents = get_all_agents(user_id)
    for agent in agents:
        if agent["id"] == agent_id:
            return agent
    return None


def create_agent(
    user_id: str,
    title: str,
    role: str,
    model: str,
    prompts: Optional[Dict[str, str]] = None,
    active: bool = True
) -> Dict[str, Any]:
    """
    Create a new agent configuration for a user.

    Args:
        user_id: The user's identifier
        title: Human-friendly name for the agent
        role: Description of the agent's expertise/role
        model: The LLM model identifier
        prompts: Optional custom prompts for each stage
        active: Whether the agent is active

    Returns:
        The created agent configuration
    """
    data = load_agents(user_id)

    agent = {
        "id": str(uuid.uuid4()),
        "title": title,
        "role": role,
        "model": model,
        "prompts": prompts or {},
        "active": active,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }

    data["agents"].append(agent)
    save_agents(user_id, data)

    return agent


def update_agent(user_id: str, agent_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Update an existing agent configuration for a user.

    Args:
        user_id: The user's identifier
        agent_id: The agent's unique identifier
        updates: Dict of fields to update

    Returns:
        Updated agent configuration or None if not found
    """
    data = load_agents(user_id)

    for i, agent in enumerate(data["agents"]):
        if agent["id"] == agent_id:
            # Update fields
            for key, value in updates.items():
                if key != "id" and key != "created_at":  # Don't allow changing these
                    agent[key] = value

            agent["updated_at"] = datetime.utcnow().isoformat()
            data["agents"][i] = agent
            save_agents(user_id, data)
            return agent

    return None


def delete_agent(user_id: str, agent_id: str) -> bool:
    """
    Delete an agent configuration for a user.

    Args:
        user_id: The user's identifier
        agent_id: The agent's unique identifier

    Returns:
        True if deleted, False if not found
    """
    data = load_agents(user_id)

    original_length = len(data["agents"])
    data["agents"] = [agent for agent in data["agents"] if agent["id"] != agent_id]

    if len(data["agents"]) < original_length:
        save_agents(user_id, data)
        return True

    return False


def set_chairman(user_id: str, agent_id: Optional[str]) -> bool:
    """
    Set which agent is the chairman for a user.

    Args:
        user_id: The user's identifier
        agent_id: The agent's unique identifier, or None to use default

    Returns:
        True if successful
    """
    data = load_agents(user_id)

    # Validate agent exists if not None
    if agent_id is not None:
        agent = get_agent_by_id(user_id, agent_id)
        if not agent:
            return False

    data["chairman"] = agent_id
    save_agents(user_id, data)
    return True


def get_chairman(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the chairman agent configuration for a user.

    Args:
        user_id: The user's identifier

    Returns:
        Chairman agent configuration or None if using default
    """
    data = load_agents(user_id)
    chairman_id = data.get("chairman")

    if chairman_id:
        return get_agent_by_id(user_id, chairman_id)

    return None


def initialize_default_agents_data() -> Dict[str, Any]:
    """
    Create the default agents data structure.

    Returns:
        Dict with default agents and chairman
    """
    default_agents = [
        {
            "id": str(uuid.uuid4()),
            "title": "Ethics & Values Advisor",
            "role": "Provides ethical guidance and helps evaluate decisions through a moral lens, considering values, principles, and long-term consequences.",
            "model": "anthropic/claude-sonnet-4.5",
            "prompts": {
                "stage1": "You are the Ethics & Values Advisor on a personal board of directors. Evaluate the following question from an ethical perspective, considering moral principles, values, and long-term consequences:\n\n{user_query}"
            },
            "active": True,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Technology & Innovation Expert",
            "role": "Offers technical insights, evaluates technological feasibility, and provides guidance on innovation and digital transformation.",
            "model": "openai/gpt-5.1",
            "prompts": {
                "stage1": "You are the Technology & Innovation Expert on a personal board of directors. Analyze the following question from a technical and innovation perspective:\n\n{user_query}"
            },
            "active": True,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Leadership & Strategy Coach",
            "role": "Provides strategic guidance, leadership development advice, and helps with long-term planning and decision-making.",
            "model": "google/gemini-3-pro-preview",
            "prompts": {
                "stage1": "You are the Leadership & Strategy Coach on a personal board of directors. Provide strategic and leadership-focused guidance on:\n\n{user_query}"
            },
            "active": True,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Financial & Business Advisor",
            "role": "Offers financial insights, business strategy, and helps evaluate economic implications of decisions.",
            "model": "x-ai/grok-4",
            "prompts": {
                "stage1": "You are the Financial & Business Advisor on a personal board of directors. Analyze the following from a financial and business perspective:\n\n{user_query}"
            },
            "active": True,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
    ]

    return {"agents": default_agents, "chairman": None}


def initialize_default_agents(user_id: str) -> List[Dict[str, Any]]:
    """
    Initialize with default agent templates for a user if no agents exist.

    Args:
        user_id: The user's identifier

    Returns:
        List of created default agents
    """
    existing = get_all_agents(user_id)
    if existing:
        return existing

    # Create default agents
    data = initialize_default_agents_data()
    save_agents(user_id, data)

    return data["agents"]
