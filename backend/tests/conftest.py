"""
Shared pytest fixtures for all tests.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, Request, Response

from backend.main import app


@pytest_asyncio.fixture
async def async_client():
    """Create async test client for FastAPI app."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_fx_response():
    """Create a mock Frankfurter API response."""
    return {
        "amount": 1.0,
        "base": "EUR",
        "start_date": "2025-07-01",
        "end_date": "2025-07-03",
        "rates": {
            "2025-07-01": {"USD": 1.0912},
            "2025-07-02": {"USD": 1.093},
            "2025-07-03": {"USD": 1.0945},
        },
    }


@pytest.fixture
def mock_cache_service(mocker):
    """Mock cache service responses."""

    class MockCacheClient:
        """Mock cache client."""

        def __init__(self):
            self.storage = {}

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        async def get(self, key: str):
            """Mock get from cache."""
            return self.storage.get(key)

        async def set(self, key: str, value, ttl: int = 300):
            """Mock set to cache."""
            self.storage[key] = value
            return True

    return MockCacheClient()


@pytest.fixture
def mock_fx_client_success(mocker, mock_fx_response):
    """Mock successful FX client."""

    class MockFXClient:
        """Mock FX client that always succeeds."""

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        async def fetch_rates(self, start, end, fallback_url=None):
            """Mock fetch rates."""
            return mock_fx_response

    return MockFXClient()


@pytest.fixture
def mock_fx_client_failure(mocker):
    """Mock failing FX client."""
    from backend.services.fx_client import FXClientError

    class MockFXClient:
        """Mock FX client that always fails."""

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        async def fetch_rates(self, start, end, fallback_url=None):
            """Mock fetch rates that fails."""
            raise FXClientError("Mock FX client failure")

    return MockFXClient()


@pytest.fixture
def mock_fallback_service():
    """Mock fallback service response."""
    return {
        "amount": 1.0,
        "base": "EUR",
        "rates": {
            "2025-07-01": {"USD": 1.0912},
            "2025-07-02": {"USD": 1.093},
            "2025-07-03": {"USD": 1.0945},
        },
    }
