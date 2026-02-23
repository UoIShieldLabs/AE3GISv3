import sys
import json
from pathlib import Path

# Bring backend into path
repo_root = Path(__file__).parent.parent
sys.path.append(str(repo_root))

from backend.schemas import TopologyData
from backend.services.clab_generator import generate_clab_yaml

def test_validation():
    json_path = repo_root / "automation" / "enterprise_topology.json"
    
    with open(json_path) as f:
        data = json.load(f)

    print("1. Validating against backend Pydantic Schema...")
    try:
        # Load it into the strict backend model
        valid_model = TopologyData.model_validate(data)
        print("✅ Strict Pydantic Validation Passed!")
    except Exception as e:
        print("❌ Strict Pydantic Validation Failed!")
        print(e)
        sys.exit(1)

    print("\n2. Validating ContainerLab YAML generation...")
    try:
        # Feed the JSON dict into the generator exactly as it does in backend
        yaml_out = generate_clab_yaml(data)
        print("✅ ContainerLab YAML Generation Succeeded!")
        print("\n--- YAML OUTPUT ---")
        print(yaml_out)
    except Exception as e:
        print("❌ ContainerLab YAML Generation Failed!")
        print(e)
        sys.exit(1)

if __name__ == "__main__":
    test_validation()
