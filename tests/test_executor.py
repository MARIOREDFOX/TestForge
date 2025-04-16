import unittest
from testforge.core.executor import load_config, run_tests

class TestExecutor(unittest.TestCase):

    def test_load_config(self):
        config = load_config("examples/test_config.yaml")
        self.assertIn('tests', config)

    def test_run_tests(self):
        # Simulate a basic test run
        result = run_tests(config_file="examples/test_config.yaml", tag="firmware")
        self.assertIsNone(result)  # Adjust based on actual return value from run_tests()

if __name__ == '__main__':
    unittest.main()

