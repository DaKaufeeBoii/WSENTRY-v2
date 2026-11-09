"""Full-screen W-SENTRY status on the UNO Q's own monitor (SBC mode). Stdlib only.
   python3 ~/w-sentry/scripts/unoq/console.py        (q quits)"""
import curses
import json
import math
import time
import urllib.request

URL = "http://127.0.0.1:8000/api/status"
STATE = {"safe": ("PROTECTED - inspecting traffic, no attack", 1), "alert": ("ATTACK DETECTED", 3),
         "blocked": ("ATTACKER BLOCKED BY THE KERNEL FIREWALL", 2), "off": ("FIREWALL OFF - traffic is NOT inspected", 4)}
NAMES = {"DoS_Flood": "DDoS / DoS flood", "Intrusion_Probe": "port scan / probe",
         "Spoofing": "spoofing / MITM", "Jamming": "RF jamming"}


def fetch():
    try:
        with urllib.request.urlopen(URL, timeout=1) as r:
            return json.loads(r.read())
    except Exception:
        return None


def bar(v, width):
    return "#" * int(min(1.0, math.log10(v + 1) / 3.5) * width)    # log scale: ~3000/s fills it


def draw(scr, s):
    scr.erase()
    h, w = scr.getmaxyx()

    def put(y, x, text, attr=0):
        if 0 <= y < h and x < w - 1:
            scr.addnstr(y, x, text, w - x - 1, attr)

    if not s:
        put(1, 2, "W-SENTRY detector not reachable on 127.0.0.1:8000 - start scripts/unoq/run_detector.sh",
            curses.color_pair(3) | curses.A_BOLD)
        scr.refresh()
        return
    d, inf, t = s.get("device") or {}, s.get("inference") or {}, s.get("traffic") or {}
    put(0, 2, f"W-SENTRY on {d.get('board', '?')}  |  SoC {d.get('soc') or '?'}  |  {d.get('cpu', '?')}  |  "
              f"{d.get('arch', '?')}  |  {d.get('os', '?')}  |  host {d.get('host', '?')}", curses.A_BOLD)
    put(1, 2, f"model sha256 {d.get('model_sha', '?')}  |  inferences on this board: {inf.get('count', 0):,}  |  "
              f"{inf.get('last_ms', 0):.1f} ms last, {inf.get('avg_ms', 0):.1f} ms avg")
    on = s.get("protection")
    put(3, 2, f"FIREWALL: {'ON ' if on else 'OFF'}   ({s.get('enforce')}, chain WSENTRY)   - press the button on the board to toggle",
        curses.color_pair(1 if on else 4) | curses.A_BOLD)
    text, col = STATE.get(s.get("state"), ("?", 4))
    put(5, 2, f"  {text}  ", curses.color_pair(col) | curses.A_BOLD | curses.A_REVERSE)
    last = s.get("last")
    if last:
        put(6, 2, f"ATTACK: {NAMES.get(last.get('label'), last.get('label'))} ({last.get('label')})  "
                  f"confidence {last.get('conf', 0) * 100:.0f}%  from {last.get('ip')}  "
                  f"{time.time() - last.get('ts', time.time()):.0f} s ago")
    bw = max(10, w - 48)
    put(8, 2, f"packets in ({t.get('iface', '?')})  {t.get('rx_pps', 0):>9,} /s  {bar(t.get('rx_pps', 0), bw)}")
    put(9, 2, f"reached the OS       {t.get('delivered_pps', 0):>9,} /s  {bar(t.get('delivered_pps', 0), bw)}",
        curses.color_pair(3))
    put(10, 2, f"dropped by W-SENTRY  {t.get('dropped_pps', 0):>9,} /s  {bar(t.get('dropped_pps', 0), bw)}"
               f"   total {t.get('dropped_total', 0):,}", curses.color_pair(2))
    put(12, 2, "kernel rules right now (iptables -S WSENTRY):", curses.A_BOLD)
    for i, r in enumerate((s.get("rules") or ["(firewall not enforcing)"])[:6]):
        put(13 + i, 4, r)
    put(h - 1, 2, "q quits  |  every number here is read from this board's kernel and the model running on this board")
    scr.refresh()


def main(scr):
    curses.curs_set(0)
    scr.nodelay(True)
    curses.start_color()
    curses.use_default_colors()
    for i, c in enumerate([curses.COLOR_GREEN, curses.COLOR_RED, curses.COLOR_YELLOW, curses.COLOR_WHITE], 1):
        curses.init_pair(i, c, -1)
    while scr.getch() not in (ord("q"), ord("Q")):
        draw(scr, fetch())
        time.sleep(0.5)


if __name__ == "__main__":
    curses.wrapper(main)
