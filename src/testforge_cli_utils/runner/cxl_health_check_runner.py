from testforge_cli_utils.core.base_executor import Executor
from testforge_cli_utils.tests.health.health import HealthTests


class CXLHealthCheckRunner(Executor):
    def __init__(self, env, **kwargs):
        super().__init__(env, **kwargs)
        self.hosts = env.get("hosts", [])
        self.health_test = HealthTests()

    def run(self):
        self.health_test.run(self.hosts)
