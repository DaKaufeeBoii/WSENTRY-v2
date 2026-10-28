/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#09090B",
        surface: "#18181B",
        surface2: "#1f1f24",
        surface3: "#26262b",
        edge: "#27272A",
        edgesoft: "#1f1f23",
        ink: "#FAFAFA",
        muted: "#A1A1AA",
        faint: "#71717A",
        accent: "#22D3EE",
        model: {
          rf: "#a78bfa",
          xgb: "#f59e0b",
          hybrid: "#22D3EE",
          dann: "#f472b6",
        },
        threat: {
          normal: "#34d399",
          jamming: "#a78bfa",
          spoofing: "#f59e0b",
          dos: "#f87171",
          intrusion: "#fbbf24",
        },
        good: "#34d399",
        warn: "#fbbf24",
        bad: "#f87171",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
        mono: ["ui-monospace", "SF Mono", "JetBrains Mono", "Consolas", "monospace"],
      },
      boxShadow: {
        glow: "0 0 12px 1px rgba(34,211,238,0.25)",
      },
      keyframes: {
        pulsedot: { "0%,100%": { opacity: "1" }, "50%": { opacity: "0.35" } },
        slidein: { from: { opacity: "0", transform: "translateY(-4px)" }, to: { opacity: "1", transform: "translateY(0)" } },
      },
      animation: {
        pulsedot: "pulsedot 1.6s ease-in-out infinite",
        slidein: "slidein 0.25s ease-out",
      },
    },
  },
  plugins: [],
};
