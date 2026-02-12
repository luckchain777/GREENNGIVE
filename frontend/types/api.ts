/**
 * TypeScript types matching backend Pydantic schemas.
 * Backend: backend/models/schemas.py
 */

/**
 * Valid breakdown types for summary endpoint.
 */
export type BreakdownType = 'day';

/**
 * Health check response schema.
 */
export interface HealthResponse {
  status: string;
  service: string;
  version: string;
}

/**
 * Daily FX rate breakdown.
 * Matches backend DayBreakdown model.
 */
export interface DayBreakdown {
  /** Date of the rate (YYYY-MM-DD format) */
  date: string;
  /** EUR→USD exchange rate */
  rate: number;
  /** Percentage change from previous day (null for first day) */
  pct_change: number | null;
}

/**
 * Summary totals for FX rate period.
 * Matches backend Totals model.
 */
export interface Totals {
  /** Exchange rate at start date */
  start_rate: number;
  /** Exchange rate at end date */
  end_rate: number;
  /** Total percentage change from start to end (null if zero division) */
  total_pct_change: number | null;
  /** Mean exchange rate over period */
  mean_rate: number;
}

/**
 * Summary response with optional daily breakdown.
 * Matches backend SummaryResponse model.
 */
export interface SummaryResponse {
  /** Start date of the period (YYYY-MM-DD format) */
  start: string;
  /** End date of the period (YYYY-MM-DD format) */
  end: string;
  /** Daily breakdown (only if breakdown=day) */
  days?: DayBreakdown[];
  /** Summary totals for the period */
  totals: Totals;
}

/**
 * API error response.
 */
export interface ApiError {
  detail: string;
}
