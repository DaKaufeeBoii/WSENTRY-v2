"""
Live packet capture wrapping scapy.sniff() in a background worker thread.
"""
import time
import threading
from collections import deque
from typing import Optional, List, Dict, Any

from src.live.buffer import PacketBuffer, PacketRecord
from src.live.feature_extractor import LiveFeatureExtractor


class LiveCapture:
    """
    Captures raw packets from a network interface using Scapy in a background thread,
    maintains a sliding window for behavioral feature extraction, and populates
    a thread-safe PacketBuffer.
    """

    def __init__(
        self,
        iface: Optional[str],
        buffer: PacketBuffer,
        feature_extractor: Optional[LiveFeatureExtractor] = None,
        window_size: int = 5,
    ) -> None:
        self.iface = iface
        self.buffer = buffer
        self.feature_extractor = feature_extractor or LiveFeatureExtractor(window_size=window_size)
        self.window_size = window_size
        self._sliding_window: deque = deque(maxlen=window_size)
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.is_running = False

    @staticmethod
    def list_interfaces() -> List[Dict[str, str]]:
        """Returns list of available network interfaces with friendly human-readable labels."""
        interfaces = []
        try:
            import scapy.all as scapy_all
            import sys

            guid_map = {}
            if sys.platform.startswith("win"):
                try:
                    from scapy.arch.windows import get_windows_if_list
                    for w in get_windows_if_list():
                        g = w.get("guid", "").strip("{}").upper()
                        if g:
                            guid_map[g] = w
                except Exception:
                    pass

            for iface in scapy_all.get_if_list():
                dev_str = str(iface)
                label = dev_str
                clean_guid = ""
                if "{" in dev_str and "}" in dev_str:
                    clean_guid = dev_str.split("{")[1].split("}")[0].upper()

                if clean_guid and clean_guid in guid_map:
                    info = guid_map[clean_guid]
                    name = info.get("name", "NIC")
                    desc = info.get("description", "")
                    ips = [ip for ip in info.get("ips", []) if not ip.startswith("fe80")]
                    ip_str = f" [{ips[0]}]" if ips else ""
                    label = f"🌐 {name}{ip_str} — {desc}"
                elif "loopback" in dev_str.lower():
                    label = "🔄 Loopback [127.0.0.1] (Localhost Self-Test)"

                interfaces.append({"id": dev_str, "label": label, "name": dev_str})
        except Exception as e:
            interfaces = [{"id": "Default", "label": f"Standard Loopback / Auto ({e})", "name": "Default"}]

        if not interfaces:
            interfaces.append({"id": "Default", "label": "Standard NIC", "name": "Default"})

        # Prioritize interfaces that have active IP addresses or are Loopback
        interfaces.sort(key=lambda x: (0 if "[" in x["label"] else 1, x["label"]))
        return interfaces

    def start(self) -> None:
        """Starts packet capture in background daemon thread."""
        if self.is_running:
            return
        self._stop_event.clear()
        self.is_running = True
        self._thread = threading.Thread(target=self._run_sniff, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stops packet capture."""
        self.is_running = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def _packet_callback(self, packet: Any) -> None:
        """Called for each captured packet."""
        parsed = self.feature_extractor.parse_packet(packet)
        self._sliding_window.append(parsed)

        # Compute behavioral features if window has enough history
        window_list = list(self._sliding_window)
        raw_feats = self.feature_extractor.extract_features_dict(window_list)

        record = PacketRecord(
            timestamp=parsed["timestamp"] if parsed["timestamp"] > 0 else time.time(),
            src_ip=parsed["src_ip"],
            dst_ip=parsed["dst_ip"],
            src_port=parsed["src_port"],
            dst_port=parsed["dst_port"],
            protocol=parsed["protocol"],
            length=parsed["length"],
            flags=parsed["flags"],
            raw_features=raw_feats,
            prediction=-1,
            confidence=0.0,
            label="Pending",
        )
        self.buffer.append(record)

    def _run_sniff(self) -> None:
        """Background sniffing loop."""
        try:
            import scapy.all as scapy_all

            kwargs: Dict[str, Any] = {
                "prn": self._packet_callback,
                "stop_filter": lambda p: self._stop_event.is_set(),
                "store": False,
            }
            if self.iface and self.iface != "Default":
                kwargs["iface"] = self.iface

            scapy_all.sniff(**kwargs)
        except Exception as e:
            print(f"[LiveCapture] Scapy sniffing error or permission denied ({e}). Falling back to simulation.")
            self._run_simulation()

    def _run_simulation(self) -> None:
        """Fallback simulation generator when live raw capture lacks Npcap/admin."""
        import random
        while not self._stop_event.is_set():
            time.sleep(0.1)
            # Generate simulated packet
            is_attack = random.random() < 0.15
            if is_attack:
                src_ip = "192.168.1.50"
                dst_port = 80
                protocol = "TCP"
                flags = "S"
                length = 64
            else:
                src_ip = f"192.168.1.{random.randint(10, 200)}"
                dst_port = random.choice([80, 443, 53, 22])
                protocol = random.choice(["TCP", "UDP"])
                flags = "A" if protocol == "TCP" else ""
                length = random.randint(60, 1400)

            fake_pkt = {
                "timestamp": time.time(),
                "length": length,
                "payload_length": max(0, length - 40),
                "protocol": protocol,
                "src_ip": src_ip,
                "dst_ip": "192.168.1.100",
                "src_port": random.randint(1024, 65535),
                "dst_port": dst_port,
                "flags": flags,
            }
            self._packet_callback(fake_pkt)

