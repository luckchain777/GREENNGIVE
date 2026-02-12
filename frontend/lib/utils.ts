/**
 * Utility functions for formatting and trend calculations.
 */
import { format, parseISO } from 'date-fns';

/**
 * Format a date string to human-readable format.
 * @param dateStr - ISO date string (YYYY-MM-DD)
 * @returns Formatted date (e.g., "Jan 01, 2025")
 */
export function formatDate(dateStr: string): string {
  try {
    const date = parseISO(dateStr);
    return format(date, 'MMM dd, yyyy');
  } catch {
    return dateStr;
  }
}

/**
 * Format exchange rate to 4 decimal places.
 * @param rate - Exchange rate number
 * @returns Formatted rate string (e.g., "1.0912")
 */
export function formatRate(rate: number): string {
  return rate.toFixed(4);
}

/**
 * Format percentage change with sign and 3 decimal places.
 * @param pct - Percentage change (can be null)
 * @returns Formatted percentage (e.g., "+0.165%", "-0.123%", "—")
 */
export function formatPercentage(pct: number | null): string {
  if (pct === null) {
    return '—';
  }
  const sign = pct > 0 ? '+' : '';
  return `${sign}${pct.toFixed(3)}%`;
}

/**
 * Determine trend direction from percentage change.
 * @param pct - Percentage change (can be null)
 * @returns Trend direction
 */
export function getTrend(pct: number | null): 'up' | 'down' | 'neutral' {
  if (pct === null || pct === 0) {
    return 'neutral';
  }
  return pct > 0 ? 'up' : 'down';
}

/**
 * Get trend arrow based on percentage change.
 * @param pct - Percentage change (can be null)
 * @returns Arrow character
 */
export function getTrendArrow(pct: number | null): string {
  const trend = getTrend(pct);
  switch (trend) {
    case 'up':
      return '↑';
    case 'down':
      return '↓';
    default:
      return '→';
  }
}

/**
 * Get Tailwind color class based on trend.
 * @param pct - Percentage change (can be null)
 * @returns Tailwind text color class
 */
export function getTrendColor(pct: number | null): string {
  const trend = getTrend(pct);
  switch (trend) {
    case 'up':
      return 'text-trend-up';
    case 'down':
      return 'text-trend-down';
    default:
      return 'text-trend-neutral';
  }
}

/**
 * Get hex color for chart bars based on percentage change.
 * @param pct - Percentage change (can be null)
 * @returns Hex color code
 */
export function getBarColor(pct: number | null): string {
  const trend = getTrend(pct);
  switch (trend) {
    case 'up':
      return '#10b981'; // green-500
    case 'down':
      return '#ef4444'; // red-500
    default:
      return '#6b7280'; // gray-500
  }
}

/**
 * Format a date input string to YYYY-MM-DD format.
 * @param dateStr - Date string from input
 * @returns ISO date string
 */
export function toISODateString(dateStr: string): string {
  return dateStr;
}

/**
 * Get date N days ago from today in YYYY-MM-DD format.
 * @param daysAgo - Number of days to subtract
 * @returns ISO date string
 */
export function getDaysAgo(daysAgo: number): string {
  const date = new Date();
  date.setDate(date.getDate() - daysAgo);
  return date.toISOString().split('T')[0];
}

/**
 * Get today's date in YYYY-MM-DD format.
 * @returns ISO date string
 */
export function getToday(): string {
  return new Date().toISOString().split('T')[0];
}

/**
 * Validate date range.
 * @param start - Start date string
 * @param end - End date string
 * @returns Error message if invalid, null if valid
 */
export function validateDateRange(start: string, end: string): string | null {
  if (!start || !end) {
    return 'Both start and end dates are required';
  }

  const startDate = new Date(start);
  const endDate = new Date(end);

  if (isNaN(startDate.getTime()) || isNaN(endDate.getTime())) {
    return 'Invalid date format';
  }

  if (endDate < startDate) {
    return 'End date must be on or after start date';
  }

  const diffDays = Math.floor((endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24));
  if (diffDays > 90) {
    return 'Date range cannot exceed 90 days';
  }

  return null;
}
