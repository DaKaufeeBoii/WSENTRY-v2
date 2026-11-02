"""
W-SENTRY live detector server (laptop A).

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
import json
import socket
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys

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


class Detector:
    def __init__(self):
        print("[detector] loading model (models/saved) ...")
        self.engine = InferenceEngine(model_dir=str(PROJECT_ROOT / "models" / "saved"))
        self.lock = threading.Lock()
        self.clients = []            # SSE wfile handles
        self.devices = {}            # ip -> device dict
        self.blocks = {}             # ip -> unblock_ts
        self.cooldown = {}           # ip -> last_rule_ts
        self.rule_seq = 1
        self.protection = True       # dashboard ON/OFF: when off, classify but never block
        print("[detector] model ready.")

    # --- model ---
    def classify(self, sequences):
        """sequences: list of (5,20). Returns list of (cls, conf)."""
        arr = np.asarray(sequences, dtype=np.float32)
        if arr.ndim == 2:
            arr = arr[None, ...]
        out = self.engine.predict_batch(arr)
        return [(int(c), float(conf)) for c, conf, _ in out]

    def is_blocked(self, ip):
        with self.lock:
            t = self.blocks.get(ip)
            if t and t < time.time():
                del self.blocks[ip]
                self.broadcast({"type": "unblock", "ip": ip})
                return False
            return t is not None

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
                self.blocks[ip] = now + BLOCK_SECONDS
                rule = (f'[dry run] netsh advfirewall firewall add rule '
                        f'name="W-SENTRY_{rid}" dir=in action=block remoteip={ip}')
            else:
                rule = f"alert raised - sensor network hops to a clean channel (RF jamming from {ip})"
        return action, rule, is_block

    # --- SSE ---
    def broadcast(self, msg):
        line = f"data: {json.dumps(msg)}\n\n".encode()
        dead = []
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
            return self._json(200, {"wsentry": True, "host": socket.gethostname()})
        if path == "/api/events":
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            hello = {"type": "hello", "host": socket.gethostname(),
                     "ips": lan_ips(), "devices": list(DET.devices.values())}
            try:
                self.wfile.write(f"data: {json.dumps(hello)}\n\n".encode())
                self.wfile.flush()
            except Exception:
                return
            DET.clients.append(self.wfile)
            try:
                while True:
                    time.sleep(15)
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
            DET.broadcast({"type": "attack", "ip": ip, "device": dev,
                           "kind": body.get("kind"), "results": results,
                           "action": action, "rule": rule})
            return self._json(200, {"ok": True, "classified": results,
                                    "action": action, "blocked": DET.is_blocked(ip)})

        if path == "/api/protection":
            DET.protection = bool(body.get("on", True))
            if not DET.protection:
                with DET.lock:
                    DET.blocks.clear()
                DET.broadcast({"type": "unblock"})
            DET.broadcast({"type": "protection", "on": DET.protection})
            return self._json(200, {"ok": True, "protection": DET.protection})
        if path == "/api/block":
            if body.get("ip"):
                with DET.lock:
                    DET.blocks[body["ip"]] = time.time() + BLOCK_SECONDS
            return self._json(200, {"ok": True})
        if path == "/api/unblock":
            with DET.lock:
                if body.get("ip"):
                    DET.blocks.pop(body["ip"], None)
                else:
                    DET.blocks.clear()
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


def main():
    global DET
    ap = argparse.ArgumentParser(description="W-SENTRY live detector server")
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()
    DET = Detector()
    threading.Thread(target=discovery_responder, args=(args.port,), daemon=True).start()
    srv = ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    ips = ", ".join(f"{i}:{args.port}" for i in lan_ips()) or f"localhost:{args.port}"
    print(f"[detector] listening on {ips}  (discovery UDP {DISCOVERY_PORT})")
    print("[detector] the dashboard and attacker connect here; the real model runs on every attack.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n[detector] stopped.")


if __name__ == "__main__":
    main()
