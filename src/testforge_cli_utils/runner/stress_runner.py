"""Multi-host stress test runner."""
from __future__ import annotations
import logging
from typing import Any, Dict
from testforge_cli_utils.core.base_executor import Executor

logger = logging.getLogger("testforge.runner.stress")


class StressRunner(Executor):
    def __init__(self, env: Dict[str, Any], **kwargs):
        super().__init__(env, **kwargs)
        self.hosts = env.get("hosts", [])
        self.thresholds = env.get("stress_thresholds", {})

    def run(self) -> None:
        from testforge_cli_utils.utils.hardware_info import HardwareInfo
        from testforge_cli_utils.tests.stress.stress_tests import StressTests

        if not self.hosts:
            logger.warning("StressRunner: no hosts defined")
            return

        st = StressTests(self.thresholds)

        for host in self.hosts:
            logger.info("Running stress tests on %s", host)
            hw = HardwareInfo(
                host=host,
                username=self.env.get("username", "root"),
                password=self.env.get("password"),
                key_filename=self.env.get("key_filename"),
            )
            results: Dict[str, Any] = {}
            st.run_all(hw, results)
            hw.close()
            for name, r in results.items():
                logger.info("[%s] %s: %s", host, name, r.get("status"))
