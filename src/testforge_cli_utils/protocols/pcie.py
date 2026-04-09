"""PCIe protocol test helpers."""
from __future__ import annotations
import logging
from typing import Dict

logger = logging.getLogger("testforge.protocol.pcie")


def run_test(hw=None) -> bool:
    """Basic PCIe presence test."""
    if hw is None:
        logger.warning("No HardwareInfo provided to pcie.run_test()")
        return False
    devices = hw.get_pcie_devices()
    logger.info("PCIe devices:\n%s", devices)
    return bool(devices and "[UNAVAILABLE" not in devices)


def check_link_status(hw) -> Dict[str, str]:
    return {
        "link_status": hw.get_pcie_link_status(),
        "errors":      hw.get_pcie_errors(),
        "bandwidth":   hw.get_pcie_bandwidth(),
    }
