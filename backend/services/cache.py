"""
Cache client for communicating with the cache service.
"""
from typing import Any, Optional

import httpx
from loguru import logger

# Cache service configuration
CACHE_SERVICE_URL = "http://localhost:8001"
DEFAULT_TTL = 300  # 5 minutes


class CacheClient:
    """
    HTTP client wrapper for cache service.

    Uses httpx.AsyncClient with connection pooling for efficient requests.
    """

    def __init__(
        self,
        base_url: str = CACHE_SERVICE_URL,
        timeout: float = 5.0,
    ):
        """
        Initialize cache client.

        Args:
            base_url: Base URL of cache service
            timeout: Request timeout in seconds
        """
        self._base_url = base_url
        self._timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def get(self, key: str) -> Optional[dict]:
        """
        Get value from cache.

        Args:
            key: Cache key to retrieve

        Returns:
            Cached value as dict, or None if not found/expired/error
        """
        if not self._client:
            raise RuntimeError("CacheClient must be used as async context manager")

        try:
            response = await self._client.get(f"/cache/get/{key}")
            response.raise_for_status()

            data = response.json()
            value = data.get("value")

            if value is None:
                logger.debug(f"Cache miss for key: {key}")
            else:
                logger.debug(f"Cache hit for key: {key}")

            return value

        except httpx.HTTPError as e:
            logger.warning(f"Cache get failed for key {key}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting cache for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int = DEFAULT_TTL) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache (must be JSON-serializable)
            ttl: Time-to-live in seconds

        Returns:
            True if successful, False otherwise
        """
        if not self._client:
            raise RuntimeError("CacheClient must be used as async context manager")

        try:
            payload = {"key": key, "value": value, "ttl": ttl}
            response = await self._client.post("/cache/set", json=payload)
            response.raise_for_status()

            data = response.json()
            success = data.get("success", False)

            if success:
                logger.debug(f"Cache set successful for key: {key}")
            else:
                logger.warning(f"Cache set failed for key: {key}")

            return success

        except httpx.HTTPError as e:
            logger.warning(f"Cache set failed for key {key}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error setting cache for key {key}: {e}")
            return False
