"""
Tests for FX client with retry logic.
"""
import pytest
import pytest_asyncio
from httpx import HTTPError, HTTPStatusError, Request, Response

from backend.services.fx_client import FXClient, FXClientError


@pytest_asyncio.fixture
async def fx_client():
    """Create FX client for testing."""
    async with FXClient() as client:
        yield client


@pytest.mark.asyncio
class TestFXClient:
    """Tests for FXClient."""

    async def test_fetch_rates_success(self, fx_client, mocker):
        """Test successful fetch from Frankfurter API."""
        # Arrange
        mock_response = Response(
            200,
            json={
                "amount": 1.0,
                "base": "EUR",
                "start_date": "2025-07-01",
                "end_date": "2025-07-03",
                "rates": {
                    "2025-07-01": {"USD": 1.0912},
                    "2025-07-02": {"USD": 1.093},
                    "2025-07-03": {"USD": 1.0945},
                },
            },
            request=Request(
                "GET",
                "https://api.frankfurter.dev/v1/2025-07-01..2025-07-03?base=EUR&symbols=USD",
            ),
        )
        mocker.patch.object(fx_client._client, "get", return_value=mock_response)

        # Act
        result = await fx_client.fetch_rates("2025-07-01", "2025-07-03")

        # Assert
        assert result["amount"] == 1.0
        assert result["base"] == "EUR"
        assert len(result["rates"]) == 3
        assert result["rates"]["2025-07-01"]["USD"] == 1.0912

    async def test_fetch_rates_single_day(self, fx_client, mocker):
        """Test fetching rates for a single day."""
        # Arrange
        mock_response = Response(
            200,
            json={
                "amount": 1.0,
                "base": "EUR",
                "rates": {"2026-02-11": {"USD": 1.19}},
            },
            request=Request(
                "GET",
                "https://api.frankfurter.dev/v1/2026-02-11..2026-02-11?base=EUR&symbols=USD",
            ),
        )
        mocker.patch.object(fx_client._client, "get", return_value=mock_response)

        # Act
        result = await fx_client.fetch_rates("2026-02-11", "2026-02-11")

        # Assert
        assert len(result["rates"]) == 1
        assert result["rates"]["2026-02-11"]["USD"] == 1.19

    async def test_fetch_rates_http_error_retries(self, fx_client, mocker):
        """Test that HTTP errors trigger retries."""
        # Arrange
        call_count = 0

        def mock_get_with_retries(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise HTTPError("Network error")
            # Success on 3rd attempt
            return Response(
                200,
                json={
                    "amount": 1.0,
                    "base": "EUR",
                    "rates": {"2025-07-01": {"USD": 1.0912}},
                },
                request=Request(
                    "GET",
                    "https://api.frankfurter.dev/v1/2025-07-01..2025-07-01?base=EUR&symbols=USD",
                ),
            )

        mocker.patch.object(
            fx_client._client, "get", side_effect=mock_get_with_retries
        )

        # Act
        result = await fx_client.fetch_rates("2025-07-01", "2025-07-01")

        # Assert
        assert call_count == 3  # Should have tried 3 times
        assert result["rates"]["2025-07-01"]["USD"] == 1.0912

    async def test_fetch_rates_fails_after_max_retries(self, fx_client, mocker):
        """Test failure after exhausting retries."""
        # Arrange
        mocker.patch.object(
            fx_client._client, "get", side_effect=HTTPError("Network error")
        )

        # Act & Assert
        with pytest.raises(FXClientError, match="Failed to fetch rates"):
            await fx_client.fetch_rates("2025-07-01", "2025-07-03")

    async def test_fetch_rates_fallback_on_failure(self, fx_client, mocker):
        """Test fallback is used when primary fails."""
        # Arrange
        call_count = 0

        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            # First call (primary) fails
            if "frankfurter" in str(args) or call_count <= 3:
                raise HTTPError("Primary service error")

            # Subsequent calls (fallback) succeed
            return Response(
                200,
                json={
                    "amount": 1.0,
                    "base": "EUR",
                    "rates": {"2025-07-01": {"USD": 1.0912}},
                },
                request=Request("GET", "http://localhost:8002/data"),
            )

        mocker.patch.object(fx_client._client, "get", side_effect=mock_get)

        # Act
        result = await fx_client.fetch_rates(
            "2025-07-01", "2025-07-01", fallback_url="http://localhost:8002"
        )

        # Assert
        assert result["rates"]["2025-07-01"]["USD"] == 1.0912

    async def test_fetch_rates_fallback_also_fails(self, fx_client, mocker):
        """Test error when both primary and fallback fail."""
        # Arrange
        mocker.patch.object(
            fx_client._client, "get", side_effect=HTTPError("Both services down")
        )

        # Act & Assert
        with pytest.raises(
            FXClientError, match="Both primary and fallback services failed"
        ):
            await fx_client.fetch_rates(
                "2025-07-01", "2025-07-03", fallback_url="http://localhost:8002"
            )

    async def test_fetch_rates_5xx_error_retries(self, fx_client, mocker):
        """Test that 5xx errors trigger retries."""
        # Arrange
        call_count = 0

        def mock_get_with_5xx(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                response = Response(
                    500,
                    json={"error": "Internal server error"},
                    request=Request("GET", "http://test"),
                )
                raise HTTPStatusError(
                    "Server error", request=response.request, response=response
                )
            # Success on 3rd attempt
            return Response(
                200,
                json={
                    "amount": 1.0,
                    "base": "EUR",
                    "rates": {"2025-07-01": {"USD": 1.0912}},
                },
                request=Request("GET", "http://test"),
            )

        mocker.patch.object(
            fx_client._client, "get", side_effect=mock_get_with_5xx
        )

        # Act
        result = await fx_client.fetch_rates("2025-07-01", "2025-07-01")

        # Assert
        assert call_count == 3
        assert result["rates"]["2025-07-01"]["USD"] == 1.0912

    async def test_context_manager_usage(self):
        """Test FX client as async context manager."""
        # Act
        async with FXClient() as client:
            # Assert
            assert client._client is not None

        # After exit, client should be closed
        assert client._client is None

    async def test_fetch_without_context_manager_raises_error(self):
        """Test fetch without context manager raises error."""
        # Arrange
        client = FXClient()

        # Act & Assert
        with pytest.raises(RuntimeError, match="must be used as async context manager"):
            await client.fetch_rates("2025-07-01", "2025-07-03")

    async def test_fetch_rates_url_format(self, fx_client, mocker):
        """Test that URL is formatted correctly."""
        # Arrange
        mock_get = mocker.patch.object(
            fx_client._client,
            "get",
            return_value=Response(
                200,
                json={"amount": 1.0, "base": "EUR", "rates": {}},
                request=Request("GET", "http://test"),
            ),
        )

        # Act
        await fx_client.fetch_rates("2025-07-01", "2025-07-03")

        # Assert
        mock_get.assert_called_once_with(
            "/2025-07-01..2025-07-03?base=EUR&symbols=USD"
        )

    async def test_fetch_rates_empty_response(self, fx_client, mocker):
        """Test handling of empty rates response."""
        # Arrange
        mock_response = Response(
            200,
            json={"amount": 1.0, "base": "EUR", "rates": {}},
            request=Request("GET", "http://test"),
        )
        mocker.patch.object(fx_client._client, "get", return_value=mock_response)

        # Act
        result = await fx_client.fetch_rates("2030-01-01", "2030-01-31")

        # Assert
        assert result["rates"] == {}

    async def test_fallback_url_format(self, fx_client, mocker):
        """Test fallback URL is formatted correctly."""
        # Arrange
        call_count = 0

        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            # First 3 calls fail (primary with retries)
            if call_count <= 3:
                raise HTTPError("Primary failed")

            # 4th call succeeds (fallback)
            return Response(
                200,
                json={"amount": 1.0, "base": "EUR", "rates": {}},
                request=Request("GET", "http://test"),
            )

        mock_get_spy = mocker.patch.object(
            fx_client._client, "get", side_effect=mock_get
        )

        # Act
        await fx_client.fetch_rates(
            "2025-07-01", "2025-07-03", fallback_url="http://localhost:8002"
        )

        # Assert - last call should be to fallback
        last_call = mock_get_spy.call_args_list[-1]
        assert "localhost:8002" in str(last_call)
        assert "start=2025-07-01" in str(last_call)
        assert "end=2025-07-03" in str(last_call)

    async def test_historical_date_range(self, fx_client, mocker):
        """Test fetching historical date range."""
        # Arrange
        mock_response = Response(
            200,
            json={
                "amount": 1.0,
                "base": "EUR",
                "rates": {
                    "1999-01-04": {"USD": 1.1789},
                    "1999-01-05": {"USD": 1.179},
                },
            },
            request=Request("GET", "http://test"),
        )
        mocker.patch.object(fx_client._client, "get", return_value=mock_response)

        # Act
        result = await fx_client.fetch_rates("1999-01-04", "1999-01-05")

        # Assert
        assert len(result["rates"]) == 2
        assert result["rates"]["1999-01-04"]["USD"] == 1.1789
