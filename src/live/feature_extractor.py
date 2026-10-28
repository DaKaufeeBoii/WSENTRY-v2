"""
Live feature extraction converting raw Scapy packets into the 20 behavioral features.
"""
import os
import math
import joblib
import numpy as np
from typing import List, Dict, Any, Optional
from collections import Counter
from sklearn.preprocessing import RobustScaler

from src.data.dataset_loader import FEATURE_COLS


class LiveFeatureExtractor:
    """
    Extracts the 20 behavioral features from a sliding window of network packets.
    Matches the schema of FEATURE_COLS in src/data/dataset_loader.py.
    """

    def __init__(self, scaler_path: Optional[str] = "models/saved/scaler.pkl", window_size: int = 5) -> None:
        self.window_size = window_size
        self.scaler = None
        if scaler_path and os.path.exists(scaler_path):
            try:
                self.scaler = joblib.load(scaler_path)
            except Exception as e:
                print(f"[LiveFeatureExtractor] Warning: Could not load scaler from {scaler_path}: {e}")
        if self.scaler is None:
            # Fallback initialized scaler with neutral medians/scales
            self.scaler = RobustScaler()
            dummy_data = np.zeros((10, len(FEATURE_COLS)), dtype=np.float32)
            self.scaler.fit(dummy_data)

    def parse_packet(self, pkt: Any) -> Dict[str, Any]:
        """Extracts normalized primitive fields from a Scapy packet or dict."""
        if isinstance(pkt, dict):
            return pkt

        info = {
            "timestamp": getattr(pkt, "time", 0.0),
            "length": len(pkt),
            "payload_length": len(getattr(pkt, "payload", b"")),
            "protocol": "OTHER",
            "src_ip": "0.0.0.0",
            "dst_ip": "0.0.0.0",
            "src_port": 0,
            "dst_port": 0,
            "flags": "",
        }

        # IP layer
        if pkt.haslayer("IP"):
            info["src_ip"] = pkt["IP"].src
            info["dst_ip"] = pkt["IP"].dst

        # Transport layer
        if pkt.haslayer("TCP"):
            info["protocol"] = "TCP"
            info["src_port"] = pkt["TCP"].sport
            info["dst_port"] = pkt["TCP"].dport
            info["flags"] = str(pkt["TCP"].flags)
        elif pkt.haslayer("UDP"):
            info["protocol"] = "UDP"
            info["src_port"] = pkt["UDP"].sport
            info["dst_port"] = pkt["UDP"].dport
        elif pkt.haslayer("ICMP"):
            info["protocol"] = "ICMP"
        elif pkt.haslayer("ARP"):
            info["protocol"] = "ARP"
            if hasattr(pkt["ARP"], "psrc"):
                info["src_ip"] = pkt["ARP"].psrc
                info["dst_ip"] = pkt["ARP"].pdst

        return info

    def extract_features_dict(self, parsed_window: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Computes the 20 behavioral features for a window of parsed packet dicts.
        """
        n = max(len(parsed_window), 1)
        lengths = [p["length"] for p in parsed_window]
        timestamps = [p["timestamp"] for p in parsed_window]
        duration = max(max(timestamps) - min(timestamps), 0.001) if len(timestamps) > 1 else 0.001

        # 1. f_volume
        f_volume = float(sum(lengths))

        # 2. f_rate
        f_rate = float(f_volume / duration)

        # 3. f_send_recv_ratio: count(src_port < 1024) / count(dst_port < 1024) + 1
        src_priv = sum(1 for p in parsed_window if p["src_port"] < 1024)
        dst_priv = sum(1 for p in parsed_window if p["dst_port"] < 1024)
        f_send_recv_ratio = float(src_priv / (dst_priv + 1.0))

        # Flags counts
        syn_count = sum(1 for p in parsed_window if "S" in p["flags"])
        ack_count = sum(1 for p in parsed_window if "A" in p["flags"])
        fin_rst_count = sum(1 for p in parsed_window if ("F" in p["flags"] or "R" in p["flags"]))
        psh_urg_ece = sum(1 for p in parsed_window if any(flag in p["flags"] for flag in ["P", "U", "E"]))

        # 4. f_control_ratio
        f_control_ratio = float((syn_count + fin_rst_count) / n)

        # 5. f_ack_ratio
        f_ack_ratio = float(ack_count / n)

        # 6. f_syn_ratio
        f_syn_ratio = float(syn_count / n)

        # 7. f_fin_rst_ratio
        f_fin_rst_ratio = float(fin_rst_count / n)

        # 8. f_variability: std(lengths) / mean(lengths) + 1
        mean_len = np.mean(lengths) if lengths else 1.0
        std_len = np.std(lengths) if lengths else 0.0
        f_variability = float(std_len / (mean_len + 1.0) + 1.0)

        # 9. f_port_entropy: Shannon entropy of unique dst_ports
        dst_ports = [p["dst_port"] for p in parsed_window]
        port_counts = Counter(dst_ports)
        entropy = 0.0
        for cnt in port_counts.values():
            p_val = cnt / n
            entropy -= p_val * math.log2(p_val)
        f_port_entropy = float(entropy)

        # 10. f_flag_intensity
        f_flag_intensity = float(psh_urg_ece)

        # 11. f_payload_ratio
        payload_sum = sum(p["payload_length"] for p in parsed_window)
        f_payload_ratio = float(payload_sum / (f_volume + 1.0) + 1.0)

        # 12. f_timing: mean inter-arrival time
        if len(timestamps) > 1:
            sorted_t = sorted(timestamps)
            iats = [sorted_t[i] - sorted_t[i - 1] for i in range(1, len(sorted_t))]
            f_timing = float(np.mean(iats))
        else:
            f_timing = 0.01

        # 13. f_burst: max packets per 100ms bin
        if len(timestamps) > 1:
            min_t = min(timestamps)
            bins = Counter(int((t - min_t) / 0.1) for t in timestamps)
            f_burst = float(max(bins.values()))
        else:
            f_burst = 1.0

        # 14. f_protocol_type: mode protocol as float (TCP=1, UDP=2, ICMP=3, other=0)
        proto_map = {"TCP": 1.0, "UDP": 2.0, "ICMP": 3.0}
        proto_counts = Counter(p["protocol"] for p in parsed_window)
        mode_proto = proto_counts.most_common(1)[0][0] if proto_counts else "TCP"
        f_protocol_type = float(proto_map.get(mode_proto, 0.0))

        # 15. f_energy: sum(length^2)
        f_energy = float(sum(l ** 2 for l in lengths))

        # 16. f_distance: count of unique dst_ips
        f_distance = float(len(set(p["dst_ip"] for p in parsed_window)))

        # 17. f_rank: max_packet_length / mean_packet_length
        f_rank = float(max(lengths) / (mean_len + 1.0)) if lengths else 1.0

        # 18. f_anomaly_score: abs(f_send_recv_ratio - 1) * f_rate
        f_anomaly_score = float(abs(f_send_recv_ratio - 1.0) * (f_rate / 1000.0))

        # 19. f_conn_state: count(SYN) + count(ACK) + count(FIN)
        f_conn_state = float(syn_count + ack_count + fin_rst_count)

        # 20. f_mqtt_activity: packets with dst_port in {1883, 8883}
        mqtt_pkts = sum(1 for p in parsed_window if p["dst_port"] in {1883, 8883})
        f_mqtt_activity = float(mqtt_pkts)

        return {
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

    def extract(self, packets: List[Any]) -> np.ndarray:
        """
        Converts a list of packets into model input array of shape (1, window_size, 20).
        Applies log-norm, clipping, and RobustScaler transform.
        """
        parsed = [self.parse_packet(p) for p in packets]
        if not parsed:
            # Empty fallback
            return np.zeros((1, self.window_size, len(FEATURE_COLS)), dtype=np.float32)

        # Pad window if smaller than window_size
        while len(parsed) < self.window_size:
            parsed.append(parsed[-1])

        # For temporal dynamics, compute feature vector per step in window
        step_features = []
        for i in range(1, self.window_size + 1):
            sub_window = parsed[:i]
            feats = self.extract_features_dict(sub_window)
            vec = [feats[col] for col in FEATURE_COLS]
            step_features.append(vec)

        # Array of shape (window_size, 20)
        X = np.array(step_features, dtype=np.float64)

        # Log-transform and clip matching preprocessor.py
        X = np.sign(X) * np.log1p(np.abs(X))
        X = np.clip(X, -50.0, 50.0).astype(np.float32)

        # RobustScaler
        if self.scaler is not None:
            try:
                X = self.scaler.transform(X).astype(np.float32)
            except Exception:
                pass

        # Shape as batch of 1: (1, window_size, 20)
        return np.expand_dims(X, axis=0)

