"""
W-SENTRY live detector server (laptop A / Arduino UNO Q).

Loads the REAL trained model (models/saved/hybrid_model.pt via InferenceEngine)
and runs it, live, on the feature artifacts the attacker laptop sends. The model
decides the class and confidence; the mitigation policy decides whether to block.
A blocked source is refused (HTTP 403) on its next attack, exactly like a firewall
rule taking effect. The dashboard subscribes to /api/events (SSE) and renders what
the model actually decided.

Nothing here performs a real network attack. The "attack" is feature vectors
(real held-out dataset records) sent over HTTP; this server classifies them.

Stdlib HTTP server + the project's own InferenceEngine. Run with the project venv
(needs torch): python scripts/detector_server.py
"""
import argparse
from collections import Counter
import hashlib
import ipaddress
import json
import math
import os
from pathlib import Path
import platform
import shutil
import signal
import socket
import struct
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.live.inference import InferenceEngine, THREAT_LABELS  # noqa: E402

DISCOVERY_PORT = 50505
CONF_THRESHOLD = 0.85
BLOCK_SECONDS = 45
COOLDOWN_SECONDS = 8

# model class -> (action, is_block). Jamming cannot be firewalled: alert only.
POLICY = {1: ("ALERT_ONLY", False), 2: ("BLOCK_IP", True),
          3: ("BLOCK + RATE_LIMIT", True), 4: ("BLOCK_IP", True)}

CHAIN = "WSENTRY"


class Firewall:
    """Kernel firewall on Linux (iptables), or a dry run that only describes the rule.

    In iptables mode a blocked source keeps access to the W-SENTRY API port, so laptop B
    still gets HTTP 403 and its menu (combo, before/after) keeps working. Every other
    packet from that source is dropped by the kernel (ping, real scans, real floods)."""

    def __init__(self, mode="dryrun", port=8000, run=subprocess.run, which=shutil.which):
        self.mode, self.port, self.run = mode, port, run
        if mode != "iptables":
            return
        if not which("iptables"):
            raise SystemExit("[firewall] iptables not found. On the board: sudo apt-get install -y iptables")
        self._ipt("-N", CHAIN)                               # create; harmless error if it exists
        self._ipt("-F", CHAIN)                               # start empty: no stale blocks
        if self._ipt("-C", "INPUT", "-j", CHAIN).returncode != 0:
            self._ipt("-I", "INPUT", "1", "-j", CHAIN)       # our chain is checked first

    def _ipt(self, *args):
        return self.run(["iptables", "-w", *args], capture_output=True, text=True)

    def _rules(self, ip):
        return [["-s", ip, "-p", "tcp", "--dport", str(self.port), "-j", "RETURN"],
                ["-s", ip, "-j", "DROP"]]

    def describe(self, ip, rid):
        if self.mode == "iptables":
            return f"iptables -A {CHAIN} -s {ip} -j DROP   (W-SENTRY_{rid}, enforced on {platform.node()})"
        return (f'[dry run] netsh advfirewall firewall add rule '
                f'name="W-SENTRY_{rid}" dir=in action=block remoteip={ip}')

    def block(self, ip):
        if self.mode != "iptables":
            return
        for r in self._rules(ip):
            res = self._ipt("-A", CHAIN, *r)
            if res.returncode != 0:
                print(f"[firewall] could not block {ip}: {res.stderr.strip()}")

    def unblock(self, ip):
        if self.mode == "iptables":
            for r in self._rules(ip):
                self._ipt("-D", CHAIN, *r)

    def clear(self):
        if self.mode == "iptables":
            self._ipt("-F", CHAIN)

    def listing(self):
        """Live rules in our chain (iptables -S WSENTRY). Served by /api/status, so checks need no sudo."""
        if self.mode != "iptables":
            return []
        return self._ipt("-S", CHAIN).stdout.splitlines()

    def dropped(self):
        """Packets dropped so far by our DROP rules (kernel counters). Resets when rules are removed."""
        if self.mode != "iptables":
            return 0
        return parse_drops(self._ipt("-L", CHAIN, "-v", "-x", "-n").stdout)

    def teardown(self):
        if self.mode == "iptables":
            self._ipt("-F", CHAIN)
            self._ipt("-D", "INPUT", "-j", CHAIN)
            self._ipt("-X", CHAIN)


class Detector:
    def __init__(self, fw=None, engine=None):
        if engine is None:
            print("[detector] loading model (models/saved) ...")
            self.engine = InferenceEngine(model_dir=str(PROJECT_ROOT / "models" / "saved"))
            print("[detector] model ready.")
        else:
            self.engine = engine
        self.fw = fw or Firewall("dryrun")
        self.lock = threading.RLock()
        self.sse_lock = threading.Lock()
        self.last = None
        self.own_ips = set(lan_ips())
        self.infer = {"count": 0, "last_ms": 0.0, "avg_ms": 0.0}
        self.traffic = {}
        self.device = {}
        self.clients = []            # SSE wfile handles
        self.devices = {}            # ip -> device dict
        self.blocks = {}             # ip -> unblock_ts
        self.cooldown = {}           # ip -> last_rule_ts
        self.rule_seq = 1
        self.protection = True       # dashboard ON/OFF: when off, classify but never block

    # --- model ---
    def classify(self, sequences):
        """sequences: list of (5,20). Returns list of (cls, conf)."""
        arr = np.asarray(sequences, dtype=np.float32)
        if arr.ndim == 2:
            arr = arr[None, ...]
        t0 = time.perf_counter()
        out = self.engine.predict_batch(arr)
        ms = (time.perf_counter() - t0) * 1000 / len(arr)
        i = self.infer
        i["count"] += len(arr)
        i["last_ms"] = round(ms, 2)
        i["avg_ms"] = round(ms if i["count"] == len(arr) else 0.9 * i["avg_ms"] + 0.1 * ms, 2)
        return [(int(c), float(conf)) for c, conf, _ in out]

    def is_blocked(self, ip):
        with self.lock:
            return ip in self.blocks

    def block(self, ip):
        """Block ip for BLOCK_SECONDS. The kernel rule is added only on the first block."""
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            return False                                  # trust boundary: /api/block takes any string
        if self.fw.mode == "iptables" and (addr.is_loopback or addr.is_unspecified or ip in self.own_ips):
            return False                                  # never firewall the board itself
        with self.lock:
            if ip not in self.blocks:
                self.fw.block(ip)
            self.blocks[ip] = time.time() + BLOCK_SECONDS
        return True

    def manual_block(self, ip):
        """/api/block. When enforcing, only devices that really connected can be firewalled:
        the dashboard's idle simulation posts made-up attacker IPs here."""
        if self.fw.mode == "iptables" and ip not in self.devices:
            return False
        return self.block(ip)

    def unblock(self, ip=None):
        """Unblock one ip, or everything when ip is None."""
        with self.lock:
            if ip is None:
                self.blocks.clear()
                self.fw.clear()
            elif self.blocks.pop(ip, None) is not None:
                self.fw.unblock(ip)

    def expire(self):
        """Release every block whose time ran out. Returns the released IPs."""
        now = time.time()
        with self.lock:
            gone = [ip for ip, t in self.blocks.items() if t < now]
            for ip in gone:
                self.unblock(ip)
        return gone

    def set_protection(self, on):
        """One path for the dashboard toggle, laptop B's before/after and the board's button."""
        self.protection = bool(on)
        if not self.protection:
            self.unblock()
            self.broadcast({"type": "unblock"})
        self.broadcast({"type": "protection", "on": self.protection})

    def board_state(self):
        """One word for the board's lights: off | blocked | alert | safe."""
        with self.lock:
            if not self.protection:
                return "off"
            if self.blocks:
                return "blocked"
            if self.last and time.time() - self.last["ts"] < 3:
                return "alert"
            return "safe"

    def lights_frame(self):
        """[state, attack, level] for the LED matrix. level = packets/s into the board, 0-8, log scale."""
        attack = ATTACK_CODES.get((self.last or {}).get("label"), 0)
        level = min(8, int(math.log10(self.traffic.get("rx_pps", 0) + 1) * 8 / 3))
        return [LIGHT_CODES[self.board_state()], attack, level]

    def mitigate(self, ip, cls, conf):
        """Returns (action, rule, blocked) or None if no action."""
        if not self.protection or cls <= 0 or conf < CONF_THRESHOLD:
            return None
        now = time.time()
        with self.lock:
            if now - self.cooldown.get(ip, 0) < COOLDOWN_SECONDS and ip in self.blocks:
                return None
            self.cooldown[ip] = now
            action, is_block = POLICY.get(cls, ("ALERT_ONLY", False))
            rid = self.rule_seq
            self.rule_seq += 1
            if is_block:
                self.block(ip)
                rule = self.fw.describe(ip, rid)
            else:
                rule = f"alert raised - sensor network hops to a clean channel (RF jamming from {ip})"
        return action, rule, is_block

    # --- SSE ---
    def broadcast(self, msg):
        line = f"data: {json.dumps(msg)}\n\n".encode()
        dead = []
        with self.sse_lock:
            for w in list(self.clients):
                try:
                    w.write(line)
                    w.flush()
                except Exception:
                    dead.append(w)
            for w in dead:
                if w in self.clients:
                    self.clients.remove(w)

    def seen(self, ip, extra=None):
        d = self.devices.get(ip, {"ip": ip, "name": ip})
        if extra:
            d.update(extra)
        d["lastSeen"] = int(time.time() * 1000)
        self.devices[ip] = d
        return d


DET = None

ATTACK_CODES = {"Jamming": 1, "Spoofing": 2, "DoS_Flood": 3, "Intrusion_Probe": 4}


def _read(path):
    try:
        with open(path) as f:
            return f.read().strip().strip("\x00")
    except OSError:
        return ""


def parse_net_dev(text, iface):
    """rx packet counter of iface from /proc/net/dev."""
    for line in text.splitlines():
        name, sep, rest = line.partition(":")
        if sep and name.strip() == iface:
            return int(rest.split()[1])
    return 0


def parse_in_delivers(text):
    """Ip InDelivers from /proc/net/snmp: packets handed to TCP/UDP/ICMP, i.e. after the firewall."""
    rows = [l.split() for l in text.splitlines() if l.startswith("Ip:")]
    return int(rows[1][rows[0].index("InDelivers")]) if len(rows) >= 2 else 0


def parse_drops(text):
    """Sum of the packet counters of DROP rules in `iptables -L WSENTRY -v -x -n` output."""
    total = 0
    for line in text.splitlines():
        f = line.split()
        if len(f) > 2 and f[0].isdigit() and f[2] == "DROP":
            total += int(f[0])
    return total


def _default_route():
    """(iface, gateway) of the IPv4 default route from /proc/net/route, or (None, None)."""
    for line in _read("/proc/net/route").splitlines()[1:]:
        f = line.split()
        if len(f) > 2 and f[1] == "00000000":
            return f[0], socket.inet_ntoa(struct.pack("<I", int(f[2], 16)))
    return None, None


def device_info():
    """Identity of the machine this detector runs on, read from its own kernel."""
    parts = [l.split(":", 1)[1].strip() for l in _read("/proc/cpuinfo").splitlines() if l.startswith("CPU part")]
    core = {"0xd03": "Cortex-A53", "0xd05": "Cortex-A55"}.get(parts[0], parts[0]) if parts else platform.processor()
    os_name = next((l.split("=", 1)[1].strip('"') for l in _read("/etc/os-release").splitlines()
                    if l.startswith("PRETTY_NAME=")), platform.platform())
    sha = hashlib.sha256((PROJECT_ROOT / "models" / "saved" / "hybrid_model.pt").read_bytes()).hexdigest()
    return {"board": _read("/proc/device-tree/model") or platform.node(),
            "soc": _read("/sys/devices/soc0/machine"),
            "cpu": f"{len(parts) or os.cpu_count()} x {core}",
            "arch": platform.machine(), "os": os_name, "host": socket.gethostname(),
            "model_sha": sha[:16]}


def lan_ips():
    ips = set()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ips.add(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    try:
        ips.update(socket.gethostbyname_ex(socket.gethostname())[2])
    except OSError:
        pass
    return [i for i in ips if not i.startswith("127.")]


def sweeper():
    """Expire blocks every second, even when the blocked source has gone silent."""
    while True:
        time.sleep(1)
        for ip in DET.expire():
            DET.broadcast({"type": "unblock", "ip": ip})


def traffic_loop(iface):
    """Once a second: packets into the board, packets that reached the OS, packets the firewall dropped."""
    prev, dropped_total = None, 0
    while True:
        try:
            now = (parse_net_dev(_read("/proc/net/dev"), iface),
                   parse_in_delivers(_read("/proc/net/snmp")), DET.fw.dropped())
        except Exception as e:                       # never let stats kill the detector
            print(f"[traffic] {e}")
            now = prev
        if prev and now:
            rx, dl, dr = (max(0, a - b) for a, b in zip(now, prev))
            dropped_total += dr
            DET.traffic = {"iface": iface, "rx_pps": rx, "delivered_pps": dl,
                           "dropped_pps": dr, "dropped_total": dropped_total}
        prev = now
        time.sleep(1)


LIGHT_CODES = {"safe": 0, "alert": 1, "blocked": 2, "off": 3}


def lights_loop():
    """Mirror the detector onto the LED matrix and read the board's firewall button. Never raises."""
    sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "unoq"))
    presses = None
    while True:
        try:
            from bridge_ping import bridge_call
            bridge_call("wsentry_show", *DET.lights_frame())
            n = bridge_call("wsentry_presses")
            if presses is not None and n > presses:     # '>' not '!=': a sketch restart resets the count
                DET.set_protection(not DET.protection)
                print(f"[lights] board button -> firewall {'ON' if DET.protection else 'OFF'}")
            presses = n
        except Exception as e:                       # lights must never break detection
            print(f"[lights] bridge call failed: {e}")
            time.sleep(2)
        time.sleep(0.25)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    @property
    def ip(self):
        return self.client_address[0].replace("::ffff:", "")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/api/hello":
            return self._json(200, {"wsentry": True, "host": socket.gethostname(),
                                    "arch": platform.machine(), "enforce": DET.fw.mode,
                                    "board": DET.device.get("board")})
        if path == "/api/status":
            with DET.lock:
                blocked = sorted(DET.blocks)
            return self._json(200, {"wsentry": True, "host": socket.gethostname(),
                                    "arch": platform.machine(), "enforce": DET.fw.mode,
                                    "protection": DET.protection, "blocked": blocked,
                                    "last": DET.last, "state": DET.board_state(),
                                    "rules": DET.fw.listing(), "device": DET.device,
                                    "inference": DET.infer, "traffic": DET.traffic,
                                    "lights": DET.lights_frame()})
        if path == "/api/events":
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            hello = {"type": "hello", "host": socket.gethostname(),
                     "arch": platform.machine(), "enforce": DET.fw.mode,
                     "board": DET.device.get("board"),
                     "ips": lan_ips(), "devices": list(DET.devices.values())}
            try:
                self.wfile.write(f"data: {json.dumps(hello)}\n\n".encode())
                self.wfile.flush()
            except Exception:
                return
            self.connection.settimeout(2)
            DET.clients.append(self.wfile)
            try:
                while True:
                    time.sleep(15)
                    with DET.sse_lock:
                        self.wfile.write(b": ping\n\n")
                        self.wfile.flush()
            except Exception:
                if self.wfile in DET.clients:
                    DET.clients.remove(self.wfile)
            return
        self._json(404, {"error": "not found"})

    def _body(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        try:
            return json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return {}

    def do_POST(self):
        path = self.path.split("?")[0]
        ip = self.ip
        body = self._body()

        if path == "/api/connect":
            dev = DET.seen(ip, {"name": body.get("name", ip), "os": body.get("os", ""),
                                "via": body.get("via", ""), "connectedAt": int(time.time() * 1000)})
            DET.broadcast({"type": "connect", "device": dev})
            return self._json(200, {"ok": True, "detector": socket.gethostname(), "you": ip})

        if path == "/api/heartbeat":
            DET.broadcast({"type": "heartbeat", "device": DET.seen(ip)})
            return self._json(200, {"ok": True, "blocked": DET.is_blocked(ip)})

        if path == "/api/attack":
            dev = DET.seen(ip)
            if DET.protection and DET.is_blocked(ip):
                DET.broadcast({"type": "refused", "ip": ip, "device": dev,
                               "packets": len(body.get("samples") or [])})
                return self._json(403, {"blocked": True})
            seqs = body.get("samples") or []
            if not seqs:
                return self._json(400, {"error": "no samples"})
            results = []
            action = rule = None
            for (cls, conf) in DET.classify(seqs):
                r = {"cls": cls, "conf": round(conf, 3), "label": THREAT_LABELS.get(cls, "?")}
                m = DET.mitigate(ip, cls, conf)
                if m and not action:
                    action, rule, _ = m
                results.append(r)
            threats = [r for r in results if r["cls"] > 0]
            if threats:
                top = max(threats, key=lambda r: r["conf"])
                DET.last = {**top, "ip": ip, "ts": time.time()}
            DET.broadcast({"type": "attack", "ip": ip, "device": dev,
                           "kind": body.get("kind"), "results": results,
                           "action": action, "rule": rule})
            return self._json(200, {"ok": True, "classified": results,
                                    "action": action, "blocked": DET.is_blocked(ip)})

        if path == "/api/protection":
            DET.set_protection(body.get("on", True))
            return self._json(200, {"ok": True, "protection": DET.protection})
        if path == "/api/block":
            ok = DET.manual_block(str(body["ip"])) if body.get("ip") else False
            return self._json(200, {"ok": ok})
        if path == "/api/unblock":
            DET.unblock(body.get("ip") or None)
            return self._json(200, {"ok": True})
        self._json(404, {"error": "not found"})


def discovery_responder(http_port):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind(("", DISCOVERY_PORT))
    except OSError as e:
        print(f"[detector] discovery disabled: {e}")
        return
    reply = json.dumps({"wsentry": True, "host": socket.gethostname(), "port": http_port}).encode()
    while True:
        try:
            data, addr = s.recvfrom(1024)
            if data.strip() == b"WSENTRY_DISCOVER":
                s.sendto(reply, addr)
        except OSError:
            break


LIVE_SKIP_PORTS = {8000, 22}                  # control channel (dashboard, attacker API) and SSH
FAMILY = {1: "jam", 2: "spoof", 3: "dos", 4: "scan"}


def live_loop(iface, block_packets, never_block):
    """--mode live: sniff real frames on iface, classify them with the same model, block the top source."""
    from src.features.ciciot_features import _parse
    from src.live.cic_live import CicLive, top_source
    live = CicLive(PROJECT_ROOT / "models" / "saved" / "scaler.json", block_packets)
    s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(0x0003))
    s.bind((iface, 0))
    print(f"[live] sniffing {iface}, {block_packets}-packet blocks; never blocking {sorted(never_block)}")
    batch, incoming, start, last_emit = [], [], time.time(), 0.0
    while True:
        buf, addr = s.recvfrom(65535)
        p = _parse(buf)
        if p and p[0] == "ip" and p[2]["l4"] and p[2]["l4"][0] == "tcp" \
                and {p[2]["l4"][1], p[2]["l4"][2]} & LIVE_SKIP_PORTS:
            continue
        frame = (time.time(), buf)
        batch.append(frame)                        # features: both directions, like the dataset capture
        if addr[2] != socket.PACKET_OUTGOING:
            incoming.append(frame)                 # attribution: only what arrived from outside; the board's
        if len(batch) < 10 * block_packets and time.time() - start < 1.0:   # own RST replies would halve shares
            continue
        frames, inc, batch, incoming, start = batch, incoming, [], [], time.time()
        try:
            ip, share = top_source(inc, exclude=DET.own_ips | never_block)
            attributed = ip is not None and share >= 0.5
            if attributed and DET.protection and DET.is_blocked(ip):
                # AF_PACKET sees packets before netfilter: the kernel is already dropping these.
                if time.time() - last_emit >= 1.0:
                    last_emit = time.time()
                    DET.broadcast({"type": "refused", "ip": ip, "device": DET.seen(ip),
                                   "packets": min(len(inc), 50)})
                continue
            wins = live.windows(frames)
            if not len(wins):
                continue
            results = DET.classify(wins)
            threats = [(c, q) for c, q in results if c > 0]
            if not threats:
                continue
            action = rule = None
            if attributed:
                c, conf = max(threats, key=lambda t: t[1])
                DET.last = {"cls": c, "conf": round(conf, 3), "label": THREAT_LABELS.get(c, "?"),
                            "ip": ip, "ts": time.time()}
                m = DET.mitigate(ip, c, conf)
                if m:
                    action, rule, _ = m
            print(f"[live] {time.strftime('%H:%M:%S')} frames={len(frames)} in={len(inc)} top={ip} "
                  f"share={share:.2f} classes={dict(Counter(c for c, _ in results))} action={action}")
            if attributed and (action or time.time() - last_emit >= 1.0):   # at most ~1 event/s
                last_emit = time.time()
                fam = FAMILY[Counter(c for c, _ in threats).most_common(1)[0][0]]
                DET.broadcast({"type": "attack", "ip": ip, "device": DET.seen(ip), "kind": fam,
                               "source": "live", "action": action, "rule": rule,
                               "results": [{"cls": c, "conf": round(q, 3), "label": THREAT_LABELS.get(c, "?")}
                                           for c, q in results]})
        except Exception as e:                    # one bad batch must not stop the sniffer
            print(f"[live] batch skipped: {e}")


def _stop(*_):
    raise KeyboardInterrupt                           # SIGTERM (systemd) -> same cleanup as Ctrl+C


def main():
    global DET
    ap = argparse.ArgumentParser(description="W-SENTRY live detector server")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--enforce", choices=["dryrun", "iptables"], default="dryrun",
                    help="iptables: real kernel rule on Linux (needs root). dryrun: only show the rule (default).")
    ap.add_argument("--threads", type=int, default=0, help="torch CPU threads (0 = torch default; use 4 on the UNO Q)")
    ap.add_argument("--lights", choices=["none", "bridge"], default="none",
                    help="bridge: mirror state onto the UNO Q LED matrix")
    ap.add_argument("--iface", default=None, help="interface to count packets on (default: the default route's)")
    ap.add_argument("--mode", choices=["replay", "live"], default="replay",
                    help="live: sniff real network packets on iface and classify them. replay: classify records over HTTP.")
    ap.add_argument("--block-packets", type=int, default=100, help="packets per block in live mode (default: 100)")
    ap.add_argument("--never-block", default="", help="comma-separated IPs never to block in live mode")
    args = ap.parse_args()
    if (args.enforce == "iptables" or args.mode == "live") and hasattr(os, "geteuid") and os.geteuid() != 0:
        raise SystemExit("[detector] --enforce iptables / --mode live needs root. On the board run: bash scripts/unoq/run_detector.sh")
    if args.threads:
        import torch
        torch.set_num_threads(args.threads)
    fw = Firewall(args.enforce, port=args.port)
    DET = Detector(fw=fw)
    DET.device = device_info()
    iface = args.iface or _default_route()[0] or "wlan0"
    threading.Thread(target=traffic_loop, args=(iface,), daemon=True).start()
    if args.mode == "live":
        gw = _default_route()[1]
        never = {ip.strip() for ip in args.never_block.split(",") if ip.strip()} | ({gw} if gw else set())
        threading.Thread(target=live_loop, args=(iface, args.block_packets, never), daemon=True).start()
    signal.signal(signal.SIGTERM, _stop)
    threading.Thread(target=discovery_responder, args=(args.port,), daemon=True).start()
    threading.Thread(target=sweeper, daemon=True).start()
    if args.lights == "bridge":
        threading.Thread(target=lights_loop, daemon=True).start()
    srv = ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    ips = ", ".join(f"{i}:{args.port}" for i in lan_ips()) or f"localhost:{args.port}"
    print(f"[detector] listening on {ips}  (discovery UDP {DISCOVERY_PORT})  "
          f"enforce={args.enforce}  arch={platform.machine()}  iface={iface}  board={DET.device['board']}")
    print("[detector] the dashboard and attacker connect here; the real model runs on every attack.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n[detector] stopped.")
    finally:
        fw.teardown()
        if args.enforce == "iptables":
            print("[detector] firewall chain WSENTRY removed.")


if __name__ == "__main__":
    main()
