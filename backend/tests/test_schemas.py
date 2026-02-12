"""
Tests for Pydantic schemas.
"""
from datetime import date, datetime

import pytest
from pydantic import ValidationError

from backend.models.schemas import (
    BreakdownEnum,
    CacheEntry,
    DayBreakdown,
    FrankfurterRateResponse,
    HealthResponse,
    SummaryResponse,
    Totals,
)


class TestBreakdownEnum:
    """Tests for BreakdownEnum."""

    def test_valid_day_value(self):
        """Test valid 'day' enum value."""
        # Arrange & Act
        breakdown = BreakdownEnum.DAY

        # Assert
        assert breakdown == "day"
        assert breakdown.value == "day"

    def test_enum_from_string(self):
        """Test creating enum from string."""
        # Arrange & Act
        breakdown = BreakdownEnum("day")

        # Assert
        assert breakdown == BreakdownEnum.DAY


class TestHealthResponse:
    """Tests for HealthResponse schema."""

    def test_valid_health_response(self):
        """Test creating valid health response."""
        # Arrange & Act
        response = HealthResponse(
            status="ok", service="fx-pattern", version="1.0.0"
        )

        # Assert
        assert response.status == "ok"
        assert response.service == "fx-pattern"
        assert response.version == "1.0.0"

    def test_health_response_serialization(self):
        """Test health response serializes to dict."""
        # Arrange
        response = HealthResponse(
            status="ok", service="fx-pattern", version="1.0.0"
        )

        # Act
        data = response.model_dump()

        # Assert
        assert data == {
            "status": "ok",
            "service": "fx-pattern",
            "version": "1.0.0",
        }

    def test_missing_field_raises_error(self):
        """Test missing required field raises validation error."""
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            HealthResponse(status="ok", service="fx-pattern")

        assert "version" in str(exc_info.value)


class TestDayBreakdown:
    """Tests for DayBreakdown schema."""

    def test_valid_day_breakdown(self):
        """Test creating valid day breakdown."""
        # Arrange & Act
        breakdown = DayBreakdown(
            date=date(2025, 7, 1), rate=1.0912, pct_change=0.165
        )

        # Assert
        assert breakdown.date == date(2025, 7, 1)
        assert breakdown.rate == 1.0912
        assert breakdown.pct_change == 0.165

    def test_day_breakdown_with_none_pct_change(self):
        """Test day breakdown with None pct_change (first day)."""
        # Arrange & Act
        breakdown = DayBreakdown(
            date=date(2025, 7, 1), rate=1.0912, pct_change=None
        )

        # Assert
        assert breakdown.pct_change is None

    def test_negative_rate_raises_error(self):
        """Test negative rate raises validation error."""
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            DayBreakdown(date=date(2025, 7, 1), rate=-1.0912, pct_change=None)

        assert "Rate must be positive" in str(exc_info.value)

    def test_zero_rate_raises_error(self):
        """Test zero rate raises validation error."""
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            DayBreakdown(date=date(2025, 7, 1), rate=0.0, pct_change=None)

        assert "Rate must be positive" in str(exc_info.value)

    def test_date_as_string_converts(self):
        """Test date string converts to date object."""
        # Arrange & Act
        breakdown = DayBreakdown(
            date="2025-07-01", rate=1.0912, pct_change=None
        )

        # Assert
        assert breakdown.date == date(2025, 7, 1)
        assert isinstance(breakdown.date, date)


class TestTotals:
    """Tests for Totals schema."""

    def test_valid_totals(self):
        """Test creating valid totals."""
        # Arrange & Act
        totals = Totals(
            start_rate=1.0912,
            end_rate=1.0945,
            total_pct_change=0.302,
            mean_rate=1.0929,
        )

        # Assert
        assert totals.start_rate == 1.0912
        assert totals.end_rate == 1.0945
        assert totals.total_pct_change == 0.302
        assert totals.mean_rate == 1.0929

    def test_totals_with_none_pct_change(self):
        """Test totals with None total_pct_change (zero division guard)."""
        # Arrange & Act
        totals = Totals(
            start_rate=1.0912,
            end_rate=1.0945,
            total_pct_change=None,
            mean_rate=1.0929,
        )

        # Assert
        assert totals.total_pct_change is None

    def test_negative_start_rate_raises_error(self):
        """Test negative start_rate raises validation error."""
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            Totals(
                start_rate=-1.0912,
                end_rate=1.0945,
                total_pct_change=0.302,
                mean_rate=1.0929,
            )

        assert "Rates must be positive" in str(exc_info.value)

    def test_zero_mean_rate_raises_error(self):
        """Test zero mean_rate raises validation error."""
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            Totals(
                start_rate=1.0912,
                end_rate=1.0945,
                total_pct_change=0.302,
                mean_rate=0.0,
            )

        assert "Rates must be positive" in str(exc_info.value)


class TestSummaryResponse:
    """Tests for SummaryResponse schema."""

    def test_summary_without_breakdown(self):
        """Test summary response without daily breakdown."""
        # Arrange
        totals = Totals(
            start_rate=1.0912,
            end_rate=1.0945,
            total_pct_change=0.302,
            mean_rate=1.0929,
        )

        # Act
        summary = SummaryResponse(
            start=date(2025, 7, 1), end=date(2025, 7, 3), totals=totals
        )

        # Assert
        assert summary.start == date(2025, 7, 1)
        assert summary.end == date(2025, 7, 3)
        assert summary.days is None
        assert summary.totals == totals

    def test_summary_with_breakdown(self):
        """Test summary response with daily breakdown."""
        # Arrange
        days = [
            DayBreakdown(date=date(2025, 7, 1), rate=1.0912, pct_change=None),
            DayBreakdown(date=date(2025, 7, 2), rate=1.093, pct_change=0.165),
            DayBreakdown(date=date(2025, 7, 3), rate=1.0945, pct_change=0.137),
        ]
        totals = Totals(
            start_rate=1.0912,
            end_rate=1.0945,
            total_pct_change=0.302,
            mean_rate=1.0929,
        )

        # Act
        summary = SummaryResponse(
            start=date(2025, 7, 1),
            end=date(2025, 7, 3),
            days=days,
            totals=totals,
        )

        # Assert
        assert summary.days == days
        assert len(summary.days) == 3

    def test_end_before_start_raises_error(self):
        """Test end date before start date raises validation error."""
        # Arrange
        totals = Totals(
            start_rate=1.0912,
            end_rate=1.0945,
            total_pct_change=0.302,
            mean_rate=1.0929,
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            SummaryResponse(
                start=date(2025, 7, 3), end=date(2025, 7, 1), totals=totals
            )

        assert "End date must not be before start date" in str(exc_info.value)

    def test_same_start_and_end_date_allowed(self):
        """Test same start and end date is allowed."""
        # Arrange
        totals = Totals(
            start_rate=1.0912,
            end_rate=1.0912,
            total_pct_change=0.0,
            mean_rate=1.0912,
        )

        # Act
        summary = SummaryResponse(
            start=date(2025, 7, 1), end=date(2025, 7, 1), totals=totals
        )

        # Assert
        assert summary.start == summary.end

    def test_summary_serialization(self):
        """Test summary response serializes correctly."""
        # Arrange
        totals = Totals(
            start_rate=1.0912,
            end_rate=1.0945,
            total_pct_change=0.302,
            mean_rate=1.0929,
        )
        summary = SummaryResponse(
            start=date(2025, 7, 1), end=date(2025, 7, 3), totals=totals
        )

        # Act
        data = summary.model_dump()

        # Assert
        assert data["start"] == date(2025, 7, 1)
        assert data["end"] == date(2025, 7, 3)
        assert data["days"] is None
        assert data["totals"]["start_rate"] == 1.0912


class TestFrankfurterRateResponse:
    """Tests for FrankfurterRateResponse schema."""

    def test_valid_frankfurter_response(self):
        """Test creating valid Frankfurter API response."""
        # Arrange & Act
        response = FrankfurterRateResponse(
            amount=1.0,
            base="EUR",
            rates={
                "2025-07-01": {"USD": 1.0912},
                "2025-07-02": {"USD": 1.093},
                "2025-07-03": {"USD": 1.0945},
            },
        )

        # Assert
        assert response.amount == 1.0
        assert response.base == "EUR"
        assert len(response.rates) == 3
        assert response.rates["2025-07-01"]["USD"] == 1.0912

    def test_frankfurter_response_with_single_date(self):
        """Test Frankfurter response with single date."""
        # Arrange & Act
        response = FrankfurterRateResponse(
            amount=1.0, base="EUR", rates={"2026-02-11": {"USD": 1.19}}
        )

        # Assert
        assert len(response.rates) == 1

    def test_empty_rates_allowed(self):
        """Test empty rates dict is allowed."""
        # Arrange & Act
        response = FrankfurterRateResponse(amount=1.0, base="EUR", rates={})

        # Assert
        assert response.rates == {}


class TestCacheEntry:
    """Tests for CacheEntry schema."""

    def test_cache_entry_with_dict_value(self):
        """Test cache entry with dict value."""
        # Arrange
        value = {"rate": 1.0912, "date": "2025-07-01"}
        expiry = datetime(2025, 7, 1, 12, 0, 0)

        # Act
        entry = CacheEntry(value=value, expiry=expiry)

        # Assert
        assert entry.value == value
        assert entry.expiry == expiry

    def test_cache_entry_with_string_value(self):
        """Test cache entry with string value."""
        # Arrange
        value = "cached_string"
        expiry = datetime(2025, 7, 1, 12, 0, 0)

        # Act
        entry = CacheEntry(value=value, expiry=expiry)

        # Assert
        assert entry.value == "cached_string"

    def test_cache_entry_with_list_value(self):
        """Test cache entry with list value."""
        # Arrange
        value = [1, 2, 3, 4, 5]
        expiry = datetime(2025, 7, 1, 12, 0, 0)

        # Act
        entry = CacheEntry(value=value, expiry=expiry)

        # Assert
        assert entry.value == [1, 2, 3, 4, 5]

    def test_cache_entry_serialization(self):
        """Test cache entry serializes correctly."""
        # Arrange
        value = {"test": "data"}
        expiry = datetime(2025, 7, 1, 12, 0, 0)
        entry = CacheEntry(value=value, expiry=expiry)

        # Act
        data = entry.model_dump()

        # Assert
        assert data["value"] == {"test": "data"}
        assert data["expiry"] == expiry
