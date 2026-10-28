"""
Tests for active defense mitigation engine and firewall rules.
"""
import time
from datetime import datetime, timezone, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.live.mitigation import MitigationEngine, MitigationMode
from src.live.buffer import PacketRecord


def _make_record(threat_class: int, src_ip: str = "192.168.1.50") -> PacketRecord:
    labels = {0: "Normal", 1: "Jamming", 2: "Spoofing", 3: "DoS_Flood", 4: "Intrusion_Probe"}
    return PacketRecord(
        timestamp=time.time(),
        src_ip=src_ip,
        dst_ip="192.168.1.100",
        src_port=1234,
        dst_port=80,
        protocol="TCP",
        length=64,
        flags="S",
        prediction=threat_class,
        confidence=0.96,
        label=labels.get(threat_class, "Unknown"),
    )


def test_mitigation_simulated_mode():
    """Simulated mode logs actions and succeeds without actual OS command execution."""
    engine = MitigationEngine(mode=MitigationMode.SIMULATED)
    rec = _make_record(threat_class=3, src_ip="192.168.1.50")
    action = engine.respond(rec)

    assert action is not None
    assert action.success is True
    assert action.mode == MitigationMode.SIMULATED
    assert action.action == "BLOCK_IP"
    assert "WSENTRY_BLOCK" in action.rule_command

    log = engine.get_log()
    assert len(log) == 1
    assert log[0].src_ip == "192.168.1.50"


def test_mitigation_cooldown():
    """Consecutive threats from the same src_ip within cooldown window return None."""
    engine = MitigationEngine(mode=MitigationMode.SIMULATED, cooldown_seconds=10.0)
    rec = _make_record(threat_class=3, src_ip="192.168.1.75")

    # First attempt: triggers action
    act1 = engine.respond(rec)
    assert act1 is not None

    # Immediate second attempt: suppressed by cooldown
    act2 = engine.respond(rec)
    assert act2 is None


def test_mitigation_decision_logic():
    """Verifies action types per threat class."""
    engine = MitigationEngine(mode=MitigationMode.SIMULATED, cooldown_seconds=0.0)

    # Class 0: Normal -> None
    assert engine.respond(_make_record(0, "192.168.1.10")) is None

    # Class 1: Jamming -> ALERT_ONLY
    act_jam = engine.respond(_make_record(1, "192.168.1.11"))
    assert act_jam is not None
    assert act_jam.action == "ALERT_ONLY"

    # Class 2: Spoofing -> BLOCK_IP
    act_spoof = engine.respond(_make_record(2, "192.168.1.12"))
    assert act_spoof is not None
    assert act_spoof.action == "BLOCK_IP"

    # Class 3: DoS_Flood -> BLOCK_IP
    act_dos = engine.respond(_make_record(3, "192.168.1.13"))
    assert act_dos is not None
    assert act_dos.action == "BLOCK_IP"

    # Class 4: Intrusion_Probe -> BLOCK_IP
    act_probe = engine.respond(_make_record(4, "192.168.1.14"))
    assert act_probe is not None
    assert act_probe.action == "BLOCK_IP"


def test_mitigation_cleanup():
    """Rules older than max_age are cleaned up."""
    engine = MitigationEngine(mode=MitigationMode.SIMULATED)
    rec = _make_record(threat_class=3, src_ip="192.168.1.99")
    engine.respond(rec)

    assert "192.168.1.99" in engine.get_active_blocks()

    # Artificially age the active block
    engine._active_blocks["192.168.1.99"] = datetime.now(timezone.utc) - timedelta(seconds=400)

    removed_cnt = engine.cleanup_expired(max_age_seconds=300.0)
    assert removed_cnt == 1
    assert "192.168.1.99" not in engine.get_active_blocks()

