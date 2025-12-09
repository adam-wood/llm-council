"""Tests for storage.py - conversation management."""

import pytest
import json
import os
from pathlib import Path
from freezegun import freeze_time
from backend import storage


class TestConversationCRUD:
    """Test conversation CRUD operations."""

    def test_create_conversation(self, temp_data_dir):
        """Test creating a new conversation."""
        with freeze_time("2024-01-01 12:00:00"):
            conv = storage.create_conversation("test-conv-1")

            assert conv["id"] == "test-conv-1"
            assert conv["created_at"] == "2024-01-01T12:00:00"
            assert conv["title"] == "New Conversation"
            assert conv["messages"] == []

    def test_get_conversation(self, temp_data_dir):
        """Test retrieving a conversation."""
        storage.create_conversation("test-conv-1")

        conv = storage.get_conversation("test-conv-1")

        assert conv is not None
        assert conv["id"] == "test-conv-1"

    def test_get_nonexistent_conversation(self, temp_data_dir):
        """Test retrieving non-existent conversation."""
        conv = storage.get_conversation("non-existent")

        assert conv is None

    def test_save_conversation(self, temp_data_dir):
        """Test saving conversation updates."""
        conv = storage.create_conversation("test-conv-1")
        conv["title"] = "Updated Title"
        conv["messages"].append({"role": "user", "content": "Test"})

        storage.save_conversation(conv)

        # Reload and verify
        loaded = storage.get_conversation("test-conv-1")
        assert loaded["title"] == "Updated Title"
        assert len(loaded["messages"]) == 1

    def test_list_conversations(self, temp_data_dir):
        """Test listing all conversations."""
        with freeze_time("2024-01-01 10:00:00"):
            storage.create_conversation("conv-1")

        with freeze_time("2024-01-01 12:00:00"):
            storage.create_conversation("conv-2")

        with freeze_time("2024-01-01 11:00:00"):
            storage.create_conversation("conv-3")

        conversations = storage.list_conversations()

        # Should return metadata only
        assert len(conversations) == 3

        # Should be sorted by creation time, newest first
        assert conversations[0]["id"] == "conv-2"  # 12:00
        assert conversations[1]["id"] == "conv-3"  # 11:00
        assert conversations[2]["id"] == "conv-1"  # 10:00

    def test_list_conversations_metadata_only(self, temp_data_dir):
        """Test that list_conversations returns metadata only."""
        conv = storage.create_conversation("test-conv-1")
        storage.add_user_message("test-conv-1", "Test message")

        conversations = storage.list_conversations()

        # Should have metadata fields
        assert "id" in conversations[0]
        assert "created_at" in conversations[0]
        assert "title" in conversations[0]
        assert "message_count" in conversations[0]

        # Should NOT have full messages
        assert "messages" not in conversations[0]

    def test_list_conversations_empty(self, temp_data_dir):
        """Test listing when no conversations exist."""
        conversations = storage.list_conversations()

        assert conversations == []

    def test_delete_conversation(self, temp_data_dir):
        """Test deleting an existing conversation."""
        # Create a conversation
        storage.create_conversation("test-conv-1")
        assert storage.get_conversation("test-conv-1") is not None

        # Delete it
        result = storage.delete_conversation("test-conv-1")

        assert result is True
        assert storage.get_conversation("test-conv-1") is None

        # Verify file is removed
        path = storage.get_conversation_path("test-conv-1")
        assert not os.path.exists(path)

    def test_delete_nonexistent_conversation(self, temp_data_dir):
        """Test deleting a conversation that doesn't exist."""
        result = storage.delete_conversation("non-existent")

        assert result is False


class TestMessageOperations:
    """Test message-related operations."""

    def test_add_user_message(self, temp_data_dir):
        """Test adding a user message."""
        storage.create_conversation("test-conv-1")
        storage.add_user_message("test-conv-1", "Hello, world!")

        conv = storage.get_conversation("test-conv-1")

        assert len(conv["messages"]) == 1
        assert conv["messages"][0]["role"] == "user"
        assert conv["messages"][0]["content"] == "Hello, world!"

    def test_add_user_message_to_nonexistent_conversation(self, temp_data_dir):
        """Test adding message to non-existent conversation."""
        with pytest.raises(ValueError, match="Conversation .* not found"):
            storage.add_user_message("non-existent", "Test")

    def test_add_assistant_message(self, temp_data_dir):
        """Test adding an assistant message with all stages."""
        storage.create_conversation("test-conv-1")

        stage1 = [{"agent_id": "1", "agent_title": "Agent", "model": "test", "response": "Response"}]
        stage2 = [{"agent_id": "1", "agent_title": "Agent", "model": "test", "ranking": "FINAL RANKING:\n1. Response A", "parsed_ranking": ["Response A"]}]
        stage3 = {"agent_title": "Chairman", "model": "test", "response": "Final"}

        storage.add_assistant_message("test-conv-1", stage1, stage2, stage3)

        conv = storage.get_conversation("test-conv-1")

        assert len(conv["messages"]) == 1
        assert conv["messages"][0]["role"] == "assistant"
        assert conv["messages"][0]["stage1"] == stage1
        assert conv["messages"][0]["stage2"] == stage2
        assert conv["messages"][0]["stage3"] == stage3

    def test_add_assistant_message_to_nonexistent_conversation(self, temp_data_dir):
        """Test adding assistant message to non-existent conversation."""
        with pytest.raises(ValueError, match="Conversation .* not found"):
            storage.add_assistant_message("non-existent", [], [], {})

    def test_message_ordering(self, temp_data_dir):
        """Test that messages maintain insertion order."""
        storage.create_conversation("test-conv-1")

        storage.add_user_message("test-conv-1", "Message 1")
        storage.add_assistant_message("test-conv-1", [], [], {})
        storage.add_user_message("test-conv-1", "Message 2")

        conv = storage.get_conversation("test-conv-1")

        assert len(conv["messages"]) == 3
        assert conv["messages"][0]["role"] == "user"
        assert conv["messages"][0]["content"] == "Message 1"
        assert conv["messages"][1]["role"] == "assistant"
        assert conv["messages"][2]["role"] == "user"
        assert conv["messages"][2]["content"] == "Message 2"


class TestTitleOperations:
    """Test conversation title operations."""

    def test_update_conversation_title(self, temp_data_dir):
        """Test updating conversation title."""
        storage.create_conversation("test-conv-1")
        storage.update_conversation_title("test-conv-1", "Custom Title")

        conv = storage.get_conversation("test-conv-1")

        assert conv["title"] == "Custom Title"

    def test_update_title_of_nonexistent_conversation(self, temp_data_dir):
        """Test updating title of non-existent conversation."""
        with pytest.raises(ValueError, match="Conversation .* not found"):
            storage.update_conversation_title("non-existent", "Title")

    def test_default_title(self, temp_data_dir):
        """Test that conversations have default title."""
        conv = storage.create_conversation("test-conv-1")

        assert conv["title"] == "New Conversation"

    def test_list_includes_custom_title(self, temp_data_dir):
        """Test that list_conversations includes custom titles."""
        storage.create_conversation("test-conv-1")
        storage.update_conversation_title("test-conv-1", "Custom Title")

        conversations = storage.list_conversations()

        assert conversations[0]["title"] == "Custom Title"

    def test_list_fallback_to_default_title(self, temp_data_dir):
        """Test list_conversations fallback when title is missing."""
        # Manually create conversation without title
        conv = {
            "id": "test-conv-1",
            "created_at": "2024-01-01T00:00:00",
            "messages": []
        }
        storage.save_conversation(conv)

        conversations = storage.list_conversations()

        assert conversations[0]["title"] == "New Conversation"


class TestFilePersistence:
    """Test file system persistence."""

    def test_conversation_saved_to_file(self, temp_data_dir):
        """Test that conversation is saved to JSON file."""
        storage.create_conversation("test-conv-1")

        file_path = os.path.join(temp_data_dir, "test-conv-1.json")
        assert os.path.exists(file_path)

        with open(file_path, 'r') as f:
            data = json.load(f)

        assert data["id"] == "test-conv-1"

    def test_data_directory_created_automatically(self, monkeypatch):
        """Test that data directory is created if it doesn't exist."""
        import tempfile
        temp_dir = tempfile.mkdtemp()
        new_data_dir = os.path.join(temp_dir, "nested", "data")

        monkeypatch.setattr("backend.storage.DATA_DIR", new_data_dir)

        storage.create_conversation("test-conv-1")

        assert os.path.exists(new_data_dir)

    def test_get_conversation_path(self):
        """Test conversation file path generation."""
        path = storage.get_conversation_path("test-conv-1")

        assert path.endswith("test-conv-1.json")

    def test_multiple_conversations_separate_files(self, temp_data_dir):
        """Test that each conversation gets its own file."""
        storage.create_conversation("conv-1")
        storage.create_conversation("conv-2")

        assert os.path.exists(os.path.join(temp_data_dir, "conv-1.json"))
        assert os.path.exists(os.path.join(temp_data_dir, "conv-2.json"))


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_conversation_id(self, temp_data_dir):
        """Test creating conversation with empty ID."""
        conv = storage.create_conversation("")

        assert conv["id"] == ""

    def test_conversation_with_special_characters_in_id(self, temp_data_dir):
        """Test conversation ID with special characters."""
        # This might fail on some file systems, but should be handled gracefully
        conv_id = "test-conv-!@#$%"
        try:
            conv = storage.create_conversation(conv_id)
            assert conv is not None
        except (OSError, ValueError):
            # Expected on some systems
            pass

    def test_message_count_accuracy(self, temp_data_dir):
        """Test that message_count in list is accurate."""
        storage.create_conversation("test-conv-1")
        storage.add_user_message("test-conv-1", "Message 1")
        storage.add_user_message("test-conv-1", "Message 2")
        storage.add_assistant_message("test-conv-1", [], [], {})

        conversations = storage.list_conversations()

        assert conversations[0]["message_count"] == 3

    def test_unicode_in_messages(self, temp_data_dir):
        """Test handling of Unicode characters in messages."""
        storage.create_conversation("test-conv-1")
        storage.add_user_message("test-conv-1", "Hello 世界 🌍 emoji")

        conv = storage.get_conversation("test-conv-1")

        assert conv["messages"][0]["content"] == "Hello 世界 🌍 emoji"

    def test_large_message_content(self, temp_data_dir):
        """Test handling of large message content."""
        storage.create_conversation("test-conv-1")
        large_content = "A" * 100000  # 100KB of text

        storage.add_user_message("test-conv-1", large_content)

        conv = storage.get_conversation("test-conv-1")

        assert len(conv["messages"][0]["content"]) == 100000

    def test_overwrite_existing_conversation_file(self, temp_data_dir):
        """Test that saving overwrites existing file."""
        conv = storage.create_conversation("test-conv-1")
        storage.add_user_message("test-conv-1", "First message")

        conv = storage.get_conversation("test-conv-1")
        conv["messages"].append({"role": "user", "content": "Second message"})
        storage.save_conversation(conv)

        # Reload and verify both messages
        loaded = storage.get_conversation("test-conv-1")
        assert len(loaded["messages"]) == 2
