import yaml
from testforge.utils.retry import retry_test

def load_config(config_file):
    """Loads the YAML configuration for tests."""
    with open(config_file, 'r') as f:
        return yaml.safe_load(f)

def run_tests(config_file="examples/test_config.yaml", tag=None, test=None):
    """Run the tests as per the configuration file."""
    config = load_config(config_file)
    tests = config.get('tests', [])

    # Filter tests by tag or test name
    if tag:
        tests = [t for t in tests if tag in t.get('tags', [])]
    if test:
        tests = [t for t in tests if t.get('name') == test]

    # Execute filtered tests
    for test in tests:
        if test.get('enabled', False):
            print(f"Running test: {test['name']}")
            result = execute_test(test)
            if result:
                print(f"Test {test['name']} passed")
            else:
                print(f"Test {test['name']} failed")

def execute_test(test):
    """Simulate running a test."""
    # Placeholder for actual test execution logic
    return retry_test(lambda: True, retries=3)  # Example retry function

