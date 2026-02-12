'use client';

/**
 * Bar chart displaying percentage changes over time.
 */
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { DayBreakdown } from '@/types/api';
import { formatDate, getBarColor } from '@/lib/utils';

interface RateChartProps {
  days: DayBreakdown[];
}

export function RateChart({ days }: RateChartProps) {
  if (!days || days.length === 0) {
    return null;
  }

  // Transform data for chart
  const chartData = days.map((day) => ({
    date: formatDate(day.date).split(',')[0], // Short date (e.g., "Jan 01")
    pct_change: day.pct_change || 0,
    fullDate: formatDate(day.date),
  }));

  return (
    <div className="w-full h-80">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={chartData}
          margin={{ top: 20, right: 30, left: 20, bottom: 60 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="date"
            angle={-45}
            textAnchor="end"
            height={80}
            tick={{ fontSize: 12 }}
            stroke="#6b7280"
          />
          <YAxis
            label={{
              value: '% Change',
              angle: -90,
              position: 'insideLeft',
              style: { fontSize: 12, fill: '#6b7280' },
            }}
            tick={{ fontSize: 12 }}
            stroke="#6b7280"
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#ffffff',
              border: '1px solid #d1d5db',
              borderRadius: '6px',
              padding: '8px',
            }}
            formatter={(value: number) => [`${value.toFixed(3)}%`, 'Change']}
            labelFormatter={(label, payload) => {
              if (payload && payload[0]) {
                return payload[0].payload.fullDate;
              }
              return label;
            }}
          />
          <Bar dataKey="pct_change" name="% Change">
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={getBarColor(entry.pct_change)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
