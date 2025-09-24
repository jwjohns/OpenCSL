import os
import yaml

def load_yaml_file(path: str):
    with open(path, "r") as f:
        return yaml.safe_load(f)

def load_semantics(base_dir: str = None):
    if base_dir is None:
        base_dir = os.path.join(os.path.dirname(__file__), "..", "semantics")
    base_dir = os.path.abspath(base_dir)
    semantics = {"metrics": {}, "dimensions": {}}

    for root, _, files in os.walk(base_dir):
        for file in files:
            if file.endswith((".yml", ".yaml")):
                full = os.path.join(root, file)
                data = load_yaml_file(full)
                # Determine type based on directory structure
                if "metrics" in root:
                    semantics["metrics"][data["name"]] = data
                elif "dimensions" in root:
                    semantics["dimensions"][data["name"]] = data

    return semantics