/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        'primary': '#38bdf8',
        'background-dark': '#0d1117',
        'surface': '#161b22',
        'border-color': '#30363d',
        'text-primary': '#e6edf3',
        'text-secondary': '#7d8590',
      },
      fontFamily: {
        'display': ['Inter', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
