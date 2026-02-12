"""
Factory functions for creating test data.
"""
import datetime as dt
from typing import Optional

from backend.models.schemas import DayBreakdown, SummaryResponse, Totals


def create_fx_response(
    start: str = "2025-07-01",
    end: str = "2025-07-03",
    rates: Optional[dict] = None,
) -> dict:
    """
    Create a mock Frankfurter API response.

    Args:
        start: Start date string
        end: End date string
        rates: Optional dict of rates (date -> {"USD": rate})

    Returns:
        Dict matching Frankfurter API format
    """
    if rates is None:
        rates = {
            "2025-07-01": {"USD": 1.0912},
            "2025-07-02": {"USD": 1.093},
            "2025-07-03": {"USD": 1.0945},
        }

    return {
        "amount": 1.0,
        "base": "EUR",
        "start_date": start,
        "end_date": end,
        "rates": rates,
    }


def create_summary_response(
    start: str = "2025-07-01",
    end: str = "2025-07-03",
    with_breakdown: bool = False,
) -> SummaryResponse:
    """
    Create a summary response for testing.

    Args:
        start: Start date string
        end: End date string
        with_breakdown: Whether to include daily breakdown

    Returns:
        SummaryResponse instance
    """
    start_date = dt.date.fromisoformat(start)
    end_date = dt.date.fromisoformat(end)

    totals = Totals(
        start_rate=1.0912,
        end_rate=1.0945,
        total_pct_change=0.302,
        mean_rate=1.0929,
    )

    days = None
    if with_breakdown:
        days = [
            DayBreakdown(date=start_date, rate=1.0912, pct_change=None),
            DayBreakdown(
                date=start_date + dt.timedelta(days=1),
                rate=1.093,
                pct_change=0.165,
            ),
            DayBreakdown(
                date=end_date,
                rate=1.0945,
                pct_change=0.137,
            ),
        ]

    return SummaryResponse(start=start_date, end=end_date, days=days, totals=totals)


def create_day_breakdown(
    date_str: str = "2025-07-01",
    rate: float = 1.0912,
    pct_change: Optional[float] = None,
) -> DayBreakdown:
    """
    Create a single day breakdown for testing.

    Args:
        date_str: Date string (YYYY-MM-DD)
        rate: Exchange rate
        pct_change: Optional percentage change

    Returns:
        DayBreakdown instance
    """
    return DayBreakdown(
        date=dt.date.fromisoformat(date_str), rate=rate, pct_change=pct_change
    )


def create_totals(
    start_rate: float = 1.0912,
    end_rate: float = 1.0945,
    total_pct_change: Optional[float] = 0.302,
    mean_rate: float = 1.0929,
) -> Totals:
    """
    Create totals for testing.

    Args:
        start_rate: Starting rate
        end_rate: Ending rate
        total_pct_change: Total percentage change (None for zero-division case)
        mean_rate: Mean rate

    Returns:
        Totals instance
    """
    return Totals(
        start_rate=start_rate,
        end_rate=end_rate,
        total_pct_change=total_pct_change,
        mean_rate=mean_rate,
    )
