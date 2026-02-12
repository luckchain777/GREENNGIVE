"""
Pure calculation functions for FX rate analysis.
All functions include zero-division guards.
"""
from typing import Optional


def calculate_pct_change(current: float, previous: float) -> Optional[float]:
    """
    Calculate percentage change between two values.

    Args:
        current: Current value
        previous: Previous value

    Returns:
        Percentage change rounded to 3 decimal places, or None if previous is zero
    """
    if previous == 0:
        return None

    return round(((current - previous) / previous) * 100, 3)


def calculate_total_pct_change(start_rate: float, end_rate: float) -> Optional[float]:
    """
    Calculate total percentage change from start to end rate.

    Args:
        start_rate: Starting exchange rate
        end_rate: Ending exchange rate

    Returns:
        Total percentage change rounded to 3 decimal places, or None if start_rate is zero
    """
    if start_rate == 0:
        return None

    return round(((end_rate - start_rate) / start_rate) * 100, 3)


def calculate_mean_rate(rates: list[float]) -> float:
    """
    Calculate mean (average) of a list of rates.

    Args:
        rates: List of exchange rates

    Returns:
        Mean rate rounded to 4 decimal places

    Raises:
        ValueError: If rates list is empty
    """
    if not rates:
        raise ValueError("Cannot calculate mean of empty list")

    return round(sum(rates) / len(rates), 4)
