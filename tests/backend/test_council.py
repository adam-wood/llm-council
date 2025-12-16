"""Tests for council.py - core orchestration logic."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from backend.council import (
    parse_ranking_from_text,
    calculate_aggregate_rankings,
    generate_conversation_title,
    stage1_collect_responses,
    stage2_collect_rankings,
    stage3_synthesize_final,
    run_full_council
)
from tests.conftest import TEST_USER_ID


class TestParseRankingFromText:
    """Test the ranking text parser."""

    def test_parse_numbered_format(self, sample_ranking_text_numbered):
        """Test parsing numbered format: '1. Response A'."""
        result = parse_ranking_from_text(sample_ranking_text_numbered)
        assert result == ["Response C", "Response A", "Response B"]

    def test_parse_plain_format(self, sample_ranking_text_plain):
        """Test parsing plain format without numbers."""
        result = parse_ranking_from_text(sample_ranking_text_plain)
        assert result == ["Response B", "Response C", "Response A"]

    def test_parse_missing_final_ranking_header(self):
        """Test fallback when 'FINAL RANKING:' header is missing."""
        text = "Response A is best, then Response B, then Response C"
        result = parse_ranking_from_text(text)
        assert result == ["Response A", "Response B", "Response C"]

    def test_parse_with_multiple_sections(self):
        """Test that only rankings after 'FINAL RANKING:' are extracted."""
        text = """Response A mentioned here in discussion.
        Response B is also good.

        FINAL RANKING:
        1. Response C
        2. Response B
        3. Response A"""
        result = parse_ranking_from_text(text)
        assert result == ["Response C", "Response B", "Response A"]

    def test_parse_empty_string(self):
        """Test parsing empty string."""
        result = parse_ranking_from_text("")
        assert result == []

    def test_parse_no_responses(self):
        """Test when no 'Response X' patterns found."""
        text = "FINAL RANKING:\nThis is unclear"
        result = parse_ranking_from_text(text)
        assert result == []

    def test_parse_mixed_format(self):
        """Test with mixed numbered and unnumbered format."""
        text = """FINAL RANKING:
        1. Response A
        Response B
        2. Response C"""
        result = parse_ranking_from_text(text)
        # Should extract numbered items first (parser behavior)
        assert "Response A" in result
        assert "Response C" in result
        # Note: Response B without number may not be captured by numbered regex

    def test_parse_case_sensitivity(self):
        """Test that 'Response' must be capitalized."""
        text = "FINAL RANKING:\nresponse A\nResponse B"
        result = parse_ranking_from_text(text)
        # Should only match properly capitalized
        assert result == ["Response B"]

    def test_parse_with_extended_labels(self):
        """Test parsing with labels beyond Z (edge case)."""
        text = "FINAL RANKING:\nResponse A\nResponse Z"
        result = parse_ranking_from_text(text)
        assert result == ["Response A", "Response Z"]


class TestCalculateAggregateRankings:
    """Test aggregate ranking calculation."""

    def test_basic_aggregation(self, sample_label_to_model):
        """Test basic aggregation across multiple rankings."""
        stage2_results = [
            {
                "agent_id": "agent-1",
                "agent_title": "Agent One",
                "model": "test/model-1",
                "ranking": "FINAL RANKING:\n1. Response A\n2. Response B\n3. Response C",
                "parsed_ranking": ["Response A", "Response B", "Response C"]
            },
            {
                "agent_id": "agent-2",
                "agent_title": "Agent Two",
                "model": "test/model-2",
                "ranking": "FINAL RANKING:\n1. Response C\n2. Response A\n3. Response B",
                "parsed_ranking": ["Response C", "Response A", "Response B"]
            }
        ]

        result = calculate_aggregate_rankings(stage2_results, sample_label_to_model)

        # Agent One: positions [1, 2] = avg 1.5
        # Agent Two: positions [3, 1] = avg 2.0
        # Agent Three: positions [2, 3] = avg 2.5
        assert len(result) == 3
        assert result[0]["agent_title"] == "Agent One"
        assert result[0]["average_rank"] == 1.5
        assert result[1]["agent_title"] == "Agent Three"
        assert result[1]["average_rank"] == 2.0
        assert result[2]["agent_title"] == "Agent Two"
        assert result[2]["average_rank"] == 2.5

    def test_tie_handling(self, sample_label_to_model):
        """Test when agents have same average rank."""
        stage2_results = [
            {
                "agent_id": "agent-1",
                "agent_title": "Agent One",
                "model": "test/model-1",
                "ranking": "FINAL RANKING:\n1. Response A\n2. Response B",
                "parsed_ranking": ["Response A", "Response B"]
            },
            {
                "agent_id": "agent-2",
                "agent_title": "Agent Two",
                "model": "test/model-2",
                "ranking": "FINAL RANKING:\n1. Response B\n2. Response A",
                "parsed_ranking": ["Response B", "Response A"]
            }
        ]

        result = calculate_aggregate_rankings(stage2_results, sample_label_to_model)

        # Both should have avg rank of 1.5
        assert len(result) == 2
        assert result[0]["average_rank"] == 1.5
        assert result[1]["average_rank"] == 1.5

    def test_empty_rankings(self, sample_label_to_model):
        """Test with empty stage2 results."""
        result = calculate_aggregate_rankings([], sample_label_to_model)
        assert result == []

    def test_partial_rankings(self, sample_label_to_model):
        """Test when agents rank different subsets of responses."""
        stage2_results = [
            {
                "agent_id": "agent-1",
                "agent_title": "Agent One",
                "model": "test/model-1",
                "ranking": "FINAL RANKING:\n1. Response A",
                "parsed_ranking": ["Response A"]
            },
            {
                "agent_id": "agent-2",
                "agent_title": "Agent Two",
                "model": "test/model-2",
                "ranking": "FINAL RANKING:\n1. Response A\n2. Response B",
                "parsed_ranking": ["Response A", "Response B"]
            }
        ]

        result = calculate_aggregate_rankings(stage2_results, sample_label_to_model)

        # Response A: [1, 1] = avg 1.0
        # Response B: [2] = avg 2.0
        assert len(result) == 2
        assert result[0]["agent_title"] == "Agent One"
        assert result[0]["average_rank"] == 1.0
        assert result[0]["rankings_count"] == 2

    def test_rankings_count(self, sample_label_to_model):
        """Test that rankings_count is correctly calculated."""
        stage2_results = [
            {
                "agent_id": "agent-1",
                "agent_title": "Agent One",
                "model": "test/model-1",
                "ranking": "FINAL RANKING:\n1. Response A\n2. Response B\n3. Response C",
                "parsed_ranking": ["Response A", "Response B", "Response C"]
            }
        ]

        result = calculate_aggregate_rankings(stage2_results, sample_label_to_model)

        # All three agents should have rankings_count of 1
        for agent_result in result:
            assert agent_result["rankings_count"] == 1


class TestGenerateConversationTitle:
    """Test conversation title generation."""

    @pytest.mark.asyncio
    async def test_successful_title_generation(self, mock_openrouter_client):
        """Test successful title generation."""
        # Mock the response with a title
        mock_openrouter_client.post.return_value.json.return_value = {
            "choices": [{"message": {"content": "Test Conversation Title"}}]
        }

        with patch("httpx.AsyncClient", return_value=mock_openrouter_client):
            result = await generate_conversation_title("What is the meaning of life?")
            assert result == "Test Conversation Title"

    @pytest.mark.asyncio
    async def test_title_truncation(self, mock_openrouter_client):
        """Test that long titles are truncated."""
        long_title = "A" * 60
        mock_openrouter_client.post.return_value.json.return_value = {
            "choices": [{"message": {"content": long_title}}]
        }

        with patch("httpx.AsyncClient", return_value=mock_openrouter_client):
            result = await generate_conversation_title("Test query")
            assert len(result) <= 50
            assert result.endswith("...")

    @pytest.mark.asyncio
    async def test_quote_stripping(self, mock_openrouter_client):
        """Test that quotes are stripped from title."""
        mock_openrouter_client.post.return_value.json.return_value = {
            "choices": [{"message": {"content": '"Quoted Title"'}}]
        }

        with patch("httpx.AsyncClient", return_value=mock_openrouter_client):
            result = await generate_conversation_title("Test query")
            assert result == "Quoted Title"

    @pytest.mark.asyncio
    async def test_fallback_on_failure(self):
        """Test fallback when API fails."""
        with patch("backend.council.query_model", return_value=None):
            result = await generate_conversation_title("Test query")
            assert result == "New Conversation"


class TestStage1CollectResponses:
    """Test Stage 1: Collect responses."""

    @pytest.mark.asyncio
    async def test_with_active_agents(self, sample_agents, temp_data_dir, test_user_id):
        """Test stage 1 with active agents configured."""
        # Setup agents
        with patch("backend.council.agent_storage.get_active_agents", return_value=sample_agents[:2]):
            with patch("backend.council.query_model") as mock_query:
                mock_query.return_value = {"content": "Test response"}

                result = await stage1_collect_responses(test_user_id, "Test query?")

                assert len(result) == 2
                assert result[0]["agent_title"] == "Agent One"
                assert result[1]["agent_title"] == "Agent Two"
                assert all("response" in r for r in result)

    @pytest.mark.asyncio
    async def test_legacy_fallback(self, temp_data_dir, test_user_id):
        """Test fallback to COUNCIL_MODELS when no agents configured."""
        with patch("backend.council.agent_storage.get_active_agents", return_value=[]):
            with patch("backend.council.COUNCIL_MODELS", ["test/model-1", "test/model-2"]):
                with patch("backend.council.query_model") as mock_query:
                    mock_query.return_value = {"content": "Test response"}

                    result = await stage1_collect_responses(test_user_id, "Test query?")

                    assert len(result) == 2

    @pytest.mark.asyncio
    async def test_graceful_degradation_on_failures(self, sample_agents, test_user_id):
        """Test that stage 1 continues with successful responses when some fail."""
        with patch("backend.council.agent_storage.get_active_agents", return_value=sample_agents[:2]):
            with patch("backend.council.query_model") as mock_query:
                # First call succeeds, second fails
                mock_query.side_effect = [
                    {"content": "Success"},
                    None
                ]

                result = await stage1_collect_responses(test_user_id, "Test query?")

                # Should only have one successful response
                assert len(result) == 1
                assert result[0]["response"] == "Success"

    @pytest.mark.asyncio
    async def test_agent_specific_prompt_priority(self, sample_agent, test_user_id):
        """Test that agent-specific prompts take priority."""
        agent_with_prompt = sample_agent.copy()
        agent_with_prompt["prompts"] = {"stage1": "Custom prompt: {user_query}"}

        with patch("backend.council.agent_storage.get_active_agents", return_value=[agent_with_prompt]):
            with patch("backend.council.query_model") as mock_query:
                mock_query.return_value = {"content": "Response"}

                await stage1_collect_responses(test_user_id, "Test?")

                # Check that the custom prompt was used
                call_args = mock_query.call_args
                messages = call_args[0][1]
                assert "Custom prompt: Test?" in messages[0]["content"]


class TestStage2CollectRankings:
    """Test Stage 2: Collect rankings."""

    @pytest.mark.asyncio
    async def test_anonymization(self, sample_stage1_results, sample_agents, test_user_id):
        """Test that responses are properly anonymized."""
        with patch("backend.council.agent_storage.get_active_agents", return_value=sample_agents[:3]):
            with patch("backend.council.query_model") as mock_query:
                mock_query.return_value = {"content": "FINAL RANKING:\n1. Response A"}

                results, label_to_model = await stage2_collect_rankings(
                    test_user_id,
                    "Test query?",
                    sample_stage1_results
                )

                # Check label_to_model mapping
                assert "Response A" in label_to_model
                assert "Response B" in label_to_model
                assert "Response C" in label_to_model
                assert label_to_model["Response A"]["agent_title"] == "Agent One"

    @pytest.mark.asyncio
    async def test_ranking_parsing(self, sample_stage1_results, sample_agents, test_user_id):
        """Test that rankings are parsed correctly."""
        with patch("backend.council.agent_storage.get_active_agents", return_value=sample_agents[:1]):
            with patch("backend.council.query_model") as mock_query:
                mock_query.return_value = {
                    "content": "FINAL RANKING:\n1. Response B\n2. Response A\n3. Response C"
                }

                results, _ = await stage2_collect_rankings(
                    test_user_id,
                    "Test query?",
                    sample_stage1_results
                )

                assert results[0]["parsed_ranking"] == ["Response B", "Response A", "Response C"]

    @pytest.mark.asyncio
    async def test_legacy_fallback_stage2(self, sample_stage1_results, test_user_id):
        """Test fallback when no agents configured in stage 2."""
        with patch("backend.council.agent_storage.get_active_agents", return_value=[]):
            with patch("backend.council.query_model") as mock_query:
                mock_query.return_value = {"content": "FINAL RANKING:\n1. Response A"}

                results, _ = await stage2_collect_rankings(
                    test_user_id,
                    "Test query?",
                    sample_stage1_results
                )

                # Should create legacy agents from stage1 results
                assert len(results) == 3


class TestStage3SynthesizeFinal:
    """Test Stage 3: Final synthesis."""

    @pytest.mark.asyncio
    async def test_with_chairman_agent(self, sample_stage1_results, test_user_id):
        """Test synthesis with designated chairman."""
        chairman = {
            "id": "chairman-1",
            "title": "The Chairman",
            "model": "test/chairman",
            "prompts": {}
        }

        stage2_results = [
            {
                "agent_id": "agent-1",
                "agent_title": "Agent One",
                "model": "test/model-1",
                "ranking": "FINAL RANKING:\n1. Response A",
                "parsed_ranking": ["Response A"]
            }
        ]

        with patch("backend.council.agent_storage.get_chairman", return_value=chairman):
            with patch("backend.council.query_model") as mock_query:
                mock_query.return_value = {"content": "Final synthesis"}

                result = await stage3_synthesize_final(
                    test_user_id,
                    "Test query?",
                    sample_stage1_results,
                    stage2_results
                )

                assert result["agent_title"] == "The Chairman"
                assert result["model"] == "test/chairman"
                assert result["response"] == "Final synthesis"

    @pytest.mark.asyncio
    async def test_fallback_to_chairman_model(self, sample_stage1_results, test_user_id):
        """Test fallback to CHAIRMAN_MODEL when no chairman agent."""
        stage2_results = []

        with patch("backend.council.agent_storage.get_chairman", return_value=None):
            with patch("backend.council.CHAIRMAN_MODEL", "test/default-chairman"):
                with patch("backend.council.query_model") as mock_query:
                    mock_query.return_value = {"content": "Final synthesis"}

                    result = await stage3_synthesize_final(
                        test_user_id,
                        "Test query?",
                        sample_stage1_results,
                        stage2_results
                    )

                    assert result["model"] == "test/default-chairman"

    @pytest.mark.asyncio
    async def test_failure_handling(self, sample_stage1_results, test_user_id):
        """Test error handling when chairman query fails."""
        with patch("backend.council.agent_storage.get_chairman", return_value=None):
            with patch("backend.council.query_model", return_value=None):
                result = await stage3_synthesize_final(
                    test_user_id,
                    "Test query?",
                    sample_stage1_results,
                    []
                )

                assert "Error" in result["response"]


class TestRunFullCouncil:
    """Test the complete 3-stage pipeline."""

    @pytest.mark.asyncio
    async def test_full_pipeline_success(self, sample_agents, test_user_id):
        """Test successful execution of all 3 stages."""
        with patch("backend.council.agent_storage.get_active_agents", return_value=sample_agents[:2]):
            with patch("backend.council.agent_storage.get_chairman", return_value=None):
                with patch("backend.council.query_model") as mock_query:
                    # Stage 1 responses
                    mock_query.side_effect = [
                        {"content": "Response 1"},
                        {"content": "Response 2"},
                        # Stage 2 rankings
                        {"content": "FINAL RANKING:\n1. Response A\n2. Response B"},
                        {"content": "FINAL RANKING:\n1. Response B\n2. Response A"},
                        # Stage 3 synthesis
                        {"content": "Final answer"}
                    ]

                    stage1, stage2, stage3, metadata = await run_full_council(test_user_id, "Test query?")

                    assert len(stage1) == 2
                    assert len(stage2) == 2
                    assert stage3["response"] == "Final answer"
                    assert "label_to_model" in metadata
                    assert "aggregate_rankings" in metadata

    @pytest.mark.asyncio
    async def test_all_models_fail_stage1(self, sample_agents, test_user_id):
        """Test when all models fail in stage 1."""
        with patch("backend.council.agent_storage.get_active_agents", return_value=sample_agents[:2]):
            with patch("backend.council.query_model", return_value=None):
                stage1, stage2, stage3, metadata = await run_full_council(test_user_id, "Test query?")

                assert stage1 == []
                assert stage2 == []
                assert "Error" in stage3["response"] or stage3["model"] == "error"

    @pytest.mark.asyncio
    async def test_metadata_structure(self, sample_agents, test_user_id):
        """Test that metadata has correct structure."""
        with patch("backend.council.agent_storage.get_active_agents", return_value=sample_agents[:2]):
            with patch("backend.council.agent_storage.get_chairman", return_value=None):
                with patch("backend.council.query_model") as mock_query:
                    mock_query.side_effect = [
                        {"content": "Response 1"},
                        {"content": "Response 2"},
                        {"content": "FINAL RANKING:\n1. Response A\n2. Response B"},
                        {"content": "FINAL RANKING:\n1. Response A\n2. Response B"},
                        {"content": "Final"}
                    ]

                    _, _, _, metadata = await run_full_council(test_user_id, "Test query?")

                    assert "label_to_model" in metadata
                    assert "aggregate_rankings" in metadata
                    assert isinstance(metadata["aggregate_rankings"], list)
