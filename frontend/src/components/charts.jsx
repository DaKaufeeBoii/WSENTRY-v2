import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  LabelList,
  Cell,
} from "recharts";
import { C, MODEL } from "../lib/theme.js";

export function ChartTooltip({ active, payload, label, unit = "", fmt = (v) => v }) {
  if (!active || !payload || !payload.length) return null;
  return (
    <div className="rounded-lg border border-edge bg-surface2/95 px-3 py-2 text-[12px] shadow-lg backdrop-blur">
      <div className="text-faint mb-1">{label}</div>
      {payload.map((p) => (
        <div key={p.name} className="flex items-center gap-2 tnum">
          <span className="w-2.5 h-2.5 rounded-[2px]" style={{ background: p.color || p.fill }} />
          <span className="text-muted">{p.name}</span>
          <span className="ml-auto font-semibold text-ink">
            {fmt(p.value)}
            {unit}
          </span>
        </div>
      ))}
    </div>
  );
}

// spec: { groups:[], series:[{name,key?,color?,vals:[]}], max, ticks?, unit?, fmt?, height? }
export function GroupedBars({ groups, series, max = 100, ticks, unit = "", fmt = (v) => v.toFixed(2), height = 280 }) {
  const data = groups.map((g, i) => {
    const row = { group: g };
    series.forEach((s) => (row[s.name] = s.vals[i]));
    return row;
  });
  const colorFor = (s) => s.color || MODEL[s.key] || C.accent;
  const labelColor = series.length > 1 ? C.muted : C.ink;

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 18, right: 8, left: -8, bottom: 4 }} barCategoryGap="22%" barGap={4}>
        <CartesianGrid vertical={false} stroke={C.grid} />
        <XAxis dataKey="group" tick={{ fill: C.muted, fontSize: 12 }} axisLine={{ stroke: C.axis }} tickLine={false} />
        <YAxis
          domain={[0, max]}
          ticks={ticks}
          tick={{ fill: C.faint, fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          width={44}
        />
        <Tooltip cursor={{ fill: "rgba(255,255,255,0.04)" }} content={<ChartTooltip unit={unit} fmt={fmt} />} />
        {series.map((s) => (
          <Bar key={s.name} dataKey={s.name} fill={colorFor(s)} radius={[4, 4, 0, 0]} maxBarSize={48} isAnimationActive={false}>
            {series.length === 1 &&
              data.map((_, i) => <Cell key={i} fill={Array.isArray(s.color) ? s.color[i] : colorFor(s)} />)}
            <LabelList
              dataKey={s.name}
              position="top"
              formatter={fmt}
              fill={labelColor}
              fontSize={10.5}
              fontWeight={600}
            />
          </Bar>
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}
