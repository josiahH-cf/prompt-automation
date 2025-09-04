import os
from pathlib import Path

import json

from prompt_automation.services.hierarchy import TemplateHierarchyScanner


def _write(p: Path, data: dict | None = None):
    p.parent.mkdir(parents=True, exist_ok=True)
    if data is None:
        data = {"id": 1, "title": "T", "style": p.parent.name, "template": [], "placeholders": []}
    p.write_text(json.dumps(data), encoding="utf-8")


def test_hierarchy_scans_nested_structure(tmp_path, monkeypatch):
    root = tmp_path / "styles"
    # Create structure
    _write(root / "A" / "01_alpha.json")
    _write(root / "A" / "beta.json")
    _write(root / "B" / "C" / "02_gamma.json")
    # Settings directory and file should be ignored
    (root / "Settings").mkdir(parents=True)
    (root / "Settings" / "settings.json").write_text("{}", encoding="utf-8")

    monkeypatch.setenv("PROMPT_AUTOMATION_PROMPTS", str(root))

    scanner = TemplateHierarchyScanner(root)
    tree = scanner.scan()

    # Root should have two top-level folders: A, B in alphabetical order
    names = [n.name for n in tree.children if n.type == "folder"]
    assert names == ["A", "B"]

    # Folder A should list 01_alpha before beta
    a = next(n for n in tree.children if n.name == "A")
    files = [n.name for n in a.children if n.type == "template"]
    assert files == ["01_alpha.json", "beta.json"]

    # Settings folder not included; and nested C under B should be present
    b = next(n for n in tree.children if n.name == "B")
    c = next(n for n in b.children if n.type == "folder" and n.name == "C")
    assert any(ch.name == "02_gamma.json" for ch in c.children)

