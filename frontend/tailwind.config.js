/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ['class'],
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        fnl: { 400: '#2aa8ff', 500: '#087eff', 600: '#1260e8', 950: '#02091b' },
      },
      fontFamily: { sans: ['Inter', 'Manrope', 'Segoe UI', 'sans-serif'] },
      boxShadow: { neon: '0 0 28px rgba(8,126,255,.28)' },
    },
  },
  plugins: [],
}

