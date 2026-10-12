"""
Firewall mitigation engine for real-time intrusion response (Windows, WSL, Simulated).
"""
import logging
import re
import subprocess
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any

from src.live.buffer import PacketRecord

logger = logging.getLogger("w_sentry.mitigation")


class MitigationMode(str, Enum):
    SIMULATED = "simulated"    # Log only, no actual firewall changes
    WINDOWS = "windows"        # netsh advfirewall on Windows
    WSL = "wsl"                # iptables via WSL


@dataclass
class MitigationAction:
    timestamp: datetime
    threat_class: int
    threat_label: str
    src_ip: str
    dst_ip: str
    action: str               # "BLOCK_IP", "RATE_LIMIT", "ALERT_ONLY"
    rule_command: str          # Command executed or simulated
    mode: MitigationMode
    success: bool
    details: str


class MitigationEngine:
    """
    Issues firewall rules in response to detected threats.
    Supports three modes: simulated (logging only), Windows (netsh),
    and WSL (iptables).
    """

    def __init__(
        self,
        mode: MitigationMode = MitigationMode.SIMULATED,
        cooldown_seconds: float = 30.0,
        max_rules: int = 50,
    ) -> None:
        self.mode = mode
        self.cooldown_seconds = cooldown_seconds
        self.max_rules = max_rules

        self._lock = threading.Lock()
        self._log: List[MitigationAction] = []
        self._active_blocks: Dict[str, datetime] = {}
        self._rule_names: Dict[str, str] = {}  # ip -> rule identifier

    def respond(self, record: PacketRecord) -> Optional[MitigationAction]:
        """
        Decision logic based on threat class:
        - Normal (0): No action.
        - Jamming (1): ALERT_ONLY (cannot block at network layer).
        - Spoofing (2): BLOCK_IP for src_ip.
        - DoS_Flood (3): BLOCK_IP for src_ip + RATE_LIMIT.
        - Intrusion_Probe (4): BLOCK_IP for src_ip.

        Returns None if cooldown not expired for this src_ip, or if threat_class == 0.
        """
        t_class = record.prediction
        src_ip = record.src_ip.strip()
        dst_ip = record.dst_ip.strip()

        # Ignore unclassified or Normal
        if t_class <= 0 or not src_ip or src_ip in ("0.0.0.0", "127.0.0.1", "::1"):
            return None

        now = datetime.now()

        with self._lock:
            # Check cooldown for this IP
            if src_ip in self._active_blocks:
                last_time = self._active_blocks[src_ip]
                elapsed = (now - last_time).total_seconds()
                if elapsed < self.cooldown_seconds:
                    return None

            # Determine action and details
            if t_class == 1:
                action_type = "ALERT_ONLY"
                rule_cmd = "N/A (Physical Layer Jamming - alert triggered)"
                success = True
                details = "Physical/MAC layer RF anomaly. Cannot isolate via IP firewall."
            elif t_class == 2:
                action_type = "BLOCK_IP"
                success, rule_cmd, details = self._dispatch_block(src_ip)
            elif t_class == 3:
                action_type = "BLOCK_IP"
                success, rule_cmd, details = self._dispatch_block(src_ip)
            elif t_class == 4:
                action_type = "BLOCK_IP"
                success, rule_cmd, details = self._dispatch_block(src_ip)
            else:
                return None

            # Record active block timestamp
            self._active_blocks[src_ip] = now

            action = MitigationAction(
                timestamp=now,
                threat_class=t_class,
                threat_label=record.label,
                src_ip=src_ip,
                dst_ip=dst_ip,
                action=action_type,
                rule_command=rule_cmd,
                mode=self.mode,
                success=success,
                details=details,
            )
            self._log.append(action)
            return action

    def _sanitize_ip_for_rule(self, ip: str) -> str:
        return re.sub(r"[^0-9a-zA-Z_]", "_", ip)

    def _dispatch_block(self, src_ip: str) -> Tuple[bool, str, str]:
        rule_suffix = self._sanitize_ip_for_rule(src_ip)
        rule_name = f"BLOCK_{rule_suffix}"
        self._rule_names[src_ip] = rule_name

        if self.mode == MitigationMode.SIMULATED:
            cmd = f'netsh advfirewall firewall add rule name="W-SENTRY_{rule_name}" dir=in action=block remoteip={src_ip}'
            return True, f"[SIMULATED] {cmd}", "Simulated rule recorded successfully."
        elif self.mode == MitigationMode.WINDOWS:
            return self._execute_block_windows(src_ip, rule_name)
        elif self.mode == MitigationMode.WSL:
            return self._execute_block_wsl(src_ip)
        return False, "UNKNOWN_MODE", "Unsupported mode."

    def _execute_block_windows(self, src_ip: str, rule_name: str) -> Tuple[bool, str, str]:
        cmd = f'netsh advfirewall firewall add rule name="W-SENTRY_{rule_name}" dir=in action=block remoteip={src_ip} protocol=any'
        try:
            res = subprocess.run(
                ["netsh", "advfirewall", "firewall", "add", "rule",
                 f"name=W-SENTRY_{rule_name}", "dir=in", "action=block",
                 f"remoteip={src_ip}", "protocol=any"],
                capture_output=True, text=True, check=False,
            )
            if res.returncode == 0:
                return True, cmd, "Windows firewall rule applied."
            return False, cmd, f"Failed: {res.stderr.strip() or res.stdout.strip()}"
        except Exception as e:
            return False, cmd, f"Exception: {str(e)}"

    def _execute_block_wsl(self, src_ip: str) -> Tuple[bool, str, str]:
        cmd = f"wsl -e sudo iptables -A INPUT -s {src_ip} -j DROP"
        try:
            res = subprocess.run(
                ["wsl", "-e", "sudo", "iptables", "-A", "INPUT", "-s", src_ip, "-j", "DROP"],
                capture_output=True, text=True, check=False,
            )
            if res.returncode == 0:
                return True, cmd, "WSL iptables rule applied."
            return False, cmd, f"WSL error: {res.stderr.strip()}"
        except Exception as e:
            return False, cmd, f"Exception: {str(e)}"

    def _execute_rate_limit_wsl(self, src_ip: str, limit: str = "10/minute") -> Tuple[bool, str, str]:
        cmd = f"wsl -e sudo iptables -A INPUT -s {src_ip} -m limit --limit {limit} -j ACCEPT"
        try:
            res = subprocess.run(
                ["wsl", "-e", "sudo", "iptables", "-A", "INPUT", "-s", src_ip,
                 "-m", "limit", "--limit", limit, "-j", "ACCEPT"],
                capture_output=True, text=True, check=False,
            )
            return (res.returncode == 0), cmd, res.stderr.strip()
        except Exception as e:
            return False, cmd, str(e)

    def cleanup_expired(self, max_age_seconds: float = 300.0) -> int:
        """Remove firewall rules older than max_age_seconds. Returns count removed."""
        with self._lock:
            now = datetime.now()
            expired_ips = [
                ip for ip, added in self._active_blocks.items()
                if (now - added).total_seconds() > max_age_seconds
            ]
            count = 0
            for ip in expired_ips:
                self._remove_rule(ip)
                del self._active_blocks[ip]
                count += 1
            return count

    def _remove_rule(self, ip: str) -> None:
        rule_name = self._rule_names.get(ip, f"BLOCK_{self._sanitize_ip_for_rule(ip)}")
        if self.mode == MitigationMode.WINDOWS:
            try:
                subprocess.run(
                    ["netsh", "advfirewall", "firewall", "delete", "rule", f"name=W-SENTRY_{rule_name}"],
                    capture_output=True, check=False,
                )
            except Exception:
                pass
        elif self.mode == MitigationMode.WSL:
            try:
                subprocess.run(
                    ["wsl", "-e", "sudo", "iptables", "-D", "INPUT", "-s", ip, "-j", "DROP"],
                    capture_output=True, check=False,
                )
            except Exception:
                pass

    def clear_all_rules(self) -> int:
        """Clear all active rules and history."""
        with self._lock:
            count = len(self._active_blocks)
            for ip in list(self._active_blocks.keys()):
                self._remove_rule(ip)
            self._active_blocks.clear()
            self._rule_names.clear()
            return count

    def get_log(self) -> List[MitigationAction]:
        with self._lock:
            return list(self._log)

    def get_active_blocks(self) -> Dict[str, datetime]:
        with self._lock:
            return dict(self._active_blocks)
