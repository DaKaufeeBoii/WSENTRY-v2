"""
Live feature extractor converting raw packet windows into 20 behavioral features.
"""
import math
import os
import time
from collections import Counter
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
from sklearn.preprocessing import RobustScaler

from src.data.dataset_loader import FEATURE_COLS


class LiveFeatureExtractor:
    """
    Converts a sliding window of raw scapy packets into the 20 behavioral
    features matching FEATURE_COLS from src/data/dataset_loader.py.
    """

    def __init__(self, scaler_path: str = "models/saved/scaler.pkl") -> None:
        self.scaler_path = scaler_path
        self.scaler = self._load_or_create_scaler(scaler_path)

    def _load_or_create_scaler(self, path: str) -> RobustScaler:
        """Load fitted RobustScaler from disk."""
        candidates = [
            path,
            os.path.abspath(path),
            os.path.join(os.path.dirname(__file__), "..", "..", "models", "saved", "scaler.pkl"),
            os.path.join("models", "saved", "scaler.pkl"),
        ]
        for p in candidates:
            if os.path.exists(p):
                try:
                    loaded = joblib.load(p)
                    if isinstance(loaded, RobustScaler):
                        return loaded
                except Exception:
                    pass

        raise FileNotFoundError(
            f"Fitted RobustScaler not found at '{path}' or candidate locations. "
            "Please ensure real model artifacts exist in models/saved/scaler.pkl."
        )

    def _parse_packet(self, pkt: Any) -> Dict[str, Any]:
        """Extract per-packet raw fields: src_ip, dst_ip, src_port, dst_port,
        protocol, flags, length, payload_length, timestamp."""
        ts = getattr(pkt, "time", time.time())
        length = len(pkt) if hasattr(pkt, "__len__") else getattr(pkt, "len", 64)

        src_ip = "0.0.0.0"
        dst_ip = "0.0.0.0"
        src_port = 0
        dst_port = 0
        protocol_name = "OTHER"
        proto_num = 0.0
        flags_str = ""
        payload_len = 0

        # Layer checking if scapy packet
        haslayer = getattr(pkt, "haslayer", None)
        if callable(haslayer):
            try:
                if pkt.haslayer("IP"):
                    ip_layer = pkt["IP"]
                    src_ip = getattr(ip_layer, "src", "0.0.0.0")
                    dst_ip = getattr(ip_layer, "dst", "0.0.0.0")
                elif pkt.haslayer("IPv6"):
                    ip_layer = pkt["IPv6"]
                    src_ip = getattr(ip_layer, "src", "::")
                    dst_ip = getattr(ip_layer, "dst", "::")
                elif pkt.haslayer("ARP"):
                    arp = pkt["ARP"]
                    src_ip = getattr(arp, "psrc", "0.0.0.0")
                    dst_ip = getattr(arp, "pdst", "0.0.0.0")
                    protocol_name = "ARP"

                if pkt.haslayer("TCP"):
                    tcp = pkt["TCP"]
                    src_port = int(getattr(tcp, "sport", 0))
                    dst_port = int(getattr(tcp, "dport", 0))
                    protocol_name = "TCP"
                    proto_num = 1.0
                    flags_val = getattr(tcp, "flags", "")
                    flags_str = str(flags_val).upper()
                    if hasattr(tcp, "payload"):
                        payload_len = len(tcp.payload)
                elif pkt.haslayer("UDP"):
                    udp = pkt["UDP"]
                    src_port = int(getattr(udp, "sport", 0))
                    dst_port = int(getattr(udp, "dport", 0))
                    protocol_name = "UDP"
                    proto_num = 2.0
                    if hasattr(udp, "payload"):
                        payload_len = len(udp.payload)
                elif pkt.haslayer("ICMP"):
                    protocol_name = "ICMP"
                    proto_num = 3.0
            except Exception:
                pass
        else:
            # Fallback for dict/mock objects in tests
            src_ip = getattr(pkt, "src_ip", getattr(pkt, "src", "0.0.0.0"))
            dst_ip = getattr(pkt, "dst_ip", getattr(pkt, "dst", "0.0.0.0"))
            src_port = getattr(pkt, "src_port", getattr(pkt, "sport", 0))
            dst_port = getattr(pkt, "dst_port", getattr(pkt, "dport", 0))
            proto = getattr(pkt, "protocol", "TCP")
            protocol_name = proto if isinstance(proto, str) else "TCP"
            proto_map = {"TCP": 1.0, "UDP": 2.0, "ICMP": 3.0}
            proto_num = proto_map.get(protocol_name.upper(), 0.0)
            flags_str = str(getattr(pkt, "flags", "")).upper()
            payload_len = getattr(pkt, "payload_len", max(0, length - 40))

        return {
            "timestamp": float(ts),
            "src_ip": str(src_ip),
            "dst_ip": str(dst_ip),
            "src_port": int(src_port),
            "dst_port": int(dst_port),
            "protocol": protocol_name,
            "proto_num": proto_num,
            "flags": flags_str,
            "length": int(length),
            "payload_len": int(payload_len),
        }

    def _extract_vector_for_subwindow(self, sub_window: List[Dict[str, Any]]) -> np.ndarray:
        """Extract a single 20-element feature vector from a window of parsed packets."""
        n_pkts = len(sub_window)
        if n_pkts == 0:
            return np.zeros(len(FEATURE_COLS), dtype=np.float32)

        lengths = [p["length"] for p in sub_window]
        payloads = [p["payload_len"] for p in sub_window]
        timestamps = [p["timestamp"] for p in sub_window]
        src_ports = [p["src_port"] for p in sub_window]
        dst_ports = [p["dst_port"] for p in sub_window]
        flags_list = [p["flags"] for p in sub_window]
        dst_ips = [p["dst_ip"] for p in sub_window]
        proto_nums = [p["proto_num"] for p in sub_window]

        # f_volume: sum of packet lengths in window
        f_volume = float(sum(lengths))

        # f_rate: f_volume / window_duration_seconds
        duration = max(timestamps[-1] - timestamps[0], 0.001) if n_pkts > 1 else 0.01
        f_rate = float(f_volume / duration)

        # f_send_recv_ratio: count(src_port < 1024) / (count(dst_port < 1024) + 1)
        src_privileged = sum(1 for sp in src_ports if 0 < sp < 1024)
        dst_privileged = sum(1 for dp in dst_ports if 0 < dp < 1024)
        f_send_recv_ratio = float(src_privileged / (dst_privileged + 1.0))

        # Flags counts
        syn_count = sum(1 for f in flags_list if "S" in f or "SYN" in f)
        fin_count = sum(1 for f in flags_list if "F" in f or "FIN" in f)
        rst_count = sum(1 for f in flags_list if "R" in f or "RST" in f)
        ack_count = sum(1 for f in flags_list if "A" in f or "ACK" in f)
        psh_count = sum(1 for f in flags_list if "P" in f or "PSH" in f)
        urg_count = sum(1 for f in flags_list if "U" in f or "URG" in f)
        ece_count = sum(1 for f in flags_list if "E" in f or "ECE" in f)

        # Ratios
        f_control_ratio = float((syn_count + fin_count + rst_count) / n_pkts)
        f_ack_ratio = float(ack_count / n_pkts)
        f_syn_ratio = float(syn_count / n_pkts)
        f_fin_rst_ratio = float((fin_count + rst_count) / n_pkts)

        # f_variability: std(packet_lengths) / mean(packet_lengths) + 1
        mean_len = float(np.mean(lengths))
        std_len = float(np.std(lengths))
        f_variability = float((std_len / (mean_len + 1e-5)) + 1.0)

        # f_port_entropy: Shannon entropy of unique dst_ports
        port_counts = Counter(dst_ports)
        entropy = 0.0
        for cnt in port_counts.values():
            p = cnt / n_pkts
            entropy -= p * math.log2(p + 1e-9)
        f_port_entropy = float(entropy)

        # f_flag_intensity: count(PSH|URG|ECE flags)
        f_flag_intensity = float(psh_count + urg_count + ece_count)

        # f_payload_ratio: sum(payload_bytes) / (f_volume + 1e-5) + 1
        f_payload_ratio = float((sum(payloads) / (f_volume + 1e-5)) + 1.0)

        # f_timing: mean(inter-arrival times)
        if n_pkts > 1:
            iats = np.diff(timestamps)
            f_timing = float(np.mean(np.maximum(iats, 0.0)))
        else:
            f_timing = 0.01

        # f_burst: max(packets_per_100ms_bin)
        if n_pkts > 1 and (timestamps[-1] - timestamps[0]) > 0:
            bins = int(max(1, math.ceil((timestamps[-1] - timestamps[0]) / 0.1)))
            hist, _ = np.histogram(timestamps, bins=bins)
            f_burst = float(np.max(hist))
        else:
            f_burst = float(n_pkts)

        # f_protocol_type: mode protocol as float (TCP=1, UDP=2, ICMP=3, other=0)
        mode_proto = Counter(proto_nums).most_common(1)[0][0]
        f_protocol_type = float(mode_proto)

        # f_energy: sum(length^2)
        f_energy = float(sum(L * L for L in lengths))

        # f_distance: count(unique dst_ips)
        f_distance = float(len(set(dst_ips)))

        # f_rank: max_packet_length / mean_packet_length
        f_rank = float(max(lengths) / (mean_len + 1e-5))

        # f_anomaly_score: abs(f_send_recv_ratio - 1) * f_rate
        f_anomaly_score = float(abs(f_send_recv_ratio - 1.0) * f_rate)

        # f_conn_state: count(SYN) + count(ACK) + count(FIN)
        f_conn_state = float(syn_count + ack_count + fin_count)

        # f_mqtt_activity: count(packets with dst_port in {1883, 8883})
        f_mqtt_activity = float(sum(1 for dp in dst_ports if dp in (1883, 8883)))

        feature_dict = {
            "f_volume": f_volume,
            "f_rate": f_rate,
            "f_send_recv_ratio": f_send_recv_ratio,
            "f_control_ratio": f_control_ratio,
            "f_ack_ratio": f_ack_ratio,
            "f_syn_ratio": f_syn_ratio,
            "f_fin_rst_ratio": f_fin_rst_ratio,
            "f_variability": f_variability,
            "f_port_entropy": f_port_entropy,
            "f_flag_intensity": f_flag_intensity,
            "f_payload_ratio": f_payload_ratio,
            "f_timing": f_timing,
            "f_burst": f_burst,
            "f_protocol_type": f_protocol_type,
            "f_energy": f_energy,
            "f_distance": f_distance,
            "f_rank": f_rank,
            "f_anomaly_score": f_anomaly_score,
            "f_conn_state": f_conn_state,
            "f_mqtt_activity": f_mqtt_activity,
        }

        return np.array([feature_dict[col] for col in FEATURE_COLS], dtype=np.float32)

    def extract(self, packets: List[Any], window_size: int = 5) -> np.ndarray:
        """
        Converts a window of packets into shape (1, window_size, 20).
        Applies log-transform, clipping, and RobustScaler transform.
        """
        parsed = [self._parse_packet(p) for p in packets]

        # Ensure we have window_size elements
        if len(parsed) < window_size:
            if len(parsed) == 0:
                # Fallback empty parsed
                parsed = [self._parse_packet(None)] * window_size
            else:
                # Pad with first packet to reach window_size
                pad = [parsed[0]] * (window_size - len(parsed))
                parsed = pad + parsed
        elif len(parsed) > window_size:
            parsed = parsed[-window_size:]

        # For each time step t in the sequence, compute features using history up to t
        vectors = []
        for i in range(1, window_size + 1):
            vec = self._extract_vector_for_subwindow(parsed[:i])
            vectors.append(vec)

        raw_features = np.stack(vectors, axis=0)  # Shape (window_size, 20)

        # Preprocessing matching preprocessor.py:
        # 1. Log-transform
        feat_log = np.sign(raw_features) * np.log1p(np.abs(raw_features))
        # 2. Clip to [-50, 50]
        feat_clip = np.clip(feat_log, -50.0, 50.0).astype(np.float32)
        # 3. RobustScaler transform
        feat_scaled = self.scaler.transform(feat_clip).astype(np.float32)

        # Reshape to (1, window_size, 20)
        return np.expand_dims(feat_scaled, axis=0)

    def extract_single_record_features(self, packet: Any) -> Dict[str, float]:
        """Convenience method to get readable raw feature dict for a single packet."""
        parsed = [self._parse_packet(packet)]
        vec = self._extract_vector_for_subwindow(parsed)
        return {col: float(val) for col, val in zip(FEATURE_COLS, vec)}
