"""Call functions the UNO Q sketch registered with Bridge.provide, from plain Linux Python.
   Test: sudo ~/w-sentry/.venv/bin/python ~/w-sentry/scripts/unoq/bridge_ping.py"""
import socket
import time

import msgpack

SOCK = "/var/run/arduino-router.sock"


def bridge_call(method, *params, path=SOCK, timeout=2.0):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as c:
        c.settimeout(timeout)
        c.connect(path)
        c.sendall(msgpack.packb([0, 1, method, list(params)]))
        unpacker = msgpack.Unpacker(raw=False)
        while True:
            data = c.recv(4096)
            if not data:
                raise ConnectionError("router closed the connection without a reply")
            unpacker.feed(data)
            for msg in unpacker:
                if isinstance(msg, list) and len(msg) == 4 and msg[0] == 1:
                    if msg[2]:
                        raise RuntimeError(f"bridge error: {msg[2]}")
                    return msg[3]


if __name__ == "__main__":
    before = bridge_call("wsentry_presses")
    for name, args in [("safe, small graph", (0, 0, 3)), ("alert DDOS", (1, 3, 6)),
                       ("blocked DDOS", (2, 3, 8)), ("firewall off", (3, 0, 0)), ("safe", (0, 0, 0))]:
        end = time.time() + 4
        while time.time() < end:                    # keep feeding it: the sketch's watchdog wants
            bridge_call("wsentry_show", *args)      # an update at least every 3 s
            time.sleep(0.5)
        print(name)
    print("button presses during this run:", bridge_call("wsentry_presses") - before)
