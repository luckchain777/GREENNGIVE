"""
Standalone fallback data reader service using FireDucks.pandas.
Runs on port 8002, serves backup FX data from JSON file.
"""
import json
from contextlib import asynccontextmanager
from pathlib import Path

import fireducks.pandas as pd
from fastapi import FastAPI, HTTPException, Query
from loguru import logger
from pydantic import BaseModel

# Global DataFrame
fx_data = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str
    version: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events."""
    global fx_data

    # Startup: Load FX data
    try:
        data_path = Path(__file__).parent / "data" / "sample_fx.json"
        logger.info(f"Loading FX data from {data_path}")

        with open(data_path, "r") as f:
            data = json.load(f)

        # Convert rates dict to list of records
        records = []
        for date_str, rates in data["rates"].items():
            records.append({"date": date_str, "USD": rates["USD"]})

        # Create DataFrame with date index
        fx_data = pd.DataFrame(records)
        fx_data["date"] = pd.to_datetime(fx_data["date"])
        fx_data = fx_data.sort_values("date")

        logger.info(f"Loaded {len(fx_data)} FX records")

    except Exception as e:
        logger.error(f"Failed to load FX data: {e}")
        raise

    yield

    # Shutdown: cleanup if needed
    logger.info("Shutting down fallback reader")


app = FastAPI(
    title="GREENNGIVE Fallback Reader",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="ok", service="fallback-reader", version="1.0.0"
    )


@app.get("/data")
async def get_data(
    start: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end: str = Query(..., description="End date (YYYY-MM-DD)"),
):
    """
    Get FX data for date range.

    Args:
        start: Start date in YYYY-MM-DD format
        end: End date in YYYY-MM-DD format

    Returns:
        Dict matching Frankfurter API format with date range data
    """
    if fx_data is None:
        raise HTTPException(status_code=500, detail="FX data not loaded")

    try:
        # Parse dates
        start_date = pd.to_datetime(start)
        end_date = pd.to_datetime(end)

        # Filter DataFrame by date range
        mask = (fx_data["date"] >= start_date) & (fx_data["date"] <= end_date)
        filtered = fx_data[mask]

        if filtered.empty:
            logger.warning(f"No data found for range {start} to {end}")
            return {"amount": 1.0, "base": "EUR", "rates": {}}

        # Convert to dict format matching Frankfurter API
        rates = {}
        for _, row in filtered.iterrows():
            date_str = row["date"].strftime("%Y-%m-%d")
            rates[date_str] = {"USD": float(row["USD"])}

        logger.info(f"Returning {len(rates)} rates for {start} to {end}")

        return {"amount": 1.0, "base": "EUR", "rates": rates}

    except ValueError as e:
        logger.error(f"Invalid date format: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
    except Exception as e:
        logger.error(f"Error fetching data: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching data: {e}")


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting fallback reader service on port 8002")
    uvicorn.run(app, host="0.0.0.0", port=8002)
