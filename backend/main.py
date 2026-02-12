"""
GREENNGIVE - Main FastAPI application for FX rate summaries.
Orchestrates cache service, FX client, and fallback service.
"""
import datetime as dt
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from backend.models.schemas import (
    BreakdownEnum,
    DayBreakdown,
    HealthResponse,
    SummaryResponse,
    Totals,
)
from backend.services.cache import CacheClient
from backend.services.calculator import (
    calculate_mean_rate,
    calculate_pct_change,
    calculate_total_pct_change,
)
from backend.services.fx_client import FXClient, FXClientError

# Configuration
CACHE_SERVICE_URL = "http://localhost:8001"
FALLBACK_SERVICE_URL = "http://localhost:8002"
CACHE_TTL = 300  # 5 minutes
MAX_DATE_RANGE_DAYS = 90  # 3 months (configurable)

# Global clients
fx_client: Optional[FXClient] = None
cache_client: Optional[CacheClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    global fx_client, cache_client

    # Startup
    logger.info("Starting GREENNGIVE FX service")
    fx_client = FXClient()
    await fx_client.__aenter__()

    cache_client = CacheClient(base_url=CACHE_SERVICE_URL)
    await cache_client.__aenter__()

    logger.info("All services initialized")

    yield

    # Shutdown
    logger.info("Shutting down GREENNGIVE FX service")

    if fx_client:
        await fx_client.__aexit__(None, None, None)

    if cache_client:
        await cache_client.__aexit__(None, None, None)

    logger.info("Shutdown complete")


app = FastAPI(
    title="GREENNGIVE FX Service",
    version="1.0.0",
    description="EUR→USD exchange rate service with caching and fallback",
    lifespan=lifespan,
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(400)
async def bad_request_handler(request, exc):
    """Handle 400 Bad Request errors."""
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )


@app.exception_handler(502)
async def bad_gateway_handler(request, exc):
    """Handle 502 Bad Gateway errors."""
    return JSONResponse(
        status_code=502,
        content={"detail": "Upstream service unavailable"},
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Handle 500 Internal Server errors."""
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.

    Returns:
        Service health status
    """
    return HealthResponse(
        status="ok",
        service="fx-pattern",
        version="1.0.0",
    )


@app.get("/summary", response_model=SummaryResponse)
async def get_summary(
    start: str = Query(..., description="Start date (YYYY-MM-DD)", pattern=r"^\d{4}-\d{2}-\d{2}$"),
    end: str = Query(..., description="End date (YYYY-MM-DD)", pattern=r"^\d{4}-\d{2}-\d{2}$"),
    breakdown: Optional[BreakdownEnum] = Query(None, description="Include daily breakdown"),
):
    """
    Get FX rate summary for date range.

    Args:
        start: Start date (YYYY-MM-DD)
        end: End date (YYYY-MM-DD)
        breakdown: Optional "day" for daily breakdown

    Returns:
        Summary with totals and optional daily breakdown

    Raises:
        HTTPException: 400 for invalid dates, 502 for service unavailable, 500 for other errors
    """
    # Validate dates
    try:
        start_date = dt.date.fromisoformat(start)
        end_date = dt.date.fromisoformat(end)

        if end_date < start_date:
            raise HTTPException(
                status_code=400,
                detail="End date must not be before start date",
            )

        # Validate date range duration
        date_range_days = (end_date - start_date).days
        if date_range_days > MAX_DATE_RANGE_DAYS:
            raise HTTPException(
                status_code=400,
                detail=f"Date range exceeds maximum allowed duration of {MAX_DATE_RANGE_DAYS} days (approximately 3 months). "
                f"Requested range: {date_range_days} days",
            )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date format: {e}",
        )

    # Check cache
    cache_key = f"fx:{start}:{end}"
    cached_data = None

    if cache_client:
        try:
            cached_data = await cache_client.get(cache_key)
            if cached_data:
                logger.info(f"Cache hit for {cache_key}")
        except Exception as e:
            logger.warning(f"Cache get failed: {e}")

    # Fetch rates if not cached
    if not cached_data:
        logger.info(f"Cache miss for {cache_key}, fetching from API")

        try:
            # Fetch from Frankfurter API with fallback
            rates_data = await fx_client.fetch_rates(
                start, end, fallback_url=FALLBACK_SERVICE_URL
            )

            # Cache the result
            if cache_client and rates_data:
                try:
                    await cache_client.set(cache_key, rates_data, ttl=CACHE_TTL)
                except Exception as e:
                    logger.warning(f"Cache set failed: {e}")

            cached_data = rates_data

        except FXClientError as e:
            logger.error(f"FX client error: {e}")
            raise HTTPException(
                status_code=502,
                detail="Failed to fetch exchange rates from upstream services",
            )
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise HTTPException(
                status_code=500,
                detail="Internal server error",
            )

    # Process rates data
    if not cached_data or not cached_data.get("rates"):
        raise HTTPException(
            status_code=404,
            detail=f"No exchange rate data found for {start} to {end}",
        )

    rates_dict = cached_data["rates"]

    # Sort dates
    sorted_dates = sorted(rates_dict.keys())

    if not sorted_dates:
        raise HTTPException(
            status_code=404,
            detail=f"No exchange rate data found for {start} to {end}",
        )

    # Extract rates
    rates = [rates_dict[date]["USD"] for date in sorted_dates]

    # Calculate totals
    start_rate = rates[0]
    end_rate = rates[-1]
    total_pct_change = calculate_total_pct_change(start_rate, end_rate)
    mean_rate = calculate_mean_rate(rates)

    totals = Totals(
        start_rate=start_rate,
        end_rate=end_rate,
        total_pct_change=total_pct_change,
        mean_rate=mean_rate,
    )

    # Calculate daily breakdown if requested
    days = None
    if breakdown == BreakdownEnum.DAY:
        days = []
        prev_rate = None

        for date_str in sorted_dates:
            rate = rates_dict[date_str]["USD"]
            pct_change = None

            if prev_rate is not None:
                pct_change = calculate_pct_change(rate, prev_rate)

            days.append(
                DayBreakdown(
                    date=dt.date.fromisoformat(date_str),
                    rate=rate,
                    pct_change=pct_change,
                )
            )

            prev_rate = rate

    return SummaryResponse(
        start=start_date,
        end=end_date,
        days=days,
        totals=totals,
    )


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting main FX service on port 8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
