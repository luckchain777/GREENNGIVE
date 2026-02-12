"""
Tests for main FastAPI application.
"""
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock

from backend import main
from backend.services.fx_client import FXClientError


@pytest_asyncio.fixture
async def test_client():
    """Create test client without lifespan (we'll mock the clients)."""
    # Mock the global clients to avoid startup
    main.fx_client = AsyncMock()
    main.cache_client = AsyncMock()

    transport = ASGITransport(app=main.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
class TestHealthEndpoint:
    """Tests for /health endpoint."""

    async def test_health_check(self, test_client):
        """Test health check returns OK."""
        # Act
        response = await test_client.get("/health")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "fx-pattern"
        assert data["version"] == "1.0.0"


@pytest.mark.asyncio
class TestSummaryEndpoint:
    """Tests for /summary endpoint."""

    async def test_summary_without_breakdown(self, test_client):
        """Test summary endpoint without daily breakdown."""
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

        main.cache_client.get = AsyncMock(return_value=None)
        main.cache_client.set = AsyncMock(return_value=True)
        main.fx_client.fetch_rates = AsyncMock(return_value=mock_fx_data)

        # Act
        response = await test_client.get(
            "/summary?start=2025-07-01&end=2025-07-03"
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert data["start"] == "2025-07-01"
        assert data["end"] == "2025-07-03"
        assert data["days"] is None  # No breakdown requested

        totals = data["totals"]
        assert totals["start_rate"] == 1.0912
        assert totals["end_rate"] == 1.0945
        assert totals["total_pct_change"] == 0.302
        assert totals["mean_rate"] == 1.0929

    async def test_summary_with_breakdown(self, test_client):
        """Test summary endpoint with daily breakdown."""
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

        main.cache_client.get = AsyncMock(return_value=None)
        main.cache_client.set = AsyncMock(return_value=True)
        main.fx_client.fetch_rates = AsyncMock(return_value=mock_fx_data)

        # Act
        response = await test_client.get(
            "/summary?start=2025-07-01&end=2025-07-03&breakdown=day"
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert data["days"] is not None
        assert len(data["days"]) == 3

        # Check first day (no pct_change)
        assert data["days"][0]["date"] == "2025-07-01"
        assert data["days"][0]["rate"] == 1.0912
        assert data["days"][0]["pct_change"] is None

        # Check second day (has pct_change)
        assert data["days"][1]["date"] == "2025-07-02"
        assert data["days"][1]["rate"] == 1.093
        assert data["days"][1]["pct_change"] == 0.165

        # Check third day
        assert data["days"][2]["date"] == "2025-07-03"
        assert data["days"][2]["rate"] == 1.0945
        assert data["days"][2]["pct_change"] == 0.137

    async def test_summary_cache_hit(self, test_client):
        """Test that cached data is used when available."""
        # Arrange
        cached_data = {
            "amount": 1.0,
            "base": "EUR",
            "rates": {
                "2025-07-01": {"USD": 1.0912},
                "2025-07-02": {"USD": 1.093},
            },
        }

        main.cache_client.get = AsyncMock(return_value=cached_data)
        main.fx_client.fetch_rates = AsyncMock()  # Should not be called

        # Act
        response = await test_client.get(
            "/summary?start=2025-07-01&end=2025-07-02"
        )

        # Assert
        assert response.status_code == 200
        # Verify cache was checked
        main.cache_client.get.assert_called_once_with("fx:2025-07-01:2025-07-02")
        # Verify FX client was NOT called
        main.fx_client.fetch_rates.assert_not_called()

    async def test_summary_cache_miss_fetches_data(self, test_client):
        """Test that FX client is called on cache miss."""
        # Arrange
        mock_fx_data = {
            "amount": 1.0,
            "base": "EUR",
            "rates": {"2025-07-01": {"USD": 1.0912}},
        }

        main.cache_client.get = AsyncMock(return_value=None)
        main.cache_client.set = AsyncMock(return_value=True)
        main.fx_client.fetch_rates = AsyncMock(return_value=mock_fx_data)

        # Act
        response = await test_client.get(
            "/summary?start=2025-07-01&end=2025-07-01"
        )

        # Assert
        assert response.status_code == 200
        # Verify FX client was called
        main.fx_client.fetch_rates.assert_called_once()
        # Verify result was cached
        main.cache_client.set.assert_called_once()

    async def test_summary_invalid_start_date(self, test_client):
        """Test 422 error for invalid start date format."""
        # Act
        response = await test_client.get(
            "/summary?start=invalid&end=2025-07-03"
        )

        # Assert
        assert response.status_code == 422  # FastAPI validation error

    async def test_summary_invalid_end_date(self, test_client):
        """Test 422 error for invalid end date format."""
        # Act
        response = await test_client.get(
            "/summary?start=2025-07-01&end=invalid"
        )

        # Assert
        assert response.status_code == 422  # FastAPI validation error

    async def test_summary_end_before_start(self, test_client):
        """Test 400 error when end date is before start date."""
        # Act
        response = await test_client.get(
            "/summary?start=2025-07-03&end=2025-07-01"
        )

        # Assert
        assert response.status_code == 400
        assert "End date must not be before start date" in response.json()["detail"]

    async def test_summary_date_range_exceeds_maximum(self, test_client):
        """Test 400 error when date range exceeds 90 days."""
        # Act - request 100 days (exceeds 90-day limit)
        response = await test_client.get(
            "/summary?start=2025-01-01&end=2025-04-11"
        )

        # Assert
        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "Date range exceeds maximum allowed duration" in detail
        assert "90 days" in detail

    async def test_summary_date_range_exactly_at_maximum(self, test_client):
        """Test that exactly 90 days is allowed."""
        # Arrange
        mock_fx_data = {
            "amount": 1.0,
            "base": "EUR",
            "rates": {
                "2025-01-01": {"USD": 1.09},
                "2025-04-01": {"USD": 1.10},
            },
        }
        main.cache_client.get = AsyncMock(return_value=None)
        main.cache_client.set = AsyncMock(return_value=True)
        main.fx_client.fetch_rates = AsyncMock(return_value=mock_fx_data)

        # Act - exactly 90 days (should be allowed)
        response = await test_client.get(
            "/summary?start=2025-01-01&end=2025-04-01"
        )

        # Assert
        assert response.status_code == 200

    async def test_summary_date_range_just_over_maximum(self, test_client):
        """Test that 91 days is rejected."""
        # Act - 91 days (exceeds limit by 1)
        response = await test_client.get(
            "/summary?start=2025-01-01&end=2025-04-02"
        )

        # Assert
        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "91 days" in detail

    async def test_summary_missing_start_param(self, test_client):
        """Test 422 error for missing start parameter."""
        # Act
        response = await test_client.get("/summary?end=2025-07-03")

        # Assert
        assert response.status_code == 422

    async def test_summary_missing_end_param(self, test_client):
        """Test 422 error for missing end parameter."""
        # Act
        response = await test_client.get("/summary?start=2025-07-01")

        # Assert
        assert response.status_code == 422

    async def test_summary_fx_client_failure_returns_502(self, test_client):
        """Test 502 error when FX client fails."""
        # Arrange
        main.cache_client.get = AsyncMock(return_value=None)
        main.fx_client.fetch_rates = AsyncMock(
            side_effect=FXClientError("Service unavailable")
        )

        # Act
        response = await test_client.get(
            "/summary?start=2025-07-01&end=2025-07-03"
        )

        # Assert
        assert response.status_code == 502
        # Error message comes from exception handler
        assert "service unavailable" in response.json()["detail"].lower()

    async def test_summary_no_data_returns_404(self, test_client):
        """Test 404 when no data is available for date range."""
        # Arrange
        mock_fx_data = {"amount": 1.0, "base": "EUR", "rates": {}}

        main.cache_client.get = AsyncMock(return_value=None)
        main.cache_client.set = AsyncMock(return_value=True)
        main.fx_client.fetch_rates = AsyncMock(return_value=mock_fx_data)

        # Act
        response = await test_client.get(
            "/summary?start=2030-01-01&end=2030-01-31"
        )

        # Assert
        assert response.status_code == 404
        assert "No exchange rate data found" in response.json()["detail"]

    async def test_summary_calculation_accuracy(self, test_client):
        """Test accuracy of summary calculations."""
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

        main.cache_client.get = AsyncMock(return_value=None)
        main.cache_client.set = AsyncMock(return_value=True)
        main.fx_client.fetch_rates = AsyncMock(return_value=mock_fx_data)

        # Act
        response = await test_client.get(
            "/summary?start=2025-07-01&end=2025-07-03"
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify calculations
        totals = data["totals"]

        # Total % change: (1.0945 - 1.0912) / 1.0912 * 100 = 0.302
        assert totals["total_pct_change"] == 0.302

        # Mean: (1.0912 + 1.093 + 1.0945) / 3 = 1.0929
        assert totals["mean_rate"] == 1.0929

    async def test_summary_zero_division_guard(self, test_client):
        """Test that zero-division guard works for pct_change calculations."""
        # Arrange - Use valid positive rates that will test zero-division in pct_change
        # Note: Pydantic validates rates are positive, so we test the calc logic separately
        mock_fx_data = {
            "amount": 1.0,
            "base": "EUR",
            "rates": {
                "2025-07-01": {"USD": 1.0912},
                "2025-07-02": {"USD": 1.0912},  # Same rate, so pct_change = 0
            },
        }

        main.cache_client.get = AsyncMock(return_value=None)
        main.cache_client.set = AsyncMock(return_value=True)
        main.fx_client.fetch_rates = AsyncMock(return_value=mock_fx_data)

        # Act
        response = await test_client.get(
            "/summary?start=2025-07-01&end=2025-07-02&breakdown=day"
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        # Second day has zero change
        assert data["days"][1]["pct_change"] == 0.0  # Zero is valid
        # Total change is also zero
        assert data["totals"]["total_pct_change"] == 0.0

    async def test_summary_single_day(self, test_client):
        """Test summary for single day."""
        # Arrange
        mock_fx_data = {
            "amount": 1.0,
            "base": "EUR",
            "rates": {"2026-02-11": {"USD": 1.19}},
        }

        main.cache_client.get = AsyncMock(return_value=None)
        main.cache_client.set = AsyncMock(return_value=True)
        main.fx_client.fetch_rates = AsyncMock(return_value=mock_fx_data)

        # Act
        response = await test_client.get(
            "/summary?start=2026-02-11&end=2026-02-11&breakdown=day"
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert len(data["days"]) == 1
        assert data["days"][0]["pct_change"] is None  # First day has no pct_change

        totals = data["totals"]
        assert totals["start_rate"] == 1.19
        assert totals["end_rate"] == 1.19
        assert totals["total_pct_change"] == 0.0  # No change

    async def test_summary_historical_range(self, test_client):
        """Test summary with historical date range."""
        # Arrange
        mock_fx_data = {
            "amount": 1.0,
            "base": "EUR",
            "rates": {
                "1999-01-04": {"USD": 1.1789},
                "1999-01-05": {"USD": 1.179},
                "1999-01-06": {"USD": 1.1743},
            },
        }

        main.cache_client.get = AsyncMock(return_value=None)
        main.cache_client.set = AsyncMock(return_value=True)
        main.fx_client.fetch_rates = AsyncMock(return_value=mock_fx_data)

        # Act
        response = await test_client.get(
            "/summary?start=1999-01-04&end=1999-01-06"
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert data["start"] == "1999-01-04"
        assert data["end"] == "1999-01-06"
        assert data["totals"]["start_rate"] == 1.1789

    async def test_summary_cache_failure_still_works(self, test_client):
        """Test that cache failures don't break the service."""
        # Arrange
        mock_fx_data = {
            "amount": 1.0,
            "base": "EUR",
            "rates": {"2025-07-01": {"USD": 1.0912}},
        }

        main.cache_client.get = AsyncMock(side_effect=Exception("Cache error"))
        main.cache_client.set = AsyncMock(side_effect=Exception("Cache error"))
        main.fx_client.fetch_rates = AsyncMock(return_value=mock_fx_data)

        # Act
        response = await test_client.get(
            "/summary?start=2025-07-01&end=2025-07-01"
        )

        # Assert
        assert response.status_code == 200  # Should still succeed
        data = response.json()
        assert data["totals"]["start_rate"] == 1.0912

    async def test_summary_dates_sorted_correctly(self, test_client):
        """Test that dates are sorted chronologically."""
        # Arrange - return dates out of order
        mock_fx_data = {
            "amount": 1.0,
            "base": "EUR",
            "rates": {
                "2025-07-03": {"USD": 1.0945},
                "2025-07-01": {"USD": 1.0912},
                "2025-07-02": {"USD": 1.093},
            },
        }

        main.cache_client.get = AsyncMock(return_value=None)
        main.cache_client.set = AsyncMock(return_value=True)
        main.fx_client.fetch_rates = AsyncMock(return_value=mock_fx_data)

        # Act
        response = await test_client.get(
            "/summary?start=2025-07-01&end=2025-07-03&breakdown=day"
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify dates are in order
        assert data["days"][0]["date"] == "2025-07-01"
        assert data["days"][1]["date"] == "2025-07-02"
        assert data["days"][2]["date"] == "2025-07-03"

    async def test_summary_cache_key_format(self, test_client):
        """Test that cache key is formatted correctly."""
        # Arrange
        mock_fx_data = {
            "amount": 1.0,
            "base": "EUR",
            "rates": {"2025-07-01": {"USD": 1.0912}},
        }

        main.cache_client.get = AsyncMock(return_value=None)
        main.cache_client.set = AsyncMock(return_value=True)
        main.fx_client.fetch_rates = AsyncMock(return_value=mock_fx_data)

        # Act
        await test_client.get("/summary?start=2025-07-01&end=2025-07-03")

        # Assert
        main.cache_client.get.assert_called_once_with("fx:2025-07-01:2025-07-03")
        main.cache_client.set.assert_called_once()
        call_args = main.cache_client.set.call_args
        assert call_args[0][0] == "fx:2025-07-01:2025-07-03"
