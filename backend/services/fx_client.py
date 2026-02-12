"""
FX client for fetching exchange rates from Frankfurter API with retry logic.
"""
from typing import Optional

import httpx
from loguru import logger
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# Configuration
FRANKFURTER_BASE_URL = "https://api.frankfurter.dev/v1"
REQUEST_TIMEOUT = 5.0  # seconds


class FXClientError(Exception):
    """Exception raised when FX client fails after all retries."""

    pass


class FXClient:
    """
    Async HTTP client for Frankfurter API with automatic retry.

    Retries on:
    - Network errors (ConnectError, TimeoutException)
    - HTTP 5xx errors
    - Other HTTP errors

    Retry strategy:
    - 3 attempts total
    - Exponential backoff: 0.2s, 0.4s, 0.8s
    """

    def __init__(
        self,
        base_url: str = FRANKFURTER_BASE_URL,
        timeout: float = REQUEST_TIMEOUT,
    ):
        """
        Initialize FX client.

        Args:
            base_url: Base URL for Frankfurter API
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

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.2, min=0.2, max=0.8),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.HTTPStatusError)),
        reraise=True,
    )
    async def _fetch_with_retry(self, url: str) -> httpx.Response:
        """
        Internal method to fetch with automatic retry.

        Args:
            url: URL path to fetch (relative to base_url)

        Returns:
            HTTP response

        Raises:
            httpx.HTTPError: On network/timeout errors
            httpx.HTTPStatusError: On HTTP error status codes
        """
        if not self._client:
            raise RuntimeError("FXClient must be used as async context manager")

        logger.debug(f"Fetching: {url}")
        response = await self._client.get(url)
        response.raise_for_status()
        return response

    async def fetch_rates(
        self, start: str, end: str, fallback_url: Optional[str] = None
    ) -> dict:
        """
        Fetch exchange rates for date range.

        Args:
            start: Start date (YYYY-MM-DD)
            end: End date (YYYY-MM-DD)
            fallback_url: Optional fallback service URL

        Returns:
            Dict with rates in format:
            {
                "amount": 1.0,
                "base": "EUR",
                "rates": {
                    "2025-07-01": {"USD": 1.0912},
                    ...
                }
            }

        Raises:
            FXClientError: If fetch fails after retries and no fallback available
        """
        url = f"/{start}..{end}?base=EUR&symbols=USD"

        try:
            response = await self._fetch_with_retry(url)
            data = response.json()

            logger.info(
                f"Successfully fetched rates for {start} to {end} "
                f"({len(data.get('rates', {}))} days)"
            )

            return data

        except (httpx.HTTPError, httpx.HTTPStatusError) as e:
            logger.warning(
                f"Frankfurter API failed after retries: {e}. "
                f"Attempting fallback if available."
            )

            # Try fallback if provided
            if fallback_url:
                try:
                    return await self._fetch_from_fallback(
                        fallback_url, start, end
                    )
                except Exception as fallback_error:
                    logger.error(f"Fallback also failed: {fallback_error}")
                    raise FXClientError(
                        "Both primary and fallback services failed"
                    ) from e

            raise FXClientError(
                f"Failed to fetch rates from Frankfurter API: {e}"
            ) from e

    async def _fetch_from_fallback(
        self, fallback_url: str, start: str, end: str
    ) -> dict:
        """
        Fetch rates from fallback service.

        Args:
            fallback_url: Fallback service base URL
            start: Start date (YYYY-MM-DD)
            end: End date (YYYY-MM-DD)

        Returns:
            Dict with rates data

        Raises:
            httpx.HTTPError: On network/HTTP errors
        """
        if not self._client:
            raise RuntimeError("FXClient must be used as async context manager")

        url = f"{fallback_url}/data?start={start}&end={end}"
        logger.info(f"Fetching from fallback: {url}")

        response = await self._client.get(url)
        response.raise_for_status()
        data = response.json()

        logger.info(
            f"Fallback fetch successful: {len(data.get('rates', {}))} days"
        )

        return data
