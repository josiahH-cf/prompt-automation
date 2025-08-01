import json
from pathlib import Path
from prompt_automation import renderer


def test_sample_prompts_valid():
    # Try multiple locations for prompts directory
    possible_bases = [
        Path(__file__).resolve().parents[1] / "prompts" / "styles",  # Development structure
        Path(__file__).resolve().parents[2] / "prompts" / "styles",  # Alternative structure
        Path.home() / ".prompt-automation" / "prompts" / "styles"    # User directory
    ]
    
    base = None
    for possible_base in possible_bases:
        if possible_base.exists():
            base = possible_base
            break
    
    if not base:
        # Skip test if no prompts directory found
        import pytest
        pytest.skip("No prompts directory found for testing")
    
    for path in base.rglob("*.json"):
        data = json.loads(path.read_text())
        assert renderer.validate_template(data)
