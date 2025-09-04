import os
from pathlib import Path
import json

import pytest

from prompt_automation.services.hierarchy import TemplateHierarchyScanner
from prompt_automation.services.hierarchy_fs import TemplateFSService, HierarchyError


def test_crud_operations_update_tree(tmp_path, monkeypatch):
    root = tmp_path / "styles"
    (root / "Code").mkdir(parents=True)
    (root / "Settings").mkdir(parents=True)
    (root / "Settings" / "settings.json").write_text("{}", encoding="utf-8")
    (root / "Code" / "01_a.json").write_text(json.dumps({"id": 1, "title": "A", "style": "Code", "template": [], "placeholders": []}), encoding="utf-8")

    monkeypatch.setenv("PROMPT_AUTOMATION_PROMPTS", str(root))

    scanner = TemplateHierarchyScanner(root, cache_ttl=60)
    svc = TemplateFSService(root=root, on_change=scanner.invalidate)

    # Initial scan
    tree = scanner.scan()
    code = next(n for n in tree.children if n.name == "Code")
    assert any(ch.name == "01_a.json" for ch in code.children)

    # Create folder and template
    svc.create_folder("New")
    svc.create_template("New/02_b.json", {"id": 2, "title": "B", "style": "New", "template": [], "placeholders": []})
    tree = scanner.scan()
    new = next(n for n in tree.children if n.name == "New")
    assert any(ch.name == "02_b.json" for ch in new.children)

    # Move template (simulate drag/drop)
    svc.move_template("New/02_b.json", "Code/02_b.json")
    tree = scanner.scan()
    code = next(n for n in tree.children if n.name == "Code")
    assert any(ch.name == "02_b.json" for ch in code.children)
    new = next(n for n in tree.children if n.name == "New")
    assert not any(ch.name == "02_b.json" for ch in new.children)

    # Rename folder
    svc.rename_folder("New", "NewX")
    tree = scanner.scan()
    assert any(n.name == "NewX" for n in tree.children)
    assert not any(n.name == "New" for n in tree.children)

    # Duplicate then delete template
    svc.duplicate_template("Code/02_b.json", "Code/02_b_copy.json")
    tree = scanner.scan()
    code = next(n for n in tree.children if n.name == "Code")
    assert any(ch.name == "02_b_copy.json" for ch in code.children)
    svc.delete_template("Code/02_b_copy.json")
    tree = scanner.scan()
    code = next(n for n in tree.children if n.name == "Code")
    assert not any(ch.name == "02_b_copy.json" for ch in code.children)

    # Delete folder (empty)
    svc.delete_folder("NewX")
    tree = scanner.scan()
    assert not any(n.name == "NewX" for n in tree.children)

    # Non-empty delete should error without recursive
    with pytest.raises(HierarchyError) as ei:
        svc.delete_folder("Code")
    assert ei.value.code == "E_NOT_EMPTY"

