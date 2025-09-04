from pathlib import Path
import json

from prompt_automation.services.hierarchy import TemplateHierarchyScanner
from prompt_automation.services import template_search as tsearch


def _w(p: Path):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"id": 1, "title": "T", "style": p.parent.name, "template": [], "placeholders": []}), encoding="utf-8")


def test_flat_listing_unchanged(tmp_path, monkeypatch):
    root = tmp_path / "styles"
    _w(root / "Code" / "01_a.json")
    _w(root / "Code" / "b.json")
    _w(root / "Plans" / "c.json")
    monkeypatch.setenv("PROMPT_AUTOMATION_PROMPTS", str(root))

    # Ensure the search module points at our temp root regardless of prior imports
    import importlib
    importlib.reload(tsearch)
    # Monkeypatch PROMPTS_DIR used inside template_search
    tsearch.PROMPTS_DIR = root
    flat = tsearch.list_templates(recursive=True)
    # Should see all three JSON files (order not guaranteed here)
    names = sorted(p.name for p in flat)
    assert names == ["01_a.json", "b.json", "c.json"]

    # Tree scan count equals flat count across folders
    scanner = TemplateHierarchyScanner(root)
    tree = scanner.scan()
    def _count(n):
        c = 0
        for ch in n.children:
            if ch.type == "template":
                c += 1
            else:
                c += _count(ch)
        return c
    assert _count(tree) == len(flat)
