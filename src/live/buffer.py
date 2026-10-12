"""
Thread-safe ring buffer and statistics tracking for live network packets.
"""
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, List, Dict, Optional


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
    raw_features: dict = field(default_factory=dict)
    prediction: int = -1   # Threat class (0-4), -1 if not yet classified
    confidence: float = 0.0  # Calibrated softmax probability
    label: str = "Pending"  # "Normal", "Jamming", "Spoofing", "DoS_Flood", "Intrusion_Probe"


class PacketBuffer:
    """Thread-safe ring buffer for packet records."""

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
        """Append a new packet record thread-safely."""
        with self._lock:
            self._buffer.append(record)
            self._stats["total_packets"] += 1
            if record.prediction > 0:
                self._stats["threats_detected"] += 1
                if record.prediction in self._stats["by_class"]:
                    self._stats["by_class"][record.prediction] += 1

    def update_prediction(self, record: PacketRecord, prediction: int, confidence: float, label: str) -> None:
        """Update an existing record with classification results."""
        with self._lock:
            record.prediction = prediction
            record.confidence = confidence
            record.label = label
            if prediction > 0:
                self._stats["threats_detected"] += 1
            if prediction in self._stats["by_class"]:
                self._stats["by_class"][prediction] += 1

    def get_recent(self, n: int = 100) -> List[PacketRecord]:
        """Return the n most recent packet records (newest last)."""
        with self._lock:
            if n <= 0:
                return []
            records = list(self._buffer)
            return records[-n:]

    def get_unclassified(self, max_batch: int = 32) -> List[PacketRecord]:
        """Fetch pending records that have not been classified yet."""
        with self._lock:
            unclassified = [rec for rec in self._buffer if rec.prediction == -1]
            return unclassified[:max_batch]

    def get_stats(self) -> Dict[str, Any]:
        """Return a snapshot copy of current buffer statistics."""
        with self._lock:
            return {
                "total_packets": self._stats["total_packets"],
                "threats_detected": self._stats["threats_detected"],
                "by_class": dict(self._stats["by_class"]),
                "current_buffer_size": len(self._buffer),
            }

    def get_threat_rate(self, window_seconds: float = 60.0) -> float:
        """Calculate threat percentage over the last window_seconds."""
        with self._lock:
            if not self._buffer:
                return 0.0
            now = time.time()
            cutoff = now - window_seconds
            recent = [rec for rec in self._buffer if rec.timestamp >= cutoff]
            if not recent:
                return 0.0
            classified = [rec for rec in recent if rec.prediction >= 0]
            if not classified:
                return 0.0
            threats = [rec for rec in classified if rec.prediction > 0]
            return round((len(threats) / len(classified)) * 100.0, 2)

    def get_packets_per_second(self, window_seconds: float = 5.0) -> float:
        """Calculate packet capture throughput over the last window_seconds."""
        with self._lock:
            if not self._buffer:
                return 0.0
            now = time.time()
            cutoff = now - window_seconds
            count = sum(1 for rec in self._buffer if rec.timestamp >= cutoff)
            return round(count / max(window_seconds, 1.0), 1)

    def clear(self) -> None:
        """Clear the ring buffer and reset counters."""
        with self._lock:
            self._buffer.clear()
            self._stats["total_packets"] = 0
            self._stats["threats_detected"] = 0
            self._stats["by_class"] = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
