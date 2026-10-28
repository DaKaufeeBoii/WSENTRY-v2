"""
Tab 6: Connection Profiler and Mitigation Engine Log
Displays per-IP host connection profiles, firewall execution logs, and active rule management.
"""
from datetime import datetime, timezone
from collections import defaultdict, Counter
import streamlit as st
import pandas as pd

from src.live.buffer import PacketBuffer
from src.live.mitigation import MitigationEngine, MitigationMode


def render(buffer: PacketBuffer, mitigation: MitigationEngine) -> None:
    st.subheader("Host Connection Profiler & Active Mitigation")

    # Mode Selector and Controls
    c_mode, c_clear, c_stats = st.columns([2, 1, 1])

    with c_mode:
        current_mode = mitigation.mode.value
        mode_options = ["simulated", "windows", "wsl"]
        selected_mode_str = st.selectbox(
            "Firewall Mitigation Mode",
            mode_options,
            index=mode_options.index(current_mode) if current_mode in mode_options else 0,
            help="Simulated: logs actions without OS changes. Windows: netsh advfirewall. WSL: sudo iptables."
        )
        mitigation.mode = MitigationMode(selected_mode_str)

    with c_clear:
        st.write("")
        st.write("")
        if st.button("🗑️ Clear All Rules", type="secondary", width="stretch"):
            active = list(mitigation.get_active_blocks().keys())
            for ip in active:
                mitigation.remove_block(ip)
            st.success(f"Removed {len(active)} active firewall rules.")
            st.rerun()

    with c_stats:
        active_blocks = mitigation.get_active_blocks()
        st.metric("Active Block Rules", len(active_blocks))

    st.markdown("---")

    # Connection Profiler Table (grouped by src_ip)
    st.subheader("Source IP Connection Profiles")
    recent = buffer.get_recent(n=500)

    if recent:
        ip_groups = defaultdict(list)
        for r in recent:
            if r.src_ip not in ["0.0.0.0", ""]:
                ip_groups[r.src_ip].append(r)

        profile_rows = []
        for ip, pkts in ip_groups.items():
            total_cnt = len(pkts)
            threat_cnt = sum(1 for p in pkts if p.prediction > 0)
            threat_labels = [p.label for p in pkts if p.prediction > 0]
            dominant_class = Counter(threat_labels).most_common(1)[0][0] if threat_labels else "Normal"
            avg_conf = sum(p.confidence for p in pkts) / total_cnt if total_cnt > 0 else 0.0

            # Status determination
            if ip in active_blocks:
                status = "🚨 BLOCKED"
            elif threat_cnt > 0:
                status = "⚠️ SUSPICIOUS"
            else:
                status = "🟢 ACTIVE"

            profile_rows.append({
                "Source IP": ip,
                "Packet Count": total_cnt,
                "Threats": threat_cnt,
                "Dominant Category": dominant_class,
                "Avg Confidence": f"{avg_conf * 100:.1f}%",
                "Status": status,
            })

        df_profiles = pd.DataFrame(profile_rows).sort_values(by="Threats", ascending=False)
        st.dataframe(df_profiles, hide_index=True, width="stretch")
    else:
        st.info("No connections registered yet in PacketBuffer.")

    st.markdown("---")

    # Active Blocks Summary
    st.subheader("Active Firewall Rules")
    if active_blocks:
        now = datetime.now(timezone.utc)
        block_rows = []
        for ip, added_at in active_blocks.items():
            elapsed = (now - added_at).total_seconds()
            remaining = max(0, int(300.0 - elapsed))
            block_rows.append({
                "Target IP": ip,
                "Blocked At (UTC)": added_at.strftime("%H:%M:%S"),
                "TTL Remaining": f"{remaining}s",
                "Action": "BLOCK_ALL_INBOUND",
            })
        st.dataframe(pd.DataFrame(block_rows), hide_index=True, width="stretch")
    else:
        st.caption("No active blocking rules currently deployed.")

    st.markdown("---")

    # Mitigation Action Log
    st.subheader("Mitigation Audit Log")
    log_actions = mitigation.get_log()
    if log_actions:
        log_rows = []
        for act in reversed(log_actions[-50:]):
            log_rows.append({
                "Timestamp": act.timestamp.strftime("%H:%M:%S.%f")[:-3],
                "Source IP": act.src_ip,
                "Threat Label": act.threat_label,
                "Action": act.action,
                "Mode": act.mode.value.upper(),
                "Execution Status": "SUCCESS" if act.success else "FAILED",
                "Command / Details": act.rule_command,
            })
        st.dataframe(pd.DataFrame(log_rows), hide_index=True, width="stretch")
    else:
        st.caption("No mitigation events triggered yet.")

