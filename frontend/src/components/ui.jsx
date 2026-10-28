export function Card({ title, note, right, className = "", children, pad = true }) {
  return (
    <div className={`card min-w-0 ${pad ? "p-5" : ""} ${className}`}>
      {(title || right) && (
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="min-w-0">
            {title && <div className="text-[13.5px] font-semibold leading-tight">{title}</div>}
            {note && <div className="text-[12px] text-faint mt-0.5">{note}</div>}
          </div>
          {right}
        </div>
      )}
      {children}
    </div>
  );
}

export function SectionHeader({ eyebrow, title, sub }) {
  return (
    <div className="mb-5">
      {eyebrow && (
        <div className="text-[11px] uppercase tracking-[0.18em] text-accent font-semibold mb-2">{eyebrow}</div>
      )}
      <h2 className="text-xl md:text-2xl font-bold">{title}</h2>
      {sub && <p className="text-[14px] text-muted mt-2 max-w-[74ch]">{sub}</p>}
    </div>
  );
}

export function KpiCard({ label, value, unit, sub, highlight }) {
  return (
    <div className="relative overflow-hidden card p-4">
      <span className="absolute left-0 inset-y-0 w-[3px] bg-accent/90" />
      <div className="text-[11.5px] uppercase tracking-wide text-faint leading-tight">{label}</div>
      <div className={`mt-2 text-[26px] font-bold tracking-tight tnum ${highlight ? "text-accent" : "text-ink"}`}>
        {value}
        {unit && <span className="text-[0.55em] text-muted font-semibold">{unit}</span>}
      </div>
      {sub && <div className="text-[11.5px] text-muted mt-1">{sub}</div>}
    </div>
  );
}

export function Legend({ items }) {
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1.5 text-[12.5px] text-muted mb-3">
      {items.map((it) => (
        <span key={it.name} className="inline-flex items-center gap-2">
          <span className="w-3 h-3 rounded-[3px] shrink-0" style={{ background: it.color }} />
          {it.name}
        </span>
      ))}
    </div>
  );
}

export function Meter({ value, max = 1, color = "#22D3EE", height = 8 }) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div className="w-full rounded-full bg-surface2 overflow-hidden" style={{ height }}>
      <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: color }} />
    </div>
  );
}

export function Stat({ label, value, color }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <span className="text-[13px] text-muted">{label}</span>
      <span className="text-[22px] font-bold tnum" style={color ? { color } : undefined}>
        {value}
      </span>
    </div>
  );
}
