/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Cimas Healthathon 3.0 — innovations.cimas.co.zw/healthathon
        brand: {
          50: '#e8f1fb',
          100: '#c5d9f5',
          200: '#9ec0ee',
          300: '#6fa3e6',
          400: '#498de0',
          500: '#0056A3',
          600: '#004d94',
          700: '#003f7a',
          800: '#003163',
          900: '#0B2E4E',
        },
        teal: {
          400: '#2dd4bf',
          500: '#00A99D',
          600: '#00897b',
        },
        sky: {
          400: '#49A5E6',
          500: '#3b97dc',
        },
        cimas: {
          dark: '#0a0f1a',
        },
      },
      fontFamily: {
        sans: ['Inter', 'Segoe UI', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        card: '0 1px 3px rgba(0,0,0,.06), 0 4px 16px rgba(0,86,163,.08)',
        modal: '0 20px 60px rgba(0,0,0,.18)',
      },
    },
  },
  plugins: [],
}
