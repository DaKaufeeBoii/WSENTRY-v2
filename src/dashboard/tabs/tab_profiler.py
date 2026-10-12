"""
Tab 6: Connection Profiler & Firewall Mitigation Log.
"""
from collections import defaultdict, Counter
from datetime import datetime
import pandas as pd
import streamlit as st

from src.live.buffer import PacketBuffer
from src.live.mitigation import MitigationEngine, MitigationMode
from src.live.inference import THREAT_LABELS


def render(buffer: PacketBuffer, mitigation: MitigationEngine) -> None:
    st.subheader("Connection Profiler & Automated Firewall Mitigation")
    st.caption("Active host telemetry, automated defense dispatch, and real-time firewall rule auditing.")

    # 1. Mitigation Engine Configuration Bar
    cfg_col1, cfg_col2, cfg_col3 = st.columns([2, 1.5, 1.5])

    with cfg_col1:
        current_mode = mitigation.mode.value if hasattr(mitigation.mode, "value") else str(mitigation.mode)
        mode_idx = ["simulated", "windows", "wsl"].index(current_mode) if current_mode in ["simulated", "windows", "wsl"] else 0
        new_mode_str = st.selectbox(
            "Firewall Defense Mode:",
            ["simulated", "windows", "wsl"],
            index=mode_idx,
            format_func=lambda m: {
                "simulated": "🛡️ Simulated (Dry-Run / Audit Log)",
                "windows": "⚡ Windows Host (netsh advfirewall)",
                "wsl": "🐧 WSL Ubuntu (iptables packet drop)",
            }[m],
        )
        if new_mode_str != current_mode:
            mitigation.mode = MitigationMode(new_mode_str)
            st.success(f"Switched mitigation mode to: {mitigation.mode.value.upper()}")

    with cfg_col2:
        st.write("")
        st.write("")
        if st.button("🗑️ Clear All Active Rules", type="secondary", use_container_width=True):
            removed = mitigation.clear_all_rules()
            st.info(f"Cleared {removed} active firewall rules.")
            st.rerun()

    with cfg_col3:
        st.write("")
        st.write("")
        if st.button("🔄 Expire Old Blocks", use_container_width=True):
            cleaned = mitigation.cleanup_expired(max_age_seconds=60.0)
            st.info(f"Expired {cleaned} rules older than 60s.")
            st.rerun()

    st.markdown("---")

    # 2. Host Connection Profiler Table
    st.markdown("### Host Connection Profiles (Grouped by Source IP)")
    recent_packets = buffer.get_recent(500)
    active_blocks = mitigation.get_active_blocks()

    if recent_packets:
        ip_groups = defaultdict(list)
        for p in recent_packets:
            if p.src_ip and p.src_ip not in ("0.0.0.0", "::"):
                ip_groups[p.src_ip].append(p)

        profile_rows = []
        for src_ip, pkts in ip_groups.items():
            total_count = len(pkts)
            threat_pkts = [p for p in pkts if p.prediction > 0]
            threat_count = len(threat_pkts)

            # Dominant class
            preds = [p.prediction for p in pkts if p.prediction >= 0]
            if preds:
                dominant_code = Counter(preds).most_common(1)[0][0]
                dominant_label = THREAT_LABELS.get(dominant_code, "Normal")
            else:
                dominant_label = "Pending"

            # Average confidence
            confs = [p.confidence for p in pkts if p.confidence > 0]
            avg_conf = (sum(confs) / len(confs) * 100) if confs else 0.0

            # Status
            if src_ip in active_blocks:
                status = "🔴 BLOCKED"
            elif threat_count > 0:
                status = "🟠 FLAGGED"
            else:
                status = "🟢 ACTIVE"

            profile_rows.append({
                "Source IP": src_ip,
                "Packet Count": total_count,
                "Threats": threat_count,
                "Dominant Class": dominant_label,
                "Avg Confidence": f"{avg_conf:.1f}%",
                "Status": status,
            })

        df_profiles = pd.DataFrame(profile_rows).sort_values(by="Threats", ascending=False)
        st.dataframe(df_profiles, height=220)
    else:
        st.info("No network activity captured yet.")

    st.markdown("---")

    # 3. Active Firewall Rules and Mitigation Audit Log
    col_active, col_log = st.columns([1, 2])

    with col_active:
        st.markdown("### Active Rule Leases")
        now = datetime.now()
        active_items = []
        for ip, added in active_blocks.items():
            elapsed = (now - added).total_seconds()
            remaining = max(0, int(300.0 - elapsed))
            active_items.append({
                "Blocked IP": ip,
                "Remaining": f"{remaining}s",
            })

        if active_items:
            st.dataframe(pd.DataFrame(active_items), height=250)
        else:
            st.success("No active IP block rules currently enforced.")

    with col_log:
        st.markdown("### Mitigation Action Audit Log")
        actions = mitigation.get_log()
        if actions:
            log_rows = []
            for a in reversed(actions[-50:]):
                t_str = a.timestamp.strftime("%H:%M:%S")
                status_icon = "✅" if a.success else "❌"
                log_rows.append({
                    "Time": t_str,
                    "Source IP": a.src_ip,
                    "Threat": a.threat_label,
                    "Action": a.action,
                    "Command": a.rule_command,
                    "Mode": a.mode.value if hasattr(a.mode, "value") else str(a.mode),
                    "Status": f"{status_icon} {'Success' if a.success else 'Failed'}",
                })
            st.dataframe(pd.DataFrame(log_rows), height=250)
        else:
            st.info("No mitigation actions triggered yet.")
