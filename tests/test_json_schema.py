import json
from pathlib import Path
from promptpilot import renderer


def test_sample_prompts_valid():
    base = Path(__file__).resolve().parents[1] / "prompts" / "styles"
    for path in base.rglob("*.json"):
        data = json.loads(path.read_text())
        assert renderer.validate_template(data)
