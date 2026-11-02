"""
Unit and integration tests for Phase 3 packet capture and ring buffer.
"""
import time
import threading
import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.live.buffer import PacketBuffer, PacketRecord
from src.live.capture import LiveCapture


def test_packet_buffer_append_and_retrieve():
    """Buffer stores and returns records in order."""
    buf = PacketBuffer(maxlen=100)
    rec1 = PacketRecord(
        timestamp=time.time(),
        src_ip="192.168.1.10",
        dst_ip="192.168.1.100",
        src_port=12345,
        dst_port=80,
        protocol="TCP",
        length=64,
        flags="S",
        prediction=0,
        confidence=0.98,
        label="Normal",
    )
    rec2 = PacketRecord(
        timestamp=time.time() + 0.1,
        src_ip="192.168.1.50",
        dst_ip="192.168.1.100",
        src_port=54321,
        dst_port=80,
        protocol="TCP",
        length=64,
        flags="S",
        prediction=3,
        confidence=0.95,
        label="DoS_Flood",
    )

    buf.append(rec1)
    buf.append(rec2)

    stats = buf.get_stats()
    assert stats["total_packets"] == 2
    assert stats["threats_detected"] == 1
    assert stats["by_class"][3] == 1

    recent = buf.get_recent(n=2)
    assert len(recent) == 2
    assert recent[0].src_ip == "192.168.1.50"  # newest first
    assert recent[1].src_ip == "192.168.1.10"


def test_packet_buffer_maxlen():
    """Buffer drops oldest records when full."""
    buf = PacketBuffer(maxlen=5)
    for i in range(10):
        rec = PacketRecord(
            timestamp=float(i),
            src_ip=f"10.0.0.{i}",
            dst_ip="10.0.0.1",
            src_port=1000 + i,
            dst_port=80,
            protocol="TCP",
            length=100,
            flags="A",
            prediction=0,
            confidence=0.9,
            label="Normal",
        )
        buf.append(rec)

    stats = buf.get_stats()
    assert stats["total_packets"] == 10
    assert stats["buffer_size"] == 5

    recent = buf.get_recent(n=5)
    assert len(recent) == 5
    # The oldest 5 should have been dropped; newest is 9
    assert recent[0].src_ip == "10.0.0.9"
    assert recent[-1].src_ip == "10.0.0.5"


def test_packet_buffer_thread_safety():
    """Concurrent appends and reads from multiple threads without deadlock or corruption."""
    buf = PacketBuffer(maxlen=500)
    threads = []
    num_threads = 5
    items_per_thread = 50

    def worker(worker_id):
        for j in range(items_per_thread):
            rec = PacketRecord(
                timestamp=time.time(),
                src_ip=f"192.168.{worker_id}.{j}",
                dst_ip="192.168.1.1",
                src_port=2000 + j,
                dst_port=443,
                protocol="TCP",
                length=128,
                flags="A",
                prediction=0,
                confidence=0.99,
                label="Normal",
            )
            buf.append(rec)
            _ = buf.get_recent(n=10)

    for tid in range(num_threads):
        t = threading.Thread(target=worker, args=(tid,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    stats = buf.get_stats()
    assert stats["total_packets"] == num_threads * items_per_thread


def test_live_capture_list_interfaces():
    """Returns at least one valid interface dictionary."""
    ifaces = LiveCapture.list_interfaces()
    assert isinstance(ifaces, list)
    assert len(ifaces) > 0
    assert "name" in ifaces[0]

