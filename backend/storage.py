"""JSON-based storage for conversations with user scoping."""

import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from .config import get_user_conversations_dir


def ensure_user_dir(user_id: str):
    """Ensure the user's conversations directory exists."""
    Path(get_user_conversations_dir(user_id)).mkdir(parents=True, exist_ok=True)


def get_conversation_path(user_id: str, conversation_id: str) -> str:
    """Get the file path for a conversation."""
    return os.path.join(get_user_conversations_dir(user_id), f"{conversation_id}.json")


def create_conversation(user_id: str, conversation_id: str) -> Dict[str, Any]:
    """
    Create a new conversation.

    Args:
        user_id: The user's identifier
        conversation_id: Unique identifier for the conversation

    Returns:
        New conversation dict
    """
    ensure_user_dir(user_id)

    conversation = {
        "id": conversation_id,
        "user_id": user_id,
        "created_at": datetime.utcnow().isoformat(),
        "title": "New Conversation",
        "messages": []
    }

    # Save to file
    path = get_conversation_path(user_id, conversation_id)
    with open(path, 'w') as f:
        json.dump(conversation, f, indent=2)

    return conversation


def get_conversation(user_id: str, conversation_id: str) -> Optional[Dict[str, Any]]:
    """
    Load a conversation from storage.

    Args:
        user_id: The user's identifier
        conversation_id: Unique identifier for the conversation

    Returns:
        Conversation dict or None if not found
    """
    path = get_conversation_path(user_id, conversation_id)

    if not os.path.exists(path):
        return None

    with open(path, 'r') as f:
        return json.load(f)


def delete_conversation(user_id: str, conversation_id: str) -> bool:
    """
    Delete a conversation from storage.

    Args:
        user_id: The user's identifier
        conversation_id: Unique identifier for the conversation

    Returns:
        True if deleted successfully, False if not found
    """
    path = get_conversation_path(user_id, conversation_id)

    if not os.path.exists(path):
        return False

    os.remove(path)
    return True


def save_conversation(user_id: str, conversation: Dict[str, Any]):
    """
    Save a conversation to storage.

    Args:
        user_id: The user's identifier
        conversation: Conversation dict to save
    """
    ensure_user_dir(user_id)

    path = get_conversation_path(user_id, conversation['id'])
    with open(path, 'w') as f:
        json.dump(conversation, f, indent=2)


def list_conversations(user_id: str) -> List[Dict[str, Any]]:
    """
    List all conversations for a user (metadata only).

    Args:
        user_id: The user's identifier

    Returns:
        List of conversation metadata dicts
    """
    ensure_user_dir(user_id)
    data_dir = get_user_conversations_dir(user_id)

    conversations = []
    for filename in os.listdir(data_dir):
        if filename.endswith('.json'):
            path = os.path.join(data_dir, filename)
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                    # Return metadata only
                    conversations.append({
                        "id": data["id"],
                        "created_at": data["created_at"],
                        "title": data.get("title", "New Conversation"),
                        "message_count": len(data["messages"])
                    })
            except (json.JSONDecodeError, KeyError):
                # Skip corrupted files
                continue

    # Sort by creation time, newest first
    conversations.sort(key=lambda x: x["created_at"], reverse=True)

    return conversations


def add_user_message(user_id: str, conversation_id: str, content: str):
    """
    Add a user message to a conversation.

    Args:
        user_id: The user's identifier
        conversation_id: Conversation identifier
        content: User message content
    """
    conversation = get_conversation(user_id, conversation_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")

    conversation["messages"].append({
        "role": "user",
        "content": content
    })

    save_conversation(user_id, conversation)


def add_assistant_message(
    user_id: str,
    conversation_id: str,
    stage1: List[Dict[str, Any]],
    stage2: List[Dict[str, Any]],
    stage3: Dict[str, Any]
):
    """
    Add an assistant message with all 3 stages to a conversation.

    Args:
        user_id: The user's identifier
        conversation_id: Conversation identifier
        stage1: List of individual model responses
        stage2: List of model rankings
        stage3: Final synthesized response
    """
    conversation = get_conversation(user_id, conversation_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")

    conversation["messages"].append({
        "role": "assistant",
        "stage1": stage1,
        "stage2": stage2,
        "stage3": stage3
    })

    save_conversation(user_id, conversation)


def update_conversation_title(user_id: str, conversation_id: str, title: str):
    """
    Update the title of a conversation.

    Args:
        user_id: The user's identifier
        conversation_id: Conversation identifier
        title: New title for the conversation
    """
    conversation = get_conversation(user_id, conversation_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")

    conversation["title"] = title
    save_conversation(user_id, conversation)
