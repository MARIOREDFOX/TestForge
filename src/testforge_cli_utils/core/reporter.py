import json

def generate_report(results):
    """Generate a JSON report for the tests."""
    report = {"tests": results}
    with open("test_report.json", "w") as f:
        json.dump(report, f, indent=4)

def display_report(results):
    """Display a simple report to the console."""
    for result in results:
        print(f"Test {result['name']} - Status: {result['status']}")

