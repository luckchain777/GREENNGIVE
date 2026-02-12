"""
Tests for fallback reader service.
"""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.fallback_reader import app


@pytest.fixture(scope="module")
def client():
    """Create test client for FastAPI app."""
    # Trigger startup event to load data
    with TestClient(app) as c:
        yield c


class TestFallbackReader:
    """Tests for fallback reader service."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        # Act
        response = client.get("/health")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "fallback-reader"
        assert data["version"] == "1.0.0"

    def test_data_file_exists(self):
        """Test that sample FX data file exists."""
        # Arrange
        data_path = Path(__file__).parent.parent / "data" / "sample_fx.json"

        # Assert
        assert data_path.exists()
        assert data_path.is_file()

    def test_data_file_valid_json(self):
        """Test that data file is valid JSON."""
        # Arrange
        data_path = Path(__file__).parent.parent / "data" / "sample_fx.json"

        # Act
        with open(data_path, "r") as f:
            data = json.load(f)

        # Assert
        assert "amount" in data
        assert "base" in data
        assert "rates" in data
        assert data["base"] == "EUR"
        assert isinstance(data["rates"], dict)

    def test_get_data_single_day(self, client):
        """Test getting data for a single day."""
        # Act
        response = client.get("/data?start=2025-07-01&end=2025-07-01")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["amount"] == 1.0
        assert data["base"] == "EUR"
        assert "2025-07-01" in data["rates"]
        assert data["rates"]["2025-07-01"]["USD"] == 1.0912

    def test_get_data_date_range(self, client):
        """Test getting data for a date range."""
        # Act
        response = client.get("/data?start=2025-07-01&end=2025-07-03")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["rates"]) == 3
        assert "2025-07-01" in data["rates"]
        assert "2025-07-02" in data["rates"]
        assert "2025-07-03" in data["rates"]
        assert data["rates"]["2025-07-01"]["USD"] == 1.0912
        assert data["rates"]["2025-07-02"]["USD"] == 1.093
        assert data["rates"]["2025-07-03"]["USD"] == 1.0945

    def test_get_data_historical_range(self, client):
        """Test getting historical data from 1999."""
        # Act
        response = client.get("/data?start=1999-01-04&end=1999-01-08")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["rates"]) == 5
        assert "1999-01-04" in data["rates"]
        assert "1999-01-08" in data["rates"]
        assert data["rates"]["1999-01-04"]["USD"] == 1.1789

    def test_get_data_recent_range(self, client):
        """Test getting recent data from 2026."""
        # Act
        response = client.get("/data?start=2026-02-10&end=2026-02-11")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["rates"]) == 2
        assert "2026-02-10" in data["rates"]
        assert "2026-02-11" in data["rates"]
        assert data["rates"]["2026-02-11"]["USD"] == 1.19

    def test_get_data_with_gaps(self, client):
        """Test date range with gaps (weekends/holidays not in data)."""
        # Act - request range that includes dates not in our sample
        response = client.get("/data?start=2025-07-01&end=2025-07-05")

        # Assert
        assert response.status_code == 200
        data = response.json()
        # Should return only dates that exist in the data
        assert len(data["rates"]) == 5  # 07-01 through 07-05 are all in our data

    def test_get_data_no_results(self, client):
        """Test date range with no data."""
        # Act - request a date range not in our data
        response = client.get("/data?start=2030-01-01&end=2030-01-31")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["rates"] == {}

    def test_get_data_invalid_start_date(self, client):
        """Test invalid start date format."""
        # Act
        response = client.get("/data?start=invalid&end=2025-07-03")

        # Assert
        assert response.status_code == 400
        assert "Invalid date format" in response.json()["detail"]

    def test_get_data_invalid_end_date(self, client):
        """Test invalid end date format."""
        # Act
        response = client.get("/data?start=2025-07-01&end=invalid")

        # Assert
        assert response.status_code == 400
        assert "Invalid date format" in response.json()["detail"]

    def test_get_data_missing_start_param(self, client):
        """Test missing start parameter."""
        # Act
        response = client.get("/data?end=2025-07-03")

        # Assert
        assert response.status_code == 422  # Unprocessable Entity

    def test_get_data_missing_end_param(self, client):
        """Test missing end parameter."""
        # Act
        response = client.get("/data?start=2025-07-01")

        # Assert
        assert response.status_code == 422  # Unprocessable Entity

    def test_get_data_cross_decade_range(self, client):
        """Test date range spanning multiple decades."""
        # Act - range from 1999 to 2026
        response = client.get("/data?start=1999-01-04&end=2026-02-11")

        # Assert
        assert response.status_code == 200
        data = response.json()
        # Should return all dates in our sample
        assert len(data["rates"]) > 30  # We have data points across the range
        assert "1999-01-04" in data["rates"]
        assert "2026-02-11" in data["rates"]

    def test_get_data_response_format(self, client):
        """Test response format matches Frankfurter API."""
        # Act
        response = client.get("/data?start=2025-07-01&end=2025-07-03")

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Check structure
        assert "amount" in data
        assert "base" in data
        assert "rates" in data

        # Check types
        assert isinstance(data["amount"], (int, float))
        assert isinstance(data["base"], str)
        assert isinstance(data["rates"], dict)

        # Check rates structure
        for date_str, rates in data["rates"].items():
            assert isinstance(date_str, str)
            assert isinstance(rates, dict)
            assert "USD" in rates
            assert isinstance(rates["USD"], (int, float))

    def test_get_data_dates_sorted(self, client):
        """Test that returned dates are in chronological order."""
        # Act
        response = client.get("/data?start=2025-07-01&end=2025-07-05")

        # Assert
        assert response.status_code == 200
        data = response.json()

        dates = list(data["rates"].keys())
        sorted_dates = sorted(dates)
        assert dates == sorted_dates

    def test_get_data_reverse_range(self, client):
        """Test end date before start date returns empty results."""
        # Act - end before start
        response = client.get("/data?start=2025-07-05&end=2025-07-01")

        # Assert
        assert response.status_code == 200
        data = response.json()
        # Should return empty since end < start
        assert data["rates"] == {}
