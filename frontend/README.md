# GREENNGIVE Frontend

React + Next.js frontend for visualizing EUR/USD exchange rate data.

## Tech Stack

- **Next.js 14** with App Router
- **React 18** with TypeScript
- **Tanstack Query** for server state management
- **Tailwind CSS** for styling
- **Recharts** for data visualization
- **Axios** for HTTP requests

## Prerequisites

- Node.js 18+ and npm
- Backend API running on http://localhost:8000
- Backend must have CORS configured for http://localhost:3000

## Installation

```bash
npm install
```

## Development

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Build

```bash
npm run build
npm start
```

## Environment Variables

Create a `.env.local` file:

```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

## Features

- **Date Range Selection**: Pick start and end dates (max 90 days)
- **Summary Statistics**: Start rate, end rate, total change, mean rate
- **Daily Breakdown Table**: Rate, percentage change, and trend arrows (↑ ↓ →)
- **Interactive Chart**: Bar chart showing percentage changes (green/red/gray)
- **JSON Display**: Formatted API response with copy-to-clipboard
- **Error Handling**: User-friendly error messages with retry
- **Loading States**: Spinner during data fetching
- **Responsive Design**: Mobile, tablet, and desktop layouts

## API Integration

The frontend connects to the backend API:

- `GET /summary?start=YYYY-MM-DD&end=YYYY-MM-DD&breakdown=day`
- `GET /health`

Data is cached for 5 minutes to match backend TTL.

## Project Structure

```
frontend/
├── app/                    # Next.js app directory
│   ├── layout.tsx         # Root layout with providers
│   ├── page.tsx           # Main summary page
│   ├── globals.css        # Global styles
│   └── providers.tsx      # React Query provider
├── components/            # React components
│   ├── DateRangeForm.tsx  # Date input form
│   ├── RateTable.tsx      # Exchange rate table
│   ├── RateChart.tsx      # Percentage change chart
│   ├── JsonDisplay.tsx    # JSON viewer
│   └── LoadingSpinner.tsx # Loading indicator
├── lib/                   # Utilities and hooks
│   ├── api.ts            # Axios client
│   ├── queries.ts        # Tanstack Query hooks
│   └── utils.ts          # Formatting helpers
└── types/                # TypeScript definitions
    └── api.ts            # API response types
```

## Development Notes

- TypeScript strict mode enabled
- ESLint configured with Next.js rules
- Date validation on client-side
- Match backend cache TTL (5 minutes)
- Clean, simple UI per SPEC.md §14
