'use client';

/**
 * Date range input form with validation.
 */
import { useState, FormEvent } from 'react';
import { validateDateRange, getDaysAgo, getToday } from '@/lib/utils';

interface DateRangeFormProps {
  onSubmit: (start: string, end: string) => void;
  initialStart?: string;
  initialEnd?: string;
}

export function DateRangeForm({
  onSubmit,
  initialStart = getDaysAgo(7),
  initialEnd = getToday(),
}: DateRangeFormProps) {
  const [start, setStart] = useState(initialStart);
  const [end, setEnd] = useState(initialEnd);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    const validationError = validateDateRange(start, end);
    if (validationError) {
      setError(validationError);
      return;
    }

    setError(null);
    onSubmit(start, end);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label
            htmlFor="start-date"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            Start Date
          </label>
          <input
            id="start-date"
            type="date"
            value={start}
            onChange={(e) => setStart(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            required
          />
        </div>
        <div>
          <label
            htmlFor="end-date"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            End Date
          </label>
          <input
            id="end-date"
            type="date"
            value={end}
            onChange={(e) => setEnd(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            required
          />
        </div>
      </div>

      {error && (
        <div className="text-red-600 text-sm font-medium">
          {error}
        </div>
      )}

      <button
        type="submit"
        className="w-full md:w-auto px-6 py-2 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors"
      >
        Get Exchange Rates
      </button>
    </form>
  );
}
