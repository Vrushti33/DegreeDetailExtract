/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        charcoal: {
          DEFAULT: '#14161C',
          light: '#1B1E27',
        },
        parchment: {
          DEFAULT: '#F7F2E4',
          dark: '#EDE5D0',
        },
        brass: {
          DEFAULT: '#B98B2A',
          bright: '#D6A43E',
          muted: '#8A6A20',
        },
        maroon: '#7A2E2E',
        sage: '#4C7A5D',
      },
      fontFamily: {
        display: ['"Fraunces"', 'Georgia', 'serif'],
        body: ['"Inter"', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
