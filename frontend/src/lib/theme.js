// Shared color tokens and encoding helpers (mirrors the obsidian HTML results doc).

export const C = {
  bg: "#09090B",
  surface: "#18181B",
  surface2: "#1f1f24",
  border: "#27272A",
  grid: "#27272A",
  axis: "#3f3f46",
  ink: "#FAFAFA",
  muted: "#A1A1AA",
  faint: "#71717A",
  accent: "#22D3EE",
  good: "#34d399",
  warn: "#fbbf24",
  bad: "#f87171",
};

// Model series colors (match tailwind `model.*`).
export const MODEL = {
  rf: "#a78bfa",
  xgb: "#f59e0b",
  hybrid: "#22D3EE",
  dann: "#f472b6",
};

// Per-threat-class presentation.
export const THREAT = {
  0: { id: 0, label: "Normal", color: "#34d399", short: "NORM" },
  1: { id: 1, label: "Jamming", color: "#a78bfa", short: "JAM" },
  2: { id: 2, label: "Spoofing", color: "#f59e0b", short: "SPOOF" },
  3: { id: 3, label: "DoS", color: "#f87171", short: "DOS" },
  4: { id: 4, label: "Intrusion", color: "#fbbf24", short: "PROBE" },
};

// Transfer accuracy (0–100) -> red→amber→green. White labels stay readable (L≈40%).
export function transferColor(v) {
  const cl = Math.max(0, Math.min(100, v));
  return `hsl(${(cl * 1.4).toFixed(0)} 58% 40%)`;
}

// Delta (pp) diverging around 0: green positive, red negative, near-gray at 0.
export function deltaColor(v) {
  const mag = v >= 0 ? Math.min(v / 69, 1) : Math.min(-v / 12, 1);
  const hue = v >= 0 ? 140 : 0;
  return `hsl(${hue} ${(12 + mag * 55).toFixed(0)}% ${(20 + mag * 18).toFixed(0)}%)`;
}

// Confusion-matrix cell (row-normalized fraction) -> cyan sequential.
export function confColor(frac) {
  return `hsl(187 ${(14 + frac * 58).toFixed(0)}% ${(11 + frac * 40).toFixed(0)}%)`;
}

// Compact integer formatting for dense cells (68014 -> "68k").
export function compact(v) {
  if (v >= 10000) return (v / 1000).toFixed(0) + "k";
  if (v >= 1000) return (v / 1000).toFixed(1) + "k";
  return String(v);
}
