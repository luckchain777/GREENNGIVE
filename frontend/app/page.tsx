'use client';

/**
 * Main page displaying EUR/USD exchange rate summary.
 */
import { useState } from 'react';
import { useSummary } from '@/lib/queries';
import { getDaysAgo, getToday } from '@/lib/utils';
import { DateRangeForm } from '@/components/DateRangeForm';
import { RateTable } from '@/components/RateTable';
import { RateChart } from '@/components/RateChart';
import { JsonDisplay } from '@/components/JsonDisplay';
import { LoadingSpinner } from '@/components/LoadingSpinner';

export default function Home() {
  const [dateRange, setDateRange] = useState({
    start: getDaysAgo(7),
    end: getToday(),
  });

  const { data, isLoading, isError, error, refetch } = useSummary({
    start: dateRange.start,
    end: dateRange.end,
    breakdown: 'day',
  });

  const handleDateSubmit = (start: string, end: string) => {
    setDateRange({ start, end });
  };

  return (
    <main className="min-h-screen py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            GREENNGIVE Exchange Rates
          </h1>
          <p className="text-gray-600">
            EUR to USD exchange rate summary with daily breakdown
          </p>
        </div>

        {/* Date Range Form */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Select Date Range
          </h2>
          <DateRangeForm
            onSubmit={handleDateSubmit}
            initialStart={dateRange.start}
            initialEnd={dateRange.end}
          />
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="bg-white rounded-lg shadow-md p-6">
            <LoadingSpinner />
          </div>
        )}

        {/* Error State */}
        {isError && (
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="text-center">
              <div className="text-red-600 text-lg font-semibold mb-2">
                Error Loading Data
              </div>
              <p className="text-gray-600 mb-4">
                {error instanceof Error
                  ? error.message
                  : 'Failed to fetch exchange rate data. Please try again.'}
              </p>
              <button
                onClick={() => refetch()}
                className="px-4 py-2 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700 transition-colors"
              >
                Retry
              </button>
            </div>
          </div>
        )}

        {/* Success State - Display Data */}
        {data && (
          <>
            {/* Summary Statistics */}
            <div className="bg-white rounded-lg shadow-md p-6 mb-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">
                Summary Statistics
              </h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <div className="text-sm text-gray-500 mb-1">Start Rate</div>
                  <div className="text-xl font-semibold text-gray-900 font-mono">
                    {data.totals.start_rate.toFixed(4)}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-500 mb-1">End Rate</div>
                  <div className="text-xl font-semibold text-gray-900 font-mono">
                    {data.totals.end_rate.toFixed(4)}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-500 mb-1">Total Change</div>
                  <div
                    className={`text-xl font-semibold font-mono ${
                      data.totals.total_pct_change === null
                        ? 'text-gray-500'
                        : data.totals.total_pct_change > 0
                        ? 'text-trend-up'
                        : data.totals.total_pct_change < 0
                        ? 'text-trend-down'
                        : 'text-gray-500'
                    }`}
                  >
                    {data.totals.total_pct_change === null
                      ? '—'
                      : `${data.totals.total_pct_change > 0 ? '+' : ''}${data.totals.total_pct_change.toFixed(3)}%`}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-500 mb-1">Mean Rate</div>
                  <div className="text-xl font-semibold text-gray-900 font-mono">
                    {data.totals.mean_rate.toFixed(4)}
                  </div>
                </div>
              </div>
            </div>

            {/* Rate Table */}
            {data.days && data.days.length > 0 && (
              <div className="bg-white rounded-lg shadow-md p-6 mb-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-4">
                  Daily Breakdown
                </h2>
                <RateTable days={data.days} />
              </div>
            )}

            {/* Rate Chart */}
            {data.days && data.days.length > 0 && (
              <div className="bg-white rounded-lg shadow-md p-6 mb-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-4">
                  Percentage Change Chart
                </h2>
                <RateChart days={data.days} />
              </div>
            )}

            {/* JSON Display */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <JsonDisplay data={data} />
            </div>
          </>
        )}
      </div>
    </main>
  );
}
