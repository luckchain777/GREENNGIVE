/**
 * Tanstack Query hooks for API data fetching.
 */
import { useQuery } from '@tanstack/react-query';
import { apiClient } from './api';
import type { SummaryResponse, HealthResponse, BreakdownType } from '@/types/api';

/**
 * Parameters for useSummary hook.
 */
interface UseSummaryParams {
  /** Start date (YYYY-MM-DD) */
  start: string;
  /** End date (YYYY-MM-DD) */
  end: string;
  /** Breakdown type (default: 'day') */
  breakdown?: BreakdownType;
}

/**
 * Hook to fetch exchange rate summary data.
 * Automatically enabled when both start and end dates are provided.
 * Matches backend cache TTL with 5-minute stale time.
 */
export function useSummary({ start, end, breakdown = 'day' }: UseSummaryParams) {
  return useQuery<SummaryResponse>({
    queryKey: ['summary', start, end, breakdown],
    queryFn: async () => {
      const params = new URLSearchParams({
        start,
        end,
        breakdown,
      });
      const response = await apiClient.get<SummaryResponse>(
        `/summary?${params.toString()}`
      );
      return response.data;
    },
    enabled: Boolean(start && end),
    staleTime: 5 * 60 * 1000, // 5 minutes (matches backend cache)
  });
}

/**
 * Hook to fetch health check status.
 */
export function useHealth() {
  return useQuery<HealthResponse>({
    queryKey: ['health'],
    queryFn: async () => {
      const response = await apiClient.get<HealthResponse>('/health');
      return response.data;
    },
    staleTime: 1 * 60 * 1000, // 1 minute
  });
}
