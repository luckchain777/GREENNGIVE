'use client';

/**
 * JSON display component with copy-to-clipboard functionality.
 */
import { useState } from 'react';
import { SummaryResponse } from '@/types/api';

interface JsonDisplayProps {
  data: SummaryResponse;
}

export function JsonDisplay({ data }: JsonDisplayProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(data, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy:', error);
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold text-gray-900">JSON Response</h3>
        <button
          onClick={handleCopy}
          className="px-3 py-1 text-sm bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-gray-400"
        >
          {copied ? '✓ Copied!' : 'Copy'}
        </button>
      </div>
      <textarea
        readOnly
        value={JSON.stringify(data, null, 2)}
        className="w-full h-64 p-4 font-mono text-xs bg-gray-50 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
      />
    </div>
  );
}
