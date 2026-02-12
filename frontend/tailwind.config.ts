import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        'trend-up': '#10b981',    // green-500
        'trend-down': '#ef4444',  // red-500
        'trend-neutral': '#6b7280', // gray-500
      },
    },
  },
  plugins: [],
};
export default config;
