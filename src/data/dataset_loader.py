"""
W-SENTRY dataset loaders v3.
Two-track: native features (best same-dataset) + behavioral features (cross-dataset).
"""
import pandas as pd
import numpy as np

THREAT_MAP = {0: "Normal", 1: "Jamming", 2: "Spoofing", 3: "DoS_Flood", 4: "Intrusion_Probe"}

WSN_LABEL_MAP = {
    "Normal": 0, "TDMA": 1, "Blackhole": 2, "Grayhole": 2, "Flooding": 3,
}
CIC_LABEL_MAP = {
    "BenignTraffic": 0,
    "MITM-ArpSpoofing": 2, "DNS_Spoofing": 2,
    "DDoS-ICMP_Flood": 3, "DDoS-UDP_Flood": 3, "DDoS-TCP_Flood": 3,
    "DDoS-PSHACK_Flood": 3, "DDoS-SYN_Flood": 3, "DDoS-RSTFINFlood": 3,
    "DDoS-SynonymousIP_Flood": 3, "DDoS-ICMP_Fragmentation": 3,
    "DDoS-UDP_Fragmentation": 3, "DDoS-ACK_Fragmentation": 3,
    "DDoS-HTTP_Flood": 3, "DDoS-SlowLoris": 3,
    "DoS-UDP_Flood": 3, "DoS-TCP_Flood": 3, "DoS-SYN_Flood": 3,
    "DoS-HTTP_Flood": 3,
    "Mirai-greeth_flood": 3, "Mirai-udpplain": 3, "Mirai-greip_flood": 3,
    "Recon-HostDiscovery": 4, "Recon-OSScan": 4, "Recon-PortScan": 4,
    "Recon-PingSweep": 4, "VulnerabilityScan": 4,
    "CommandInjection": 4, "SqlInjection": 4, "XSS": 4,
    "BrowserHijacking": 4, "Backdoor_Malware": 4,
    "DictionaryBruteForce": 4, "Uploading_Attack": 4,
}
EDGE_LABEL_MAP = {
    "Normal": 0, "MITM": 2,
    "DDoS_UDP": 3, "DDoS_ICMP": 3, "DDoS_TCP": 3, "DDoS_HTTP": 3,
    "SQL_injection": 4, "Password": 4, "Vulnerability_scanner": 4,
    "Uploading": 4, "Backdoor": 4, "Port_Scanning": 4,
    "XSS": 4, "Ransomware": 4, "Fingerprinting": 4,
}

# ---- Native feature columns per dataset (best same-dataset accuracy) ----

EDGE_NATIVE_COLS = [
    "tcp.flags.ack", "tcp.flags", "tcp.ack_raw", "dns.qry.name.len",
    "icmp.seq_le", "tcp.checksum", "udp.stream", "icmp.checksum",
    "dns.qry.qu", "tcp.dstport", "tcp.len", "udp.time_delta",
    "mqtt.hdrflags", "mqtt.msgtype", "mqtt.len", "tcp.seq",
    "mqtt.conflag.cleansess", "mqtt.conflags", "mqtt.proto_len",
    "mqtt.ver", "mqtt.topic_len", "http.response", "tcp.connection.fin",
    "tcp.ack", "tcp.srcport", "tcp.connection.syn", "tcp.connection.synack",
    "arp.hw.size", "arp.opcode", "http.content_length",
    "tcp.connection.rst", "udp.port", "dns.qry.type",
    "mbtcp.len", "mbtcp.trans_id",
]  # 35 features from ML-EdgeIIoT with real class discrimination

# ---- Cross-dataset behavioral features (20 features) ----

FEATURE_COLS = [
    "f_volume", "f_rate", "f_send_recv_ratio", "f_control_ratio",
    "f_ack_ratio", "f_syn_ratio", "f_fin_rst_ratio", "f_variability",
    "f_port_entropy", "f_flag_intensity", "f_payload_ratio", "f_timing",
    "f_burst", "f_protocol_type", "f_energy", "f_distance",
    "f_rank", "f_anomaly_score", "f_conn_state", "f_mqtt_activity",
]


def _safe(series, default=0.0):
    return pd.to_numeric(series, errors="coerce").fillna(default)


def _stratified_sample(df, label_col, max_rows, min_per_class=200):
    if len(df) <= max_rows:
        return df
    samples = []
    counts = df[label_col].value_counts()
    n_classes = len(counts)
    guaranteed = min(min_per_class, max_rows // n_classes)
    remaining = max_rows - guaranteed * n_classes
    for label, grp in df.groupby(label_col):
        n_prop = max(0, int(remaining * len(grp) / len(df)))
        n = min(len(grp), guaranteed + n_prop)
        samples.append(grp.sample(n, random_state=42))
    return pd.concat(samples, ignore_index=True)


# ===================== WSN-DS =====================

def load_wsn(path="data/raw/WSN-DS.csv", max_rows=200000, mode="native"):
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()
    if max_rows:
        df = _stratified_sample(df, "Attack type", max_rows)
    df["threat_class"] = df["Attack type"].map(WSN_LABEL_MAP)
    df = df.dropna(subset=["threat_class"])
    df["threat_class"] = df["threat_class"].astype(int)

    time_col = df["Time"].replace(0, 1).astype(float)
    data_total = (df["DATA_S"] + df["DATA_R"]).astype(float)
    ctrl_total = (df["ADV_S"] + df["ADV_R"] + df["JOIN_S"] + df["JOIN_R"]
                  + df["SCH_S"] + df["SCH_R"]).astype(float)

    if mode == "native":
        # WSN native features = same as behavioral (routing-layer dataset)
        pass

    features = pd.DataFrame({
        "f_volume":          data_total,
        "f_rate":            data_total / time_col,
        "f_send_recv_ratio": df["DATA_S"] / (df["DATA_R"] + 1),
        "f_control_ratio":   ctrl_total / (data_total + 1),
        "f_ack_ratio":       df["ADV_R"] / (df["ADV_S"] + 1),
        "f_syn_ratio":       df["JOIN_S"] / (data_total + 1),
        "f_fin_rst_ratio":   df["SCH_S"] / (data_total + 1),
        "f_variability":     df["Expaned Energy"] / (time_col * (data_total + 1)),
        "f_port_entropy":    df["Rank"].astype(float) / (df["Rank"].max() + 1),
        "f_flag_intensity":  df["send_code"].astype(float),
        "f_payload_ratio":   df["Data_Sent_To_BS"] / (data_total + 1),
        "f_timing":          time_col,
        "f_burst":           (df["SCH_S"] + df["SCH_R"]).astype(float),
        "f_protocol_type":   df["Is_CH"].astype(float),
        "f_energy":          df["Expaned Energy"].astype(float),
        "f_distance":        df["Dist_To_CH"] / (df["dist_CH_To_BS"] + 1),
        "f_rank":            df["Rank"].astype(float),
        "f_anomaly_score":   (df["DATA_S"] - df["DATA_R"]).abs() / (data_total + 1),
        "f_conn_state":      (df["JOIN_S"] + df["JOIN_R"]).astype(float),
        "f_mqtt_activity":   0.0,
    })
    features["threat_class"] = df["threat_class"].values
    features["dataset"] = "wsn"
    return features.replace([np.inf, -np.inf], 0).fillna(0)


# ===================== CIC-IoT =====================

def load_cic(path="data/raw/IoT_Intrusion.csv", max_rows=200000, mode="native"):
    df = pd.read_csv(path)
    if max_rows:
        df = _stratified_sample(df, "label", max_rows, min_per_class=200)
    df["threat_class"] = df["label"].map(CIC_LABEL_MAP)
    df = df.dropna(subset=["threat_class"])
    df["threat_class"] = df["threat_class"].astype(int)

    duration = df["Duration"].replace(0, 1).astype(float)
    number = df["Number"].replace(0, 1).astype(float)

    features = pd.DataFrame({
        "f_volume":          df["Tot sum"].astype(float),
        "f_rate":            df["Rate"].astype(float),
        "f_send_recv_ratio": df["Srate"] / (df["Drate"] + 1),
        "f_control_ratio":   (df["syn_count"] + df["fin_count"] + df["rst_count"]) / number,
        "f_ack_ratio":       df["ack_count"] / number,
        "f_syn_ratio":       df["syn_count"] / number,
        "f_fin_rst_ratio":   (df["fin_count"] + df["rst_count"]) / number,
        "f_variability":     df["Std"] / (df["AVG"] + 1),
        "f_port_entropy":    df["Covariance"].astype(float),
        "f_flag_intensity":  (df["psh_flag_number"] + df["ece_flag_number"]).astype(float),
        "f_payload_ratio":   df["AVG"] / (df["Max"] + 1),
        "f_timing":          df["IAT"].astype(float),
        "f_burst":           df["Magnitue"].astype(float),
        "f_protocol_type":   df["Protocol Type"].astype(float),
        "f_energy":          df["Tot size"].astype(float),
        "f_distance":        df["Radius"].astype(float),
        "f_rank":            df["Weight"].astype(float),
        "f_anomaly_score":   df["Variance"].astype(float),
        "f_conn_state":      (df["syn_flag_number"] + df["ack_flag_number"]).astype(float),
        "f_mqtt_activity":   (df["DNS"] + df["DHCP"] + df["ARP"]).astype(float),
    })
    features["threat_class"] = df["threat_class"].values
    features["dataset"] = "cic"
    return features.replace([np.inf, -np.inf], 0).fillna(0)


# ===================== Edge-IIoT =====================

def _load_edge_raw(path, max_rows):
    """Load and sample raw Edge-IIoT dataframe."""
    df = pd.read_csv(path, low_memory=False)
    df["Attack_type"] = df["Attack_type"].astype(str).str.strip()
    if max_rows:
        df = _stratified_sample(df, "Attack_type", max_rows, min_per_class=200)
    df["threat_class"] = df["Attack_type"].map(EDGE_LABEL_MAP)
    df = df.dropna(subset=["threat_class"])
    df["threat_class"] = df["threat_class"].astype(int)
    return df


def load_edge(path="data/raw/DNN-EdgeIIoT-dataset.csv", max_rows=200000, mode="native"):
    # Use pre-balanced ML file for native mode (better class balance + cleaner features)
    if mode == "native":
        ml_path = path.replace("DNN-EdgeIIoT-dataset.csv", "ML-EdgeIIoT-dataset.csv")
        import os
        if os.path.exists(ml_path):
            path = ml_path

    df = _load_edge_raw(path, max_rows)

    if mode == "native":
        # Use the 24 most discriminative raw columns directly
        features = pd.DataFrame()
        for col in EDGE_NATIVE_COLS:
            features[col] = _safe(df[col])
        features["threat_class"] = df["threat_class"].values
        features["dataset"] = "edge"
        return features.replace([np.inf, -np.inf], 0).fillna(0)

    # Behavioral mode for cross-dataset
    tcp_len = _safe(df["tcp.len"])
    tcp_flags_ack = _safe(df["tcp.flags.ack"])
    tcp_flags = _safe(df["tcp.flags"])
    tcp_seq = _safe(df["tcp.seq"])
    tcp_ack = _safe(df["tcp.ack"])
    tcp_dstport = _safe(df["tcp.dstport"])
    tcp_srcport = _safe(df["tcp.srcport"])
    tcp_checksum = _safe(df["tcp.checksum"])
    tcp_conn_syn = _safe(df["tcp.connection.syn"])
    tcp_conn_fin = _safe(df["tcp.connection.fin"])
    tcp_conn_rst = _safe(df["tcp.connection.rst"])
    mqtt_len = _safe(df["mqtt.len"])
    mqtt_hdr = _safe(df["mqtt.hdrflags"])
    mqtt_msgtype = _safe(df["mqtt.msgtype"])
    mqtt_topic_len = _safe(df["mqtt.topic_len"])
    mqtt_ver = _safe(df["mqtt.ver"])
    dns_qry_len = _safe(df["dns.qry.name.len"])
    udp_time = _safe(df["udp.time_delta"])
    udp_port = _safe(df["udp.port"])
    udp_stream = _safe(df["udp.stream"])
    icmp_seq = _safe(df["icmp.seq_le"])
    icmp_cksum = _safe(df["icmp.checksum"])

    time_proxy = udp_time.replace(0, 1)

    features = pd.DataFrame({
        "f_volume":          tcp_len + mqtt_len,
        "f_rate":            (tcp_len + mqtt_len) / time_proxy,
        "f_send_recv_ratio": tcp_srcport / (tcp_dstport + 1),
        "f_control_ratio":   (tcp_conn_syn + tcp_conn_fin + tcp_conn_rst) / (tcp_len + 1),
        "f_ack_ratio":       tcp_flags_ack,
        "f_syn_ratio":       tcp_conn_syn,
        "f_fin_rst_ratio":   tcp_conn_fin + tcp_conn_rst,
        "f_variability":     tcp_checksum / (tcp_checksum.mean() + 1),
        "f_port_entropy":    (tcp_srcport - tcp_dstport).abs() / (tcp_srcport + tcp_dstport + 1),
        "f_flag_intensity":  tcp_flags,
        "f_payload_ratio":   dns_qry_len / (tcp_len + dns_qry_len + 1),
        "f_timing":          udp_time,
        "f_burst":           icmp_seq + icmp_cksum,
        "f_protocol_type":   (udp_port > 0).astype(float) + (dns_qry_len > 0).astype(float),
        "f_energy":          udp_stream,
        "f_distance":        mqtt_topic_len + mqtt_msgtype,
        "f_rank":            mqtt_hdr / (mqtt_len + 1),
        "f_anomaly_score":   tcp_seq / (tcp_ack + 1),
        "f_conn_state":      tcp_conn_syn + tcp_flags_ack + tcp_conn_fin,
        "f_mqtt_activity":   mqtt_len + mqtt_ver,
    })
    features["threat_class"] = df["threat_class"].values
    features["dataset"] = "edge"
    return features.replace([np.inf, -np.inf], 0).fillna(0)


def get_feature_cols(mode="native", dataset="wsn"):
    """Return the feature column list for a given mode/dataset."""
    if mode == "native" and dataset == "edge":
        return EDGE_NATIVE_COLS
    return FEATURE_COLS
