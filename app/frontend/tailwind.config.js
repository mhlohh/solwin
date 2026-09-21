/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        card: "var(--card)",
        elevated: "var(--elevated)",
        inset: "var(--inset)",
        line: "var(--border)",
        "line-strong": "var(--border-strong)",
        "text-1": "var(--text-1)",
        "text-2": "var(--text-2)",
        "text-3": "var(--text-3)",
        accent: "var(--accent)",
        "accent-weak": "var(--accent-weak)",
        "accent-line": "var(--accent-border)",
        ok: "var(--ok)",
        "ok-weak": "var(--ok-weak)",
        "ok-line": "var(--ok-border)",
        warn: "var(--warn)",
        "warn-weak": "var(--warn-weak)",
        "warn-line": "var(--warn-border)",
        danger: "var(--danger)",
        "danger-weak": "var(--danger-weak)",
        "danger-line": "var(--danger-border)",
      },
      fontFamily: {
        sans: ['"Inter"', "-apple-system", "BlinkMacSystemFont", "sans-serif"],
        mono: [
          '"SF Mono"',
          '"JetBrains Mono"',
          "ui-monospace",
          "monospace",
        ],
      },
      boxShadow: {
        1: "var(--shadow-1)",
        2: "var(--shadow-2)",
      },
    },
  },
  plugins: [],
};
