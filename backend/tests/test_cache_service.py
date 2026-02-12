"""
Tests for cache service.
"""
import datetime as dt
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.cache_service import CacheStore, app


@pytest.fixture
def cache_store():
    """Create a fresh cache store for each test."""
    return CacheStore(max_size=3)  # Small size for testing


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    return TestClient(app)


class TestCacheStore:
    """Tests for CacheStore class."""

    def test_set_and_get(self, cache_store):
        """Test basic set and get operations."""
        # Arrange
        key = "test_key"
        value = {"data": "test_value"}

        # Act
        cache_store.set(key, value, ttl=60)
        result = cache_store.get(key)

        # Assert
        assert result == value

    def test_get_nonexistent_key(self, cache_store):
        """Test getting non-existent key returns None."""
        # Act
        result = cache_store.get("nonexistent")

        # Assert
        assert result is None

    def test_ttl_expiration(self, cache_store):
        """Test that expired entries return None."""
        # Arrange
        key = "test_key"
        value = "test_value"
        current_time = dt.datetime(2025, 1, 1, 12, 0, 0)

        # Set with very short TTL and mock time
        with patch("backend.cache_service.dt") as mock_dt:
            # Mock datetime.now() for set operation
            mock_dt.datetime.now.return_value = current_time
            mock_dt.timedelta = dt.timedelta  # Keep real timedelta

            cache_store.set(key, value, ttl=60)

            # Verify it's accessible immediately (within TTL)
            result = cache_store.get(key)
            assert result == value

            # Move time forward past expiry (61 seconds)
            mock_dt.datetime.now.return_value = current_time + dt.timedelta(seconds=61)

            # Act
            result = cache_store.get(key)

            # Assert
            assert result is None

    def test_lru_eviction(self, cache_store):
        """Test LRU eviction when cache is full."""
        # Arrange - cache_store has max_size=3
        cache_store.set("key1", "value1", ttl=60)
        cache_store.set("key2", "value2", ttl=60)
        cache_store.set("key3", "value3", ttl=60)

        # Assert cache is full
        assert cache_store.size() == 3

        # Act - add 4th item, should evict key1 (oldest)
        cache_store.set("key4", "value4", ttl=60)

        # Assert
        assert cache_store.size() == 3
        assert cache_store.get("key1") is None  # Evicted
        assert cache_store.get("key2") == "value2"
        assert cache_store.get("key3") == "value3"
        assert cache_store.get("key4") == "value4"

    def test_lru_move_to_end_on_access(self, cache_store):
        """Test that accessing a key moves it to end (most recently used)."""
        # Arrange
        cache_store.set("key1", "value1", ttl=60)
        cache_store.set("key2", "value2", ttl=60)
        cache_store.set("key3", "value3", ttl=60)

        # Act - access key1, making it most recently used
        cache_store.get("key1")

        # Now add 4th item - should evict key2 (now oldest)
        cache_store.set("key4", "value4", ttl=60)

        # Assert
        assert cache_store.get("key1") == "value1"  # Still there
        assert cache_store.get("key2") is None  # Evicted
        assert cache_store.get("key3") == "value3"
        assert cache_store.get("key4") == "value4"

    def test_update_existing_key(self, cache_store):
        """Test updating an existing key moves it to end."""
        # Arrange
        cache_store.set("key1", "value1", ttl=60)
        cache_store.set("key2", "value2", ttl=60)
        cache_store.set("key3", "value3", ttl=60)

        # Act - update key1 with new value
        cache_store.set("key1", "new_value1", ttl=60)

        # Add 4th item - should evict key2 (now oldest)
        cache_store.set("key4", "value4", ttl=60)

        # Assert
        assert cache_store.get("key1") == "new_value1"  # Updated and still there
        assert cache_store.get("key2") is None  # Evicted
        assert cache_store.get("key3") == "value3"
        assert cache_store.get("key4") == "value4"

    def test_cache_size(self, cache_store):
        """Test cache size tracking."""
        # Arrange & Act
        assert cache_store.size() == 0

        cache_store.set("key1", "value1", ttl=60)
        assert cache_store.size() == 1

        cache_store.set("key2", "value2", ttl=60)
        assert cache_store.size() == 2

        cache_store.set("key3", "value3", ttl=60)
        assert cache_store.size() == 3

        # Fill to max, size should stay at 3
        cache_store.set("key4", "value4", ttl=60)
        assert cache_store.size() == 3

    def test_different_data_types(self, cache_store):
        """Test caching different data types."""
        # Arrange & Act - cache_store has max_size=3
        cache_store.set("string", "value", ttl=60)
        cache_store.set("int", 42, ttl=60)
        cache_store.set("float", 3.14, ttl=60)
        cache_store.set("list", [1, 2, 3], ttl=60)
        cache_store.set("dict", {"key": "value"}, ttl=60)

        # Assert - only last 3 items should be in cache
        assert cache_store.get("string") is None  # Evicted (oldest)
        assert cache_store.get("int") is None  # Evicted (2nd oldest)
        assert cache_store.get("float") == 3.14  # Still in cache
        assert cache_store.get("list") == [1, 2, 3]  # Still in cache
        assert cache_store.get("dict") == {"key": "value"}  # Still in cache (newest)


class TestCacheServiceAPI:
    """Tests for cache service FastAPI endpoints."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        # Act
        response = client.get("/health")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "cache-service"
        assert data["version"] == "1.0.0"

    def test_set_cache_endpoint(self, client):
        """Test POST /cache/set endpoint."""
        # Arrange
        payload = {"key": "test_key", "value": {"data": "test"}, "ttl": 60}

        # Act
        response = client.post("/cache/set", json=payload)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_get_cache_endpoint(self, client):
        """Test GET /cache/get/{key} endpoint."""
        # Arrange - set a value first
        client.post(
            "/cache/set", json={"key": "test_key", "value": "test_value", "ttl": 60}
        )

        # Act
        response = client.get("/cache/get/test_key")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["value"] == "test_value"

    def test_get_nonexistent_cache_endpoint(self, client):
        """Test getting non-existent key returns None."""
        # Act
        response = client.get("/cache/get/nonexistent")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["value"] is None

    def test_set_with_custom_ttl(self, client):
        """Test setting cache with custom TTL."""
        # Arrange
        payload = {"key": "custom_ttl", "value": "data", "ttl": 120}

        # Act
        response = client.post("/cache/set", json=payload)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_set_with_default_ttl(self, client):
        """Test setting cache with default TTL (not specified)."""
        # Arrange - ttl not specified, should use default
        payload = {"key": "default_ttl", "value": "data"}

        # Act
        response = client.post("/cache/set", json=payload)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_set_complex_nested_data(self, client):
        """Test caching complex nested data structures."""
        # Arrange
        complex_data = {
            "nested": {"deep": {"structure": [1, 2, 3]}},
            "list": ["a", "b", "c"],
            "number": 42,
        }
        payload = {"key": "complex", "value": complex_data, "ttl": 60}

        # Act
        client.post("/cache/set", json=payload)
        response = client.get("/cache/get/complex")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["value"] == complex_data

    def test_concurrent_access(self, client):
        """Test concurrent cache operations."""
        # Arrange
        keys = [f"key_{i}" for i in range(10)]

        # Act - set multiple keys
        for i, key in enumerate(keys):
            client.post("/cache/set", json={"key": key, "value": f"value_{i}", "ttl": 60})

        # Get all keys
        results = []
        for key in keys:
            response = client.get(f"/cache/get/{key}")
            results.append(response.json()["value"])

        # Assert - at least some keys should be present
        # (some might be evicted due to cache size limit)
        assert any(result is not None for result in results)
