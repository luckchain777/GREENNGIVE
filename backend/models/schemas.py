"""
Pydantic models for request/response schemas and data validation.
"""
import datetime as dt
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class BreakdownEnum(str, Enum):
    """Valid breakdown types for summary endpoint."""

    DAY = "day"


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str = Field(..., description="Service health status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")


class DayBreakdown(BaseModel):
    """Daily FX rate breakdown."""

    date: dt.date = Field(..., description="Date of the rate")
    rate: float = Field(..., description="EUR→USD exchange rate")
    pct_change: Optional[float] = Field(
        None, description="Percentage change from previous day (None for first day)"
    )

    @field_validator("rate")
    @classmethod
    def rate_must_be_positive(cls, v: float) -> float:
        """Validate that rate is positive."""
        if v <= 0:
            raise ValueError("Rate must be positive")
        return v


class Totals(BaseModel):
    """Summary totals for FX rate period."""

    start_rate: float = Field(..., description="Exchange rate at start date")
    end_rate: float = Field(..., description="Exchange rate at end date")
    total_pct_change: Optional[float] = Field(
        ..., description="Total percentage change from start to end (None if zero division)"
    )
    mean_rate: float = Field(..., description="Mean exchange rate over period")

    @field_validator("start_rate", "end_rate", "mean_rate")
    @classmethod
    def rates_must_be_positive(cls, v: float) -> float:
        """Validate that rates are positive."""
        if v <= 0:
            raise ValueError("Rates must be positive")
        return v


class SummaryResponse(BaseModel):
    """Summary response with optional daily breakdown."""

    start: dt.date = Field(..., description="Start date of the period")
    end: dt.date = Field(..., description="End date of the period")
    days: Optional[list[DayBreakdown]] = Field(
        None, description="Daily breakdown (only if breakdown=day)"
    )
    totals: Totals = Field(..., description="Summary totals for the period")

    @model_validator(mode='after')
    def validate_date_range(self) -> 'SummaryResponse':
        """Validate that end date is not before start date."""
        if self.end < self.start:
            raise ValueError("End date must not be before start date")
        return self


class FrankfurterRateResponse(BaseModel):
    """Response from Frankfurter API for date range queries."""

    amount: float = Field(..., description="Base amount (typically 1.0)")
    base: str = Field(..., description="Base currency code (EUR)")
    rates: dict[str, dict[str, float]] = Field(
        ..., description="Nested dict: {date: {currency: rate}}"
    )


class CacheEntry(BaseModel):
    """Cache entry with value and expiry timestamp."""

    value: Any = Field(..., description="Cached value (can be any type)")
    expiry: dt.datetime = Field(..., description="Expiry timestamp for TTL")

    model_config = ConfigDict(arbitrary_types_allowed=True)
