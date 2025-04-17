import yaml
import os
from testforge.utils.host_check import is_host_alive
from testforge.utils import hardware_info
from testforge.utils.retry import retry_test
from testforge.runner.cxl_health_check_runner import CXLHealthCheckRunner

# Register test runners
TEST_RUNNERS = {
    "cxl_health_check": CXLHealthCheckRunner,
    # Add more runners here in future
}

def load_config(config_file):
    """Loads the YAML configuration for tests."""
    with open(config_file, 'r') as f:
        return yaml.safe_load(f)

def run_tests(config_file="examples/test_config.yaml", tag=None, test=None, env_file=None):
    """Main entry point to run tests."""
    config = load_config(config_file)
    env = {}

    if env_file and os.path.exists(env_file):
        with open(env_file, 'r') as f:
            env = yaml.safe_load(f)

        test_type = env.get("test_type", "").lower()
        if test_type in TEST_RUNNERS:
            runner_class = TEST_RUNNERS[test_type]
            runner = runner_class(env)
            runner.run()
            return  # Exit after running specific runner

    # Fallback: default config-based test execution
    tests = config.get('tests', [])

    if tag:
        tests = [t for t in tests if tag in t.get('tags', [])]
    if test:
        tests = [t for t in tests if t.get('name') == test]

    for test in tests:
        if test.get('enabled', False):
            print(f"Running test: {test['name']} with env: {env}")
            result = execute_test(test, env)
            status = "passed" if result else "failed"
            print(f"Test {test['name']} {status}")

def execute_test(test, env):
    host = env.get("hostname")
    tag = test.get("tags", [])[0]
    logs = []

    logs.append(f"\n=== Running Test: {test['name']} on {host} ===")

    if not is_host_alive(host):
        logs.append(f"[FAIL] {host} is not reachable.")
        write_logs(logs)
        return False

    logs.append(f"[OK] {host} is reachable.")

    if tag == "ping":
        # Already covered by is_host_alive
        pass
    elif tag == "firmware":
        logs.append(hardware_info.get_firmware_info(host))
    elif tag == "cpu":
        logs.append(hardware_info.get_cpu_info(host))
    elif tag == "bmc":
        logs.append(hardware_info.get_bmc_info(host))
    elif tag == "all":
        logs.append(hardware_info.get_cpu_info(host))
        logs.append(hardware_info.get_memory_info(host))
        logs.append(hardware_info.get_bios_info(host))
        logs.append(hardware_info.get_bmc_info(host))
        logs.append(hardware_info.get_disk_info(host))
        logs.append(hardware_info.get_firmware_info(host))

    write_logs(logs)
    return True

def write_logs(logs):
    os.makedirs("logs", exist_ok=True)
    with open("logs/results.log", "a") as f:
        for line in logs:
            f.write(line + "\n")

