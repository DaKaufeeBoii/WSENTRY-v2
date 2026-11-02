#!/usr/bin/env python3
"""W-SENTRY attacker - simple text menu (laptop B).

Finds the W-SENTRY laptop on the network, keeps the link alive, and lets the
presenter launch each attack by picking a number. No commands to type.

Run:  python menu.py      (or double-click run.cmd on Windows)
"""
import sys
import threading
import time

import attacker  # the client in this same folder

HEARTBEAT = True


def heartbeat(base):
    """Keep this device showing ONLINE on the dashboard."""
    while HEARTBEAT:
        try:
            attacker.post(base, "/api/heartbeat", {})
        except Exception:
            pass
        time.sleep(2)


MENU = [
    ("DoS flood", "dos"),
    ("SYN flood", "synflood"),
    ("UDP flood", "udpflood"),
    ("Port scan", "scan"),
    ("OS fingerprinting", "osfingerprint"),
    ("Spoofing / MITM", "spoof"),
    ("Jamming (RF)", "jam"),
    ("Multi-stage combo (recon -> probe -> spoof -> DoS)", "combo"),
    ("Before vs after W-SENTRY (pick a type)", "beforeafter"),
]


def banner(target, me, host):
    print("\n" + "=" * 54)
    print("  W-SENTRY  -  ATTACKER CONSOLE  (laptop B)")
    print("=" * 54)
    print("  detector : %s  (%s)" % (host, target))
    print("  this pc  : %s   [ONLINE - heartbeat every 2s]" % me)
    print("=" * 54)


def ask_duration(default=15):
    raw = input("  Duration in seconds [%d]: " % default).strip()
    try:
        return max(2, int(raw))
    except ValueError:
        return default


def main():
    print("=== W-SENTRY attacker menu ===")
    attacker.SAMPLES.update(attacker.load_samples())

    # Find the detector (or let the user type its IP).
    manual = ""
    if len(sys.argv) > 1:
        manual = sys.argv[1]
    try:
        if manual:
            target, port, via = manual, 8000, "manual IP"
        else:
            target, port, via = attacker.find_target(8000)
    except SystemExit:
        ip = input("\n  Could not find it. Type the W-SENTRY laptop IP (or Enter to quit): ").strip()
        if not ip:
            return
        target, port, via = ip, 8000, "manual IP"

    base = "http://%s:%d" % (target, port)
    me = attacker.handshake(base, target, port, via)
    host = "W-SENTRY"
    threading.Thread(target=heartbeat, args=(base,), daemon=True).start()

    while True:
        banner(target, me, host)
        for i, (label, _) in enumerate(MENU, 1):
            print("  %d. %s" % (i, label))
        print("  0. Quit")
        choice = input("\n  Choose an attack [0-%d]: " % len(MENU)).strip()

        if choice in ("0", "q", "quit", ""):
            break
        if not choice.isdigit() or not (1 <= int(choice) <= len(MENU)):
            print("  Not a valid option.")
            continue

        _, kind = MENU[int(choice) - 1]
        try:
            if kind == "combo":
                attacker.combo(base, target, me, ask_duration(6))
            elif kind == "beforeafter":
                print("\n  Which attack to compare?")
                types = ["dos", "scan", "spoof", "jam"]
                for i, t in enumerate(types, 1):
                    print("   %d. %s" % (i, attacker.KINDS[t][0]))
                c = input("  Type [1-%d]: " % len(types)).strip()
                t = types[int(c) - 1] if c.isdigit() and 1 <= int(c) <= len(types) else "dos"
                attacker.before_after(base, target, t, me, ask_duration())
            else:
                attacker.attack(base, target, kind, ask_duration(), me)
        except KeyboardInterrupt:
            print("\n  (attack stopped)")
        input("\n  --- done. Press Enter for the menu ---")

    print("\n  Bye.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
