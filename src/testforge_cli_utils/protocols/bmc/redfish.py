"""
Redfish (DMTF REST API) BMC test helper.

Requires 'requests' to be installed and a BMC with Redfish support.
"""
from __future__ import annotations
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("testforge.protocol.redfish")

try:
    import requests
    requests.packages.urllib3.disable_warnings()  # type: ignore[attr-defined]
    _REQUESTS_AVAILABLE = True
except ImportError:
    _REQUESTS_AVAILABLE = False


class RedfishClient:
    """Minimal Redfish client for BMC validation."""

    BASE_PATHS = {
        "system":    "/redfish/v1/Systems/1",
        "chassis":   "/redfish/v1/Chassis/1",
        "managers":  "/redfish/v1/Managers/1",
        "eventlog":  "/redfish/v1/Systems/1/LogServices/Log1/Entries",
    }

    def __init__(self, host: str, username: str, password: str, port: int = 443):
        if not _REQUESTS_AVAILABLE:
            raise RuntimeError("Install 'requests': pip install requests")
        self.base_url = f"https://{host}:{port}"
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.session.verify = False
        self.session.headers.update({"Content-Type": "application/json"})

    def get(self, path: str) -> Dict[str, Any]:
        url = self.base_url + path
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            logger.warning("Redfish GET %s failed: %s", path, exc)
            return {"error": str(exc)}

    def get_system_info(self) -> Dict[str, Any]:
        return self.get(self.BASE_PATHS["system"])

    def get_chassis_info(self) -> Dict[str, Any]:
        return self.get(self.BASE_PATHS["chassis"])

    def get_manager_info(self) -> Dict[str, Any]:
        return self.get(self.BASE_PATHS["managers"])

    def get_event_log(self) -> Dict[str, Any]:
        return self.get(self.BASE_PATHS["eventlog"])

    def power_on(self) -> Dict[str, Any]:
        return self._power_action("On")

    def power_off(self) -> Dict[str, Any]:
        return self._power_action("ForceOff")

    def power_reset(self) -> Dict[str, Any]:
        return self._power_action("ForceRestart")

    def _power_action(self, action: str) -> Dict[str, Any]:
        url = self.base_url + "/redfish/v1/Systems/1/Actions/ComputerSystem.Reset"
        try:
            resp = self.session.post(url, json={"ResetType": action}, timeout=15)
            resp.raise_for_status()
            return {"status": "ok", "action": action}
        except Exception as exc:
            logger.error("Redfish power action %s failed: %s", action, exc)
            return {"error": str(exc)}


def run_test(host: str = None, username: str = None, password: str = None) -> bool:
    """Basic Redfish connectivity smoke test."""
    if not all([host, username, password]):
        logger.warning("Redfish run_test requires host, username, password")
        return False
    client = RedfishClient(host, username, password)
    info = client.get_system_info()
    ok = "error" not in info
    logger.info("Redfish system info: %s", info.get("Model", info))
    return ok
