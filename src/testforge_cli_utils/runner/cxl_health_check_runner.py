"""CXL health check runner."""
from __future__ import annotations

import logging
from typing import Any, Dict

from testforge_cli_utils.core.base_executor import Executor
from testforge_cli_utils.tests.health.health import HealthTests

logger = logging.getLogger("testforge.runner.cxl")


class CXLHealthCheckRunner(Executor):
    def __init__(self, env: Dict[str, Any], **kwargs: Any) -> None:
        super().__init__(env, **kwargs)
        self.hosts = env.get("hosts", [])
        self.health_test = HealthTests()

    def run(self) -> None:
        if not self.hosts:
            logger.warning("CXLHealthCheckRunner: no hosts defined in env")
            return

        results = self.health_test.run(self.hosts, self.env)
        for host, result in results.items():
            status = result.get("status", "?")
            logger.info("Host %s overall: %s", host, status)
            for check, val in result.get("checks", {}).items():
                logger.info("  %-20s %s", check, val)
