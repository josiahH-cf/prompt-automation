import json
from pathlib import Path

from prompt_automation.gui.wizard.steps import (
    SUGGESTED_PLACEHOLDERS,
    next_template_id,
    ensure_style,
    suggest_placeholders,
    generate_template_body,
)


def test_next_template_id_uniqueness(tmp_path: Path):
    style_root = tmp_path / "styles" / "Demo"
    style_root.mkdir(parents=True)
    # create two template files with IDs 1 and 2
    for i in (1, 2):
        data = {"id": i, "style": style_root.name}
        (style_root / f"t{i}.json").write_text(json.dumps(data))
    assert next_template_id(style_root) == 3


def test_ensure_style_creation(tmp_path: Path):
    base = tmp_path / "styles"
    shared = ensure_style("Alpha", base_dir=base)
    private = ensure_style("Beta", private=True, base_dir=base)
    assert shared == base / "Alpha"
    assert private == base.parent / "local" / "Beta"
    assert shared.is_dir() and private.is_dir()


def test_suggest_placeholders():
    existing = {"objective", "inputs"}
    suggestions = suggest_placeholders(existing)
    assert "objective" not in suggestions
    assert "inputs" not in suggestions
    # Ensure suggestions are subset of default list
    for s in suggestions:
        assert s in SUGGESTED_PLACEHOLDERS


def test_generate_template_body_deterministic():
    placeholders = ["a", "b"]
    body1 = generate_template_body(placeholders)
    body2 = generate_template_body(placeholders)
    assert body1 == body2
    assert "{{a}}" in body1 and "{{b}}" in body1
