import yaml

def parse_yaml(file_path):
    """Parse YAML files."""
    with open(file_path, 'r') as f:
        return yaml.safe_load(f)

