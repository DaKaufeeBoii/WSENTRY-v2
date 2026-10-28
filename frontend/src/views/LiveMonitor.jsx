import { useMemo } from "react";
import { Play, Pause, RotateCcw, Radar } from "lucide-react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
} from "recharts";
import { Card, Meter } from "../components/ui.jsx";
import { ThreatBadge } from "../components/ThreatBadge.jsx";
import { ChartTooltip } from "../components/charts.jsx";
import { useFeed, feed } from "../lib/mockFeed.js";
import { C, THREAT } from "../lib/theme.js";

function fmtTime(ts) {
  const d = new Date(ts);
  return d.toLocaleTimeString([], { hour12: false });
}

function ControlBtn({ onClick, children, tone = "default" }) {
  const tones = {
    live: "bg-good/15 text-good border-good/40 hover:bg-good/25",
    stop: "bg-bad/15 text-bad border-bad/40 hover:bg-bad/25",
    default: "bg-surface2 text-muted border-edge hover:text-ink",
  };
  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center gap-2 rounded-lg border px-3.5 py-2 text-[13px] font-medium transition-colors ${tones[tone]}`}
    >
      {children}
    </button>
  );
}

function StatTile({ label, value, sub, color }) {
  return (
    <div className="card p-4">
      <div className="text-[11.5px] uppercase tracking-wide text-faint">{label}</div>
      <div className="mt-1.5 text-[28px] font-bold tnum leading-none" style={color ? { color } : undefined}>
        {value}
      </div>
      {sub && <div className="text-[11.5px] text-muted mt-1.5">{sub}</div>}
    </div>
  );
}

export default function LiveMonitor() {
  const s = useFeed();

  const hist = useMemo(() => {
    const bins = Array.from({ length: 10 }, (_, i) => ({ bin: `${50 + i * 5}`, count: 0 }));
    s.confidences.forEach((c) => {
      let idx = Math.floor((c - 0.5) / 0.05);
      if (idx < 0) idx = 0;
      if (idx > 9) idx = 9;
      bins[idx].count += 1;
    });
    return bins;
  }, [s.confidences]);

  const dist = useMemo(
    () =>
      Object.entries(s.stats.byClass)
        .map(([k, v]) => ({ name: THREAT[k].label, value: v, color: THREAT[k].color }))
        .filter((d) => d.value > 0),
    [s.stats]
  );

  const severityColor = s.threatRate >= 40 ? C.bad : s.threatRate >= 15 ? C.warn : C.good;
  const rows = s.packets.slice(0, 40);

  return (
    <div>
      <div className="flex flex-wrap items-center gap-3 mb-5">
        <div className="flex items-center gap-2 mr-auto">
          <Radar size={20} className="text-accent" />
          <div>
            <div className="text-[15px] font-semibold leading-tight">Live SOC Monitor</div>
            <div className="text-[12px] text-faint">
              Simulated NIC capture · classified by the hybrid model{s.episode ? " · attack episode in progress" : ""}
            </div>
          </div>
        </div>
        {s.running ? (
          <ControlBtn onClick={() => feed.stop()} tone="stop">
            <Pause size={15} /> Stop capture
          </ControlBtn>
        ) : (
          <ControlBtn onClick={() => feed.start()} tone="live">
            <Play size={15} /> Start capture
          </ControlBtn>
        )}
        <ControlBtn onClick={() => feed.reset()}>
          <RotateCcw size={15} /> Reset
        </ControlBtn>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
        <div className="card p-4">
          <div className="text-[11.5px] uppercase tracking-wide text-faint">Threat rate</div>
          <div className="mt-1.5 text-[28px] font-bold tnum leading-none" style={{ color: severityColor }}>
            {s.threatRate.toFixed(0)}%
          </div>
          <div className="mt-2.5">
            <Meter value={s.threatRate} max={100} color={severityColor} />
          </div>
          <div className="text-[11px] text-faint mt-1.5">rolling 15s window</div>
        </div>
        <StatTile label="Packets / sec" value={s.pps} sub="current tick" color={C.accent} />
        <StatTile label="Threats detected" value={s.stats.threats.toLocaleString()} sub="session total" color={C.bad} />
        <StatTile label="Total packets" value={s.stats.total.toLocaleString()} sub="session total" />
      </div>

      <Card title="Packet rate" note="packets/sec with threats highlighted" className="mb-4">
        <ResponsiveContainer width="100%" height={150}>
          <AreaChart data={s.rateHistory} margin={{ top: 6, right: 6, left: -18, bottom: 0 }}>
            <defs>
              <linearGradient id="ppsFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={C.accent} stopOpacity={0.35} />
                <stop offset="100%" stopColor={C.accent} stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis dataKey="t" tick={{ fill: C.faint, fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={(t) => `${t}s`} />
            <YAxis tick={{ fill: C.faint, fontSize: 10 }} axisLine={false} tickLine={false} width={34} />
            <Tooltip content={<ChartTooltip />} />
            <Area type="monotone" dataKey="pps" name="pkts/s" stroke={C.accent} strokeWidth={2} fill="url(#ppsFill)" isAnimationActive={false} />
            <Area type="monotone" dataKey="threats" name="threats" stroke={C.bad} strokeWidth={1.6} fill="none" isAnimationActive={false} />
          </AreaChart>
        </ResponsiveContainer>
      </Card>

      <div className="grid lg:grid-cols-3 gap-4">
        <Card title="Packet stream" note="last 40 packets · newest first" className="lg:col-span-2" pad={false}>
          <div className="overflow-x-auto max-h-[460px] overflow-y-auto">
            <table className="w-full text-[12.5px]">
              <thead className="sticky top-0 bg-surface z-10">
                <tr className="text-faint text-[11px] uppercase tracking-wide">
                  {["Time", "Source", "Dest", "Proto", "Class", "Conf", "Action"].map((h) => (
                    <th key={h} className="text-left font-semibold px-3 py-2.5 border-b border-edge whitespace-nowrap">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((p) => {
                  const t = THREAT[p.cls];
                  return (
                    <tr key={p.id} className="border-b border-edgesoft hover:bg-surface2">
                      <td className="px-3 py-2 tnum text-faint font-mono whitespace-nowrap">{fmtTime(p.ts)}</td>
                      <td className="px-3 py-2 tnum font-mono whitespace-nowrap">{p.src}</td>
                      <td className="px-3 py-2 tnum font-mono text-muted whitespace-nowrap">{p.dst}</td>
                      <td className="px-3 py-2 text-muted">{p.proto}</td>
                      <td className="px-3 py-2">
                        <ThreatBadge cls={p.cls} />
                      </td>
                      <td className="px-3 py-2 w-24">
                        <div className="flex items-center gap-2">
                          <span className="tnum text-[11.5px] w-9">{(p.confidence * 100).toFixed(0)}%</span>
                          <div className="flex-1">
                            <Meter value={p.confidence} max={1} color={t.color} height={5} />
                          </div>
                        </div>
                      </td>
                      <td className="px-3 py-2 whitespace-nowrap">
                        {p.action === "—" ? (
                          <span className="text-faint">—</span>
                        ) : (
                          <span className="text-[11px] font-semibold" style={{ color: p.cls === 1 ? C.warn : C.bad }}>
                            {p.action}
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
                {rows.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-3 py-10 text-center text-faint">
                      Capture paused — press Start to stream packets.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>

        <div className="space-y-4">
          <Card title="Traffic distribution" note="session, by class">
            {dist.length > 0 ? (
              <ResponsiveContainer width="100%" height={180}>
                <PieChart>
                  <Pie data={dist} dataKey="value" nameKey="name" innerRadius={44} outerRadius={70} paddingAngle={2} stroke="none" isAnimationActive={false}>
                    {dist.map((d) => (
                      <Cell key={d.name} fill={d.color} />
                    ))}
                  </Pie>
                  <Tooltip content={<ChartTooltip fmt={(v) => v.toLocaleString()} />} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[180px] flex items-center justify-center text-faint text-[13px]">No traffic yet</div>
            )}
            <div className="flex flex-wrap gap-x-3 gap-y-1 mt-2 text-[11.5px]">
              {dist.map((d) => (
                <span key={d.name} className="inline-flex items-center gap-1.5 text-muted">
                  <span className="w-2.5 h-2.5 rounded-[2px]" style={{ background: d.color }} />
                  {d.name}
                </span>
              ))}
            </div>
          </Card>

          <Card title="Confidence histogram" note="last 200 predictions">
            <ResponsiveContainer width="100%" height={150}>
              <BarChart data={hist} margin={{ top: 4, right: 4, left: -24, bottom: 0 }}>
                <XAxis dataKey="bin" tick={{ fill: C.faint, fontSize: 9 }} axisLine={false} tickLine={false} tickFormatter={(b) => `${b}%`} interval={1} />
                <YAxis tick={{ fill: C.faint, fontSize: 10 }} axisLine={false} tickLine={false} width={34} />
                <Tooltip cursor={{ fill: "rgba(255,255,255,0.04)" }} content={<ChartTooltip />} />
                <Bar dataKey="count" name="count" fill={C.accent} radius={[3, 3, 0, 0]} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </div>
      </div>
    </div>
  );
}
