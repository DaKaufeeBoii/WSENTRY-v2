// Self-contained SOC simulation: generates a live packet stream, classifies it,
// and drives a mock mitigation engine. No backend, no real capture — everything
// here is synthetic so the dashboard runs standalone. Exposed as an external
// store (useSyncExternalStore) so every view shares one running simulation.

import { useSyncExternalStore } from "react";
import { THREAT } from "./theme.js";

const MAX_PACKETS = 400;
const MAX_RATE = 60;
const MAX_LOG = 120;
const BLOCK_MS = 45000;
const COOLDOWN_MS = 12000;

const ATTACK_TYPES = [1, 2, 3, 4]; // Jamming, Spoofing, DoS, Intrusion
const ATTACKERS = ["192.168.1.50", "192.168.1.73", "45.137.21.9", "185.220.101.4", "10.0.0.66"];
const VICTIM = "10.0.0.100";

const rint = (a, b) => a + Math.floor(Math.random() * (b - a + 1));
const pick = (arr) => arr[Math.floor(Math.random() * arr.length)];
const internalIp = () => `10.0.0.${rint(2, 240)}`;
const now = () => Date.now();

function ruleCommand(mode, ip, id) {
  if (mode === "windows")
    return `netsh advfirewall firewall add rule name="W-SENTRY_${id}" dir=in action=block remoteip=${ip} protocol=any`;
  if (mode === "wsl") return `iptables -A INPUT -s ${ip} -j DROP`;
  return `[SIMULATED] drop traffic from ${ip}`;
}

function actionForClass(cls) {
  switch (cls) {
    case 1: return "ALERT_ONLY"; // Jamming — cannot block at network layer
    case 3: return "BLOCK + RATE_LIMIT"; // DoS
    default: return "BLOCK_IP"; // Spoofing / Intrusion
  }
}

class Feed {
  constructor() {
    this.listeners = new Set();
    this.timer = null;
    this.running = false;
    this.mode = "simulated";
    this.ruleSeq = 1;
    this.packetSeq = 1;
    this.episode = null; // {cls, attacker, ticksLeft}
    this.cooldowns = new Map(); // ip -> ts of last rule
    this.reset(false);
  }

  reset(notify = true) {
    this.packets = [];
    this.rateHistory = Array.from({ length: MAX_RATE }, (_, i) => ({ t: i - MAX_RATE, pps: 0, threats: 0 }));
    this.stats = { total: 0, threats: 0, byClass: { 0: 0, 1: 0, 2: 0, 3: 0, 4: 0 } };
    this.connections = new Map();
    this.mitigationLog = [];
    this.activeBlocks = new Map();
    this.confidences = [];
    this.episode = null;
    this.cooldowns.clear();
    this._rebuild();
    if (notify) this._emit();
  }

  subscribe(cb) {
    this.listeners.add(cb);
    return () => this.listeners.delete(cb);
  }
  getSnapshot() {
    return this.snapshot;
  }
  _emit() {
    for (const cb of this.listeners) cb();
  }

  start() {
    if (this.running) return;
    this.running = true;
    this.timer = setInterval(() => this._tick(), 1000);
    this._rebuild();
    this._emit();
  }
  stop() {
    this.running = false;
    if (this.timer) clearInterval(this.timer);
    this.timer = null;
    this._rebuild();
    this._emit();
  }
  toggle() {
    this.running ? this.stop() : this.start();
  }
  setMode(mode) {
    this.mode = mode;
    this._rebuild();
    this._emit();
  }

  _maybeEpisode() {
    if (this.episode) {
      this.episode.ticksLeft -= 1;
      if (this.episode.ticksLeft <= 0) this.episode = null;
    } else if (Math.random() < 0.22) {
      this.episode = { cls: pick(ATTACK_TYPES), attacker: pick(ATTACKERS), ticksLeft: rint(3, 7) };
    }
  }

  _makePacket() {
    const ep = this.episode;
    let cls, src, dst, proto, length;
    if (ep && Math.random() < 0.78) {
      cls = ep.cls;
      src = ep.attacker;
      dst = VICTIM;
      if (cls === 3) { proto = pick(["TCP", "UDP", "ICMP"]); length = rint(40, 120); }
      else if (cls === 1) { proto = "802.11"; length = rint(0, 60); }
      else if (cls === 2) { proto = pick(["ARP", "TCP"]); length = rint(42, 300); }
      else { proto = pick(["TCP", "UDP"]); length = rint(40, 200); }
      // occasional misclassification noise
      if (Math.random() < 0.08) cls = pick([0, ...ATTACK_TYPES]);
    } else {
      cls = 0;
      src = internalIp();
      dst = pick([internalIp(), VICTIM, "8.8.8.8", "140.82.112.3"]);
      proto = pick(["TCP", "UDP", "TCP", "ICMP"]);
      length = rint(60, 1400);
    }
    const base = cls === 0 ? 0.9 : 0.8;
    const confidence = Math.min(0.999, base + Math.random() * (cls === 0 ? 0.099 : 0.199));
    return {
      id: this.packetSeq++,
      ts: now(),
      src,
      dst,
      srcPort: rint(1024, 65535),
      dstPort: cls === 3 ? pick([80, 53, 443]) : pick([80, 443, 22, 1883, 8080, rint(1024, 60000)]),
      proto,
      length,
      cls,
      label: THREAT[cls].label,
      confidence: +confidence.toFixed(3),
      action: "—",
    };
  }

  _respond(pkt) {
    if (pkt.cls === 0 || pkt.confidence < 0.85) return;
    const last = this.cooldowns.get(pkt.src) || 0;
    if (now() - last < COOLDOWN_MS) return;
    this.cooldowns.set(pkt.src, now());
    const action = actionForClass(pkt.cls);
    const id = this.ruleSeq++;
    const rule = action === "ALERT_ONLY" ? `log alert — jamming from ${pkt.src}` : ruleCommand(this.mode, pkt.src, id);
    const entry = {
      id,
      ts: now(),
      cls: pkt.cls,
      label: pkt.label,
      src: pkt.src,
      dst: pkt.dst,
      action,
      rule,
      mode: this.mode,
      success: true,
    };
    pkt.action = action;
    this.mitigationLog.unshift(entry);
    if (this.mitigationLog.length > MAX_LOG) this.mitigationLog.length = MAX_LOG;
    if (action !== "ALERT_ONLY") {
      this.activeBlocks.set(pkt.src, { ip: pkt.src, since: now(), until: now() + BLOCK_MS, action, cls: pkt.cls });
    }
  }

  _track(pkt) {
    this.stats.total += 1;
    this.stats.byClass[pkt.cls] += 1;
    if (pkt.cls !== 0) this.stats.threats += 1;
    let c = this.connections.get(pkt.src);
    if (!c) {
      c = { ip: pkt.src, packets: 0, threats: 0, byClass: { 0: 0, 1: 0, 2: 0, 3: 0, 4: 0 }, confSum: 0, lastSeen: 0 };
      this.connections.set(pkt.src, c);
    }
    c.packets += 1;
    c.byClass[pkt.cls] += 1;
    c.confSum += pkt.confidence;
    c.lastSeen = pkt.ts;
    if (pkt.cls !== 0) c.threats += 1;
    this.confidences.push(pkt.confidence);
    if (this.confidences.length > 200) this.confidences.shift();
  }

  manualBlock(ip) {
    const id = this.ruleSeq++;
    this.activeBlocks.set(ip, { ip, since: now(), until: now() + BLOCK_MS, action: "BLOCK_IP", cls: -1, manual: true });
    this.mitigationLog.unshift({
      id, ts: now(), cls: -1, label: "Manual", src: ip, dst: VICTIM,
      action: "BLOCK_IP", rule: ruleCommand(this.mode, ip, id), mode: this.mode, success: true, manual: true,
    });
    if (this.mitigationLog.length > MAX_LOG) this.mitigationLog.length = MAX_LOG;
    this._rebuild();
    this._emit();
  }
  unblock(ip) {
    this.activeBlocks.delete(ip);
    this._rebuild();
    this._emit();
  }
  clearRules() {
    this.activeBlocks.clear();
    this._rebuild();
    this._emit();
  }

  _tick() {
    this._maybeEpisode();
    const n = this.episode ? rint(10, 26) : rint(2, 8);
    let threatsThisTick = 0;
    for (let i = 0; i < n; i++) {
      const pkt = this._makePacket();
      this._track(pkt);
      this._respond(pkt);
      if (pkt.cls !== 0) threatsThisTick += 1;
      this.packets.unshift(pkt);
    }
    if (this.packets.length > MAX_PACKETS) this.packets.length = MAX_PACKETS;
    // expire blocks
    for (const [ip, b] of this.activeBlocks) if (now() > b.until) this.activeBlocks.delete(ip);
    // rate history
    this.rateHistory.push({ t: 0, pps: n, threats: threatsThisTick });
    if (this.rateHistory.length > MAX_RATE) this.rateHistory.shift();
    this.rateHistory = this.rateHistory.map((r, i) => ({ ...r, t: i - this.rateHistory.length + 1 }));
    this._rebuild();
    this._emit();
  }

  _rebuild() {
    const recentThreat = this.rateHistory.slice(-15);
    const windowPkts = recentThreat.reduce((a, r) => a + r.pps, 0);
    const windowThreats = recentThreat.reduce((a, r) => a + r.threats, 0);
    const threatRate = windowPkts ? (windowThreats / windowPkts) * 100 : 0;
    const lastPps = this.rateHistory[this.rateHistory.length - 1]?.pps || 0;
    // Fresh references for anything consumed via useMemo so memoization re-runs
    // (these arrays/objects are otherwise mutated in place).
    this.snapshot = {
      running: this.running,
      mode: this.mode,
      packets: this.packets.slice(),
      rateHistory: this.rateHistory.slice(),
      stats: { total: this.stats.total, threats: this.stats.threats, byClass: { ...this.stats.byClass } },
      threatRate,
      pps: lastPps,
      connections: Array.from(this.connections.values()).sort((a, b) => b.packets - a.packets),
      mitigationLog: this.mitigationLog.slice(),
      activeBlocks: Array.from(this.activeBlocks.values()).sort((a, b) => a.until - b.until),
      confidences: this.confidences.slice(),
      episode: this.episode,
    };
  }
}

export const feed = new Feed();

export function useFeed() {
  return useSyncExternalStore(
    (cb) => feed.subscribe(cb),
    () => feed.getSnapshot()
  );
}
