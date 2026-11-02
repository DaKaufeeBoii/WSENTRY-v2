"""
CICIoT2023's 46 features computed from any Ethernet pcap, so other datasets can share
CICIoT2023's feature space.

A standard-library port of the dataset's own extractor (supplementary/pcap2csv,
Feature_extraction.py and helpers, dpkt-based). It keeps that code's behaviour,
quirks included, because the published CSVs were made with it:
  - captures are cut into 10 MB chunks (tcpdump -C 10) and all state resets per chunk;
  - one row per IPv4 or ARP frame, then rows are averaged in consecutive blocks of
    n packets (10, or 100 for flood attacks, per the paper);
  - IAT is the gap to the previous packet, except at a chunk's first packet and every
    20th packet, where it is the absolute timestamp (so IAT encodes capture time);
  - the incoming and outgoing size lists are always identical, so Magnitue, Radius,
    Covariance, Variance and Weight derive from one list; Drate is always 0 and
    Srate equals Rate; Rate carries over to packets that do not update it;
  - the per-flow counters are crossed: ack_count counts FIN, fin_count RST,
    urg_count PSH and rst_count ACK flags (syn_count counts SYN);
  - LLC is 1 for every IPv4 frame.
"""
import math
import socket
import struct

import numpy as np
import pandas as pd

FEATURES = [
    "flow_duration", "Header_Length", "Protocol Type", "Duration", "Rate", "Srate", "Drate",
    "fin_flag_number", "syn_flag_number", "rst_flag_number", "psh_flag_number", "ack_flag_number",
    "ece_flag_number", "cwr_flag_number", "ack_count", "syn_count", "fin_count", "urg_count", "rst_count",
    "HTTP", "HTTPS", "DNS", "Telnet", "SMTP", "SSH", "IRC", "TCP", "UDP", "DHCP", "ARP", "ICMP", "IPv", "LLC",
    "Tot sum", "Min", "Max", "AVG", "Std", "Tot size", "IAT", "Number", "Magnitue", "Radius", "Covariance",
    "Variance", "Weight",
]
CHUNK_BYTES = 10_000_000  # tcpdump -C 10: a new file once the current one exceeds 10 million bytes


def read_pcap(path):
    """
    Yield (timestamp seconds, frame bytes) from a libpcap or pcapng file. Timestamps are
    rounded down to microseconds and built as sec + usec * 1e-6, as dpkt reads the classic
    pcap files that `tcpdump -w` writes in the official pipeline.
    """
    with open(path, "rb") as f:
        magic = f.read(4)
        f.seek(0)
        if magic == b"\x0a\x0d\x0d\x0a":
            yield from _read_pcapng(f)
            return
        head = f.read(24)
        endian = {b"\xd4\xc3\xb2\xa1": "<", b"\xa1\xb2\xc3\xd4": ">",
                  b"\x4d\x3c\xb2\xa1": "<", b"\xa1\xb2\x3c\x4d": ">"}[head[:4]]
        per_sec = 10**9 if head[:4] in (b"\x4d\x3c\xb2\xa1", b"\xa1\xb2\x3c\x4d") else 10**6
        rec = struct.Struct(endian + "IIII")
        while True:
            h = f.read(16)
            if len(h) < 16:
                return
            sec, sub, caplen, _ = rec.unpack(h)
            yield sec + (sub * 10**6 // per_sec) * 1e-6, f.read(caplen)


def _read_pcapng(f):
    """Enhanced and simple packet blocks of a pcapng file, any interface."""
    endian, units = "<", []  # per-interface ticks per second
    while True:
        head = f.read(8)
        if len(head) < 8:
            return
        btype = struct.unpack(endian + "I", head[:4])[0]
        if head[:4] == b"\x0a\x0d\x0d\x0a":  # section header: byte order, interfaces restart
            bom = f.read(4)
            endian = "<" if bom == b"\x4d\x3c\x2b\x1a" else ">"
            blen = struct.unpack(endian + "I", head[4:])[0]
            f.read(blen - 12)
            units = []
            continue
        blen = struct.unpack(endian + "I", head[4:])[0]
        body = f.read(blen - 8)[:-4]
        if btype == 1:  # interface description: default 1e6 ticks/s unless if_tsresol says otherwise
            res, pos = 10**6, 8
            while pos + 4 <= len(body):
                code, olen = struct.unpack(endian + "HH", body[pos:pos + 4])
                if code == 0:
                    break
                if code == 9:
                    v = body[pos + 4]
                    res = 2 ** (v & 0x7F) if v & 0x80 else 10 ** v
                pos += 4 + olen + (-olen % 4)
            units.append(res)
        elif btype == 6:  # enhanced packet
            iface, hi, lo, caplen, _ = struct.unpack(endian + "IIIII", body[:20])
            ticks, per = (hi << 32) | lo, units[iface]
            yield ticks // per + ((ticks % per) * 10**6 // per) * 1e-6, body[20:20 + caplen]
        elif btype == 3:  # simple packet: no timestamp
            yield 0.0, body[4:]


def chunks(packets):
    """Group packets as `tcpdump -C 10` splits files (24-byte file header, 16 bytes per record)."""
    chunk, size = [], 24
    for ts, buf in packets:
        if size > CHUNK_BYTES:
            yield chunk
            chunk, size = [], 24
        chunk.append((ts, buf))
        size += 16 + len(buf)
    if chunk:
        yield chunk


def _parse(buf):
    """Return (kind, frame_len, info) for IPv4/ARP frames as dpkt sees them, else None."""
    if len(buf) < 14:
        return None
    etype, off = struct.unpack("!H", buf[12:14])[0], 14
    if etype == 0x8100:  # one 802.1Q tag
        etype, off = struct.unpack("!H", buf[16:18])[0], 18
    if etype == 0x0806:  # dpkt's ARP keeps the Ethernet padding, so the frame counts in full
        return ("arp", len(buf), None) if len(buf) >= off + 28 else None
    if etype != 0x0800 or len(buf) < off + 20:
        return None
    vhl, _, total, _, frag, ttl, proto = struct.unpack("!BBHHHBB", buf[off:off + 10])
    hl = (vhl & 0x0F) * 4
    if hl < 20:
        return None  # dpkt cannot parse it; the extractor fails on such frames
    # dpkt trims the IP payload to the total-length field (whole buffer when it is 0)
    end = min(off + total, len(buf)) if total else len(buf)
    ip = {"src": socket.inet_ntoa(buf[off + 12:off + 16]), "dst": socket.inet_ntoa(buf[off + 16:off + 20]),
          "ttl": ttl, "p": proto, "l4": None}
    l4 = off + hl
    if not frag & 0x1FFF:  # dpkt parses TCP/UDP only when the fragment offset is 0
        if proto == 6 and end - l4 >= 20:
            sport, dport = struct.unpack("!HH", buf[l4:l4 + 4])
            ip["l4"] = ("tcp", sport, dport, buf[l4 + 13])
        elif proto == 17 and end - l4 >= 8:
            sport, dport = struct.unpack("!HH", buf[l4:l4 + 4])
            ip["l4"] = ("udp", sport, dport, 0)
    return "ip", end, ip


def _two_streams(sizes):
    """dynamic_two_streams on identical incoming/outgoing lists."""
    mean, var = sum(sizes) / len(sizes), float(np.var(sizes))
    return math.sqrt(2 * mean), math.sqrt(2 * var), var, (1.0 if var != 0 else 0.0), float(len(sizes) ** 2)


def chunk_rows(chunk):
    """One feature row per IPv4/ARP frame of one chunk, with the extractor's running state."""
    rows, flows, flow_flags = [], {}, {}
    ethsize, pack = [], []
    rate = srate = drate = 0.0
    first_ts = 0.0
    magnite = radius = cov = var_ratio = weight = 0.0
    for ts, buf in chunk:
        parsed = _parse(buf)
        if parsed is None:
            continue
        kind, size, ip = parsed
        r = dict.fromkeys(FEATURES, 0.0)
        ethsize.append(size)
        tot = sum(ethsize)
        r["Tot sum"], r["Min"], r["Max"] = tot, min(ethsize), max(ethsize)
        r["AVG"], r["Std"] = tot / len(ethsize), float(np.std(ethsize))
        if len(ethsize) % 20 == 0:
            magnite, radius, cov, var_ratio, weight = _two_streams(pack)  # previous packets only
            ethsize, pack, first_ts = [], [], 0.0
        else:
            pack.append(size)
            magnite, radius, cov, var_ratio, weight = _two_streams(pack)
        r["IAT"], first_ts = ts - first_ts, ts
        r["Magnitue"], r["Radius"], r["Covariance"], r["Variance"], r["Weight"] = magnite, radius, cov, var_ratio, weight
        r["Tot size"], r["Number"] = size, len(ethsize)
        if kind == "arp":
            r["ARP"] = 1
        else:
            r["IPv"], r["LLC"], r["Protocol Type"], r["Duration"] = 1, 1, ip["p"], ip["ttl"]
            r["ICMP"] = int(ip["p"] == 1)
            if ip["l4"]:
                l4, sport, dport, flags = ip["l4"]
                key = tuple(sorted([(ip["src"], sport), (ip["dst"], dport)]))
                flows.setdefault((l4, key), []).append((size, ts))
                pkts = flows[(l4, key)]
                ports = {sport, dport}
                if l4 == "udp":
                    r["UDP"], r["DNS"] = 1, int(53 in ports)
                    r["DHCP"] = int(sport == 67 or dport == 68)
                else:
                    r["TCP"] = 1
                    r["HTTP"], r["HTTPS"], r["SSH"] = int(80 in ports), int(443 in ports), int(22 in ports)
                    r["IRC"], r["SMTP"], r["Telnet"] = int(21 in ports), int(25 in ports), int(23 in ports)
                    bits = [(flags >> i) & 1 for i in range(8)]  # fin syn rst psh ack urg ece cwr
                    for name, b in zip(["fin", "syn", "rst", "psh", "ack"], bits):
                        r[f"{name}_flag_number"] = b
                    r["ece_flag_number"], r["cwr_flag_number"] = bits[6], bits[7]
                    c = flow_flags.get(key, [0, 0, 0, 0, 0])
                    c = [c[i] + bits[i] for i in range(5)]  # crossed: fin, syn, rst, psh, ack
                    flow_flags[key] = c
                    r["ack_count"], r["syn_count"], r["fin_count"], r["urg_count"], r["rst_count"] = c
                times = sorted(t for _, t in pkts)
                r["Header_Length"] = sum(s for s, _ in pkts)
                r["flow_duration"] = times[-1] - times[0]
                if r["flow_duration"] != 0:
                    rate = srate = len(pkts) / r["flow_duration"]
                    # the reversed flow key exists only when both endpoints are identical
                    drate = rate if key[0] == key[1] else 0.0
        r["Rate"], r["Srate"], r["Drate"] = rate, srate, drate
        rows.append(r)
    return rows


def extract(path, n_rows=10):
    """CICIoT2023 feature rows for one pcap: per-chunk rows averaged in blocks of n_rows packets."""
    out = []
    for chunk in chunks(read_pcap(path)):
        rows = pd.DataFrame(chunk_rows(chunk), columns=FEATURES)
        if len(rows):
            out.append(rows.groupby(np.arange(len(rows)) // n_rows).mean())
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame(columns=FEATURES)
