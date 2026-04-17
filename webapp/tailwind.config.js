/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Kinetic Precision design system
        "surface-lowest": "#0e0e0e",
        "surface-low": "#1c1b1b",
        "surface-mid": "#201f1f",
        "surface-high": "#2a2a2a",
        "surface-highest": "#353534",
        "surface-dim": "#131313",
        "primary": "#ffb4a8",
        "primary-container": "#ff5540",
        "on-surface": "#e5e2e1",
        "on-surface-var": "#ebbbb4",
        "secondary-container": "#454747",
        // Semantic
        bg: '#131313',
        card: '#0e0e0e',
        accent: '#ff5540',
        error: '#FF4444',
      },
      borderRadius: {
        DEFAULT: "0px",
        sm: "0px",
        md: "0px",
        lg: "0px",
        xl: "0px",
        "2xl": "0px",
        "3xl": "0px",
        full: "9999px",
      },
      fontFamily: {
        sans: ["Space Grotesk", "system-ui", "sans-serif"],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      },
    },
  },
  plugins: [],
}
