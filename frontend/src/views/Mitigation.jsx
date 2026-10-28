import { useMemo } from "react";
import { ShieldAlert, ShieldOff, Ban, Trash2, CheckCircle2 } from "lucide-react";
import { Card, SectionHeader } from "../components/ui.jsx";
import { ThreatBadge } from "../components/ThreatBadge.jsx";
import { useFeed, feed } from "../lib/mockFeed.js";
import { C, THREAT } from "../lib/theme.js";

const MODES = [
  { id: "simulated", label: "Simulated" },
  { id: "windows", label: "Windows (netsh)" },
  { id: "wsl", label: "WSL (iptables)" },
];

function dominant(byClass) {
  let best = 0, bestV = -1;
  for (const k of Object.keys(byClass)) if (byClass[k] > bestV) (bestV = byClass[k]), (best = +k);
  return best;
}
function fmtTime(ts) {
  return new Date(ts).toLocaleTimeString([], { hour12: false });
}

export default function Mitigation() {
  const s = useFeed();
  const blocked = useMemo(() => new Map(s.activeBlocks.map((b) => [b.ip, b])), [s.activeBlocks]);
  const nowTs = Date.now();

  return (
    <div>
      <SectionHeader
        eyebrow="Firewall responses"
        title="Mitigation engine"
        sub="Automated responses to classified threats, with a per-IP cooldown. Rule commands are generated for the selected platform but never executed — this is a simulated response log."
      />

      <div className="flex flex-wrap items-center gap-3 mb-4">
        <span className="text-[12.5px] text-faint">Execution mode</span>
        <div className="flex gap-1.5">
          {MODES.map((m) => (
            <button
              key={m.id}
              onClick={() => feed.setMode(m.id)}
              className={`rounded-lg border px-3 py-1.5 text-[12.5px] font-medium transition-colors ${
                s.mode === m.id ? "bg-accent text-[#06181c] border-accent" : "bg-surface2 text-muted border-edge hover:text-ink"
              }`}
            >
              {m.label}
            </button>
          ))}
        </div>
        <button
          onClick={() => feed.clearRules()}
          className="ml-auto inline-flex items-center gap-2 rounded-lg border border-edge bg-surface2 px-3 py-1.5 text-[12.5px] font-medium text-muted hover:text-ink"
        >
          <Trash2 size={14} /> Clear all rules
        </button>
      </div>

      <div className="grid lg:grid-cols-3 gap-4">
        <Card title="Connections" note="grouped by source IP" className="lg:col-span-2" pad={false}>
          <div className="overflow-x-auto max-h-[420px] overflow-y-auto">
            <table className="w-full text-[12.5px]">
              <thead className="sticky top-0 bg-surface z-10">
                <tr className="text-faint text-[11px] uppercase tracking-wide">
                  {["Source IP", "Pkts", "Threats", "Dominant", "Avg conf", "Status", ""].map((h) => (
                    <th key={h} className="text-left font-semibold px-3 py-2.5 border-b border-edge whitespace-nowrap">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {s.connections.slice(0, 30).map((c) => {
                  const dom = dominant(c.byClass);
                  const b = blocked.get(c.ip);
                  const avg = c.packets ? c.confSum / c.packets : 0;
                  const status = b
                    ? b.action && b.action.includes("RATE")
                      ? { t: "RATE_LIMITED", color: C.warn }
                      : { t: "BLOCKED", color: C.bad }
                    : c.threats > 0
                    ? { t: "WATCH", color: C.warn }
                    : { t: "ACTIVE", color: C.good };
                  return (
                    <tr key={c.ip} className="border-b border-edgesoft hover:bg-surface2">
                      <td className="px-3 py-2 font-mono tnum whitespace-nowrap">{c.ip}</td>
                      <td className="px-3 py-2 tnum text-muted">{c.packets}</td>
                      <td className="px-3 py-2 tnum" style={{ color: c.threats ? C.bad : C.faint }}>{c.threats}</td>
                      <td className="px-3 py-2">
                        <ThreatBadge cls={dom} />
                      </td>
                      <td className="px-3 py-2 tnum text-muted">{(avg * 100).toFixed(0)}%</td>
                      <td className="px-3 py-2">
                        <span className="text-[11px] font-semibold" style={{ color: status.color }}>
                          {status.t}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-right whitespace-nowrap">
                        {b ? (
                          <button
                            onClick={() => feed.unblock(c.ip)}
                            className="inline-flex items-center gap-1 rounded-md border border-edge px-2 py-1 text-[11px] text-good hover:bg-surface3"
                          >
                            <ShieldOff size={12} /> Unblock
                          </button>
                        ) : (
                          <button
                            onClick={() => feed.manualBlock(c.ip)}
                            className="inline-flex items-center gap-1 rounded-md border border-edge px-2 py-1 text-[11px] text-bad hover:bg-surface3"
                          >
                            <Ban size={12} /> Block
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
                {s.connections.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-3 py-10 text-center text-faint">
                      No connections yet — start the capture on the Live Monitor.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>

        <Card title="Active blocks" note="auto-expire after 45s">
          {s.activeBlocks.length === 0 ? (
            <div className="h-[120px] flex items-center justify-center text-faint text-[13px]">No active blocks</div>
          ) : (
            <div className="space-y-2.5">
              {s.activeBlocks.map((b) => {
                const remain = Math.max(0, Math.round((b.until - nowTs) / 1000));
                return (
                  <div key={b.ip} className="flex items-center justify-between rounded-lg border border-edge bg-surface2 px-3 py-2">
                    <div className="min-w-0">
                      <div className="font-mono text-[12.5px] tnum truncate">{b.ip}</div>
                      <div className="text-[11px] text-faint">{b.manual ? "manual" : b.action}</div>
                    </div>
                    <div className="text-right">
                      <div className="tnum text-[13px] font-semibold" style={{ color: C.warn }}>
                        {remain}s
                      </div>
                      <button onClick={() => feed.unblock(b.ip)} className="text-[11px] text-faint hover:text-ink">
                        release
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </Card>
      </div>

      <Card title="Mitigation log" note={`${s.mitigationLog.length} actions · mode: ${s.mode}`} className="mt-4" pad={false}>
        <div className="overflow-x-auto max-h-[380px] overflow-y-auto">
          <table className="w-full text-[12.5px]">
            <thead className="sticky top-0 bg-surface z-10">
              <tr className="text-faint text-[11px] uppercase tracking-wide">
                {["Time", "Source", "Threat", "Action", "Rule", "OK"].map((h) => (
                  <th key={h} className="text-left font-semibold px-3 py-2.5 border-b border-edge whitespace-nowrap">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {s.mitigationLog.map((e) => (
                <tr key={e.id} className="border-b border-edgesoft hover:bg-surface2 animate-slidein">
                  <td className="px-3 py-2 font-mono tnum text-faint whitespace-nowrap">{fmtTime(e.ts)}</td>
                  <td className="px-3 py-2 font-mono tnum whitespace-nowrap">{e.src}</td>
                  <td className="px-3 py-2">
                    {e.cls >= 0 ? <ThreatBadge cls={e.cls} /> : <span className="text-faint text-[11px]">manual</span>}
                  </td>
                  <td className="px-3 py-2 font-semibold whitespace-nowrap" style={{ color: e.action === "ALERT_ONLY" ? C.warn : C.bad }}>
                    {e.action}
                  </td>
                  <td className="px-3 py-2 font-mono text-[11px] text-muted max-w-[320px] truncate" title={e.rule}>
                    {e.rule}
                  </td>
                  <td className="px-3 py-2">
                    <CheckCircle2 size={15} className="text-good" />
                  </td>
                </tr>
              ))}
              {s.mitigationLog.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-3 py-10 text-center text-faint">
                    No mitigations yet — threats trigger automatic responses here.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
