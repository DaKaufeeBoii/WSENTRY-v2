"""
Tests for the CICIoT2023 feature port on a synthetic capture: one TCP flow plus an ARP frame.
"""
import math
import os
import struct
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.features.ciciot_features import chunk_rows, extract, read_pcap

T0 = 1_660_000_000.0
FIN, SYN, PSH, ACK = 0x01, 0x02, 0x08, 0x10


def tcp_frame(payload_len, flags, sport=40000, dport=80, ttl=64):
    total = 20 + 20 + payload_len
    ip = struct.pack("!BBHHHBBH4s4s", 0x45, 0, total, 1, 0, ttl, 6, 0, bytes([10, 0, 0, 1]), bytes([10, 0, 0, 2]))
    tcp = struct.pack("!HHIIBBHHH", sport, dport, 0, 0, 0x50, flags, 1024, 0, 0)
    return b"\xaa" * 6 + b"\xbb" * 6 + b"\x08\x00" + ip + tcp + b"x" * payload_len


def arp_frame():
    return b"\xff" * 6 + b"\xbb" * 6 + b"\x08\x06" + b"\x00" * 28 + b"\x00" * 18  # padded to 60 bytes


def write_pcap(path, frames):
    with open(path, "wb") as f:
        f.write(struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1))
        for ts, buf in frames:
            sec = int(ts)
            f.write(struct.pack("<IIII", sec, round((ts - sec) * 1e6), len(buf), len(buf)) + buf)


@pytest.fixture
def capture(tmp_path):
    frames = [(T0 + 0.1 * i, tcp_frame(i, FIN if i % 5 == 0 else ACK | PSH)) for i in range(25)]
    frames.append((T0 + 2.6, arp_frame()))
    path = tmp_path / "toy.pcap"
    write_pcap(path, frames)
    return path, frames


def test_rows_reproduce_the_extractor_quirks(capture):
    path, frames = capture
    rows = chunk_rows(list(read_pcap(path)))
    assert len(rows) == 26
    first, second, twentieth = rows[0], rows[1], rows[19]
    assert first["IAT"] == pytest.approx(T0)                 # absolute timestamp at a chunk's first packet
    assert second["IAT"] == pytest.approx(0.1, abs=1e-6)     # otherwise the gap to the previous packet
    assert twentieth["IAT"] == pytest.approx(T0 + 1.9)       # and again at every 20th packet
    assert twentieth["Number"] == 0 and rows[18]["Number"] == 19
    assert twentieth["Weight"] == 19 ** 2                    # previous 19 packets only
    assert first["Weight"] == 1 and first["Magnitue"] == pytest.approx(math.sqrt(2 * 54))
    assert all(r["Srate"] == r["Rate"] and r["Drate"] == 0 for r in rows)
    # ack_count counts FIN flags (packets 0, 5, 10, ...), rst_count counts ACK flags
    assert rows[10]["ack_count"] == 3 and rows[10]["rst_count"] == 8 and rows[10]["urg_count"] == 8
    assert first["HTTP"] == 1 and first["TCP"] == 1 and first["LLC"] == 1 and first["Duration"] == 64
    assert rows[24]["Header_Length"] == sum(len(b) for _, b in frames[:25])
    arp = rows[25]
    assert arp["ARP"] == 1 and arp["IPv"] == 0 and arp["LLC"] == 0 and arp["Tot size"] == 60
    assert arp["Rate"] == rows[24]["Rate"]                   # Rate carries over to frames that do not set it


def test_extract_averages_blocks_within_a_chunk(capture):
    path, _ = capture
    out = extract(path, n_rows=10)
    assert len(out) == 3                                     # 26 rows -> blocks of 10, 10, 6
    assert out.loc[2, "ARP"] == pytest.approx(1 / 6)
