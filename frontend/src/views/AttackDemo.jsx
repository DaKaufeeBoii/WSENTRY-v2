import { useMemo } from "react";
import { Radio, UserX, Zap, Search, ShieldCheck, ShieldOff, Play, Pause, RotateCcw, CheckCircle2, Circle, XCircle } from "lucide-react";
import { Card, SectionHeader } from "../components/ui.jsx";
import { ThreatBadge } from "../components/ThreatBadge.jsx";
import { useFeed, feed } from "../lib/mockFeed.js";
import { C, THREAT } from "../lib/theme.js";

const VICTIM = "10.0.0.100";
const BTN =
  "inline-flex items-center gap-2 rounded-lg border border-edge bg-surface px-3.5 py-2 text-[13px] font-medium text-muted hover:text-ink hover:bg-surface2";

const ATTACKS = [
  { cls: 3, icon: Zap, name: "DoS flood", ip: "192.168.1.50", desc: "SYN / UDP / ICMP flood against the gateway" },
  { cls: 3, icon: Zap, name: "SYN flood", ip: "192.168.1.51", desc: "TCP half-open connection flood" },
  { cls: 3, icon: Zap, name: "UDP flood", ip: "192.168.1.52", desc: "High-rate UDP packet flood (DDoS)" },
  { cls: 4, icon: Search, name: "Port scan", ip: "192.168.1.91", desc: "Reconnaissance probe across service ports" },
  { cls: 4, icon: Search, name: "OS fingerprint", ip: "192.168.1.92", desc: "Stack probing to identify the host OS" },
  { cls: 4, icon: Search, name: "Vuln scan", ip: "192.168.1.93", desc: "Automated vulnerability scanner sweep" },
  { cls: 2, icon: UserX, name: "Spoofing / MITM", ip: "192.168.1.73", desc: "ARP / DNS spoofing, blackhole routing" },
  { cls: 1, icon: Radio, name: "Jamming", ip: "192.168.1.66", desc: "Rogue node disrupting the sensor channel" },
];

function fmtTime(ts) {
  return new Date(ts).toLocaleTimeString([], { hour12: false });
}
function secs(a, b) {
  return `${((b - a) / 1000).toFixed(1)}s`;
}

function Step({ state, title, children }) {
  const Icon = state === "done" ? CheckCircle2 : state === "fail" ? XCircle : Circle;
  const color = state === "done" ? C.good : state === "fail" ? C.bad : C.faint;
  return (
    <div className="flex gap-3">
      <Icon size={20} style={{ color }} className="shrink-0 mt-0.5" />
      <div className="min-w-0">
        <div className="text-[13.5px] font-semibold" style={{ color: state === "pending" ? C.faint : C.ink }}>
          {title}
        </div>
        <div className="text-[12.5px] text-muted mt-0.5 break-words">{children}</div>
      </div>
    </div>
  );
}

function Big({ label, value, color, sub }) {
  return (
    <div className="card p-4">
      <div className="text-[11.5px] uppercase tracking-wide text-faint">{label}</div>
      <div className="mt-1.5 text-[30px] font-bold tnum leading-none" style={{ color: color || C.ink }}>
        {value}
      </div>
      {sub && <div className="text-[11px] text-faint mt-1.5">{sub}</div>}
    </div>
  );
}

function NetworkLink({ s }) {
  const t = Date.now();
  const b = s.bridge || {};
  return (
    <Card title="Network link" note="attacker devices on the LAN" className="mb-5">
      <div className="grid md:grid-cols-3 gap-4">
        <div>
          <div className="text-[11px] uppercase tracking-wide text-faint">This device (W-SENTRY)</div>
          <div className="flex items-center gap-2 mt-1.5">
            <span className="w-2.5 h-2.5 rounded-full" style={{ background: b.up ? C.good : C.bad }} />
            <span className="text-[14px] font-semibold">{b.board || b.host || "detector"}</span>
          </div>
          <div className="font-mono text-[13px] mt-1">{(b.ips || []).join(" · ") || "—"}</div>
          <div className="text-[12px] text-faint mt-1">{b.up ? `live model on ${b.board || b.host || "detector"}${b.arch ? ` (${b.arch})` : ""} · ${b.enforce === "iptables" ? "kernel firewall" : "dry-run firewall"}` : "model server offline — start detector_server.py"}</div>
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-wide text-faint">Connected devices</div>
          {s.devices.length === 0 && <div className="text-[12.5px] text-faint mt-1.5">No device connected yet — run attacker.py connect</div>}
          {s.devices.slice(0, 3).map((dv) => {
            const online = t - dv.lastSeen < 6000;
            return (
              <div key={dv.ip} className="mt-1.5">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full" style={{ background: online ? C.good : C.faint }} />
                  <span className="text-[13.5px] font-semibold">{dv.name}</span>
                  <span className="text-[10.5px] font-bold tracking-wide" style={{ color: online ? C.good : C.faint }}>
                    {online ? "ONLINE" : "OFFLINE"}
                  </span>
                </div>
                <div className="font-mono text-[12.5px] text-muted">
                  {dv.ip} · seen {Math.max(0, Math.round((t - dv.lastSeen) / 1000))}s ago
                </div>
              </div>
            );
          })}
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-wide text-faint">Connection log</div>
          {s.connLog.length === 0 && <div className="text-[12.5px] text-faint mt-1.5">—</div>}
          {s.connLog.slice(0, 5).map((l, k) => (
            <div key={k} className="text-[12px] mt-1 leading-snug">
              <span className="font-mono text-faint">{fmtTime(l.ts)}</span> <span className="font-semibold">{l.name}</span>{" "}
              <span className="font-mono text-muted">({l.ip})</span> <span className="text-muted">{l.text}</span>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}

function ipStatus(d) {
  if (!d.protection) return { text: "ACTIVE · unrestricted", color: C.bad };
  if (d.cls === 1 && d.mitigatedAt) return { text: "ALERT · channel hopped", color: C.warn };
  if (d.mitigatedAt) return { text: d.action === "BLOCK + RATE_LIMIT" ? "BLOCKED + RATE LIMITED" : "BLOCKED", color: C.good };
  return { text: "ACTIVE · not yet stopped", color: C.warn };
}

export default function AttackDemo() {
  const s = useFeed();
  const d = s.demo;
  const attackerPkts = useMemo(
    () => (d ? s.packets.filter((p) => p.src === d.attacker).slice(0, 10) : []),
    [s.packets, d]
  );

  const steps = d && [
    {
      state: "done",
      title: "Attack launched",
      body: `${THREAT[d.cls].label} from ${d.attacker}${d.remote ? ` (${s.devices.find((x) => x.ip === d.attacker)?.name || "remote device"}, over the network)` : ""} → ${VICTIM} at ${fmtTime(d.startedAt)}`,
    },
    {
      state: !d.protection ? "fail" : d.detectedAt ? "done" : "pending",
      title: "Detected by the hybrid model",
      body: !d.protection
        ? "W-SENTRY is off — no traffic is inspected"
        : d.detectedAt
        ? `Classified as ${THREAT[d.detectedAs].label} at ${(d.detectConf * 100).toFixed(1)}% confidence after ${d.detectedAfter} packet${d.detectedAfter === 1 ? "" : "s"} (${secs(d.startedAt, d.detectedAt)})`
        : "Inspecting attacker traffic…",
    },
    {
      state: !d.protection ? "fail" : d.mitigatedAt ? "done" : "pending",
      title: "Mitigation applied",
      body: !d.protection
        ? "No response — attacker keeps full access"
        : d.mitigatedAt
        ? `${d.action} · ${d.rule}`
        : "Waiting for a confident detection (≥ 85%)",
    },
    {
      state: !d.protection ? "fail" : d.blocked > 0 ? "done" : "pending",
      title: d.cls === 1 ? "Channel moved — jamming avoided" : "Attacker contained",
      body: !d.protection
        ? `${d.reached} attack packets reached ${VICTIM}`
        : d.blocked > 0
        ? `${d.blocked} attacker packets ${d.cls === 1 ? "sent on the old channel" : "dropped at the firewall"} since ${fmtTime(d.mitigatedAt)}`
        : "—",
    },
  ];

  const st = d && ipStatus(d);

  return (
    <div>
      <SectionHeader
        eyebrow="Live demo"
        title="Attack demo"
        sub="Launch an attack on the protected network and watch W-SENTRY respond. Each attacker packet is a held-out test record of that attack class, classified by the trained hybrid model; responses run through the mitigation engine in dry-run mode."
      />

      <div className="flex flex-wrap items-center gap-3 mb-5">
        <div className="flex rounded-lg overflow-hidden border border-edge">
          <button
            onClick={() => feed.setProtection(true)}
            className="px-4 py-2 text-[13px] font-semibold inline-flex items-center gap-2"
            style={s.protection ? { background: `${C.good}26`, color: C.good } : { color: C.faint }}
          >
            <ShieldCheck size={16} /> W-SENTRY ON
          </button>
          <button
            onClick={() => feed.setProtection(false)}
            className="px-4 py-2 text-[13px] font-semibold inline-flex items-center gap-2 border-l border-edge"
            style={!s.protection ? { background: `${C.bad}26`, color: C.bad } : { color: C.faint }}
          >
            <ShieldOff size={16} /> OFF (no IDS)
          </button>
        </div>
        <span className="text-[12.5px] text-faint mr-auto">
          {s.protection ? "Traffic is inspected by the hybrid model" : "Traffic flows uninspected — the 'before' picture"}
        </span>
        <button onClick={() => (s.running ? feed.stop() : feed.start())} className={BTN}>
          {s.running ? <Pause size={15} /> : <Play size={15} />} {s.running ? "Pause" : "Resume"}
        </button>
        <button onClick={() => feed.reset()} className={BTN}>
          <RotateCcw size={15} /> Reset
        </button>
      </div>

      <NetworkLink s={s} />

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-5">
        {ATTACKS.map((a) => {
          const t = THREAT[a.cls];
          const live = d?.active && d.attacker === a.ip && d.cls === a.cls;
          return (
            <button
              key={a.ip}
              onClick={() => feed.launch(a.cls, a.ip)}
              className="card p-4 text-left transition hover:brightness-125"
              style={{ borderColor: live ? t.color : undefined, boxShadow: live ? `0 0 0 1px ${t.color}` : undefined }}
            >
              <div className="flex items-center gap-2">
                <a.icon size={18} style={{ color: t.color }} />
                <span className="text-[14px] font-semibold">{a.name}</span>
                {live && (
                  <span className="ml-auto text-[10.5px] font-bold tracking-wide" style={{ color: t.color }}>
                    LIVE
                  </span>
                )}
              </div>
              <div className="text-[12px] text-muted mt-1.5 leading-snug">{a.desc}</div>
              <div className="text-[11.5px] text-faint mt-2 font-mono">from {a.ip}</div>
              <div
                className="mt-3 text-center text-[12.5px] font-semibold rounded-md py-1.5"
                style={{ background: `${t.color}1f`, color: t.color, border: `1px solid ${t.color}40` }}
              >
                Launch attack
              </div>
            </button>
          );
        })}
      </div>

      {!d && (
        <Card className="mb-5">
          <div className="py-8 text-center text-faint text-[13.5px]">
            Pick an attack above. Run it once with W-SENTRY OFF, then again with it ON, to compare.
          </div>
        </Card>
      )}

      {d && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
            <Big label="Attack packets sent" value={d.sent} sub={`from ${d.attacker}`} />
            <Big label="Reached the target" value={d.reached} color={C.bad} sub={VICTIM} />
            <Big label="Blocked / avoided" value={d.blocked} color={C.good} sub={d.protection ? "after mitigation" : "W-SENTRY off"} />
            <Big
              label="Time to detect"
              value={d.detectedAt ? secs(d.startedAt, d.detectedAt) : d.protection ? "…" : "never"}
              color={d.detectedAt ? C.accent : C.faint}
              sub={d.detectedAt ? `after ${d.detectedAfter} packets` : ""}
            />
          </div>

          <div className="grid lg:grid-cols-5 gap-4 mb-4">
            <Card title="Response timeline" note={d.active ? "attack in progress" : "attack finished"} className="lg:col-span-3">
              <div className="space-y-4">
                {steps.map((x) => (
                  <Step key={x.title} state={x.state} title={x.title}>
                    {x.body}
                  </Step>
                ))}
              </div>
            </Card>

            <Card title="Attacker IP status" note="before vs after" className="lg:col-span-2">
              <div className="space-y-3">
                <div className="rounded-lg border border-edge p-3">
                  <div className="text-[11px] uppercase tracking-wide text-faint">Before</div>
                  <div className="font-mono text-[15px] mt-1">{d.attacker}</div>
                  <div className="text-[12.5px] mt-1" style={{ color: C.bad }}>
                    ACTIVE · sending {THREAT[d.cls].label} traffic to {VICTIM}
                  </div>
                </div>
                <div className="rounded-lg border p-3" style={{ borderColor: `${st.color}66` }}>
                  <div className="text-[11px] uppercase tracking-wide text-faint">After</div>
                  <div className="font-mono text-[15px] mt-1">{d.attacker}</div>
                  <div className="text-[12.5px] mt-1 font-semibold" style={{ color: st.color }}>
                    {st.text}
                  </div>
                </div>
              </div>
            </Card>
          </div>

          <Card title="Attacker traffic" note={`last 10 packets from ${d.attacker}`} className="mb-4" pad={false}>
            <table className="w-full text-[12.5px]">
              <thead>
                <tr className="text-faint text-[11px] uppercase tracking-wide">
                  {["Time", "Source → Dest", "Origin", "Model verdict", "Truth", "Firewall"].map((h) => (
                    <th key={h} className="text-left font-semibold px-3 py-2.5 border-b border-edge whitespace-nowrap">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {attackerPkts.map((p) => (
                  <tr key={p.id} className="border-b border-edgesoft">
                    <td className="px-3 py-2 font-mono text-faint">{fmtTime(p.ts)}</td>
                    <td className="px-3 py-2 font-mono whitespace-nowrap">
                      {p.src} → {p.dst}
                    </td>
                    <td className="px-3 py-2 text-muted">{p.proto}</td>
                    <td className="px-3 py-2 whitespace-nowrap">
                      {p.state ? (
                        <span className="text-faint text-[11.5px]">{p.state === "dropped" ? "not reached" : "not inspected"}</span>
                      ) : (
                        <span className="inline-flex items-center gap-2">
                          <ThreatBadge cls={p.cls} />
                          <span className="tnum text-[11.5px] text-muted">{(p.confidence * 100).toFixed(0)}%</span>
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-muted">{THREAT[p.truth]?.label ?? "—"}</td>
                    <td className="px-3 py-2 font-semibold text-[11.5px] whitespace-nowrap" style={{ color: p.state === "dropped" ? C.good : p.state === "passed" ? C.bad : p.action !== "—" ? C.warn : C.faint }}>
                      {p.state === "passed" ? "PASSED" : p.state === "dropped" ? p.action : p.action !== "—" ? p.action : "allowed"}
                    </td>
                  </tr>
                ))}
                {attackerPkts.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-3 py-6 text-center text-faint">
                      Waiting for attacker packets…
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </Card>
        </>
      )}

      {s.demoLog.length > 0 && (
        <Card title="Before vs after W-SENTRY" note="every attack run this session" pad={false}>
          <div className="overflow-x-auto">
            <table className="w-full text-[12.5px]">
              <thead>
                <tr className="text-faint text-[11px] uppercase tracking-wide">
                  {["Attack", "W-SENTRY", "Attacker", "Detected", "Sent", "Reached target", "Blocked", "Final IP status"].map((h) => (
                    <th key={h} className="text-left font-semibold px-3 py-2.5 border-b border-edge whitespace-nowrap">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {s.demoLog.map((r) => {
                  const rs = ipStatus(r);
                  return (
                    <tr key={r.id} className="border-b border-edgesoft">
                      <td className="px-3 py-2">
                        <ThreatBadge cls={r.cls} />
                      </td>
                      <td className="px-3 py-2 font-semibold" style={{ color: r.protection ? C.good : C.bad }}>
                        {r.protection ? "ON" : "OFF"}
                      </td>
                      <td className="px-3 py-2 font-mono">{r.attacker}</td>
                      <td className="px-3 py-2 text-muted whitespace-nowrap">
                        {r.detectedAt ? `${secs(r.startedAt, r.detectedAt)} · ${(r.detectConf * 100).toFixed(0)}%` : "no"}
                      </td>
                      <td className="px-3 py-2 tnum">{r.sent}</td>
                      <td className="px-3 py-2 tnum font-semibold" style={{ color: C.bad }}>
                        {r.reached}
                        {r.sent ? ` (${Math.round((r.reached / r.sent) * 100)}%)` : ""}
                      </td>
                      <td className="px-3 py-2 tnum font-semibold" style={{ color: C.good }}>
                        {r.blocked}
                      </td>
                      <td className="px-3 py-2 font-semibold whitespace-nowrap" style={{ color: rs.color }}>
                        {rs.text}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
