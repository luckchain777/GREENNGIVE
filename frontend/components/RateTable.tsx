/**
 * Table displaying exchange rates with trend indicators.
 */
import { DayBreakdown } from '@/types/api';
import {
  formatDate,
  formatRate,
  formatPercentage,
  getTrendArrow,
  getTrendColor,
} from '@/lib/utils';

interface RateTableProps {
  days: DayBreakdown[];
}

export function RateTable({ days }: RateTableProps) {
  if (!days || days.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No data available for the selected date range.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse">
        <thead>
          <tr className="bg-gray-100 border-b-2 border-gray-300">
            <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">
              Date
            </th>
            <th className="px-4 py-3 text-right text-sm font-semibold text-gray-700">
              Rate (EUR→USD)
            </th>
            <th className="px-4 py-3 text-right text-sm font-semibold text-gray-700">
              % Change
            </th>
            <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700">
              Trend
            </th>
          </tr>
        </thead>
        <tbody>
          {days.map((day, index) => (
            <tr
              key={day.date}
              className={`border-b border-gray-200 hover:bg-gray-50 transition-colors ${
                index % 2 === 0 ? 'bg-white' : 'bg-gray-50'
              }`}
            >
              <td className="px-4 py-3 text-sm text-gray-900">
                {formatDate(day.date)}
              </td>
              <td className="px-4 py-3 text-sm text-right font-mono text-gray-900">
                {formatRate(day.rate)}
              </td>
              <td
                className={`px-4 py-3 text-sm text-right font-mono font-semibold ${getTrendColor(
                  day.pct_change
                )}`}
              >
                {formatPercentage(day.pct_change)}
              </td>
              <td
                className={`px-4 py-3 text-center text-xl font-bold ${getTrendColor(
                  day.pct_change
                )}`}
              >
                {getTrendArrow(day.pct_change)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
