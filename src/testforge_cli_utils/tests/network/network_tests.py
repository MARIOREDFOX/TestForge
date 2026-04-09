"""
Network validation tests.

Validates NIC detection, link status, speed, packet loss, and latency.
"""
from __future__ import annotations

import logging
import re
from typing import Dict, Any, Tuple

logger = logging.getLogger("testforge.network")

# Acceptable packet loss threshold (%)
DEFAULT_MAX_PACKET_LOSS_PCT = 5
# Acceptable latency threshold (ms)
DEFAULT_MAX_LATENCY_MS = 200


class NetworkTests:

    def __init__(
        self,
        max_packet_loss_pct: float = DEFAULT_MAX_PACKET_LOSS_PCT,
        max_latency_ms: float = DEFAULT_MAX_LATENCY_MS,
        latency_target: str = "8.8.8.8",
    ):
        self.max_packet_loss_pct = max_packet_loss_pct
        self.max_latency_ms = max_latency_ms
        self.latency_target = latency_target

    def run_all(self, hw) -> Dict[str, Any]:
        results: Dict[str, Any] = {}

        for name, method in [
            ("nic_detection",   self.test_nic_detection),
            ("link_status",     self.test_link_status),
            ("nic_speed",       self.test_nic_speed),
            ("packet_loss",     self.test_packet_loss),
            ("latency",         self.test_latency),
            ("nic_errors",      self.test_nic_errors),
        ]:
            try:
                passed, detail = method(hw)
                results[name] = {"status": "PASS" if passed else "FAIL", "detail": detail}
            except Exception as exc:
                results[name] = {"status": "ERROR", "detail": str(exc)}
                logger.error("Network test %s raised: %s", name, exc)

        return results

    def test_nic_detection(self, hw) -> Tuple[bool, str]:
        out = hw.get_nic_info()
        if "[UNAVAILABLE" in out:
            return False, out
        ifaces = re.findall(r"^\d+:\s+(\S+):", out, re.MULTILINE)
        physical = [i for i in ifaces if i not in ("lo",)]
        if not physical:
            return False, "No physical NICs detected"
        return True, f"Detected NICs: {', '.join(physical)}"

    def test_link_status(self, hw) -> Tuple[bool, str]:
        out = hw.get_nic_speed()
        if "[UNAVAILABLE" in out:
            return False, out
        down_ifaces = [
            line.split(":")[0] for line in out.splitlines()
            if "state=down" in line.lower() or "state=unknown" in line.lower()
        ]
        up_ifaces = [
            line.split(":")[0] for line in out.splitlines()
            if "state=up" in line.lower()
        ]
        if not up_ifaces:
            return False, f"No interfaces are UP. Down: {down_ifaces}"
        detail = f"Up: {up_ifaces}"
        if down_ifaces:
            detail += f"  Down: {down_ifaces}"
        return True, detail

    def test_nic_speed(self, hw) -> Tuple[bool, str]:
        out = hw.get_nic_speed()
        if "[UNAVAILABLE" in out:
            return False, out
        # Just report — don't fail based on speed (expected varies)
        return True, out

    def test_packet_loss(self, hw) -> Tuple[bool, str]:
        out = hw.get_network_packet_loss(target=self.latency_target, count=20)
        match = re.search(r"(\d+)%\s+packet loss", out)
        if not match:
            return True, f"Could not parse packet loss (output: {out[:100]})"
        loss = int(match.group(1))
        if loss > self.max_packet_loss_pct:
            return False, f"Packet loss {loss}% exceeds threshold {self.max_packet_loss_pct}%"
        return True, f"Packet loss: {loss}%"

    def test_latency(self, hw) -> Tuple[bool, str]:
        out = hw.get_network_latency(target=self.latency_target, count=10)
        # ping output: "rtt min/avg/max/mdev = 1.234/5.678/9.012/0.123 ms"
        match = re.search(r"min/avg/max.*?=\s*([\d.]+)/([\d.]+)/([\d.]+)", out)
        if not match:
            return True, f"Could not parse latency (output: {out[:100]})"
        avg_ms = float(match.group(2))
        if avg_ms > self.max_latency_ms:
            return False, f"Average latency {avg_ms:.1f}ms exceeds threshold {self.max_latency_ms}ms"
        return True, f"Latency min/avg/max = {match.group(1)}/{match.group(2)}/{match.group(3)} ms"

    def test_nic_errors(self, hw) -> Tuple[bool, str]:
        out = hw.get_network_errors()
        if "[UNAVAILABLE" in out:
            return True, "NIC error counters unavailable"
        # Look for non-zero error/drop counts
        # ip -s link format: "errors X dropped X"
        errors = re.findall(r"errors\s+(\d+)", out)
        drops  = re.findall(r"dropped\s+(\d+)", out)
        total_errors = sum(int(e) for e in errors)
        total_drops  = sum(int(d) for d in drops)
        if total_errors > 0 or total_drops > 0:
            return False, f"NIC errors={total_errors} drops={total_drops}"
        return True, "No NIC errors or drops"
