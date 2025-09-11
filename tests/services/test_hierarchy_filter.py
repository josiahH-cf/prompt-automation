from pathlib import Path
import json
from pathlib import Path

from prompt_automation.services.hierarchy import TemplateHierarchyScanner, filter_tree


def _write(p: Path):
    p.parent.mkdir(parents=True, exist_ok=True)
    data = {"id": 1, "title": "T", "style": p.parent.name, "template": [], "placeholders": []}
    p.write_text(json.dumps(data), encoding="utf-8")


def test_filter_tree_matches_case_insensitive(tmp_path, monkeypatch):
    root = tmp_path / "styles"
    _write(root / "Alpha" / "t1.json")
    _write(root / "Beta" / "t2.json")
    monkeypatch.setenv("PROMPT_AUTOMATION_PROMPTS", str(root))

    scanner = TemplateHierarchyScanner(root)
    tree = scanner.scan()
    filtered = filter_tree(tree, "alpha")
    names = [n.name for n in filtered.children if n.type == "folder"]
    assert names == ["Alpha"]
    a = filtered.children[0]
    assert a.children[0].name == "t1.json"


def test_scan_filtered_returns_empty_when_no_match(tmp_path, monkeypatch):
    root = tmp_path / "styles"
    _write(root / "A" / "one.json")
    monkeypatch.setenv("PROMPT_AUTOMATION_PROMPTS", str(root))

    scanner = TemplateHierarchyScanner(root)
    filtered = scanner.scan_filtered("missing")
    assert filtered.children == []


def test_scan_filtered_folder_match_includes_children(tmp_path, monkeypatch):
    root = tmp_path / "styles"
    _write(root / "Docs" / "readme.json")
    _write(root / "Docs" / "guide.json")
    monkeypatch.setenv("PROMPT_AUTOMATION_PROMPTS", str(root))

    scanner = TemplateHierarchyScanner(root)
    filtered = scanner.scan_filtered("docs")
    assert len(filtered.children) == 1
    doc_folder = filtered.children[0]
    names = {ch.name for ch in doc_folder.children}
    assert names == {"readme.json", "guide.json"}


def test_scan_filtered_template_match(tmp_path, monkeypatch):
    root = tmp_path / "styles"
    _write(root / "A" / "alpha.json")
    _write(root / "A" / "beta.json")
    monkeypatch.setenv("PROMPT_AUTOMATION_PROMPTS", str(root))

    scanner = TemplateHierarchyScanner(root)
    filtered = scanner.scan_filtered("beta")
    assert len(filtered.children) == 1
    a = filtered.children[0]
    assert [ch.name for ch in a.children] == ["beta.json"]


def test_filter_nested_folder(tmp_path, monkeypatch):
    root = tmp_path / "styles"
    _write(root / "Parent" / "Child" / "note.json")
    _write(root / "Other" / "file.json")
    monkeypatch.setenv("PROMPT_AUTOMATION_PROMPTS", str(root))

    scanner = TemplateHierarchyScanner(root)
    tree = scanner.scan_filtered("child")
    assert len(tree.children) == 1
    parent = tree.children[0]
    child = parent.children[0]
    assert child.name == "Child"
    assert child.children[0].name == "note.json"
