import json
from pathlib import Path


def test_template_ids_unique():
    base = Path(__file__).resolve().parents[1] / "prompts" / "styles"
    seen = {}
    for path in base.rglob("*.json"):
        data = json.loads(path.read_text())
        pid = data["id"]
        assert pid not in seen, f"Duplicate id {pid} in {path} and {seen[pid]}"
        seen[pid] = path
