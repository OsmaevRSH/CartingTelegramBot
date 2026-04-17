/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: '#0A0A0A',
        card: '#141414',
        border: '#222222',
        accent: '#00FF7F',
        orange: '#FF6B00',
        primary: '#FFFFFF',
        secondary: '#888888',
        error: '#FF4444',
      },
      fontFamily: {
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      },
    },
  },
  plugins: [],
}
