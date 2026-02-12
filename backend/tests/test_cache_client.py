"""
Tests for cache client.
"""
import pytest
import pytest_asyncio
from httpx import HTTPError, Request, Response

from backend.services.cache import CacheClient


@pytest_asyncio.fixture
async def cache_client():
    """Create cache client for testing."""
    async with CacheClient() as client:
        yield client


@pytest.mark.asyncio
class TestCacheClient:
    """Tests for CacheClient."""

    async def test_get_success(self, cache_client, mocker):
        """Test successful get operation."""
        # Arrange
        mock_response = Response(
            200,
            json={"value": {"rate": 1.0912, "date": "2025-07-01"}},
            request=Request("GET", "http://localhost:8001/cache/get/test_key"),
        )
        mock_get = mocker.patch.object(
            cache_client._client, "get", return_value=mock_response
        )

        # Act
        result = await cache_client.get("test_key")

        # Assert
        assert result == {"rate": 1.0912, "date": "2025-07-01"}
        mock_get.assert_called_once_with("/cache/get/test_key")

    async def test_get_not_found(self, cache_client, mocker):
        """Test get operation when key not found."""
        # Arrange
        mock_response = Response(
            200,
            json={"value": None},
            request=Request("GET", "http://localhost:8001/cache/get/nonexistent_key"),
        )
        mocker.patch.object(cache_client._client, "get", return_value=mock_response)

        # Act
        result = await cache_client.get("nonexistent_key")

        # Assert
        assert result is None

    async def test_get_http_error(self, cache_client, mocker):
        """Test get operation with HTTP error."""
        # Arrange
        mocker.patch.object(
            cache_client._client,
            "get",
            side_effect=HTTPError("Server error"),
        )

        # Act
        result = await cache_client.get("test_key")

        # Assert
        assert result is None

    async def test_get_timeout(self, cache_client, mocker):
        """Test get operation with timeout."""
        # Arrange
        mocker.patch.object(
            cache_client._client,
            "get",
            side_effect=HTTPError("Timeout"),
        )

        # Act
        result = await cache_client.get("test_key")

        # Assert
        assert result is None

    async def test_get_unexpected_error(self, cache_client, mocker):
        """Test get operation with unexpected error."""
        # Arrange
        mocker.patch.object(
            cache_client._client, "get", side_effect=Exception("Unexpected error")
        )

        # Act
        result = await cache_client.get("test_key")

        # Assert
        assert result is None

    async def test_set_success(self, cache_client, mocker):
        """Test successful set operation."""
        # Arrange
        mock_response = Response(
            200,
            json={"success": True},
            request=Request("POST", "http://localhost:8001/cache/set"),
        )
        mock_post = mocker.patch.object(
            cache_client._client, "post", return_value=mock_response
        )

        # Act
        result = await cache_client.set("test_key", {"data": "value"}, ttl=60)

        # Assert
        assert result is True
        mock_post.assert_called_once_with(
            "/cache/set",
            json={"key": "test_key", "value": {"data": "value"}, "ttl": 60},
        )

    async def test_set_with_default_ttl(self, cache_client, mocker):
        """Test set operation with default TTL."""
        # Arrange
        mock_response = Response(
            200,
            json={"success": True},
            request=Request("POST", "http://localhost:8001/cache/set"),
        )
        mock_post = mocker.patch.object(
            cache_client._client, "post", return_value=mock_response
        )

        # Act
        result = await cache_client.set("test_key", "value")

        # Assert
        assert result is True
        # Should use DEFAULT_TTL (300)
        call_args = mock_post.call_args
        assert call_args[1]["json"]["ttl"] == 300

    async def test_set_http_error(self, cache_client, mocker):
        """Test set operation with HTTP error."""
        # Arrange
        mocker.patch.object(
            cache_client._client,
            "post",
            side_effect=HTTPError("Server error"),
        )

        # Act
        result = await cache_client.set("test_key", "value")

        # Assert
        assert result is False

    async def test_set_timeout(self, cache_client, mocker):
        """Test set operation with timeout."""
        # Arrange
        mocker.patch.object(
            cache_client._client,
            "post",
            side_effect=HTTPError("Timeout"),
        )

        # Act
        result = await cache_client.set("test_key", "value", ttl=60)

        # Assert
        assert result is False

    async def test_set_unexpected_error(self, cache_client, mocker):
        """Test set operation with unexpected error."""
        # Arrange
        mocker.patch.object(
            cache_client._client, "post", side_effect=Exception("Unexpected error")
        )

        # Act
        result = await cache_client.set("test_key", "value")

        # Assert
        assert result is False

    async def test_context_manager_usage(self):
        """Test cache client as async context manager."""
        # Act
        async with CacheClient() as client:
            # Assert
            assert client._client is not None

        # After exit, client should be closed
        assert client._client is None

    async def test_get_without_context_manager_raises_error(self):
        """Test get without context manager raises error."""
        # Arrange
        client = CacheClient()

        # Act & Assert
        with pytest.raises(RuntimeError, match="must be used as async context manager"):
            await client.get("test_key")

    async def test_set_without_context_manager_raises_error(self):
        """Test set without context manager raises error."""
        # Arrange
        client = CacheClient()

        # Act & Assert
        with pytest.raises(RuntimeError, match="must be used as async context manager"):
            await client.set("test_key", "value")

    async def test_set_complex_data(self, cache_client, mocker):
        """Test setting complex nested data."""
        # Arrange
        complex_data = {
            "nested": {"deep": {"structure": [1, 2, 3]}},
            "list": ["a", "b", "c"],
        }
        mock_response = Response(
            200,
            json={"success": True},
            request=Request("POST", "http://localhost:8001/cache/set"),
        )
        mock_post = mocker.patch.object(
            cache_client._client, "post", return_value=mock_response
        )

        # Act
        result = await cache_client.set("complex_key", complex_data)

        # Assert
        assert result is True
        call_args = mock_post.call_args
        assert call_args[1]["json"]["value"] == complex_data

    async def test_get_with_special_characters_in_key(self, cache_client, mocker):
        """Test get with special characters in key."""
        # Arrange
        key_with_special = "fx:2025-07-01:2025-07-03"
        mock_response = Response(
            200,
            json={"value": "data"},
            request=Request("GET", f"http://localhost:8001/cache/get/{key_with_special}"),
        )
        mock_get = mocker.patch.object(
            cache_client._client, "get", return_value=mock_response
        )

        # Act
        result = await cache_client.get(key_with_special)

        # Assert
        assert result == "data"
        mock_get.assert_called_once_with(f"/cache/get/{key_with_special}")
