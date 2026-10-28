import { THREAT } from "../lib/theme.js";

export function ThreatBadge({ cls, size = "sm" }) {
  const t = THREAT[cls] || { label: "Manual", color: "#a1a1aa" };
  const pad = size === "sm" ? "px-2 py-0.5 text-[11px]" : "px-2.5 py-1 text-[12px]";
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-semibold ${pad}`}
      style={{ color: t.color, background: `${t.color}1f`, border: `1px solid ${t.color}40` }}
    >
      <span className="w-1.5 h-1.5 rounded-full" style={{ background: t.color }} />
      {t.label}
    </span>
  );
}
