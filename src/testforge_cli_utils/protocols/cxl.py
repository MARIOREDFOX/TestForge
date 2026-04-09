"""CXL (Compute Express Link) protocol test helpers."""
from __future__ import annotations
import logging
from typing import Dict

logger = logging.getLogger("testforge.protocol.cxl")


def run_test(hw=None) -> bool:
    """Basic CXL device enumeration test."""
    if hw is None:
        logger.warning("No HardwareInfo provided to cxl.run_test()")
        return False
    devices = hw.get_cxl_devices()
    logger.info("CXL devices:\n%s", devices)
    return bool(devices and "[NO CXL" not in devices and "[UNAVAILABLE" not in devices)


def check_full(hw) -> Dict[str, str]:
    return {
        "devices":  hw.get_cxl_devices(),
        "mem_info": hw.get_cxl_mem_info(),
        "topology": hw.get_cxl_topology(),
        "ports":    hw.get_cxl_port_info(),
        "dmesg":    hw.get_cxl_dmesg_events(),
    }
