"""
Firmware validation tests.

Validates and compares firmware versions for BIOS, BMC, NIC, and NVMe.
Supports before/after comparison for upgrade validation.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger("testforge.firmware")


class FirmwareTests:
    """
    Collect firmware versions and compare against expected baselines.

    Usage:
        fw_tests = FirmwareTests(expected={"bios_version": "2.7.0", "kernel": "6.1.0"})
        results = fw_tests.run_all(hw)
    """

    def __init__(self, expected: Optional[Dict[str, str]] = None):
        self.expected = expected or {}

    def run_all(self, hw) -> Dict[str, Any]:
        """
        Collect all firmware versions and compare against expected baseline.
        Returns dict of component -> {actual, expected, status}.
        """
        actual = hw.get_all_firmware_versions()
        results: Dict[str, Any] = {}

        for component, actual_version in actual.items():
            actual_clean = actual_version.strip()
            expected_version = self.expected.get(component)

            if expected_version is None:
                # No expected version set — just report
                results[component] = {
                    "actual":   actual_clean,
                    "expected": "(not checked)",
                    "status":   "INFO",
                }
            else:
                match = actual_clean == expected_version.strip()
                results[component] = {
                    "actual":   actual_clean,
                    "expected": expected_version,
                    "status":   "PASS" if match else "FAIL",
                }
                if not match:
                    logger.warning(
                        "Firmware mismatch [%s]: actual=%s expected=%s",
                        component, actual_clean, expected_version,
                    )

        return results

    def snapshot(self, hw, output_path: str) -> Dict[str, str]:
        """
        Save current firmware versions to a JSON snapshot file.
        Useful as the 'before' state before a firmware upgrade.
        """
        versions = hw.get_all_firmware_versions()
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(versions, f, indent=2)
        logger.info("Firmware snapshot saved to %s", output_path)
        return versions

    def compare_snapshots(
        self, before_path: str, hw
    ) -> Dict[str, Any]:
        """
        Compare current firmware versions against a previously saved snapshot.
        Returns dict of component -> {before, after, changed}.
        """
        if not os.path.exists(before_path):
            raise FileNotFoundError(f"Snapshot not found: {before_path}")
        with open(before_path) as f:
            before = json.load(f)

        after = hw.get_all_firmware_versions()
        results: Dict[str, Any] = {}

        all_keys = set(before) | set(after)
        for k in sorted(all_keys):
            b = before.get(k, "[not present]").strip()
            a = after.get(k, "[not present]").strip()
            results[k] = {
                "before":  b,
                "after":   a,
                "changed": b != a,
                "status":  "CHANGED" if b != a else "UNCHANGED",
            }
            if b != a:
                logger.info("Firmware changed [%s]: %s → %s", k, b, a)

        return results

    def validate_minimum_versions(
        self, hw, minimums: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Validate that firmware versions meet minimum requirements.
        Uses simple string comparison — works for version strings like "2.7.0".
        """
        actual = hw.get_all_firmware_versions()
        results: Dict[str, Any] = {}

        for component, min_ver in minimums.items():
            actual_ver = actual.get(component, "").strip()
            if not actual_ver or "[UNAVAILABLE" in actual_ver:
                results[component] = {
                    "actual": actual_ver,
                    "minimum": min_ver,
                    "status": "WARN",
                    "detail": "Version unavailable",
                }
                continue

            # Simple version tuple comparison
            try:
                a_parts = tuple(int(x) for x in actual_ver.split(".")[:4])
                m_parts = tuple(int(x) for x in min_ver.split(".")[:4])
                meets = a_parts >= m_parts
            except ValueError:
                meets = actual_ver >= min_ver  # lexicographic fallback

            results[component] = {
                "actual":  actual_ver,
                "minimum": min_ver,
                "status":  "PASS" if meets else "FAIL",
            }

        return results
