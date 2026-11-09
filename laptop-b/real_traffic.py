#!/usr/bin/env python3
"""Real attack traffic at the W-SENTRY demo board (laptop B). Stdlib only, no admin rights.
Only targets a private-network address whose W-SENTRY detector enforces a real firewall,
and stops after at most 60 seconds.

  py real_traffic.py udpflood [--duration 20] [--pps 2000] [--target IP]
  py real_traffic.py synflood [--duration 20] [--pps 1000] [--target IP]
  py real_traffic.py scan     [--pps 200] [--target IP]"""
import argparse
import ipaddress
import json
import os
import random
import socket
import sys
import threading
import time
import urllib.request

import attacker  # same folder: find_target() discovery


def demo_board(ip):
    """True only for a W-SENTRY detector that enforces a real firewall (the UNO Q), not a dry-run laptop."""
    try:
        with urllib.request.urlopen(f"http://{ip}:8000/api/hello", timeout=2) as r:
            js = json.loads(r.read() or b"{}")
        return js.get("wsentry") is True and js.get("enforce") == "iptables"
    except Exception:
        return False


def syn(ip, port):
    """One real TCP SYN: a non-blocking connect, abandoned at once (never waits for the reply)."""
    c = socket.socket()
    c.setblocking(False)
    try:
        c.connect_ex((ip, port))
    finally:
        c.close()


def paced(end, pps, send_one, sent):
    """Call send_one about pps times per second until end, or until it returns False."""
    while time.time() < end:
        t = time.time()
        for _ in range(25):
            try:
                if send_one() is False:
                    return
            except OSError:
                pass
            sent[0] += 1
        time.sleep(max(0.0, 25 / pps - (time.time() - t)))


def main():
    p = argparse.ArgumentParser(description="Real traffic at the W-SENTRY demo board")
    p.add_argument("mode", choices=["udpflood", "synflood", "scan"])
    p.add_argument("--target")
    p.add_argument("--duration", type=int, default=20)
    p.add_argument("--pps", type=int, default=0)
    a = p.parse_args()
    target = a.target or attacker.find_target(8000)[0]
    addr = ipaddress.ip_address(target)
    if not addr.is_private or addr.is_loopback or not demo_board(target):
        sys.exit(f"Refusing: {target} is not a private-network W-SENTRY board with its firewall enforcing.")
    duration = min(max(a.duration, 1), 60)
    end, sent = time.time() + duration, [0]
    if a.mode == "udpflood":
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        payload = os.urandom(512)

        def send_one():
            s.sendto(payload, (target, random.randint(1024, 65535)))
        pps = a.pps or 2000
    elif a.mode == "synflood":
        def send_one():
            syn(target, random.choice([80, 443, 23, 1883, 8080]))
        pps = a.pps or 1000
    else:
        ports = iter(random.sample(range(1, 1025), 1024))

        def send_one():
            port = next(ports, None)
            return False if port is None else syn(target, port)
        pps = a.pps or 200
    worker = threading.Thread(target=paced, args=(end, pps, send_one, sent), daemon=True)
    print(f"{a.mode} -> {target}, about {pps}/s for up to {duration}s (real packets: watch the board)")
    worker.start()
    last = 0
    while worker.is_alive():
        worker.join(1)
        print(f"  {time.strftime('%H:%M:%S')}  sent {sent[0]:,}  ({sent[0] - last:,}/s)")
        last = sent[0]
    print(f"done: {sent[0]:,} packets sent")


if __name__ == "__main__":
    main()
