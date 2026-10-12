"""
Tests for packet buffer and capture pipeline (Task 3.2, 3.9).
"""
import threading
import time
import pytest

from src.live.buffer import PacketBuffer, PacketRecord
from src.live.capture import LiveCapture


def test_packet_buffer_append_and_retrieve():
    """Buffer stores and returns records in order."""
    buf = PacketBuffer(maxlen=100)
    for i in range(10):
        rec = PacketRecord(
            timestamp=float(i),
            src_ip=f"10.0.0.{i}",
            dst_ip="192.168.1.1",
            src_port=1000 + i,
            dst_port=80,
            protocol="TCP",
            length=64,
            flags="SYN",
            prediction=0,
            confidence=0.99,
            label="Normal",
        )
        buf.append(rec)

    recent = buf.get_recent(5)
    assert len(recent) == 5
    assert recent[-1].src_ip == "10.0.0.9"
    assert recent[0].src_ip == "10.0.0.5"

    stats = buf.get_stats()
    assert stats["total_packets"] == 10
    assert stats["current_buffer_size"] == 10


def test_packet_buffer_maxlen():
    """Buffer drops oldest when full."""
    buf = PacketBuffer(maxlen=5)
    for i in range(10):
        rec = PacketRecord(
            timestamp=float(i),
            src_ip=f"10.0.0.{i}",
            dst_ip="192.168.1.1",
            src_port=1000 + i,
            dst_port=80,
            protocol="TCP",
            length=64,
            flags="SYN",
        )
        buf.append(rec)

    stats = buf.get_stats()
    assert stats["current_buffer_size"] == 5
    assert stats["total_packets"] == 10

    recent = buf.get_recent(5)
    assert recent[0].src_ip == "10.0.0.5"
    assert recent[-1].src_ip == "10.0.0.9"


def test_packet_buffer_thread_safety():
    """Concurrent append/read from multiple threads."""
    buf = PacketBuffer(maxlen=5000)

    def worker_append(start_id: int):
        for i in range(100):
            rec = PacketRecord(
                timestamp=time.time(),
                src_ip=f"10.0.{start_id}.{i}",
                dst_ip="192.168.1.1",
                src_port=80,
                dst_port=80,
                protocol="TCP",
                length=64,
                flags="SYN",
                prediction=3 if i % 2 == 0 else 0,
                confidence=0.95,
                label="DoS_Flood" if i % 2 == 0 else "Normal",
            )
            buf.append(rec)

    threads = [threading.Thread(target=worker_append, args=(t,)) for t in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    stats = buf.get_stats()
    assert stats["total_packets"] == 500
    assert stats["current_buffer_size"] == 500
    assert stats["threats_detected"] == 250


def test_live_capture_list_interfaces():
    """Returns at least one interface on the host."""
    interfaces = LiveCapture.list_interfaces()
    assert isinstance(interfaces, list)
    assert len(interfaces) >= 1
    # Check that required keys are present
    assert "name" in interfaces[0]
    assert "description" in interfaces[0]
    assert "ip" in interfaces[0]


def test_live_capture_no_mock_fallback():
    """LiveCapture must not have simulated traffic generators or mock interfaces."""
    from src.live.feature_extractor import LiveFeatureExtractor
    buf = PacketBuffer(maxlen=10)
    extractor = LiveFeatureExtractor()
    cap = LiveCapture(iface="NonExistentInterface12345", buffer=buf, feature_extractor=extractor)
    assert not hasattr(cap, "_run_simulated_stream")
    assert not hasattr(cap, "simulate_if_failed")
    assert not hasattr(cap, "is_simulated")

    # Verify interfaces listed do NOT contain Simulated / Mock entries
    ifaces = LiveCapture.list_interfaces()
    for ifc in ifaces:
        assert "simulated" not in ifc["name"].lower()
        assert "synthetic" not in ifc["description"].lower()

