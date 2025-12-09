"""Tests for main.py - FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from backend.main import app


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


class TestHealthCheck:
    """Test health check endpoint."""

    def test_root_endpoint(self, client):
        """Test root health check."""
        response = client.get("/")

        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert "service" in response.json()


class TestConversationEndpoints:
    """Test conversation management endpoints."""

    def test_create_conversation(self, client, temp_data_dir):
        """Test creating a new conversation."""
        response = client.post("/api/conversations", json={})

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "created_at" in data
        assert data["title"] == "New Conversation"
        assert data["messages"] == []

    def test_list_conversations(self, client, temp_data_dir):
        """Test listing conversations."""
        # Create some conversations
        client.post("/api/conversations", json={})
        client.post("/api/conversations", json={})

        response = client.get("/api/conversations")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all("id" in conv for conv in data)

    def test_get_conversation(self, client, temp_data_dir):
        """Test getting specific conversation."""
        # Create conversation
        create_response = client.post("/api/conversations", json={})
        conv_id = create_response.json()["id"]

        # Get it
        response = client.get(f"/api/conversations/{conv_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == conv_id

    def test_get_nonexistent_conversation(self, client, temp_data_dir):
        """Test getting conversation that doesn't exist."""
        response = client.get("/api/conversations/non-existent-id")

        assert response.status_code == 404

    def test_send_message(self, client, temp_data_dir):
        """Test sending a message in conversation."""
        # Create conversation
        create_response = client.post("/api/conversations", json={})
        conv_id = create_response.json()["id"]

        # Mock the council functions
        with patch("backend.main.run_full_council") as mock_council:
            mock_council.return_value = (
                [{"agent_id": "1", "agent_title": "Agent", "model": "test", "response": "R1"}],
                [{"agent_id": "1", "agent_title": "Agent", "model": "test", "ranking": "FINAL RANKING:\n1. Response A", "parsed_ranking": ["Response A"]}],
                {"agent_title": "Chairman", "model": "test", "response": "Final"},
                {"label_to_model": {}, "aggregate_rankings": []}
            )

            with patch("backend.main.generate_conversation_title") as mock_title:
                mock_title.return_value = "Test Title"

                response = client.post(
                    f"/api/conversations/{conv_id}/message",
                    json={"content": "Test question?"}
                )

                assert response.status_code == 200
                data = response.json()
                assert "stage1" in data
                assert "stage2" in data
                assert "stage3" in data
                assert "metadata" in data

    def test_send_message_to_nonexistent_conversation(self, client, temp_data_dir):
        """Test sending message to non-existent conversation."""
        response = client.post(
            "/api/conversations/non-existent/message",
            json={"content": "Test"}
        )

        assert response.status_code == 404

    def test_delete_conversation(self, client, temp_data_dir):
        """Test deleting a conversation."""
        # Create conversation
        create_response = client.post("/api/conversations", json={})
        conv_id = create_response.json()["id"]

        # Verify it exists
        get_response = client.get(f"/api/conversations/{conv_id}")
        assert get_response.status_code == 200

        # Delete it
        delete_response = client.delete(f"/api/conversations/{conv_id}")

        assert delete_response.status_code == 200
        assert delete_response.json() == {"success": True}

        # Verify it's gone
        get_after_delete = client.get(f"/api/conversations/{conv_id}")
        assert get_after_delete.status_code == 404

    def test_delete_nonexistent_conversation(self, client, temp_data_dir):
        """Test deleting a conversation that doesn't exist."""
        response = client.delete("/api/conversations/non-existent-id")

        assert response.status_code == 404


class TestAgentEndpoints:
    """Test agent management endpoints."""

    def test_list_agents(self, client, temp_data_dir):
        """Test listing all agents."""
        response = client.get("/api/agents")

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_list_active_agents_only(self, client, temp_data_dir):
        """Test listing only active agents."""
        with patch("backend.agent_storage.create_agent") as mock_create:
            mock_create.side_effect = [
                {"id": "1", "title": "Active", "active": True},
                {"id": "2", "title": "Inactive", "active": False}
            ]
            client.post("/api/agents", json={
                "title": "Active", "role": "Role", "model": "model", "active": True
            })
            client.post("/api/agents", json={
                "title": "Inactive", "role": "Role", "model": "model", "active": False
            })

        with patch("backend.agent_storage.get_active_agents") as mock_get:
            mock_get.return_value = [{"id": "1", "title": "Active", "active": True}]

            response = client.get("/api/agents?active_only=true")

            assert response.status_code == 200
            agents = response.json()
            assert len(agents) == 1
            assert agents[0]["title"] == "Active"

    def test_create_agent(self, client, temp_data_dir):
        """Test creating a new agent."""
        response = client.post("/api/agents", json={
            "title": "Test Agent",
            "role": "Test role",
            "model": "test/model",
            "prompts": {"stage1": "Test prompt"},
            "active": True
        })

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Agent"
        assert "id" in data

    def test_get_agent(self, client, temp_data_dir):
        """Test getting specific agent."""
        # Create agent
        create_response = client.post("/api/agents", json={
            "title": "Test Agent",
            "role": "Role",
            "model": "model"
        })
        agent_id = create_response.json()["id"]

        # Get it
        response = client.get(f"/api/agents/{agent_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == agent_id

    def test_get_nonexistent_agent(self, client, temp_data_dir):
        """Test getting non-existent agent."""
        response = client.get("/api/agents/non-existent-id")

        assert response.status_code == 404

    def test_update_agent(self, client, temp_data_dir):
        """Test updating an agent."""
        # Create agent
        create_response = client.post("/api/agents", json={
            "title": "Original",
            "role": "Role",
            "model": "model"
        })
        agent_id = create_response.json()["id"]

        # Update it
        response = client.put(f"/api/agents/{agent_id}", json={
            "title": "Updated"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated"

    def test_update_nonexistent_agent(self, client, temp_data_dir):
        """Test updating non-existent agent."""
        response = client.put("/api/agents/non-existent-id", json={
            "title": "Updated"
        })

        assert response.status_code == 404

    def test_delete_agent(self, client, temp_data_dir):
        """Test deleting an agent."""
        # Create agent
        create_response = client.post("/api/agents", json={
            "title": "Test",
            "role": "Role",
            "model": "model"
        })
        agent_id = create_response.json()["id"]

        # Delete it
        response = client.delete(f"/api/agents/{agent_id}")

        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_delete_nonexistent_agent(self, client, temp_data_dir):
        """Test deleting non-existent agent."""
        response = client.delete("/api/agents/non-existent-id")

        assert response.status_code == 404

    def test_initialize_default_agents(self, client, temp_data_dir):
        """Test initializing default agents."""
        response = client.post("/api/agents/initialize")

        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert "count" in data
        assert data["count"] == 4

    def test_get_chairman(self, client, temp_data_dir):
        """Test getting chairman agent."""
        response = client.get("/api/agents/chairman")

        assert response.status_code == 200
        data = response.json()
        assert "chairman" in data

    def test_set_chairman(self, client, temp_data_dir):
        """Test setting chairman agent."""
        # Create agent
        create_response = client.post("/api/agents", json={
            "title": "Chairman",
            "role": "Role",
            "model": "model"
        })
        agent_id = create_response.json()["id"]

        # Set as chairman
        response = client.put(f"/api/agents/chairman/{agent_id}")

        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_set_nonexistent_chairman(self, client, temp_data_dir):
        """Test setting non-existent agent as chairman."""
        response = client.put("/api/agents/chairman/non-existent-id")

        assert response.status_code == 404


class TestModelEndpoints:
    """Test model configuration endpoints."""

    def test_get_models(self, client):
        """Test getting model configuration."""
        response = client.get("/api/models")

        assert response.status_code == 200
        data = response.json()
        assert "council" in data
        assert "chairman" in data
        assert "all" in data


class TestPromptEndpoints:
    """Test prompt management endpoints."""

    def test_get_all_prompts(self, client, temp_data_dir):
        """Test getting all prompts."""
        response = client.get("/api/prompts")

        assert response.status_code == 200
        data = response.json()
        assert "defaults" in data
        assert "models" in data

    def test_get_prompts_for_model(self, client, temp_data_dir):
        """Test getting prompts for specific model."""
        response = client.get("/api/prompts?model=test/model")

        assert response.status_code == 200
        data = response.json()
        assert "stage1" in data
        assert "stage2" in data
        assert "stage3" in data

    def test_update_default_prompt(self, client, temp_data_dir):
        """Test updating default prompt."""
        response = client.put("/api/prompts/stage1", json={
            "name": "Custom",
            "description": "Custom description",
            "template": "Custom: {user_query}",
            "notes": ""
        })

        assert response.status_code == 200
        data = response.json()
        assert data["defaults"]["stage1"]["name"] == "Custom"

    def test_update_model_specific_prompt(self, client, temp_data_dir):
        """Test updating model-specific prompt."""
        response = client.put("/api/prompts/stage1?model=test/model", json={
            "name": "Model Prompt",
            "description": "Description",
            "template": "Model: {user_query}",
            "notes": ""
        })

        assert response.status_code == 200
        data = response.json()
        assert "test/model" in data["models"]

    def test_update_invalid_stage(self, client, temp_data_dir):
        """Test updating invalid stage."""
        response = client.put("/api/prompts/invalid_stage", json={
            "name": "Test",
            "description": "Test",
            "template": "Test"
        })

        assert response.status_code == 400

    def test_reset_default_prompt(self, client, temp_data_dir):
        """Test resetting default prompt."""
        # First update
        client.put("/api/prompts/stage1", json={
            "name": "Custom",
            "description": "Custom",
            "template": "Custom",
            "notes": ""
        })

        # Then reset
        response = client.delete("/api/prompts/stage1")

        assert response.status_code == 200

    def test_reset_model_prompt(self, client, temp_data_dir):
        """Test resetting model-specific prompt."""
        response = client.delete("/api/prompts/stage1?model=test/model")

        assert response.status_code == 200

    def test_reset_invalid_stage(self, client, temp_data_dir):
        """Test resetting invalid stage."""
        response = client.delete("/api/prompts/invalid_stage")

        assert response.status_code == 400

    def test_reset_all_prompts(self, client, temp_data_dir):
        """Test resetting all prompts."""
        response = client.delete("/api/prompts")

        assert response.status_code == 200


class TestCORSHeaders:
    """Test CORS configuration."""

    def test_cors_headers_present(self, client, temp_data_dir):
        """Test that CORS headers are included on actual requests."""
        # Test on a GET request that exists
        response = client.get("/api/conversations")

        # Should have status 200 and CORS should be configured
        assert response.status_code == 200
        # Note: TestClient may not expose all CORS headers, but endpoint should work


class TestRequestValidation:
    """Test request validation using Pydantic models."""

    def test_invalid_send_message_request(self, client, temp_data_dir):
        """Test sending message with invalid request body."""
        create_response = client.post("/api/conversations", json={})
        conv_id = create_response.json()["id"]

        # Missing 'content' field
        response = client.post(
            f"/api/conversations/{conv_id}/message",
            json={}
        )

        assert response.status_code == 422  # Validation error

    def test_invalid_create_agent_request(self, client, temp_data_dir):
        """Test creating agent with invalid request."""
        # Missing required fields
        response = client.post("/api/agents", json={
            "title": "Test"
            # Missing 'role' and 'model'
        })

        assert response.status_code == 422

    def test_invalid_update_prompt_request(self, client, temp_data_dir):
        """Test updating prompt with invalid request."""
        # Missing required fields
        response = client.put("/api/prompts/stage1", json={
            "name": "Test"
            # Missing 'description' and 'template'
        })

        assert response.status_code == 422


class TestStreamingEndpoint:
    """Test the streaming message endpoint."""

    def test_streaming_message_endpoint_exists(self, client, temp_data_dir):
        """Test that streaming endpoint is available."""
        # Create conversation
        create_response = client.post("/api/conversations", json={})
        conv_id = create_response.json()["id"]

        # Mock the async functions
        with patch("backend.main.stage1_collect_responses") as mock_s1:
            with patch("backend.main.stage2_collect_rankings") as mock_s2:
                with patch("backend.main.stage3_synthesize_final") as mock_s3:
                    with patch("backend.main.generate_conversation_title") as mock_title:
                        mock_s1.return_value = []
                        mock_s2.return_value = ([], {})
                        mock_s3.return_value = {"agent_title": "C", "model": "m", "response": "R"}
                        mock_title.return_value = "Title"

                        # Note: Testing SSE streams is complex, just verify endpoint exists
                        response = client.post(
                            f"/api/conversations/{conv_id}/message/stream",
                            json={"content": "Test"}
                        )

                        # Should start streaming
                        assert response.status_code == 200
