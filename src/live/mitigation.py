"""
Firewall mitigation engine issuing active defence rules on Windows (netsh) and WSL (iptables).
"""
import subprocess
import logging
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any

from src.live.buffer import PacketRecord


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
    rule_command: str          # Actual command that was/would be executed
    mode: MitigationMode
    success: bool
    details: str = ""


class MitigationEngine:
    """
    Automated network defense engine that converts classified threats into firewall rules.
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
        self._log: List[MitigationAction] = []
        self._active_blocks: Dict[str, datetime] = {}
        self._rule_names: Dict[str, str] = {}

    def respond(self, record: PacketRecord) -> Optional[MitigationAction]:
        """
        Evaluates threat class and executes mitigation if not in cooldown.
        """
        threat_class = record.prediction
        threat_label = record.label
        src_ip = record.src_ip
        now = datetime.now(timezone.utc)

        # 0. Normal traffic -> no action
        if threat_class <= 0 or src_ip in ["0.0.0.0", "127.0.0.1", ""]:
            return None

        # Check cooldown for this IP
        if src_ip in self._active_blocks:
            last_action_time = self._active_blocks[src_ip]
            if (now - last_action_time).total_seconds() < self.cooldown_seconds:
                return None

        # Determine defense action
        action_type = "ALERT_ONLY"
        rule_cmd = ""
        success = True
        details = "Informational alert"

        if threat_class == 1:
            # Jamming: physical/MAC layer issue
            action_type = "ALERT_ONLY"
            rule_cmd = "N/A (Physical/RF Interference)"
            details = "RF anomaly detected; recommend dynamic channel hopping."
        elif threat_class == 2:
            # Spoofing
            action_type = "BLOCK_IP"
            success, rule_cmd, details = self._execute_block(src_ip)
        elif threat_class == 3:
            # DoS Flood
            action_type = "BLOCK_IP"
            success, rule_cmd, details = self._execute_block(src_ip)
        elif threat_class == 4:
            # Intrusion Probe
            action_type = "BLOCK_IP"
            success, rule_cmd, details = self._execute_block(src_ip)

        mitigation = MitigationAction(
            timestamp=now,
            threat_class=threat_class,
            threat_label=threat_label,
            src_ip=src_ip,
            dst_ip=record.dst_ip,
            action=action_type,
            rule_command=rule_cmd,
            mode=self.mode,
            success=success,
            details=details,
        )

        self._log.append(mitigation)
        self._active_blocks[src_ip] = now
        return mitigation

    def _execute_block(self, src_ip: str) -> Tuple[bool, str, str]:
        rule_name = f"WSENTRY_BLOCK_{src_ip.replace('.', '_')}"
        self._rule_names[src_ip] = rule_name

        if self.mode == MitigationMode.SIMULATED:
            cmd = f"netsh advfirewall firewall add rule name=\"{rule_name}\" dir=in action=block remoteip={src_ip}"
            return True, cmd, "Simulated block recorded."

        if self.mode == MitigationMode.WINDOWS:
            cmd = f"netsh advfirewall firewall add rule name=\"{rule_name}\" dir=in action=block remoteip={src_ip} protocol=any"
            try:
                res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
                success = res.returncode == 0
                return success, cmd, res.stdout or res.stderr
            except Exception as e:
                return False, cmd, str(e)

        if self.mode == MitigationMode.WSL:
            cmd = f"wsl -e sudo iptables -A INPUT -s {src_ip} -j DROP"
            try:
                res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
                success = res.returncode == 0
                return success, cmd, res.stdout or res.stderr
            except Exception as e:
                return False, cmd, str(e)

        return True, "N/A", ""

    def remove_block(self, src_ip: str) -> Tuple[bool, str]:
        """Removes an active block rule."""
        rule_name = self._rule_names.get(src_ip, f"WSENTRY_BLOCK_{src_ip.replace('.', '_')}")
        if src_ip in self._active_blocks:
            del self._active_blocks[src_ip]

        if self.mode == MitigationMode.WINDOWS:
            cmd = f"netsh advfirewall firewall delete rule name=\"{rule_name}\""
            try:
                subprocess.run(cmd, shell=True, capture_output=True, timeout=5)
            except Exception:
                pass
        elif self.mode == MitigationMode.WSL:
            cmd = f"wsl -e sudo iptables -D INPUT -s {src_ip} -j DROP"
            try:
                subprocess.run(cmd, shell=True, capture_output=True, timeout=5)
            except Exception:
                pass

        return True, f"Unblocked {src_ip}"

    def cleanup_expired(self, max_age_seconds: float = 300.0) -> int:
        """Removes blocks older than max_age_seconds."""
        now = datetime.now(timezone.utc)
        expired_ips = [
            ip for ip, added_at in self._active_blocks.items()
            if (now - added_at).total_seconds() > max_age_seconds
        ]
        for ip in expired_ips:
            self.remove_block(ip)
        return len(expired_ips)

    def get_log(self) -> List[MitigationAction]:
        return list(self._log)

    def get_active_blocks(self) -> Dict[str, datetime]:
        return dict(self._active_blocks)

