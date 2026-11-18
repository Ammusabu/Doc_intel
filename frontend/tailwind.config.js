/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  "#EEF0FF",
          100: "#E0E2FF",
          400: "#8B80FF",
          500: "#6255ED",
          600: "#5145D8",
          700: "#4038B8",
          900: "#2A2670",
        },
        surface: {
          bg: "#070B19",
          sidebar: "#10192B",
          card: "#111B2E",
          border: "#26334A",
        },
      },
    },
  },
  plugins: [],
}
