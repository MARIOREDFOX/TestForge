"""IPMI-based BMC test helpers."""
from __future__ import annotations
import logging
from typing import Dict

logger = logging.getLogger("testforge.protocol.ipmi")


def run_test(hw=None) -> bool:
    """Basic IPMI connectivity test."""
    if hw is None:
        logger.warning("No HardwareInfo provided to ipmi.run_test()")
        return False
    info = hw.get_bmc_info()
    logger.info("BMC info:\n%s", info)
    return bool(info and "[UNAVAILABLE" not in info)


def full_check(hw) -> Dict[str, str]:
    return {
        "mc_info":       hw.get_bmc_info(),
        "sdr":           hw.get_bmc_sdr(),
        "sel":           hw.get_bmc_sel(),
        "power_status":  hw.get_bmc_power_status(),
        "chassis":       hw.get_bmc_chassis_status(),
        "fru":           hw.get_bmc_fru(),
        "lan":           hw.get_bmc_lan_info(),
    }
