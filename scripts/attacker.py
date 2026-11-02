#!/usr/bin/env python3
"""W-SENTRY attack console (demo). Sends small JSON POSTs to the dashboard server,
which renders them as simulated attack traffic. No real attack is performed.
Stdlib only."""
import argparse, json, os, platform, random, socket, sys, time
import urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor

try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

KINDS = {  # kind: (label, pool family, min pkts, max pkts)
    "dos": ("DoS flood (SYN/UDP/ICMP)", "dos", 8, 15),
    "synflood": ("TCP SYN flood", "dos", 8, 15),
    "udpflood": ("UDP flood", "dos", 8, 15),
    "httpflood": ("HTTP flood (DDoS)", "dos", 8, 15),
    "scan": ("Port scan", "scan", 2, 5),
    "osfingerprint": ("OS fingerprinting", "scan", 2, 5),
    "vulnscan": ("Vulnerability scan", "scan", 2, 5),
    "spoof": ("ARP/DNS spoofing", "spoof", 3, 6),
    "mitm": ("MITM (ARP + DNS spoof)", "spoof", 3, 6),
    "jam": ("RF jamming", "jam", 4, 8),
}

# Real held-out feature artifacts the detector's model classifies (made by
# scripts/make_attack_samples.py). The attacker sends the raw features; the
# model on the detector decides the class and whether to block.
SAMPLES = {}


def load_samples():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "attack_samples.json")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f).get("pools", {})
    except OSError:
        print("Warning: attack_samples.json not found next to attacker.py.")
        print("Run 'python scripts/make_attack_samples.py' on the W-SENTRY laptop and copy it here.")
        sys.exit(1)


def post(base, path, body):
    """Returns (status, json, rtt_ms). 403 returned as status, not raised."""
    req = urllib.request.Request(
        base + path, json.dumps(body).encode(), {"Content-Type": "application/json"}, method="POST")
    t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=3) as r:
            data, status = r.read(), r.status
    except urllib.error.HTTPError as e:
        data, status = e.read(), e.code
    try:
        js = json.loads(data or b"{}")
    except ValueError:
        js = {}
    return status, js, round((time.time() - t) * 1000)


def ts():
    return time.strftime("[%H:%M:%S]")


# --- Finding the W-SENTRY laptop on whatever network both machines are on ---
DISCOVERY_PORT = 50505
KNOWN_TARGET = "172.168.1.83"  # dashboard laptop's IP on the network used for the first test
SAVED = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".wsentry_target")


def is_wsentry(ip, port, timeout=0.6):
    try:
        with urllib.request.urlopen("http://%s:%d/api/hello" % (ip, port), timeout=timeout) as r:
            return json.loads(r.read() or b"{}").get("wsentry") is True
    except Exception:
        return False


def local_ips():
    ips = set()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # picks the outgoing interface; sends nothing
        ips.add(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    try:
        ips.update(socket.gethostbyname_ex(socket.gethostname())[2])
    except OSError:
        pass
    return [ip for ip in ips if not ip.startswith("127.")]


def by_broadcast(port, wait=2.0):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.settimeout(0.3)
    dests = {"255.255.255.255"} | {ip.rsplit(".", 1)[0] + ".255" for ip in local_ips()}
    end = time.time() + wait
    try:
        while time.time() < end:
            for d in dests:
                try:
                    s.sendto(b"WSENTRY_DISCOVER", (d, DISCOVERY_PORT))
                except OSError:
                    pass
            try:
                data, (addr, _) = s.recvfrom(1024)
                js = json.loads(data or b"{}")
                if js.get("wsentry"):
                    return addr, js.get("port", port)
            except (socket.timeout, ValueError, OSError):
                pass
    finally:
        s.close()
    return None


def by_scan(port):
    cands = []
    for ip in local_ips():
        net = ip.rsplit(".", 1)[0]
        cands += ["%s.%d" % (net, i) for i in range(1, 255) if "%s.%d" % (net, i) != ip]
    if not cands:
        return None
    with ThreadPoolExecutor(max_workers=96) as ex:
        for ip, ok in zip(cands, ex.map(lambda c: is_wsentry(c, port), cands)):
            if ok:
                return ip
    return None


def find_target(port):
    """Returns (ip, port, how it was found). Tries broadcast, saved/known IPs, then a subnet scan."""
    print("Searching for the W-SENTRY laptop on this network ...")
    hit = by_broadcast(port)
    if hit:
        return hit[0], hit[1], "LAN broadcast"
    saved = []
    if os.path.exists(SAVED):
        saved.append(open(SAVED).read().strip())
    for ip in saved + [KNOWN_TARGET]:
        if ip and is_wsentry(ip, port):
            return ip, port, "saved address"
    print("  no broadcast reply - scanning the local subnet ...")
    ip = by_scan(port)
    if ip:
        return ip, port, "subnet scan"
    print("\nCould not find W-SENTRY on this network.")
    print("Check: both laptops on the same Wi-Fi/hotspot, the dashboard is running, and")
    print("Windows Firewall on the dashboard laptop allows TCP %d and UDP %d." % (port, DISCOVERY_PORT))
    print("Or pass the IP directly:  python attacker.py <ip> <mode>")
    sys.exit(1)


def handshake(base, target, port, via=""):
    print("Connecting to %s:%d ..." % (target, port))
    try:
        st, js, rtt = post(base, "/api/connect",
                           {"name": socket.gethostname(), "os": platform.platform(), "via": via})
        if st != 200 or not js.get("ok"):
            raise OSError("unexpected response %s" % st)
    except Exception as e:
        print("\nCould not reach %s:%d (%s)" % (target, port, e))
        print("Check: both laptops on the same Wi-Fi/hotspot, the IP is correct, and")
        print("Windows Firewall allows Node.js on port %d on the dashboard laptop." % port)
        sys.exit(1)
    print("Connected to %s - handshake OK (RTT %d ms). This machine is %s."
          % (js.get("detector"), rtt, js.get("you")))
    try:
        with open(SAVED, "w") as f:
            f.write(target)
    except OSError:
        pass
    return js.get("you", "?")


def connect(base):
    print("Heartbeat every 2s. Ctrl+C to stop.")
    while True:
        try:
            st, js, rtt = post(base, "/api/heartbeat", {})
            print("%s <3 link alive (%d ms)%s" % (ts(), rtt, "  [blocked]" if js.get("blocked") else ""))
        except Exception as e:
            print("%s ! connection error: %s - retrying" % (ts(), e))
        time.sleep(2)


COMBO = ["scan", "osfingerprint", "spoof", "dos"]  # recon -> probe -> MITM -> flood


def combo(base, target, me, duration):
    """Multi-stage attack: several attack types back to back, so the model is
    shown classifying each distinct stage. Unblocks between stages so each shows."""
    dur = min(duration, 8)
    print("\nMulti-stage attack: reconnaissance -> OS probe -> spoofing -> DoS flood")
    for k in COMBO:
        print("\n----- stage: %s -----" % KINDS[k][0])
        post(base, "/api/unblock", {})
        attack(base, target, k, dur, me)
        time.sleep(1.0)
    print("\nMulti-stage attack complete. The model classified each stage on the dashboard.")


def before_after(base, target, kind, me, duration):
    """Run the attack with W-SENTRY OFF (before), then ON (after), toggling the
    real model via the detector so the dashboard flips live."""
    print("\n" + "=" * 52)
    print("  BEFORE  -  W-SENTRY OFF (no intrusion detection)")
    print("=" * 52)
    post(base, "/api/protection", {"on": False})
    post(base, "/api/unblock", {})
    attack(base, target, kind, duration, me)
    time.sleep(1.5)
    print("\n" + "=" * 52)
    print("  AFTER   -  W-SENTRY ON (model detects and blocks)")
    print("=" * 52)
    post(base, "/api/protection", {"on": True})
    post(base, "/api/unblock", {})
    attack(base, target, kind, duration, me)
    print("\nDone. Compare the two runs in the 'Before vs after W-SENTRY' table on the dashboard.")


def attack(base, target, kind, duration, me):
    label, fam, lo, hi = KINDS[kind]
    pool = SAMPLES.get(fam, [])
    if not pool:
        print("No sample artifacts for '%s' in attack_samples.json." % kind)
        sys.exit(1)
    sent = ok_pk = blk_pk = blocked = total = 0
    end = time.time() + duration
    print("Launching %s for %ds ...  (sending real feature artifacts; the model classifies them)\n"
          % (label, duration))
    while time.time() < end:
        n = random.randint(lo, hi)
        samples = [random.choice(pool) for _ in range(n)]
        try:
            st, js, _ = post(base, "/api/attack", {"kind": kind, "samples": samples})
            sent += 1
            if st == 403:
                blocked += 1
                blk_pk += n
                print("%s X BLOCKED by W-SENTRY - target refused (403)   (blocked %d)" % (ts(), blocked))
            else:
                ok_pk += n
                total += n
                verdict = ""
                if isinstance(js.get("classified"), list) and js["classified"]:
                    c = js["classified"][0]
                    verdict = "  model saw %s %d%%" % (c.get("label", "?"), round(c.get("conf", 0) * 100))
                print("%s -> %-15s %-22s +%-3d artifacts   delivered (total %d)%s"
                      % (ts(), target, label, n, total, verdict))
        except Exception as e:
            print("%s ! network error: %s - continuing" % (ts(), e))
        time.sleep(0.25)
    lines = ["Requests sent:     %d" % sent, "Packets delivered: %d" % ok_pk, "Packets blocked:   %d" % blk_pk,
             ("Attacker IP %s was BLOCKED by W-SENTRY" % me) if blocked else "Attack ran unblocked"]
    w = max(map(len, lines)) + 2
    print("\n+" + "-" * w + "+")
    for l in lines:
        print("| " + l.ljust(w - 1) + "|")
    print("+" + "-" * w + "+")


def main():
    modes = ["connect", "combo"] + list(KINDS)
    p = argparse.ArgumentParser(
        description="W-SENTRY attack console (demo traffic generator)",
        usage="attacker.py [target-ip] {%s} [--before-after] [--duration N] [--port P]" % ",".join(modes))
    p.add_argument("first", help="mode, or the dashboard laptop IP followed by a mode")
    p.add_argument("second", nargs="?", help=argparse.SUPPRESS)
    p.add_argument("--before-after", dest="before_after", action="store_true",
                   help="run the attack with W-SENTRY OFF, then ON, for the comparison")
    p.add_argument("--duration", type=int, default=20)
    p.add_argument("--port", type=int, default=8000)
    a = p.parse_args()
    target, mode = (a.first, a.second) if a.second else (None, a.first)
    if mode not in modes:
        p.error("mode must be one of: %s" % ", ".join(modes))
    print("=== W-SENTRY attack console ===")
    if mode != "connect":
        SAMPLES.update(load_samples())
    try:
        port, via = a.port, "manual IP"
        if not target:
            target, port, via = find_target(a.port)
            print("Found W-SENTRY at %s (by %s)" % (target, via))
        base = "http://%s:%d" % (target, port)
        me = handshake(base, target, port, via)
        if mode == "connect":
            connect(base)
        elif mode == "combo":
            combo(base, target, me, a.duration)
        elif a.before_after:
            before_after(base, target, mode, me, a.duration)
        else:
            attack(base, target, mode, a.duration, me)
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
