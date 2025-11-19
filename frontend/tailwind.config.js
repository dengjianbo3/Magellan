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
        'background-dark': '#0b0f19', // Deep space blue
        'surface': '#111827',         // Dark blue-grey
        'surface-light': '#1f2937',   // Lighter blue-grey for hover/active
        'surface-lighter': '#374151', 
        'primary': '#38bdf8',         // Sky blue (Tech)
        'primary-dark': '#0284c7',    // Darker sky blue
        'secondary': '#64748b',       // Slate
        'accent-cyan': '#06b6d4',     // Cyan
        'accent-violet': '#8b5cf6',   // Violet
        'border-color': 'rgba(255, 255, 255, 0.1)', // Subtle white border
        'text-primary': '#f3f4f6',    // Cool white
        'text-secondary': '#9ca3af',  // Cool grey
        'text-tertiary': '#6b7280',   // Darker grey
      },
      fontFamily: {
        'display': ['Inter', 'system-ui', 'sans-serif'],
        'mono': ['JetBrains Mono', 'monospace'],
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'tech-grid': "url(\"data:image/svg+xml,%3Csvg width='40' height='40' viewBox='0 0 40 40' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M0 0h40v40H0V0zm1 1h38v38H1V1z' fill='%2338bdf8' fill-opacity='0.03'/%3E%3C/svg%3E\")",
      },
      boxShadow: {
        'glow': '0 0 20px rgba(56, 189, 248, 0.15)',
        'glow-sm': '0 0 10px rgba(56, 189, 248, 0.1)',
      },
    },
  },
  plugins: [],
}
