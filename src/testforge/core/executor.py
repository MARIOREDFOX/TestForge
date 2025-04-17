import yaml
from testforge.utils.retry import retry_test
from testforge.runner.cxl_health_check_runner import CXLHealthCheckRunner
import os


# Register the new runner type for CXL Health Check
TEST_RUNNERS = {
    "cxl_health_check": CXLHealthCheckRunner,
    # Add other runners as needed
}

def load_config(config_file):
    """Loads the YAML configuration for tests."""
    with open(config_file, 'r') as f:
        return yaml.safe_load(f)

def run_tests(config_file="examples/test_config.yaml", tag=None, test=None, env_file=None):
    """Run the tests as per the configuration file."""
    config = load_config(config_file)
    env = {}

    if env_file and os.path.exists(env_file):
        with open(env_file, 'r') as f:
            env = yaml.safe_load(f)

        test_type = env.get("test_type", "").lower()

        if test_type == "cxl_health_check":
            runner_class = TEST_RUNNERS.get(test_type)
            if not runner_class:
                raise ValueError(f"Runner not found for test_type: {test_type}")
            runner = runner_class(env)
            runner.run()
            return  # Exit after running cxl_health_check

    # Fallback to default test execution
    tests = config.get('tests', [])

    if tag:
        tests = [t for t in tests if tag in t.get('tags', [])]
    if test:
        tests = [t for t in tests if t.get('name') == test]

    for test in tests:
        if test.get('enabled', False):
            print(f"Running test: {test['name']} with env: {env}")
            result = execute_test(test, env)
            if result:
                print(f"Test {test['name']} passed")
            else:
                print(f"Test {test['name']} failed")

def execute_test(test, env):
    """Simulate running a test with env context."""
    # Placeholder for actual test execution logic
    print(f"Using env in test '{test['name']}': {env}")
    return retry_test(lambda: True, retries=3)
