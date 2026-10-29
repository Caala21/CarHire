/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#17231e",
        muted: "#6d7972",
        accent: "#147a55",
        "accent-dark": "#0d6243",
        canvas: "#f8faf8",
        line: "#e7ece8",
      },
      boxShadow: {
        card: "0 16px 45px rgba(27, 46, 36, 0.08)",
        soft: "0 6px 24px rgba(27, 46, 36, 0.06)",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
