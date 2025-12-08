"""Storage and management for agent configurations."""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

AGENTS_FILE = Path(__file__).parent.parent / "data" / "agents.json"


def ensure_data_directory():
    """Ensure the data directory exists."""
    AGENTS_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_agents() -> Dict[str, Any]:
    """
    Load agent configurations from storage.

    Returns:
        Dict with 'agents' list and 'chairman' id
    """
    ensure_data_directory()

    if not AGENTS_FILE.exists():
        return {"agents": [], "chairman": None}

    try:
        with open(AGENTS_FILE, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {"agents": [], "chairman": None}


def save_agents(agents_data: Dict[str, Any]) -> None:
    """
    Save agent configurations to storage.

    Args:
        agents_data: Dict with 'agents' list and 'chairman' id
    """
    ensure_data_directory()

    with open(AGENTS_FILE, 'w') as f:
        json.dump(agents_data, f, indent=2)


def get_all_agents() -> List[Dict[str, Any]]:
    """
    Get all agent configurations.

    Returns:
        List of agent configurations
    """
    data = load_agents()
    return data["agents"]


def get_active_agents() -> List[Dict[str, Any]]:
    """
    Get only active agent configurations.

    Returns:
        List of active agent configurations
    """
    agents = get_all_agents()
    return [agent for agent in agents if agent.get("active", True)]


def get_agent_by_id(agent_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific agent by ID.

    Args:
        agent_id: The agent's unique identifier

    Returns:
        Agent configuration or None if not found
    """
    agents = get_all_agents()
    for agent in agents:
        if agent["id"] == agent_id:
            return agent
    return None


def create_agent(
    title: str,
    role: str,
    model: str,
    prompts: Optional[Dict[str, str]] = None,
    active: bool = True
) -> Dict[str, Any]:
    """
    Create a new agent configuration.

    Args:
        title: Human-friendly name for the agent
        role: Description of the agent's expertise/role
        model: The LLM model identifier
        prompts: Optional custom prompts for each stage
        active: Whether the agent is active

    Returns:
        The created agent configuration
    """
    data = load_agents()

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
    save_agents(data)

    return agent


def update_agent(agent_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Update an existing agent configuration.

    Args:
        agent_id: The agent's unique identifier
        updates: Dict of fields to update

    Returns:
        Updated agent configuration or None if not found
    """
    data = load_agents()

    for i, agent in enumerate(data["agents"]):
        if agent["id"] == agent_id:
            # Update fields
            for key, value in updates.items():
                if key != "id" and key != "created_at":  # Don't allow changing these
                    agent[key] = value

            agent["updated_at"] = datetime.utcnow().isoformat()
            data["agents"][i] = agent
            save_agents(data)
            return agent

    return None


def delete_agent(agent_id: str) -> bool:
    """
    Delete an agent configuration.

    Args:
        agent_id: The agent's unique identifier

    Returns:
        True if deleted, False if not found
    """
    data = load_agents()

    original_length = len(data["agents"])
    data["agents"] = [agent for agent in data["agents"] if agent["id"] != agent_id]

    if len(data["agents"]) < original_length:
        save_agents(data)
        return True

    return False


def set_chairman(agent_id: Optional[str]) -> bool:
    """
    Set which agent is the chairman.

    Args:
        agent_id: The agent's unique identifier, or None to use default

    Returns:
        True if successful
    """
    data = load_agents()

    # Validate agent exists if not None
    if agent_id is not None:
        agent = get_agent_by_id(agent_id)
        if not agent:
            return False

    data["chairman"] = agent_id
    save_agents(data)
    return True


def get_chairman() -> Optional[Dict[str, Any]]:
    """
    Get the chairman agent configuration.

    Returns:
        Chairman agent configuration or None if using default
    """
    data = load_agents()
    chairman_id = data.get("chairman")

    if chairman_id:
        return get_agent_by_id(chairman_id)

    return None


def initialize_default_agents() -> List[Dict[str, Any]]:
    """
    Initialize with default agent templates if no agents exist.

    Returns:
        List of created default agents
    """
    existing = get_all_agents()
    if existing:
        return existing

    default_agents = [
        {
            "title": "Ethics & Values Advisor",
            "role": "Provides ethical guidance and helps evaluate decisions through a moral lens, considering values, principles, and long-term consequences.",
            "model": "anthropic/claude-sonnet-4.5",
            "prompts": {
                "stage1": "You are the Ethics & Values Advisor on a personal board of directors. Evaluate the following question from an ethical perspective, considering moral principles, values, and long-term consequences:\n\n{user_query}"
            }
        },
        {
            "title": "Technology & Innovation Expert",
            "role": "Offers technical insights, evaluates technological feasibility, and provides guidance on innovation and digital transformation.",
            "model": "openai/gpt-5.1",
            "prompts": {
                "stage1": "You are the Technology & Innovation Expert on a personal board of directors. Analyze the following question from a technical and innovation perspective:\n\n{user_query}"
            }
        },
        {
            "title": "Leadership & Strategy Coach",
            "role": "Provides strategic guidance, leadership development advice, and helps with long-term planning and decision-making.",
            "model": "google/gemini-3-pro-preview",
            "prompts": {
                "stage1": "You are the Leadership & Strategy Coach on a personal board of directors. Provide strategic and leadership-focused guidance on:\n\n{user_query}"
            }
        },
        {
            "title": "Financial & Business Advisor",
            "role": "Offers financial insights, business strategy, and helps evaluate economic implications of decisions.",
            "model": "x-ai/grok-4",
            "prompts": {
                "stage1": "You are the Financial & Business Advisor on a personal board of directors. Analyze the following from a financial and business perspective:\n\n{user_query}"
            }
        }
    ]

    created = []
    for agent_data in default_agents:
        agent = create_agent(
            title=agent_data["title"],
            role=agent_data["role"],
            model=agent_data["model"],
            prompts=agent_data["prompts"],
            active=True
        )
        created.append(agent)

    return created
