import os
from pathlib import Path
import pytest

from prompt_automation.services.hierarchy import TemplateHierarchyScanner
from prompt_automation.services.hierarchy_fs import TemplateFSService, HierarchyError


def test_name_validation_and_traversal_rejected(tmp_path, monkeypatch):
    root = tmp_path / "styles"
    root.mkdir(parents=True)
    monkeypatch.setenv("PROMPT_AUTOMATION_PROMPTS", str(root))
    scanner = TemplateHierarchyScanner(root)
    svc = TemplateFSService(root=root, on_change=scanner.invalidate)

    # Invalid folder name
    with pytest.raises(HierarchyError) as ei:
        svc.create_folder("Bad Name")
    assert ei.value.code == "E_INVALID_NAME"

    # Traversal
    with pytest.raises(HierarchyError) as ei:
        svc.create_folder("../escape")
    assert ei.value.code == "E_UNSAFE_PATH"

    # Invalid template name
    with pytest.raises(HierarchyError) as ei:
        svc.create_template("Code/not_json.txt")
    assert ei.value.code == "E_INVALID_NAME"


def test_symlink_not_followed_and_cache_invalidation(tmp_path, monkeypatch):
    root = tmp_path / "styles"
    target = tmp_path / "outside"
    (root / "A").mkdir(parents=True)
    (target / "B").mkdir(parents=True)
    # Symlink may fail on some platforms (Windows without privileges); best-effort
    try:
        (root / "link").symlink_to(target, target_is_directory=True)
    except Exception:
        pass

    monkeypatch.setenv("PROMPT_AUTOMATION_PROMPTS", str(root))
    scanner = TemplateHierarchyScanner(root, cache_ttl=60)
    svc = TemplateFSService(root=root, on_change=scanner.invalidate)

    t1 = scanner.scan()
    # Ensure link folder, if present, is not included as a normal folder
    assert not any(ch.name == "link" for ch in t1.children if ch.type == "folder")

    # Cache returns without change until invalidated
    t2 = scanner.scan()
    assert t1 is t2  # cached object

    # Create a file and ensure invalidate triggers refresh
    svc.create_folder("X")
    t3 = scanner.scan()
    assert t3 is not t2
    assert any(ch.name == "X" for ch in t3.children if ch.type == "folder")

