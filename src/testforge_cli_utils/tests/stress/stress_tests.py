"""
Stress & reliability test suite.

Orchestrates CPU, memory, IO, and memory bandwidth tests
against a remote host and evaluates thresholds.
"""
from __future__ import annotations

import logging
import re
from typing import Dict, Any, Optional

logger = logging.getLogger("testforge.stress")


class StressTests:
    """
    Thin orchestration layer — delegates to HardwareInfo for execution,
    then evaluates pass/fail based on configurable thresholds.
    """

    # Default thresholds (override via constructor or env config)
    DEFAULT_THRESHOLDS = {
        "cpu_stress_duration":    30,    # seconds
        "mem_stress_duration":    30,
        "io_stress_duration":     30,
        "mem_stress_vm_bytes":    "1G",
        "mem_stress_workers":     1,
        "cpu_stress_workers":     0,     # 0 = all CPUs
    }

    def __init__(self, thresholds: Optional[Dict[str, Any]] = None):
        self.thresholds = {**self.DEFAULT_THRESHOLDS, **(thresholds or {})}

    # ------------------------------------------------------------------

    def run_all(self, hw, results: Dict[str, Any]) -> None:
        """Run all stress tests and write results into *results* dict."""
        for name, method in [
            ("cpu_stress",   self.test_cpu_stress),
            ("mem_stress",   self.test_memory_stress),
            ("io_stress",    self.test_io_stress),
            ("mem_bandwidth",self.test_memory_bandwidth),
        ]:
            try:
                passed, detail = method(hw)
                results[name] = {"status": "PASS" if passed else "FAIL", "detail": detail}
            except Exception as exc:
                results[name] = {"status": "ERROR", "detail": str(exc)}
                logger.error("Stress test %s raised: %s", name, exc)

    def test_cpu_stress(self, hw) -> tuple:
        duration = self.thresholds["cpu_stress_duration"]
        workers  = self.thresholds["cpu_stress_workers"]
        logger.info("Running CPU stress (%ds, workers=%s) …", duration, workers or "all")
        out = hw.run_cpu_stress(duration_sec=duration, workers=workers)
        passed = "stress-ng not installed" not in out and "[UNAVAILABLE" not in out
        return passed, out

    def test_memory_stress(self, hw) -> tuple:
        duration  = self.thresholds["mem_stress_duration"]
        workers   = self.thresholds["mem_stress_workers"]
        vm_bytes  = self.thresholds["mem_stress_vm_bytes"]
        logger.info("Running memory stress (%ds, %s workers, %s each) …", duration, workers, vm_bytes)
        out = hw.run_memory_stress(duration_sec=duration, workers=workers, vm_bytes=vm_bytes)
        passed = "stress-ng not installed" not in out and "[UNAVAILABLE" not in out
        return passed, out

    def test_io_stress(self, hw) -> tuple:
        duration = self.thresholds["io_stress_duration"]
        logger.info("Running IO stress (%ds) …", duration)
        out = hw.run_io_stress(duration_sec=duration)
        passed = "[IO STRESS:" not in out and "[UNAVAILABLE" not in out
        return passed, out

    def test_memory_bandwidth(self, hw) -> tuple:
        logger.info("Running memory bandwidth test …")
        out = hw.run_memory_bandwidth_test()
        passed = "[BANDWIDTH TEST:" not in out and "[UNAVAILABLE" not in out
        return passed, out
