import yaml
import os
from testforge.utils.host_check import is_host_alive
from testforge.utils import hardware_info
from testforge.utils.retry import retry_test
from testforge.runner.cxl_health_check_runner import CXLHealthCheckRunner
from testforge.utils.hardware_info import HardwareInfo
import datetime


# Register test runners
TEST_RUNNERS = {
    "cxl_health_check": CXLHealthCheckRunner,
    # Add more runners here in future
}

def timestamp():
    return datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")

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

    # Log the start of the test and print it
    logs.append(f"{timestamp()} === Running Test: {test['name']} on {host} ===")
    print(logs[-1])

    # Check if the host is alive
    if not is_host_alive(host):
        logs.append(f"{timestamp()} [FAIL] {host} is not reachable.")
        print(logs[-1])  # Print it to the console
        write_logs(logs)
        return False

    logs.append(f"{timestamp()} [PASS] {host} is reachable.")
    print(logs[-1])  # Print it to the console

    hw = HardwareInfo(host)  # Instantiate once and reuse

    # Execute specific checks based on tag
    if tag == "ping":
        pass  # Already covered by is_host_alive

    elif tag == "firmware":
        info = hw.get_firmware_info()
        logs.append(f"{timestamp()} [PASS] Firmware Info:\n{info}")
        print(logs[-1])  # Print it to the console

    elif tag == "cpu":
        info = hw.get_cpu_info()
        logs.append(f"{timestamp()} [PASS] CPU Info:\n{info}")
        print(logs[-1])  # Print it to the console

    elif tag == "bmc":
        info = hw.get_bmc_info()
        logs.append(f"{timestamp()} [PASS] BMC Info:\n{info}")
        print(logs[-1])  # Print it to the console

    elif tag == "all":
        # Collecting and printing all hardware info
        info = hw.get_cpu_info()
        logs.append(f"{timestamp()} [PASS] CPU Info:\n{info}")
        print(logs[-1])

        info = hw.get_memory_info()
        logs.append(f"{timestamp()} [PASS] Memory Info:\n{info}")
        print(logs[-1])

        info = hw.get_bios_info()
        logs.append(f"{timestamp()} [PASS] BIOS Info:\n{info}")
        print(logs[-1])

        info = hw.get_bmc_info()
        logs.append(f"{timestamp()} [PASS] BMC Info:\n{info}")
        print(logs[-1])

        info = hw.get_disk_info()
        logs.append(f"{timestamp()} [PASS] Disk Info:\n{info}")
        print(logs[-1])

        info = hw.get_firmware_info()
        logs.append(f"{timestamp()} [PASS] Firmware Info:\n{info}")
        print(logs[-1])

    # Write the logs to the results file
    write_logs(logs)
    return True

def write_logs(logs):
    os.makedirs("logs", exist_ok=True)
    with open("logs/results.log", "a") as f:
        for line in logs:
            f.write(line + "\n")

