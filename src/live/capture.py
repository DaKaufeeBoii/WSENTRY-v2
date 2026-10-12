"""
Live packet capture via Scapy with ring buffer ingestion and sliding window aggregation.
Zero mock data: sniffs real network interfaces or replays real PCAP captures.
"""
import logging
import os
import threading
import time
from collections import deque
from typing import Any, Dict, List, Optional

import scapy.all as scapy_all

from src.live.buffer import PacketBuffer, PacketRecord
from src.live.feature_extractor import LiveFeatureExtractor

logger = logging.getLogger("w_sentry.capture")


class LiveCapture:
    """
    Captures live packets from a specified network interface (or reads from a real PCAP file)
    using Scapy, extracts 20 behavioral features per sliding window, and feeds PacketRecords
    into the ring buffer.
    """

    def __init__(
        self,
        iface: str,
        buffer: PacketBuffer,
        feature_extractor: LiveFeatureExtractor,
        window_size: int = 5,
        pcap_path: Optional[str] = None,
    ) -> None:
        self.iface = iface
        self.buffer = buffer
        self.feature_extractor = feature_extractor
        self.window_size = window_size
        self.pcap_path = pcap_path

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._window: deque = deque(maxlen=window_size)
        self._window_lock = threading.Lock()
        self.error_message: Optional[str] = None

    def start(self) -> None:
        """Start packet capture in background daemon thread."""
        if self._running:
            return
        self._running = True
        self.error_message = None
        self._thread = threading.Thread(target=self._run_capture, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Signal capture thread to stop."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.5)
        self._thread = None

    @property
    def is_running(self) -> bool:
        return self._running

    def _packet_callback(self, packet: Any) -> None:
        """
        Callback invoked per packet:
        1. Parse fields via feature extractor.
        2. Append to internal sliding window deque.
        3. Extract 20 behavioral features.
        4. Append PacketRecord to buffer.
        """
        if not self._running:
            return

        parsed = self.feature_extractor._parse_packet(packet)

        with self._window_lock:
            self._window.append(packet)

        # Extract behavioral features for the current packet
        raw_feat_dict = self.feature_extractor.extract_single_record_features(packet)

        # Create record with prediction=-1 (pending inference thread)
        record = PacketRecord(
            timestamp=parsed["timestamp"],
            src_ip=parsed["src_ip"],
            dst_ip=parsed["dst_ip"],
            src_port=parsed["src_port"],
            dst_port=parsed["dst_port"],
            protocol=parsed["protocol"],
            length=parsed["length"],
            flags=parsed["flags"],
            raw_features=raw_feat_dict,
            prediction=-1,
            confidence=0.0,
            label="Pending",
        )
        self.buffer.append(record)

    def _run_capture(self) -> None:
        """Worker thread executing scapy.sniff on real interface or PCAP file."""
        try:
            if self.pcap_path and os.path.exists(self.pcap_path):
                logger.info(f"Replaying real packets from PCAP file: {self.pcap_path}")
                scapy_all.sniff(
                    offline=self.pcap_path,
                    prn=self._packet_callback,
                    stop_filter=lambda p: not self._running,
                    store=False,
                )
            else:
                logger.info(f"Starting Scapy live sniff on interface: {self.iface}...")
                sniff_kwargs: Dict[str, Any] = {
                    "prn": self._packet_callback,
                    "stop_filter": lambda p: not self._running,
                    "store": False,
                }
                if self.iface and self.iface.lower() not in ("default", "all", "auto"):
                    sniff_kwargs["iface"] = self.iface

                scapy_all.sniff(**sniff_kwargs)

        except Exception as e:
            err = f"Scapy capture error on interface '{self.iface}': {e}"
            logger.error(err)
            self.error_message = err
        finally:
            self._running = False

    @staticmethod
    def list_interfaces() -> List[Dict[str, str]]:
        """
        Return available physical and virtual network interfaces detected by the OS.
        Prioritizes interfaces with active IP addresses and clean adapter names.
        """
        interfaces: List[Dict[str, str]] = []
        seen_names = set()

        # 1. Try Windows-specific interface list via Scapy
        try:
            from scapy.arch.windows import get_windows_if_list
            win_ifs = get_windows_if_list()

            # Separate into active interfaces (with IPs) and others
            active_ifs = []
            other_ifs = []

            for item in win_ifs:
                name = item.get("name", "").strip()
                desc = item.get("description", "").strip()
                ips = item.get("ips", [])
                ip_str = ", ".join(ips) if ips else ""

                # Skip verbose filter driver sub-entries
                if any(x in name for x in ["Filter Driver", "QoS Packet Scheduler", "LightWeight Filter"]):
                    continue

                if name and name not in seen_names:
                    seen_names.add(name)
                    entry = {
                        "name": name,
                        "description": desc or name,
                        "ip": ip_str or "No assigned IP",
                    }
                    if ips:
                        active_ifs.append(entry)
                    else:
                        other_ifs.append(entry)

            # Prioritize active network adapters (Wi-Fi, Ethernet, Loopback)
            interfaces = active_ifs + other_ifs
        except Exception:
            pass

        # 2. Fallback to generic Scapy get_if_list()
        if not interfaces:
            try:
                for iface_name in scapy_all.get_if_list():
                    name_str = str(iface_name).strip()
                    if name_str and name_str not in seen_names:
                        seen_names.add(name_str)
                        interfaces.append({
                            "name": name_str,
                            "description": name_str,
                            "ip": "Auto-detected",
                        })
            except Exception:
                pass

        # 3. Ensure at least default iface is present
        if not interfaces:
            default_iface = getattr(scapy_all.conf, "iface", "Default NIC")
            interfaces.append({
                "name": str(default_iface),
                "description": "Default System Network Interface",
                "ip": "Active",
            })

        return interfaces

