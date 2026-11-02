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
const ORIGIN = { WSN: "WSN-DS", CIC: "CIC-IoT", Edge: "Edge-IIoT" };
const DEMO_ATTACKERS = { 1: "192.168.1.66", 2: "192.168.1.73", 3: "192.168.1.50", 4: "192.168.1.91" };
const DEMO_TICKS = 15;
const KIND = {
  jam: 1,
  spoof: 2, mitm: 2,
  dos: 3, synflood: 3, udpflood: 3, httpflood: 3,
  scan: 4, osfingerprint: 4, vulnscan: 4,
};
const REMOTE_IDLE_MS = 4000; // a remote attack ends once its device stops sending

// The live detector server (scripts/detector_server.py) runs the real model on the
// same host, port 8000. The dashboard subscribes to it and tells it which IPs to refuse.
const DETECTOR =
  typeof location !== "undefined" ? `${location.protocol}//${location.hostname}:8000` : "http://localhost:8000";
const bridge = (action, ip) =>
  fetch(`${DETECTOR}/api/${action}`, { method: "POST", body: JSON.stringify(ip ? { ip } : {}) }).catch(() => {});
const now = () => Date.now();

function ruleCommand(mode, ip, id) {
  if (mode === "windows")
    return `netsh advfirewall firewall add rule name="W-SENTRY_${id}" dir=in action=block remoteip=${ip} protocol=any`;
  if (mode === "wsl") return `iptables -A INPUT -s ${ip} -j DROP`;
  return `[dry run] netsh advfirewall firewall add rule name="W-SENTRY_${id}" dir=in action=block remoteip=${ip}`;
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
    this.protection = true; // W-SENTRY inspecting traffic
    this.auto = true; // random background attack episodes until a demo attack is launched
    this.demoSeq = 1;
    this.devices = new Map(); // attacker laptops seen by the network bridge
    this.connLog = [];
    this.bridgeInfo = { up: false };
    this.extra = { pps: 0, threats: 0 }; // remote packets since the last tick
    this.reset(false);
  }

  // Presenter-launched attack: a burst from an attacker whose records are
  // held-out test windows of that class, run through the normal detect/respond path.
  // Remote attacks are driven by packets arriving from another device instead of ticks.
  launch(cls, attacker = DEMO_ATTACKERS[cls], remote = false) {
    this.auto = false;
    if (this.demo?.active) this._endDemo();
    this.activeBlocks.delete(attacker);
    this.cooldowns.delete(attacker);
    bridge("unblock", attacker);
    this.demo = {
      id: this.demoSeq++, cls, attacker, protection: this.protection, active: true, remote,
      startedAt: now(), lastArrival: now(), sent: 0, reached: 0, blocked: 0,
      detectedAt: null, detectedAs: null, detectConf: null, detectedAfter: null,
      mitigatedAt: null, action: null, rule: null,
    };
    this.episode = { cls, attacker, ticksLeft: remote ? Infinity : DEMO_TICKS, manual: true, remote };
    if (!this.running) this.start();
    this._rebuild();
    this._emit();
  }
  setProtection(on) {
    this.protection = on;
    fetch(`${DETECTOR}/api/protection`, { method: "POST", body: JSON.stringify({ on }) }).catch(() => {});
    if (!on) {
      this.activeBlocks.clear();
    }
    this._rebuild();
    this._emit();
  }

  onBridge(msg) {
    if (msg.type === "hello") {
      this.bridgeInfo = { up: true, host: msg.host, ips: msg.ips };
      msg.devices.forEach((d) => this.devices.set(d.ip, d));
    } else if (msg.type === "connect") {
      this.devices.set(msg.device.ip, msg.device);
      this._log(msg.device, `connected · handshake OK${msg.device.via ? ` · found us by ${msg.device.via}` : ""}`);
    } else if (msg.type === "heartbeat") {
      this.devices.set(msg.device.ip, msg.device);
    } else if (msg.type === "attack") {
      this.devices.set(msg.device.ip, msg.device);
      this.ingest(msg);
      return;
    } else if (msg.type === "refused") {
      if (msg.device) this.devices.set(msg.device.ip, msg.device);
      this.refused(msg);
      return;
    } else if (msg.type === "protection") {
      this.protection = msg.on;
    } else if (msg.type === "unblock") {
      if (msg.ip) this.activeBlocks.delete(msg.ip);
      else this.activeBlocks.clear();
    }
    this._rebuild();
    this._emit();
  }
  setBridgeUp(up) {
    this.bridgeInfo = { ...this.bridgeInfo, up };
    this._rebuild();
    this._emit();
  }
  _log(device, text) {
    this.connLog.unshift({ ts: now(), ip: device.ip, name: device.name, text });
    if (this.connLog.length > 8) this.connLog.length = 8;
  }

  _ensureRemoteDemo(ip, cls, device) {
    if (this.demo?.active && this.demo.remote && this.demo.attacker === ip && this.demo.cls === cls) return this.demo;
    if (this.demo?.active) this._endDemo();
    this.auto = false;
    this.activeBlocks.delete(ip);
    this.demo = {
      id: this.demoSeq++, cls, attacker: ip, protection: this.protection, active: true, remote: true,
      startedAt: now(), lastArrival: now(), sent: 0, reached: 0, blocked: 0,
      detectedAt: null, detectedAs: null, detectConf: null, detectedAfter: null,
      mitigatedAt: null, action: null, rule: null,
    };
    this.episode = { cls, attacker: ip, ticksLeft: Infinity, manual: true, remote: true };
    if (device) this._log(device, `${(THREAT[cls] || {}).label} attack started`);
    if (!this.running) this.start();
    return this.demo;
  }

  // Attack over the network: the detector ran the REAL model on the artifacts
  // laptop B sent; `results` carries the model's actual per-artifact verdicts.
  ingest({ ip, kind, results, action, rule, device }) {
    const cls = KIND[kind];
    if (cls === undefined) return;
    const d = this._ensureRemoteDemo(ip, cls, device);
    d.lastArrival = now();
    for (const r of results || []) {
      const pkt = {
        id: this.packetSeq++, ts: now(), src: ip, dst: VICTIM,
        srcPort: rint(1024, 65535), dstPort: pick([80, 443, 53, 1883, 502]),
        proto: "live", length: 0, cls: r.cls, truth: cls,
        label: (THREAT[r.cls] || {}).label, confidence: r.conf, action: "—",
      };
      d.sent += 1;
      d.reached += 1;
      this._track(pkt);
      if (r.cls !== 0 && r.conf >= 0.85 && !d.detectedAt) {
        d.detectedAt = now(); d.detectedAs = r.cls; d.detectConf = r.conf; d.detectedAfter = d.sent;
      }
      this.packets.unshift(pkt);
      this.extra.pps += 1;
      if (r.cls !== 0) this.extra.threats += 1;
    }
    if (action && !d.mitigatedAt) {
      d.mitigatedAt = now(); d.action = action; d.rule = rule;
      const mc = d.detectedAs || d.cls;
      if (action !== "ALERT_ONLY")
        this.activeBlocks.set(ip, { ip, since: now(), until: now() + BLOCK_MS, action, cls: mc });
      this.mitigationLog.unshift({
        id: this.ruleSeq++, ts: now(), cls: mc, label: (THREAT[mc] || {}).label,
        src: ip, dst: VICTIM, action, rule, mode: this.mode, success: true,
      });
      if (this.mitigationLog.length > MAX_LOG) this.mitigationLog.length = MAX_LOG;
    }
    if (this.packets.length > MAX_PACKETS) this.packets.length = MAX_PACKETS;
    this._rebuild();
    this._emit();
  }

  // The detector refused a batch (403): this source is already blocked.
  refused({ ip, packets, device }) {
    const d =
      this.demo?.active && this.demo.remote && this.demo.attacker === ip
        ? this.demo
        : this._ensureRemoteDemo(ip, this.demo?.cls ?? 3, device);
    d.lastArrival = now();
    const n = Math.max(1, packets || 1);
    for (let k = 0; k < n; k++) {
      d.sent += 1;
      d.blocked += 1;
      this.packets.unshift({
        id: this.packetSeq++, ts: now(), src: ip, dst: VICTIM,
        srcPort: rint(1024, 65535), dstPort: pick([80, 443, 53, 1883, 502]),
        proto: "live", length: 0, cls: d.cls, truth: d.cls,
        state: "dropped", action: d.cls === 1 ? "CH-HOP" : "DROPPED",
      });
      this.extra.pps += 1;
    }
    if (this.packets.length > MAX_PACKETS) this.packets.length = MAX_PACKETS;
    this._rebuild();
    this._emit();
  }
  _endDemo() {
    this.demo.active = false;
    this.demo.endedAt = now();
    this.demoLog.unshift({ ...this.demo });
  }

  reset(notify = true) {
    this.packets = [];
    this.rateHistory = Array.from({ length: MAX_RATE }, (_, i) => ({ t: i - MAX_RATE, pps: 0, threats: 0 }));
    this.stats = { total: 0, inspected: 0, threats: 0, correct: 0, byClass: { 0: 0, 1: 0, 2: 0, 3: 0, 4: 0 } };
    this.demo = null;
    this.demoLog = [];
    this.connections = new Map();
    this.mitigationLog = [];
    this.activeBlocks = new Map();
    this.confidences = [];
    this.episode = null;
    this.cooldowns.clear();
    bridge("unblock");
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
      if (this.episode.ticksLeft <= 0) {
        if (this.episode.manual && this.demo?.active) this._endDemo();
        this.episode = null;
      }
    } else if (this.auto && Math.random() < 0.22) {
      this.episode = { cls: pick(ATTACK_TYPES), attacker: pick(ATTACKERS), ticksLeft: rint(3, 7) };
    }
  }

  loadReplay(data) {
    const byTruth = { 0: [], 1: [], 2: [], 3: [], 4: [] };
    data.truth.forEach((t, i) => byTruth[t].push(i));
    this.replay = { ...data, byTruth };
    this._rebuild();
    this._emit();
  }

  _replayPacket() {
    const ep = this.episode;
    const want = ep && !ep.remote && Math.random() < 0.78 ? ep.cls : 0;
    const pool = this.replay.byTruth[want].length ? this.replay.byTruth[want] : this.replay.byTruth[0];
    const attack = want !== 0;
    return this._fromRecord(
      pick(pool),
      attack ? ep.attacker : internalIp(),
      attack ? VICTIM : pick([internalIp(), VICTIM])
    );
  }

  _fromRecord(i, src, dst) {
    const cls = this.replay.pred[i];
    return {
      id: this.packetSeq++,
      ts: now(),
      src,
      dst,
      srcPort: rint(1024, 65535),
      dstPort: pick([80, 443, 53, 1883, 502]),
      proto: ORIGIN[this.replay.origin[i]] || this.replay.origin[i],
      length: 0,
      cls,
      truth: this.replay.truth[i],
      label: THREAT[cls].label,
      confidence: this.replay.conf[i],
      action: "—",
    };
  }

  _makePacket() {
    if (this.replay) return this._replayPacket();
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
    const rule = action === "ALERT_ONLY" ? `alert raised · sensor network hops to a clean channel (jamming from ${pkt.src})` : ruleCommand(this.mode, pkt.src, id);
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
      bridge("block", pkt.src);
    }
  }

  // Firewall first (blocked sources never reach the IDS), then the model, then
  // the mitigation engine. With protection off nothing is inspected.
  _process(pkt) {
    const d = this.demo?.active && pkt.src === this.demo.attacker ? this.demo : null;
    if (d) d.sent += 1;
    if (!this.protection) {
      pkt.state = "passed";
      pkt.action = "PASSED";
      if (d) d.reached += 1;
    } else if (this.activeBlocks.has(pkt.src) || (d && d.cls === 1 && d.mitigatedAt)) {
      pkt.state = "dropped";
      pkt.action = d && d.cls === 1 ? "CH-HOP" : "DROPPED";
      if (d) d.blocked += 1;
    } else {
      this._respond(pkt);
      if (d) {
        d.reached += 1;
        if (pkt.cls !== 0 && !d.detectedAt) {
          d.detectedAt = now();
          d.detectedAs = pkt.cls;
          d.detectConf = pkt.confidence;
          d.detectedAfter = d.sent;
        }
        if (pkt.action !== "—" && !d.mitigatedAt) {
          d.mitigatedAt = now();
          d.action = pkt.action;
          d.rule = this.mitigationLog[0]?.rule;
        }
      }
    }
    this._track(pkt);
  }

  _track(pkt) {
    this.stats.total += 1;
    if (pkt.state) return;
    this.stats.inspected += 1;
    if (pkt.truth !== undefined && pkt.truth === pkt.cls) this.stats.correct += 1;
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
    bridge("block", ip);
    this._rebuild();
    this._emit();
  }
  unblock(ip) {
    this.activeBlocks.delete(ip);
    bridge("unblock", ip);
    this._rebuild();
    this._emit();
  }
  clearRules() {
    this.activeBlocks.clear();
    bridge("unblock");
    this._rebuild();
    this._emit();
  }

  _tick() {
    if (this.demo?.active && this.demo.remote && now() - this.demo.lastArrival > REMOTE_IDLE_MS) {
      this._endDemo();
      this.episode = null;
    }
    this._maybeEpisode();
    let n = this.episode && !this.episode.remote ? rint(10, 26) : rint(2, 8);
    let threatsThisTick = 0;
    for (let i = 0; i < n; i++) {
      const pkt = this._makePacket();
      this._process(pkt);
      if (!pkt.state && pkt.cls !== 0) threatsThisTick += 1;
      this.packets.unshift(pkt);
    }
    if (this.packets.length > MAX_PACKETS) this.packets.length = MAX_PACKETS;
    // expire blocks
    for (const [ip, b] of this.activeBlocks)
      if (now() > b.until) {
        this.activeBlocks.delete(ip);
        bridge("unblock", ip);
      }
    n += this.extra.pps;
    threatsThisTick += this.extra.threats;
    this.extra = { pps: 0, threats: 0 };
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
      stats: { total: this.stats.total, inspected: this.stats.inspected, threats: this.stats.threats, correct: this.stats.correct, byClass: { ...this.stats.byClass } },
      protection: this.protection,
      demo: this.demo ? { ...this.demo } : null,
      demoLog: this.demoLog.slice(),
      devices: Array.from(this.devices.values()).sort((a, b) => b.lastSeen - a.lastSeen),
      connLog: this.connLog.slice(),
      bridge: this.bridgeInfo,
      replay: this.replay ? { n: this.replay.n, accuracy: this.replay.accuracy } : null,
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

// Held-out test windows classified by the deployed model (scripts/export_replay.py).
fetch(`${import.meta.env.BASE_URL}replay.json`)
  .then((r) => (r.ok ? r.json() : null))
  .then((data) => data && feed.loadReplay(data))
  .catch(() => {});

// Network bridge: devices connecting and attacking from another machine.
if (typeof EventSource !== "undefined") {
  const es = new EventSource(`${DETECTOR}/api/events`);
  es.onopen = () => feed.setBridgeUp(true);
  es.onerror = () => feed.setBridgeUp(false);
  es.onmessage = (e) => feed.onBridge(JSON.parse(e.data));
}

export function useFeed() {
  return useSyncExternalStore(
    (cb) => feed.subscribe(cb),
    () => feed.getSnapshot()
  );
}
