"""
Log validation tests.

Scans dmesg, system logs, BMC SEL, and crash signatures
for patterns that indicate hardware faults.
"""
from __future__ import annotations

import logging
import re
from typing import Dict, Any, List, Tuple

logger = logging.getLogger("testforge.log_validator")


# Patterns whose presence signals a FAIL
CRITICAL_PATTERNS: List[str] = [
    r"kernel panic",
    r"oops\b",
    r"BUG:",
    r"Call Trace",
    r"segfault",
    r"machine check",
    r"\bMCE\b",
    r"uncorrectable error",
    r"hardware error",
    r"NMI:",
    r"fatal error",
    r"io error",
    r"aer.*uncorrectable",
    r"cxl.*error",
    r"nvme.*error",
]

# Patterns that are warnings (logged but don't fail the test)
WARNING_PATTERNS: List[str] = [
    r"correctable error",
    r"aer.*correctable",
    r"link down",
    r"thermal.*trip",
    r"soft lockup",
    r"hung_task",
    r"ACPI Error",
]


def _scan(text: str, patterns: List[str]) -> List[str]:
    """Return lines from *text* that match any of *patterns*."""
    hits: List[str] = []
    compiled = [re.compile(p, re.IGNORECASE) for p in patterns]
    for line in text.splitlines():
        if any(rx.search(line) for rx in compiled):
            hits.append(line.strip())
    return hits


class LogValidator:
    """Validate log output from dmesg, SEL, and system logs."""

    def run_all(self, hw) -> Dict[str, Any]:
        results: Dict[str, Any] = {}

        checks: List[Tuple[str, str]] = [
            ("dmesg_errors",     hw.get_dmesg_errors()),
            ("dmesg_hw_events",  hw.get_dmesg_hardware_events()),
            ("mce_errors",       hw.get_mce_errors()),
            ("crash_signatures", hw.get_crash_signatures()),
            ("bmc_sel_errors",   hw.get_bmc_sel_errors()),
            ("system_logs",      hw.get_system_logs()),
        ]

        for label, text in checks:
            if "[UNAVAILABLE" in text or text.startswith("["):
                results[label] = {
                    "status": "WARN",
                    "critical_hits": [],
                    "warning_hits": [],
                    "detail": text,
                }
                continue

            critical_hits = _scan(text, CRITICAL_PATTERNS)
            warning_hits  = _scan(text, WARNING_PATTERNS)

            status = "FAIL" if critical_hits else ("WARN" if warning_hits else "PASS")
            results[label] = {
                "status":        status,
                "critical_hits": critical_hits[:10],
                "warning_hits":  warning_hits[:10],
                "detail":        f"{len(critical_hits)} critical, {len(warning_hits)} warnings",
            }
            logger.info("Log check [%s]: %s", label, status)

        return results

    def validate_dmesg(self, hw) -> Tuple[bool, str]:
        text = hw.get_dmesg_errors()
        hits = _scan(text, CRITICAL_PATTERNS)
        if hits:
            return False, f"Found {len(hits)} critical dmesg events: {hits[0]}"
        return True, "No critical dmesg errors"

    def validate_mce(self, hw) -> Tuple[bool, str]:
        text = hw.get_mce_errors()
        if "[UNAVAILABLE" in text or "MCE CHECK UNAVAILABLE" in text:
            return True, "MCE check not available (install mcelog)"
        hits = _scan(text, [r"machine check", r"\bMCE\b", r"uncorrectable"])
        if hits:
            return False, f"MCE errors found: {hits[0]}"
        return True, "No MCE errors"

    def validate_no_crashes(self, hw) -> Tuple[bool, str]:
        text = hw.get_crash_signatures()
        hits = _scan(text, [r"kernel panic", r"oops\b", r"BUG:", r"Call Trace"])
        if hits:
            return False, f"Crash signature found: {hits[0]}"
        return True, "No crash signatures"
