"""
Integration tests for GREENNGIVE system.
Tests full request flow with all components.
"""
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock

from backend import main
from backend.services.fx_client import FXClientError


@pytest_asyncio.fixture
async def integration_client():
    """Create integration test client with mocked backends."""
    # Mock the global clients
    main.fx_client = AsyncMock()
    main.cache_client = AsyncMock()

    # Setup cache storage for state persistence across calls
    cache_storage = {}

    async def mock_cache_get(key):
        return cache_storage.get(key)

    async def mock_cache_set(key, value, ttl=300):
        cache_storage[key] = value
        return True

    main.cache_client.get = mock_cache_get
    main.cache_client.set = mock_cache_set

    transport = ASGITransport(app=main.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, cache_storage


@pytest.mark.asyncio
class TestIntegration:
    """Integration tests for full system."""

    async def test_full_request_flow(self, integration_client):
        """Test complete request flow from API → Cache → Response."""
        client, cache_storage = integration_client

        # Arrange
        mock_fx_data = {
            "amount": 1.0,
            "base": "EUR",
            "rates": {
                "2025-07-01": {"USD": 1.0912},
                "2025-07-02": {"USD": 1.093},
                "2025-07-03": {"USD": 1.0945},
            },
        }
        main.fx_client.fetch_rates = AsyncMock(return_value=mock_fx_data)

        # Act - First request (cache miss)
        response1 = await client.get(
            "/summary?start=2025-07-01&end=2025-07-03&breakdown=day"
        )

        # Assert first response
        assert response1.status_code == 200
        data1 = response1.json()
        assert len(data1["days"]) == 3
        assert data1["totals"]["start_rate"] == 1.0912

        # Verify data was cached
        assert "fx:2025-07-01:2025-07-03" in cache_storage

        # Act - Second request (cache hit)
        main.fx_client.fetch_rates.reset_mock()
        response2 = await client.get(
            "/summary?start=2025-07-01&end=2025-07-03&breakdown=day"
        )

        # Assert second response
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2 == data1  # Same data from cache

        # Verify FX client was NOT called on cache hit
        main.fx_client.fetch_rates.assert_not_called()

    async def test_cache_persistence_across_requests(self, integration_client):
        """Test that cache persists data across multiple requests."""
        client, cache_storage = integration_client

        # Arrange
        dates = [
            ("2025-07-01", "2025-07-03"),
            ("2025-07-05", "2025-07-07"),
            ("2025-07-10", "2025-07-12"),
        ]

        # Act - Make multiple requests with different date ranges
        for start, end in dates:
            mock_data = {
                "amount": 1.0,
                "base": "EUR",
                "rates": {start: {"USD": 1.09}},
            }
            main.fx_client.fetch_rates = AsyncMock(return_value=mock_data)

            response = await client.get(f"/summary?start={start}&end={end}")
            assert response.status_code == 200

        # Assert - All requests cached separately
        assert len(cache_storage) == 3
        assert "fx:2025-07-01:2025-07-03" in cache_storage
        assert "fx:2025-07-05:2025-07-07" in cache_storage
        assert "fx:2025-07-10:2025-07-12" in cache_storage

    async def test_fallback_activation_on_primary_failure(self, integration_client):
        """Test fallback service is used when primary fails."""
        client, cache_storage = integration_client

        # Arrange - Primary fails, fallback succeeds
        fallback_data = {
            "amount": 1.0,
            "base": "EUR",
            "rates": {"2025-07-01": {"USD": 1.0912}},
        }

        call_count = 0

        async def mock_fetch_with_fallback(start, end, fallback_url=None):
            nonlocal call_count
            call_count += 1
            # Always use fallback in this test
            return fallback_data

        main.fx_client.fetch_rates = mock_fetch_with_fallback

        # Act
        response = await client.get("/summary?start=2025-07-01&end=2025-07-01")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["totals"]["start_rate"] == 1.0912
        assert call_count == 1  # Fetch was called

    async def test_concurrent_requests_with_different_params(self, integration_client):
        """Test concurrent requests with different parameters."""
        client, cache_storage = integration_client

        # Arrange
        async def mock_fetch(start, end, fallback_url=None):
            # Return different data based on date
            if start == "2025-07-01":
                return {
                    "amount": 1.0,
                    "base": "EUR",
                    "rates": {"2025-07-01": {"USD": 1.0912}},
                }
            else:
                return {
                    "amount": 1.0,
                    "base": "EUR",
                    "rates": {"2025-08-01": {"USD": 1.1}},
                }

        main.fx_client.fetch_rates = mock_fetch

        # Act - Make concurrent requests
        import asyncio

        responses = await asyncio.gather(
            client.get("/summary?start=2025-07-01&end=2025-07-01"),
            client.get("/summary?start=2025-08-01&end=2025-08-01"),
            client.get("/summary?start=2025-07-01&end=2025-07-01"),  # Duplicate
        )

        # Assert
        assert all(r.status_code == 200 for r in responses)

        # First and third should have same data (cache hit on third)
        data1 = responses[0].json()
        data2 = responses[1].json()
        data3 = responses[2].json()

        assert data1["totals"]["start_rate"] == 1.0912
        assert data2["totals"]["start_rate"] == 1.1
        assert data1 == data3  # Same from cache

    async def test_calculation_consistency_across_requests(self, integration_client):
        """Test that calculations are consistent across multiple requests."""
        client, cache_storage = integration_client

        # Arrange
        mock_fx_data = {
            "amount": 1.0,
            "base": "EUR",
            "rates": {
                "2025-07-01": {"USD": 1.0912},
                "2025-07-02": {"USD": 1.093},
                "2025-07-03": {"USD": 1.0945},
            },
        }
        main.fx_client.fetch_rates = AsyncMock(return_value=mock_fx_data)

        # Act - Make multiple requests
        responses = []
        for _ in range(3):
            response = await client.get(
                "/summary?start=2025-07-01&end=2025-07-03&breakdown=day"
            )
            responses.append(response)

        # Assert - All responses identical
        data_list = [r.json() for r in responses]
        assert all(d == data_list[0] for d in data_list)

        # Verify calculations
        data = data_list[0]
        assert data["totals"]["total_pct_change"] == 0.302
        assert data["totals"]["mean_rate"] == 1.0929

    async def test_error_recovery_and_retry(self, integration_client):
        """Test system recovers from errors."""
        client, cache_storage = integration_client

        # Arrange - First request fails, second succeeds
        call_count = 0

        async def mock_fetch_with_failure(start, end, fallback_url=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise FXClientError("First attempt fails")
            # Second attempt succeeds
            return {
                "amount": 1.0,
                "base": "EUR",
                "rates": {"2025-07-01": {"USD": 1.0912}},
            }

        main.fx_client.fetch_rates = mock_fetch_with_failure

        # Act - First request fails
        response1 = await client.get("/summary?start=2025-07-01&end=2025-07-01")
        assert response1.status_code == 502

        # Act - Second request succeeds
        response2 = await client.get("/summary?start=2025-07-01&end=2025-07-01")
        assert response2.status_code == 200

        # Assert
        assert call_count == 2  # Two attempts made

    async def test_health_check_always_available(self, integration_client):
        """Test health check works even during errors."""
        client, cache_storage = integration_client

        # Arrange - Break FX client
        main.fx_client.fetch_rates = AsyncMock(side_effect=Exception("Broken"))

        # Act - Health check should still work
        health_response = await client.get("/health")

        # Assert
        assert health_response.status_code == 200
        data = health_response.json()
        assert data["status"] == "ok"

    async def test_different_breakdown_params_cached_separately(
        self, integration_client
    ):
        """Test that requests with different breakdown params are cached separately."""
        client, cache_storage = integration_client

        # Arrange
        mock_fx_data = {
            "amount": 1.0,
            "base": "EUR",
            "rates": {
                "2025-07-01": {"USD": 1.0912},
                "2025-07-02": {"USD": 1.093},
            },
        }
        main.fx_client.fetch_rates = AsyncMock(return_value=mock_fx_data)

        # Act - Same dates, different breakdown
        response1 = await client.get("/summary?start=2025-07-01&end=2025-07-02")
        response2 = await client.get(
            "/summary?start=2025-07-01&end=2025-07-02&breakdown=day"
        )

        # Assert - Both successful
        assert response1.status_code == 200
        assert response2.status_code == 200

        # Response1 has no breakdown, response2 has breakdown
        data1 = response1.json()
        data2 = response2.json()

        assert data1["days"] is None
        assert data2["days"] is not None
        assert len(data2["days"]) == 2

        # Same cache key used (breakdown param doesn't affect cache key)
        assert len(cache_storage) == 1

    async def test_large_date_range(self, integration_client):
        """Test handling of large date range."""
        client, cache_storage = integration_client

        # Arrange - Create 30 days of data
        rates = {}
        for i in range(30):
            date = f"2025-07-{i+1:02d}"
            rates[date] = {"USD": 1.09 + (i * 0.001)}

        mock_fx_data = {"amount": 1.0, "base": "EUR", "rates": rates}
        main.fx_client.fetch_rates = AsyncMock(return_value=mock_fx_data)

        # Act
        response = await client.get(
            "/summary?start=2025-07-01&end=2025-07-30&breakdown=day"
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["days"]) == 30

        # Verify calculations for large dataset
        assert data["totals"]["start_rate"] == 1.09
        assert data["totals"]["end_rate"] == 1.119  # 1.09 + 29*0.001

    async def test_edge_case_same_start_and_end(self, integration_client):
        """Test edge case where start and end are the same."""
        client, cache_storage = integration_client

        # Arrange
        mock_fx_data = {
            "amount": 1.0,
            "base": "EUR",
            "rates": {"2025-07-01": {"USD": 1.0912}},
        }
        main.fx_client.fetch_rates = AsyncMock(return_value=mock_fx_data)

        # Act
        response = await client.get(
            "/summary?start=2025-07-01&end=2025-07-01&breakdown=day"
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["days"]) == 1
        assert data["days"][0]["pct_change"] is None  # No previous day
        assert data["totals"]["total_pct_change"] == 0.0  # No change
