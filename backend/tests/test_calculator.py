"""
Tests for calculator module - pure calculation functions.
Target: 100% coverage
"""
import pytest
from backend.services.calculator import (
    calculate_pct_change,
    calculate_total_pct_change,
    calculate_mean_rate,
)


class TestCalculatePctChange:
    """Tests for calculate_pct_change function."""

    def test_positive_change(self):
        """Test positive percentage change."""
        # Arrange
        current = 1.093
        previous = 1.0912

        # Act
        result = calculate_pct_change(current, previous)

        # Assert
        assert result == 0.165

    def test_negative_change(self):
        """Test negative percentage change."""
        # Arrange
        current = 1.0912
        previous = 1.1

        # Act
        result = calculate_pct_change(current, previous)

        # Assert
        assert result == -0.800

    def test_no_change(self):
        """Test zero percentage change."""
        # Arrange
        current = 1.0912
        previous = 1.0912

        # Act
        result = calculate_pct_change(current, previous)

        # Assert
        assert result == 0.0

    def test_zero_previous_returns_none(self):
        """Test zero-division guard returns None."""
        # Arrange
        current = 1.0912
        previous = 0.0

        # Act
        result = calculate_pct_change(current, previous)

        # Assert
        assert result is None

    def test_rounding_to_three_decimals(self):
        """Test result is rounded to 3 decimal places."""
        # Arrange
        current = 1.09451234
        previous = 1.09300000

        # Act
        result = calculate_pct_change(current, previous)

        # Assert
        assert result == 0.138
        assert isinstance(result, float)


class TestCalculateTotalPctChange:
    """Tests for calculate_total_pct_change function."""

    def test_positive_total_change(self):
        """Test positive total percentage change."""
        # Arrange
        start_rate = 1.0912
        end_rate = 1.0945

        # Act
        result = calculate_total_pct_change(start_rate, end_rate)

        # Assert
        assert result == 0.302

    def test_negative_total_change(self):
        """Test negative total percentage change."""
        # Arrange
        start_rate = 1.1
        end_rate = 1.0912

        # Act
        result = calculate_total_pct_change(start_rate, end_rate)

        # Assert
        assert result == -0.800

    def test_no_total_change(self):
        """Test zero total percentage change."""
        # Arrange
        start_rate = 1.0912
        end_rate = 1.0912

        # Act
        result = calculate_total_pct_change(start_rate, end_rate)

        # Assert
        assert result == 0.0

    def test_zero_start_rate_returns_none(self):
        """Test zero-division guard returns None."""
        # Arrange
        start_rate = 0.0
        end_rate = 1.0912

        # Act
        result = calculate_total_pct_change(start_rate, end_rate)

        # Assert
        assert result is None

    def test_large_change(self):
        """Test large percentage change."""
        # Arrange
        start_rate = 1.0
        end_rate = 2.0

        # Act
        result = calculate_total_pct_change(start_rate, end_rate)

        # Assert
        assert result == 100.0


class TestCalculateMeanRate:
    """Tests for calculate_mean_rate function."""

    def test_mean_of_multiple_rates(self):
        """Test calculating mean of multiple rates."""
        # Arrange
        rates = [1.0912, 1.093, 1.0945]

        # Act
        result = calculate_mean_rate(rates)

        # Assert
        assert result == 1.0929

    def test_mean_of_single_rate(self):
        """Test calculating mean of single rate."""
        # Arrange
        rates = [1.0912]

        # Act
        result = calculate_mean_rate(rates)

        # Assert
        assert result == 1.0912

    def test_mean_of_two_rates(self):
        """Test calculating mean of two rates."""
        # Arrange
        rates = [1.0, 2.0]

        # Act
        result = calculate_mean_rate(rates)

        # Assert
        assert result == 1.5

    def test_empty_list_raises_error(self):
        """Test empty list raises ValueError."""
        # Arrange
        rates = []

        # Act & Assert
        with pytest.raises(ValueError, match="Cannot calculate mean of empty list"):
            calculate_mean_rate(rates)

    def test_rounding_to_four_decimals(self):
        """Test result is rounded to 4 decimal places."""
        # Arrange
        rates = [1.091234567, 1.093456789, 1.094567890]

        # Act
        result = calculate_mean_rate(rates)

        # Assert
        # Mean should be (1.091234567 + 1.093456789 + 1.094567890) / 3 = 1.093086415...
        assert result == 1.0931
        assert isinstance(result, float)

    def test_mean_with_many_rates(self):
        """Test calculating mean with many rates."""
        # Arrange
        rates = [1.0 + i * 0.01 for i in range(10)]  # [1.0, 1.01, 1.02, ..., 1.09]

        # Act
        result = calculate_mean_rate(rates)

        # Assert
        assert result == 1.045
