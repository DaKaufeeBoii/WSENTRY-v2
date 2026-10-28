"""
Thread-safe ring buffer for live network packets and threat classifications.
"""
import time
import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional


@dataclass
class PacketRecord:
    timestamp: float
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: str          # "TCP", "UDP", "ICMP", "ARP", "OTHER"
    length: int
    flags: str             # TCP flags string, e.g. "SYN", "SYN+ACK"
    raw_features: Dict[str, float] = field(default_factory=dict)
    prediction: int = -1   # Threat class (0-4), -1 if not yet classified
    confidence: float = 0.0 # Calibrated softmax probability
    label: str = "Unclassified" # Human-readable label


class PacketBuffer:
    """Thread-safe ring buffer for storing and querying packet records."""

    def __init__(self, maxlen: int = 10000) -> None:
        self.maxlen = maxlen
        self._buffer: deque[PacketRecord] = deque(maxlen=maxlen)
        self._lock = threading.Lock()
        self._stats: Dict[str, Any] = {
            "total_packets": 0,
            "threats_detected": 0,
            "by_class": {0: 0, 1: 0, 2: 0, 3: 0, 4: 0},
        }

    def append(self, record: PacketRecord) -> None:
        with self._lock:
            self._buffer.append(record)
            self._stats["total_packets"] += 1
            if record.prediction > 0:
                self._stats["threats_detected"] += 1
                if record.prediction in self._stats["by_class"]:
                    self._stats["by_class"][record.prediction] += 1

    def update_record(self, record: PacketRecord, prediction: int, confidence: float, label: str) -> None:
        with self._lock:
            old_pred = record.prediction
            record.prediction = prediction
            record.confidence = confidence
            record.label = label
            if old_pred <= 0 and prediction > 0:
                self._stats["threats_detected"] += 1
                if prediction in self._stats["by_class"]:
                    self._stats["by_class"][prediction] += 1
            elif old_pred == -1 and prediction == 0:
                self._stats["by_class"][0] += 1

    def get_unclassified(self, limit: int = 64) -> List[PacketRecord]:
        """Returns records that still have prediction == -1."""
        with self._lock:
            records = [r for r in self._buffer if r.prediction == -1]
            return records[:limit]

    def get_recent(self, n: int = 100) -> List[PacketRecord]:
        """Returns the most recent n records, newest first."""
        with self._lock:
            items = list(self._buffer)
            return items[-n:][::-1]

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_packets": self._stats["total_packets"],
                "threats_detected": self._stats["threats_detected"],
                "by_class": dict(self._stats["by_class"]),
                "buffer_size": len(self._buffer),
            }

    def get_threat_rate(self, window_seconds: float = 60.0) -> float:
        """Percentage of packets in recent window that are threats."""
        now = time.time()
        cutoff = now - window_seconds
        with self._lock:
            recent = [r for r in self._buffer if r.timestamp >= cutoff]
            if not recent:
                return 0.0
            threats = sum(1 for r in recent if r.prediction > 0)
            return (threats / len(recent)) * 100.0

    def get_packet_rate(self, window_seconds: float = 5.0) -> float:
        """Returns packets per second in recent window."""
        now = time.time()
        cutoff = now - window_seconds
        with self._lock:
            recent = [r for r in self._buffer if r.timestamp >= cutoff]
            if not recent:
                return 0.0
            return len(recent) / max(window_seconds, 1.0)

    def clear(self) -> None:
        with self._lock:
            self._buffer.clear()
            self._stats["total_packets"] = 0
            self._stats["threats_detected"] = 0
            self._stats["by_class"] = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}

