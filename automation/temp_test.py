import json
import sys
from pathlib import Path

repo_root = Path(__file__).parent.parent
sys.path.append(str(repo_root))

from backend.services.clab_generator import generate_clab_yaml

with open("automation/enterprise_topology.json") as f:
    data = json.load(f)

print(generate_clab_yaml(data))
