"""
Standalone cache service with LRU + TTL eviction.
Runs on port 8001, shared across all API workers.
"""
import datetime as dt
from collections import OrderedDict
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from loguru import logger
from pydantic import BaseModel, Field

# Configuration
MAX_CACHE_SIZE = 1000
DEFAULT_TTL_SECONDS = 300  # 5 minutes

app = FastAPI(title="GREENNGIVE Cache Service", version="1.0.0")


class CacheSetRequest(BaseModel):
    """Request body for setting cache value."""

    key: str = Field(..., description="Cache key")
    value: Any = Field(..., description="Value to cache")
    ttl: int = Field(DEFAULT_TTL_SECONDS, description="TTL in seconds")


class CacheGetResponse(BaseModel):
    """Response for cache get operation."""

    value: Optional[Any] = Field(None, description="Cached value or None if not found/expired")


class CacheSetResponse(BaseModel):
    """Response for cache set operation."""

    success: bool = Field(..., description="Whether the set operation succeeded")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str
    version: str


class CacheStore:
    """
    LRU + TTL cache implementation using OrderedDict.

    - LRU: Tracks access order, evicts oldest when full
    - TTL: Each entry has expiry timestamp
    """

    def __init__(self, max_size: int = MAX_CACHE_SIZE):
        """Initialize cache store."""
        self._cache: OrderedDict[str, tuple[Any, dt.datetime]] = OrderedDict()
        self._max_size = max_size
        logger.info(f"Initialized cache with max_size={max_size}")

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Returns None if key not found or expired.
        Moves key to end (most recently used) on access.
        """
        if key not in self._cache:
            logger.debug(f"Cache miss: {key}")
            return None

        value, expiry = self._cache[key]

        # Check expiry
        if dt.datetime.now() > expiry:
            logger.debug(f"Cache expired: {key}")
            del self._cache[key]
            return None

        # Move to end (mark as recently used)
        self._cache.move_to_end(key)
        logger.debug(f"Cache hit: {key}")
        return value

    def set(self, key: str, value: Any, ttl: int) -> bool:
        """
        Set value in cache with TTL.

        Evicts oldest entry if cache is full.
        """
        expiry = dt.datetime.now() + dt.timedelta(seconds=ttl)

        # If key exists, remove it first (we'll re-add it at the end)
        if key in self._cache:
            del self._cache[key]

        # Evict oldest entry if cache is full
        if len(self._cache) >= self._max_size:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            logger.debug(f"Evicted oldest entry: {oldest_key}")

        # Add new entry
        self._cache[key] = (value, expiry)
        logger.debug(f"Cache set: {key} (ttl={ttl}s)")
        return True

    def size(self) -> int:
        """Return current cache size."""
        return len(self._cache)


# Global cache instance
cache_store = CacheStore()


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        service="cache-service",
        version="1.0.0"
    )


@app.post("/cache/set", response_model=CacheSetResponse)
async def set_cache(request: CacheSetRequest):
    """
    Set a value in the cache.

    Args:
        request: Cache set request with key, value, and TTL

    Returns:
        Success response
    """
    try:
        success = cache_store.set(request.key, request.value, request.ttl)
        return CacheSetResponse(success=success)
    except Exception as e:
        logger.error(f"Error setting cache: {e}")
        raise HTTPException(status_code=500, detail=f"Cache set failed: {str(e)}")


@app.get("/cache/get/{key}", response_model=CacheGetResponse)
async def get_cache(key: str):
    """
    Get a value from the cache.

    Args:
        key: Cache key to retrieve

    Returns:
        Cached value or None if not found/expired
    """
    try:
        value = cache_store.get(key)
        return CacheGetResponse(value=value)
    except Exception as e:
        logger.error(f"Error getting cache: {e}")
        raise HTTPException(status_code=500, detail=f"Cache get failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting cache service on port 8001")
    uvicorn.run(app, host="0.0.0.0", port=8001)
