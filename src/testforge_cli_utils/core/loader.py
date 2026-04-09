"""Protocol loader — resolves a protocol name to its module."""
from __future__ import annotations

import logging
from types import ModuleType
from typing import Optional

logger = logging.getLogger("testforge.loader")


def load_protocol(protocol_name: str) -> Optional[ModuleType]:
    """Return the protocol module for *protocol_name*, or None."""
    from testforge_cli_utils.protocols import bmc, cxl, pcie

    protocols = {
        "bmc":   bmc,
        "cxl":   cxl,
        "pcie":  pcie,
    }
    mod = protocols.get(protocol_name.lower())
    if mod is None:
        logger.warning("Unknown protocol: %s", protocol_name)
    return mod


def load_test_protocol(protocol_name: str):
    """Call run_test() on the named protocol module."""
    mod = load_protocol(protocol_name)
    if mod is None:
        raise ValueError(f"Protocol '{protocol_name}' not found")
    return mod.run_test()
