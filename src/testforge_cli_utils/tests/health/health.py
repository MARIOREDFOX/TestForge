"""
Health test suite — runs a broad set of checks against a list of hosts.
"""
from __future__ import annotations

import logging
from typing import List, Dict, Any

from testforge_cli_utils.utils.host_check import is_host_alive, is_ssh_reachable

logger = logging.getLogger("testforge.health")


class HealthTests:
    """Run CXL / PCIe / general health checks across multiple hosts."""

    def run(self, host_list: List[str], env: Dict[str, Any] = None) -> Dict[str, Any]:
        env = env or {}
        results = {}
        for host in host_list:
            results[host] = self.run_cxl_health_check(host, env)
        return results

    def run_cxl_health_check(self, host: str, env: Dict[str, Any] = None) -> Dict[str, Any]:
        env = env or {}
        result: Dict[str, Any] = {"host": host, "checks": {}}

        logger.info("[CXLHealthCheck] Running on host: %s", host)

        # 1. Ping
        alive = is_host_alive(host)
        result["checks"]["ping"] = "PASS" if alive else "FAIL"
        if not alive:
            logger.error("[CXLHealthCheck] %s is not reachable", host)
            result["status"] = "FAIL"
            return result

        # 2. SSH
        ssh_ok = is_ssh_reachable(host)
        result["checks"]["ssh"] = "PASS" if ssh_ok else "FAIL"
        if not ssh_ok:
            logger.error("[CXLHealthCheck] SSH not reachable on %s", host)
            result["status"] = "FAIL"
            return result

        # 3. Hardware checks
        try:
            from testforge_cli_utils.utils.hardware_info import HardwareInfo
            hw = HardwareInfo(
                host=host,
                username=env.get("username", "root"),
                password=env.get("password"),
                key_filename=env.get("key_filename"),
            )

            checks = {
                "cxl_devices":  hw.get_cxl_devices,
                "cxl_mem":      hw.get_cxl_mem_info,
                "cxl_topology": hw.get_cxl_topology,
                "pcie_devices": hw.get_pcie_devices,
                "pcie_links":   hw.get_pcie_link_status,
                "pcie_errors":  hw.get_pcie_errors,
            }

            for label, method in checks.items():
                try:
                    out = method()
                    passed = bool(out) and "[UNAVAILABLE" not in out
                    result["checks"][label] = "PASS" if passed else "WARN"
                    logger.info("[%s] %s: %s", host, label, "PASS" if passed else "WARN")
                except Exception as exc:
                    result["checks"][label] = f"ERROR: {exc}"
                    logger.warning("[%s] %s failed: %s", host, label, exc)

            hw.close()

        except Exception as exc:
            result["checks"]["ssh_connect"] = f"ERROR: {exc}"
            logger.error("[CXLHealthCheck] SSH setup failed for %s: %s", host, exc)
            result["status"] = "FAIL"
            return result

        all_ok = all(v == "PASS" for v in result["checks"].values())
        result["status"] = "PASS" if all_ok else "PARTIAL"
        return result
