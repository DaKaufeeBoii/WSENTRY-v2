"""
Tests for automated mitigation engine (Task 3.5, 3.9).
"""
import time
from datetime import datetime, timedelta
import pytest

from src.live.buffer import PacketRecord
from src.live.mitigation import MitigationEngine, MitigationMode


def test_mitigation_simulated_mode():
    """Simulated mode logs action without executing OS commands."""
    engine = MitigationEngine(mode=MitigationMode.SIMULATED)
    rec = PacketRecord(
        timestamp=time.time(),
        src_ip="192.168.1.50",
        dst_ip="192.168.1.100",
        src_port=1234,
        dst_port=80,
        protocol="TCP",
        length=64,
        flags="SYN",
        prediction=3,
        confidence=0.98,
        label="DoS_Flood",
    )
    action = engine.respond(rec)
    assert action is not None
    assert action.success is True
    assert "[SIMULATED]" in action.rule_command
    assert action.action == "BLOCK_IP"
    assert len(engine.get_log()) == 1


def test_mitigation_cooldown():
    """Same src_ip within cooldown window returns None."""
    engine = MitigationEngine(mode=MitigationMode.SIMULATED, cooldown_seconds=10.0)
    rec = PacketRecord(
        timestamp=time.time(),
        src_ip="192.168.1.50",
        dst_ip="192.168.1.100",
        src_port=1234,
        dst_port=80,
        protocol="TCP",
        length=64,
        flags="SYN",
        prediction=3,
        confidence=0.98,
        label="DoS_Flood",
    )
    first_resp = engine.respond(rec)
    assert first_resp is not None

    # Immediate second packet from same IP should be rate-limited by cooldown
    second_resp = engine.respond(rec)
    assert second_resp is None
    assert len(engine.get_log()) == 1


def test_mitigation_decision_logic():
    """DoS_Flood -> BLOCK_IP, Normal -> no action, Jamming -> ALERT_ONLY."""
    engine = MitigationEngine(mode=MitigationMode.SIMULATED, cooldown_seconds=0.0)

    # 1. Normal (0)
    rec_normal = PacketRecord(
        timestamp=time.time(), src_ip="192.168.1.2", dst_ip="192.168.1.100",
        src_port=80, dst_port=80, protocol="TCP", length=64, flags="",
        prediction=0, confidence=0.99, label="Normal",
    )
    assert engine.respond(rec_normal) is None

    # 2. Jamming (1)
    rec_jam = PacketRecord(
        timestamp=time.time(), src_ip="192.168.1.3", dst_ip="192.168.1.100",
        src_port=0, dst_port=0, protocol="OTHER", length=64, flags="",
        prediction=1, confidence=0.95, label="Jamming",
    )
    act_jam = engine.respond(rec_jam)
    assert act_jam is not None
    assert act_jam.action == "ALERT_ONLY"

    # 3. Spoofing (2)
    rec_spf = PacketRecord(
        timestamp=time.time(), src_ip="192.168.1.4", dst_ip="192.168.1.100",
        src_port=0, dst_port=0, protocol="ARP", length=42, flags="",
        prediction=2, confidence=0.96, label="Spoofing",
    )
    act_spf = engine.respond(rec_spf)
    assert act_spf is not None
    assert act_spf.action == "BLOCK_IP"

    # 4. Probe (4)
    rec_prb = PacketRecord(
        timestamp=time.time(), src_ip="192.168.1.5", dst_ip="192.168.1.100",
        src_port=1000, dst_port=22, protocol="TCP", length=60, flags="SYN",
        prediction=4, confidence=0.97, label="Intrusion_Probe",
    )
    act_prb = engine.respond(rec_prb)
    assert act_prb is not None
    assert act_prb.action == "BLOCK_IP"


def test_mitigation_cleanup():
    """Expired rules are removed after max_age."""
    engine = MitigationEngine(mode=MitigationMode.SIMULATED)
    # Manually insert an expired block
    old_time = datetime.now() - timedelta(seconds=500)
    engine._active_blocks["192.168.1.99"] = old_time

    assert "192.168.1.99" in engine.get_active_blocks()
    removed = engine.cleanup_expired(max_age_seconds=300.0)
    assert removed == 1
    assert "192.168.1.99" not in engine.get_active_blocks()
