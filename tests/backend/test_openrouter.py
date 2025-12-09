"""Tests for openrouter.py - API client."""

import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from backend.openrouter import query_model, query_models_parallel


class TestQueryModel:
    """Test single model query."""

    @pytest.mark.asyncio
    async def test_successful_query(self, mock_openrouter_client):
        """Test successful API query."""
        with patch("httpx.AsyncClient", return_value=mock_openrouter_client):
            result = await query_model(
                "test/model",
                [{"role": "user", "content": "Test message"}]
            )

            assert result is not None
            assert "content" in result
            assert result["content"] == "This is a test response from the model."

    @pytest.mark.asyncio
    async def test_with_reasoning_details(self):
        """Test response with reasoning details."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "Test content",
                    "reasoning_details": {"tokens": 100, "time": 2.5}
                }
            }]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await query_model("test/model", [{"role": "user", "content": "Test"}])

            assert result["reasoning_details"] is not None
            assert result["reasoning_details"]["tokens"] == 100

    @pytest.mark.asyncio
    async def test_http_error(self):
        """Test handling of HTTP errors."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found",
            request=MagicMock(),
            response=MagicMock()
        )

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await query_model("test/model", [{"role": "user", "content": "Test"}])

            assert result is None

    @pytest.mark.asyncio
    async def test_timeout(self):
        """Test timeout handling."""
        mock_client = MagicMock()
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await query_model("test/model", [{"role": "user", "content": "Test"}])

            assert result is None

    @pytest.mark.asyncio
    async def test_network_error(self):
        """Test network error handling."""
        mock_client = MagicMock()
        mock_client.post = AsyncMock(side_effect=httpx.NetworkError("Connection failed"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await query_model("test/model", [{"role": "user", "content": "Test"}])

            assert result is None

    @pytest.mark.asyncio
    async def test_malformed_json_response(self):
        """Test handling of malformed JSON response."""
        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await query_model("test/model", [{"role": "user", "content": "Test"}])

            assert result is None

    @pytest.mark.asyncio
    async def test_missing_content_field(self):
        """Test response with missing content field."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{
                "message": {}  # Missing content
            }]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await query_model("test/model", [{"role": "user", "content": "Test"}])

            # Should handle gracefully
            assert result is not None
            assert result["content"] is None

    @pytest.mark.asyncio
    async def test_custom_timeout(self):
        """Test custom timeout parameter."""
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=MagicMock())
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value = mock_client

            await query_model(
                "test/model",
                [{"role": "user", "content": "Test"}],
                timeout=60.0
            )

            # Verify AsyncClient was created with correct timeout
            mock_async_client.assert_called_once_with(timeout=60.0)


class TestQueryModelsParallel:
    """Test parallel model queries."""

    @pytest.mark.asyncio
    async def test_successful_parallel_queries(self):
        """Test successful queries to multiple models."""
        with patch("backend.openrouter.query_model") as mock_query:
            mock_query.side_effect = [
                {"content": "Response 1"},
                {"content": "Response 2"},
                {"content": "Response 3"}
            ]

            models = ["model-1", "model-2", "model-3"]
            messages = [{"role": "user", "content": "Test"}]

            result = await query_models_parallel(models, messages)

            assert len(result) == 3
            assert result["model-1"]["content"] == "Response 1"
            assert result["model-2"]["content"] == "Response 2"
            assert result["model-3"]["content"] == "Response 3"

    @pytest.mark.asyncio
    async def test_partial_failures(self):
        """Test when some models fail."""
        with patch("backend.openrouter.query_model") as mock_query:
            mock_query.side_effect = [
                {"content": "Success 1"},
                None,  # Failure
                {"content": "Success 2"}
            ]

            models = ["model-1", "model-2", "model-3"]
            messages = [{"role": "user", "content": "Test"}]

            result = await query_models_parallel(models, messages)

            assert len(result) == 3
            assert result["model-1"]["content"] == "Success 1"
            assert result["model-2"] is None
            assert result["model-3"]["content"] == "Success 2"

    @pytest.mark.asyncio
    async def test_all_failures(self):
        """Test when all models fail."""
        with patch("backend.openrouter.query_model", return_value=None):
            models = ["model-1", "model-2"]
            messages = [{"role": "user", "content": "Test"}]

            result = await query_models_parallel(models, messages)

            assert len(result) == 2
            assert all(v is None for v in result.values())

    @pytest.mark.asyncio
    async def test_empty_model_list(self):
        """Test with empty model list."""
        result = await query_models_parallel([], [{"role": "user", "content": "Test"}])

        assert result == {}

    @pytest.mark.asyncio
    async def test_preserves_model_order(self):
        """Test that result dict preserves model order."""
        with patch("backend.openrouter.query_model") as mock_query:
            mock_query.return_value = {"content": "Response"}

            models = ["model-a", "model-b", "model-c"]
            messages = [{"role": "user", "content": "Test"}]

            result = await query_models_parallel(models, messages)

            # Check that keys are in the same order
            result_keys = list(result.keys())
            assert result_keys == models
