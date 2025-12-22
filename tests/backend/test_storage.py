"""Tests for storage.py - conversation management."""

import pytest
import json
import os
from pathlib import Path
from freezegun import freeze_time
from backend import storage
from tests.conftest import (
    TEST_USER_ID, TEST_CONV_ID_1, TEST_CONV_ID_2, TEST_CONV_ID_3, TEST_INVALID_ID
)

# A valid UUID that won't exist in test data
NONEXISTENT_CONV_ID = "99999999-9999-9999-9999-999999999999"


class TestConversationCRUD:
    """Test conversation CRUD operations."""

    def test_create_conversation(self, temp_data_dir, test_user_id):
        """Test creating a new conversation."""
        with freeze_time("2024-01-01 12:00:00"):
            conv = storage.create_conversation(test_user_id, TEST_CONV_ID_1)

            assert conv["id"] == TEST_CONV_ID_1
            assert conv["created_at"] == "2024-01-01T12:00:00"
            assert conv["title"] == "New Conversation"
            assert conv["messages"] == []

    def test_get_conversation(self, temp_data_dir, test_user_id):
        """Test retrieving a conversation."""
        storage.create_conversation(test_user_id, TEST_CONV_ID_1)

        conv = storage.get_conversation(test_user_id, TEST_CONV_ID_1)

        assert conv is not None
        assert conv["id"] == TEST_CONV_ID_1

    def test_get_nonexistent_conversation(self, temp_data_dir, test_user_id):
        """Test retrieving non-existent conversation."""
        conv = storage.get_conversation(test_user_id, NONEXISTENT_CONV_ID)

        assert conv is None

    def test_save_conversation(self, temp_data_dir, test_user_id):
        """Test saving conversation updates."""
        conv = storage.create_conversation(test_user_id, TEST_CONV_ID_1)
        conv["title"] = "Updated Title"
        conv["messages"].append({"role": "user", "content": "Test"})

        storage.save_conversation(test_user_id, conv)

        # Reload and verify
        loaded = storage.get_conversation(test_user_id, TEST_CONV_ID_1)
        assert loaded["title"] == "Updated Title"
        assert len(loaded["messages"]) == 1

    def test_list_conversations(self, temp_data_dir, test_user_id):
        """Test listing all conversations."""
        with freeze_time("2024-01-01 10:00:00"):
            storage.create_conversation(test_user_id, TEST_CONV_ID_1)

        with freeze_time("2024-01-01 12:00:00"):
            storage.create_conversation(test_user_id, TEST_CONV_ID_2)

        with freeze_time("2024-01-01 11:00:00"):
            storage.create_conversation(test_user_id, TEST_CONV_ID_3)

        conversations = storage.list_conversations(test_user_id)

        # Should return metadata only
        assert len(conversations) == 3

        # Should be sorted by creation time, newest first
        assert conversations[0]["id"] == TEST_CONV_ID_2  # 12:00
        assert conversations[1]["id"] == TEST_CONV_ID_3  # 11:00
        assert conversations[2]["id"] == TEST_CONV_ID_1  # 10:00

    def test_list_conversations_metadata_only(self, temp_data_dir, test_user_id):
        """Test that list_conversations returns metadata only."""
        conv = storage.create_conversation(test_user_id, TEST_CONV_ID_1)
        storage.add_user_message(test_user_id, TEST_CONV_ID_1, "Test message")

        conversations = storage.list_conversations(test_user_id)

        # Should have metadata fields
        assert "id" in conversations[0]
        assert "created_at" in conversations[0]
        assert "title" in conversations[0]
        assert "message_count" in conversations[0]

        # Should NOT have full messages
        assert "messages" not in conversations[0]

    def test_list_conversations_empty(self, temp_data_dir, test_user_id):
        """Test listing when no conversations exist."""
        conversations = storage.list_conversations(test_user_id)

        assert conversations == []

    def test_delete_conversation(self, temp_data_dir, test_user_id):
        """Test deleting an existing conversation."""
        # Create a conversation
        storage.create_conversation(test_user_id, TEST_CONV_ID_1)
        assert storage.get_conversation(test_user_id, TEST_CONV_ID_1) is not None

        # Delete it
        result = storage.delete_conversation(test_user_id, TEST_CONV_ID_1)

        assert result is True
        assert storage.get_conversation(test_user_id, TEST_CONV_ID_1) is None

    def test_delete_nonexistent_conversation(self, temp_data_dir, test_user_id):
        """Test deleting a conversation that doesn't exist."""
        result = storage.delete_conversation(test_user_id, NONEXISTENT_CONV_ID)

        assert result is False

    def test_invalid_conversation_id_rejected(self, temp_data_dir, test_user_id):
        """Test that invalid conversation IDs are rejected (path traversal prevention)."""
        with pytest.raises(ValueError, match="Invalid conversation_id format"):
            storage.get_conversation(test_user_id, TEST_INVALID_ID)

        with pytest.raises(ValueError, match="Invalid conversation_id format"):
            storage.get_conversation(test_user_id, "../../../etc/passwd")


class TestMessageOperations:
    """Test message-related operations."""

    def test_add_user_message(self, temp_data_dir, test_user_id):
        """Test adding a user message."""
        storage.create_conversation(test_user_id, TEST_CONV_ID_1)
        storage.add_user_message(test_user_id, TEST_CONV_ID_1, "Hello, world!")

        conv = storage.get_conversation(test_user_id, TEST_CONV_ID_1)

        assert len(conv["messages"]) == 1
        assert conv["messages"][0]["role"] == "user"
        assert conv["messages"][0]["content"] == "Hello, world!"

    def test_add_user_message_to_nonexistent_conversation(self, temp_data_dir, test_user_id):
        """Test adding message to non-existent conversation."""
        with pytest.raises(ValueError, match="Conversation .* not found"):
            storage.add_user_message(test_user_id, NONEXISTENT_CONV_ID, "Test")

    def test_add_assistant_message(self, temp_data_dir, test_user_id):
        """Test adding an assistant message with all stages."""
        storage.create_conversation(test_user_id, TEST_CONV_ID_1)

        stage1 = [{"agent_id": "1", "agent_title": "Agent", "model": "test", "response": "Response"}]
        stage2 = [{"agent_id": "1", "agent_title": "Agent", "model": "test", "ranking": "FINAL RANKING:\n1. Response A", "parsed_ranking": ["Response A"]}]
        stage3 = {"agent_title": "Chairman", "model": "test", "response": "Final"}

        storage.add_assistant_message(test_user_id, TEST_CONV_ID_1, stage1, stage2, stage3)

        conv = storage.get_conversation(test_user_id, TEST_CONV_ID_1)

        assert len(conv["messages"]) == 1
        assert conv["messages"][0]["role"] == "assistant"
        assert conv["messages"][0]["stage1"] == stage1
        assert conv["messages"][0]["stage2"] == stage2
        assert conv["messages"][0]["stage3"] == stage3

    def test_add_assistant_message_to_nonexistent_conversation(self, temp_data_dir, test_user_id):
        """Test adding assistant message to non-existent conversation."""
        with pytest.raises(ValueError, match="Conversation .* not found"):
            storage.add_assistant_message(test_user_id, NONEXISTENT_CONV_ID, [], [], {})

    def test_message_ordering(self, temp_data_dir, test_user_id):
        """Test that messages maintain insertion order."""
        storage.create_conversation(test_user_id, TEST_CONV_ID_1)

        storage.add_user_message(test_user_id, TEST_CONV_ID_1, "Message 1")
        storage.add_assistant_message(test_user_id, TEST_CONV_ID_1, [], [], {})
        storage.add_user_message(test_user_id, TEST_CONV_ID_1, "Message 2")

        conv = storage.get_conversation(test_user_id, TEST_CONV_ID_1)

        assert len(conv["messages"]) == 3
        assert conv["messages"][0]["role"] == "user"
        assert conv["messages"][0]["content"] == "Message 1"
        assert conv["messages"][1]["role"] == "assistant"
        assert conv["messages"][2]["role"] == "user"
        assert conv["messages"][2]["content"] == "Message 2"


class TestTitleOperations:
    """Test conversation title operations."""

    def test_update_conversation_title(self, temp_data_dir, test_user_id):
        """Test updating conversation title."""
        storage.create_conversation(test_user_id, TEST_CONV_ID_1)
        storage.update_conversation_title(test_user_id, TEST_CONV_ID_1, "Custom Title")

        conv = storage.get_conversation(test_user_id, TEST_CONV_ID_1)

        assert conv["title"] == "Custom Title"

    def test_update_title_of_nonexistent_conversation(self, temp_data_dir, test_user_id):
        """Test updating title of non-existent conversation."""
        with pytest.raises(ValueError, match="Conversation .* not found"):
            storage.update_conversation_title(test_user_id, NONEXISTENT_CONV_ID, "Title")

    def test_default_title(self, temp_data_dir, test_user_id):
        """Test that conversations have default title."""
        conv = storage.create_conversation(test_user_id, TEST_CONV_ID_1)

        assert conv["title"] == "New Conversation"

    def test_list_includes_custom_title(self, temp_data_dir, test_user_id):
        """Test that list_conversations includes custom titles."""
        storage.create_conversation(test_user_id, TEST_CONV_ID_1)
        storage.update_conversation_title(test_user_id, TEST_CONV_ID_1, "Custom Title")

        conversations = storage.list_conversations(test_user_id)

        assert conversations[0]["title"] == "Custom Title"


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_message_count_accuracy(self, temp_data_dir, test_user_id):
        """Test that message_count in list is accurate."""
        storage.create_conversation(test_user_id, TEST_CONV_ID_1)
        storage.add_user_message(test_user_id, TEST_CONV_ID_1, "Message 1")
        storage.add_user_message(test_user_id, TEST_CONV_ID_1, "Message 2")
        storage.add_assistant_message(test_user_id, TEST_CONV_ID_1, [], [], {})

        conversations = storage.list_conversations(test_user_id)

        assert conversations[0]["message_count"] == 3

    def test_unicode_in_messages(self, temp_data_dir, test_user_id):
        """Test handling of Unicode characters in messages."""
        storage.create_conversation(test_user_id, TEST_CONV_ID_1)
        storage.add_user_message(test_user_id, TEST_CONV_ID_1, "Hello 世界 🌍 emoji")

        conv = storage.get_conversation(test_user_id, TEST_CONV_ID_1)

        assert conv["messages"][0]["content"] == "Hello 世界 🌍 emoji"

    def test_large_message_content(self, temp_data_dir, test_user_id):
        """Test handling of large message content."""
        storage.create_conversation(test_user_id, TEST_CONV_ID_1)
        large_content = "A" * 100000  # 100KB of text

        storage.add_user_message(test_user_id, TEST_CONV_ID_1, large_content)

        conv = storage.get_conversation(test_user_id, TEST_CONV_ID_1)

        assert len(conv["messages"][0]["content"]) == 100000

    def test_user_isolation(self, temp_data_dir):
        """Test that different users have isolated data."""
        user1 = "user_1"
        user2 = "user_2"

        storage.create_conversation(user1, TEST_CONV_ID_1)
        storage.create_conversation(user2, TEST_CONV_ID_1)

        # Each user should only see their own conversation
        user1_convs = storage.list_conversations(user1)
        user2_convs = storage.list_conversations(user2)

        assert len(user1_convs) == 1
        assert len(user2_convs) == 1

        # User 1 shouldn't see user 2's data
        assert storage.get_conversation(user1, TEST_CONV_ID_1) is not None
        assert storage.get_conversation(user2, TEST_CONV_ID_1) is not None
