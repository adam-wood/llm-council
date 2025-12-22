"""Tests for agent_storage.py - agent configuration management."""

import pytest
import json
from pathlib import Path
from freezegun import freeze_time
from backend import agent_storage
from backend.config import get_user_agents_file
from tests.conftest import TEST_USER_ID, TEST_INVALID_ID

# A valid UUID that won't exist in test data
NONEXISTENT_AGENT_ID = "99999999-9999-9999-9999-999999999999"


class TestAgentCRUD:
    """Test CRUD operations for agents."""

    def test_create_agent(self, temp_data_dir, test_user_id):
        """Test creating a new agent."""
        with freeze_time("2024-01-01 12:00:00"):
            agent = agent_storage.create_agent(
                test_user_id,
                title="Test Agent",
                role="Test role",
                model="test/model",
                prompts={"stage1": "Test prompt"},
                active=True
            )

            assert agent["title"] == "Test Agent"
            assert agent["role"] == "Test role"
            assert agent["model"] == "test/model"
            assert agent["prompts"]["stage1"] == "Test prompt"
            assert agent["active"] is True
            assert "id" in agent
            assert agent["created_at"] == "2024-01-01T12:00:00"
            assert agent["updated_at"] == "2024-01-01T12:00:00"

    def test_create_agent_default_prompts(self, temp_data_dir, test_user_id):
        """Test creating agent with default (empty) prompts."""
        agent = agent_storage.create_agent(
            test_user_id,
            title="Test Agent",
            role="Test role",
            model="test/model"
        )

        assert agent["prompts"] == {}

    def test_get_all_agents(self, temp_data_dir, test_user_id):
        """Test retrieving all agents."""
        # Clear any defaults first
        data = {"agents": [], "chairman": None}
        agent_storage.save_agents(test_user_id, data)

        # Create multiple agents
        agent_storage.create_agent(test_user_id, "Agent 1", "Role 1", "model-1")
        agent_storage.create_agent(test_user_id, "Agent 2", "Role 2", "model-2")

        agents = agent_storage.get_all_agents(test_user_id)

        assert len(agents) == 2
        assert agents[0]["title"] == "Agent 1"
        assert agents[1]["title"] == "Agent 2"

    def test_get_active_agents(self, temp_data_dir, test_user_id):
        """Test retrieving only active agents."""
        # Clear any defaults first
        data = {"agents": [], "chairman": None}
        agent_storage.save_agents(test_user_id, data)

        agent_storage.create_agent(test_user_id, "Active 1", "Role 1", "model-1", active=True)
        agent_storage.create_agent(test_user_id, "Inactive", "Role 2", "model-2", active=False)
        agent_storage.create_agent(test_user_id, "Active 2", "Role 3", "model-3", active=True)

        active_agents = agent_storage.get_active_agents(test_user_id)

        assert len(active_agents) == 2
        assert all(agent["active"] for agent in active_agents)

    def test_get_agent_by_id(self, temp_data_dir, test_user_id):
        """Test retrieving specific agent by ID."""
        # Clear any defaults first
        data = {"agents": [], "chairman": None}
        agent_storage.save_agents(test_user_id, data)

        created = agent_storage.create_agent(test_user_id, "Test Agent", "Role", "model")
        agent_id = created["id"]

        retrieved = agent_storage.get_agent_by_id(test_user_id, agent_id)

        assert retrieved is not None
        assert retrieved["id"] == agent_id
        assert retrieved["title"] == "Test Agent"

    def test_get_agent_by_id_not_found(self, temp_data_dir, test_user_id):
        """Test retrieving non-existent agent."""
        result = agent_storage.get_agent_by_id(test_user_id, NONEXISTENT_AGENT_ID)

        assert result is None

    def test_get_agent_by_invalid_id_rejected(self, temp_data_dir, test_user_id):
        """Test that invalid agent IDs are rejected (path traversal prevention)."""
        with pytest.raises(ValueError, match="Invalid agent_id format"):
            agent_storage.get_agent_by_id(test_user_id, TEST_INVALID_ID)

    def test_update_agent(self, temp_data_dir, test_user_id):
        """Test updating an agent."""
        # Clear any defaults first
        data = {"agents": [], "chairman": None}
        agent_storage.save_agents(test_user_id, data)

        created = agent_storage.create_agent(test_user_id, "Original Title", "Role", "model")
        agent_id = created["id"]

        with freeze_time("2024-01-02 12:00:00"):
            updated = agent_storage.update_agent(test_user_id, agent_id, {
                "title": "Updated Title",
                "role": "Updated Role"
            })

            assert updated["title"] == "Updated Title"
            assert updated["role"] == "Updated Role"
            assert updated["model"] == "model"  # Unchanged
            assert updated["updated_at"] == "2024-01-02T12:00:00"

    def test_update_agent_preserves_id_and_created_at(self, temp_data_dir, test_user_id):
        """Test that update doesn't change id or created_at."""
        # Clear any defaults first
        data = {"agents": [], "chairman": None}
        agent_storage.save_agents(test_user_id, data)

        with freeze_time("2024-01-01 12:00:00"):
            created = agent_storage.create_agent(test_user_id, "Test", "Role", "model")
            original_id = created["id"]
            original_created = created["created_at"]

        with freeze_time("2024-01-02 12:00:00"):
            updated = agent_storage.update_agent(test_user_id, original_id, {
                "id": "new-id",  # Should be ignored
                "created_at": "2025-01-01T00:00:00",  # Should be ignored
                "title": "New Title"
            })

            assert updated["id"] == original_id
            assert updated["created_at"] == original_created

    def test_update_agent_not_found(self, temp_data_dir, test_user_id):
        """Test updating non-existent agent."""
        result = agent_storage.update_agent(test_user_id, NONEXISTENT_AGENT_ID, {"title": "New Title"})

        assert result is None

    def test_delete_agent(self, temp_data_dir, test_user_id):
        """Test deleting an agent."""
        # Clear any defaults first
        data = {"agents": [], "chairman": None}
        agent_storage.save_agents(test_user_id, data)

        created = agent_storage.create_agent(test_user_id, "Test Agent", "Role", "model")
        agent_id = created["id"]

        success = agent_storage.delete_agent(test_user_id, agent_id)

        assert success is True
        assert agent_storage.get_agent_by_id(test_user_id, agent_id) is None

    def test_delete_agent_not_found(self, temp_data_dir, test_user_id):
        """Test deleting non-existent agent."""
        success = agent_storage.delete_agent(test_user_id, NONEXISTENT_AGENT_ID)

        assert success is False


class TestChairmanManagement:
    """Test chairman designation."""

    def test_set_chairman(self, temp_data_dir, test_user_id):
        """Test setting chairman."""
        # Clear any defaults first
        data = {"agents": [], "chairman": None}
        agent_storage.save_agents(test_user_id, data)

        agent = agent_storage.create_agent(test_user_id, "Chairman", "Role", "model")
        agent_id = agent["id"]

        success = agent_storage.set_chairman(test_user_id, agent_id)

        assert success is True

        chairman = agent_storage.get_chairman(test_user_id)
        assert chairman is not None
        assert chairman["id"] == agent_id

    def test_set_chairman_to_none(self, temp_data_dir, test_user_id):
        """Test clearing chairman (set to None)."""
        # Clear any defaults first
        data = {"agents": [], "chairman": None}
        agent_storage.save_agents(test_user_id, data)

        agent = agent_storage.create_agent(test_user_id, "Chairman", "Role", "model")
        agent_storage.set_chairman(test_user_id, agent["id"])

        # Clear chairman
        success = agent_storage.set_chairman(test_user_id, None)

        assert success is True
        assert agent_storage.get_chairman(test_user_id) is None

    def test_set_nonexistent_chairman(self, temp_data_dir, test_user_id):
        """Test setting non-existent agent as chairman."""
        success = agent_storage.set_chairman(test_user_id, NONEXISTENT_AGENT_ID)

        assert success is False

    def test_get_chairman_when_none(self, temp_data_dir, test_user_id):
        """Test getting chairman when none is set."""
        # Clear any defaults first
        data = {"agents": [], "chairman": None}
        agent_storage.save_agents(test_user_id, data)

        chairman = agent_storage.get_chairman(test_user_id)

        assert chairman is None


class TestDefaultAgents:
    """Test default agent initialization."""

    def test_initialize_default_agents(self, temp_data_dir, test_user_id):
        """Test creating default agent templates."""
        agents = agent_storage.initialize_default_agents(test_user_id)

        assert len(agents) == 4
        titles = [agent["title"] for agent in agents]
        assert "Ethics & Values Advisor" in titles
        assert "Technology & Innovation Expert" in titles
        assert "Leadership & Strategy Coach" in titles
        assert "Financial & Business Advisor" in titles

    def test_initialize_default_agents_idempotent(self, temp_data_dir, test_user_id):
        """Test that initializing defaults multiple times doesn't duplicate."""
        agents1 = agent_storage.initialize_default_agents(test_user_id)
        agents2 = agent_storage.initialize_default_agents(test_user_id)

        # Should return same number of agents (no duplication)
        assert len(agents2) == len(agents1)
        # Titles should match
        assert sorted([a["title"] for a in agents1]) == sorted([a["title"] for a in agents2])

    def test_default_agents_have_prompts(self, temp_data_dir, test_user_id):
        """Test that default agents have stage1 prompts."""
        agents = agent_storage.initialize_default_agents(test_user_id)

        for agent in agents:
            assert "stage1" in agent["prompts"]
            assert len(agent["prompts"]["stage1"]) > 0


class TestDataPersistence:
    """Test data persistence to JSON files."""

    def test_agents_persisted_to_file(self, temp_data_dir, test_user_id):
        """Test that agents are saved to JSON file."""
        # Clear any defaults first
        data = {"agents": [], "chairman": None}
        agent_storage.save_agents(test_user_id, data)

        agent = agent_storage.create_agent(test_user_id, "Test", "Role", "model")

        agents_file = Path(get_user_agents_file(test_user_id))
        assert agents_file.exists()

        with open(agents_file, 'r') as f:
            data = json.load(f)

        assert "agents" in data
        assert len(data["agents"]) == 1
        assert data["agents"][0]["title"] == "Test"

    def test_chairman_persisted(self, temp_data_dir, test_user_id):
        """Test that chairman designation is persisted."""
        # Clear any defaults first
        data = {"agents": [], "chairman": None}
        agent_storage.save_agents(test_user_id, data)

        agent = agent_storage.create_agent(test_user_id, "Chairman", "Role", "model")
        agent_storage.set_chairman(test_user_id, agent["id"])

        agents_file = Path(get_user_agents_file(test_user_id))
        with open(agents_file, 'r') as f:
            data = json.load(f)

        assert data["chairman"] == agent["id"]

    def test_load_from_corrupted_json(self, temp_data_dir, test_user_id):
        """Test handling of corrupted JSON file."""
        # Create corrupted JSON file
        agents_file = Path(get_user_agents_file(test_user_id))
        agents_file.parent.mkdir(parents=True, exist_ok=True)
        with open(agents_file, 'w') as f:
            f.write("{ invalid json }")

        # Should return default structure instead of crashing
        data = agent_storage.load_agents(test_user_id)
        # Returns default agents when file is corrupted
        assert "agents" in data
        assert "chairman" in data

    def test_load_when_file_doesnt_exist(self, temp_data_dir, test_user_id):
        """Test loading when file doesn't exist - creates defaults."""
        data = agent_storage.load_agents(test_user_id)

        # Returns default agents structure
        assert "agents" in data
        assert "chairman" in data
        # Default agents are created
        assert len(data["agents"]) == 4


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_create_agent_with_empty_strings(self, temp_data_dir, test_user_id):
        """Test creating agent with empty strings."""
        # Clear any defaults first
        data = {"agents": [], "chairman": None}
        agent_storage.save_agents(test_user_id, data)

        agent = agent_storage.create_agent(test_user_id, "", "", "")

        assert agent["title"] == ""
        assert agent["role"] == ""
        assert agent["model"] == ""

    def test_update_with_empty_dict(self, temp_data_dir, test_user_id):
        """Test updating with empty updates dict."""
        # Clear any defaults first
        data = {"agents": [], "chairman": None}
        agent_storage.save_agents(test_user_id, data)

        created = agent_storage.create_agent(test_user_id, "Test", "Role", "model")
        original_updated_at = created["updated_at"]

        with freeze_time("2024-01-02 12:00:00"):
            updated = agent_storage.update_agent(test_user_id, created["id"], {})

            # Should still update the updated_at timestamp
            assert updated["updated_at"] != original_updated_at

    def test_multiple_agents_same_model(self, temp_data_dir, test_user_id):
        """Test multiple agents can use the same model."""
        # Clear any defaults first
        data = {"agents": [], "chairman": None}
        agent_storage.save_agents(test_user_id, data)

        agent1 = agent_storage.create_agent(test_user_id, "Agent 1", "Role 1", "same/model")
        agent2 = agent_storage.create_agent(test_user_id, "Agent 2", "Role 2", "same/model")

        assert agent1["model"] == agent2["model"]
        assert agent1["id"] != agent2["id"]

    def test_active_filter_with_missing_active_field(self, temp_data_dir, test_user_id):
        """Test that agents without 'active' field are treated as active."""
        # Manually create agent without 'active' field
        data = {"agents": [{"id": "1", "title": "Test", "role": "Role", "model": "model"}], "chairman": None}
        agent_storage.save_agents(test_user_id, data)

        active_agents = agent_storage.get_active_agents(test_user_id)

        # Should default to True
        assert len(active_agents) == 1
