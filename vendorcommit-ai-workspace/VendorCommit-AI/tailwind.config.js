/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: { sans: ['Inter', 'sans-serif'] },
      colors: {
        navy: { 950: '#101d35', 900: '#15243e', 800: '#1d304e' },
        brand: { 50: '#eff6ff', 100: '#dbeafe', 500: '#2878f0', 600: '#1768df', 700: '#1557bd' },
      },
      boxShadow: {
        card: '0 1px 2px rgba(16,24,40,.025), 0 1px 4px rgba(16,24,40,.035)',
        float: '0 12px 36px rgba(15,23,42,.12)',
      },
    },
  },
  plugins: [],
};
