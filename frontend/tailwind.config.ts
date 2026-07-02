/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        jarvis: {
          bg: "#0a0e14",
          panel: "#11161f",
          accent: "#3ddbd9",
          accentDim: "#1f8a89",
          text: "#e6edf3",
          muted: "#7d8590",
        },
      },
    },
  },
  plugins: [],
};
