import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from prompt_automation.menus import render_template


def _make_template(file_placeholders, extra_tokens=None):
    extra_tokens = extra_tokens or []
    body = [
        "Primary content length: {{reference_file}}",  # ensure token present
        "{{secondary_file_path}}",  # pure path token line (removable if empty)
        "Legacy alias: {{reference_file_content}}",
    ] + extra_tokens
    placeholders = [
        {"name": "reference_file", "type": "file"},
        {"name": "secondary_file", "type": "file"},
    ]
    placeholders.extend(file_placeholders)
    return {
        "id": 99,
        "title": "MultiFile",
        "style": "Test",
        "template": body,
        "placeholders": placeholders,
    }


def test_multi_file_injection_and_paths(tmp_path, monkeypatch):
    # Create two files
    primary = tmp_path / "primary.txt"; primary.write_text("PRIMARY\nLINE2")
    secondary = tmp_path / "secondary.md"; secondary.write_text("SEC")

    tmpl = _make_template([])
    # values simulate collected raw variables (paths)
    rendered = render_template(tmpl, values={
        "reference_file": str(primary),
        "secondary_file": str(secondary),
    })
    assert "PRIMARY" in rendered and "LINE2" in rendered
    # legacy alias present
    assert "Legacy alias:" in rendered and "PRIMARY" in rendered
    # path token inserted (line should equal the path)
    assert str(secondary) in rendered.splitlines()


def test_global_fallback_only_for_reference(tmp_path, monkeypatch):
    # Global file only; template omits reference_file placeholder but references tokens
    global_file = tmp_path / "global.txt"; global_file.write_text("GLOBAL")
    # Patch get_global_reference_file to return our path
    import prompt_automation.variables.files as files_mod
    monkeypatch.setattr(files_mod, 'get_global_reference_file', lambda: str(global_file))
    import prompt_automation.menus as menus_mod
    monkeypatch.setattr(menus_mod, 'get_global_reference_file', lambda: str(global_file))

    tmpl = {
        "id": 5,
        "title": "NoRefPlaceholder",
        "style": "Test",
        "template": ["Content: {{reference_file}}", "Alias: {{reference_file_content}}", "Path: {{reference_file_path}}"],
        "placeholders": [
            {"name": "secondary_file", "type": "file"}
        ]
    }
    rendered = render_template(tmpl, values={"secondary_file": ""})
    assert "GLOBAL" in rendered  # injected content
    assert str(global_file) in rendered  # path token


def test_file_content_fresh_read(tmp_path):
    f = tmp_path / "changing.txt"; f.write_text("V1")
    tmpl = _make_template([])
    rendered1 = render_template(tmpl, values={"reference_file": str(f), "secondary_file": ""})
    assert "V1" in rendered1
    f.write_text("V2")
    rendered2 = render_template(tmpl, values={"reference_file": str(f), "secondary_file": ""})
    assert "V2" in rendered2 and "V1" not in rendered2


def test_blank_secondary_removes_line(tmp_path):
    f = tmp_path / "p.txt"; f.write_text("P")
    tmpl = _make_template([])
    rendered = render_template(tmpl, values={"reference_file": str(f), "secondary_file": ""})
    # The pure path token line should be removed when secondary file path empty
    lines = rendered.splitlines()
    assert not any(l.strip() == '' for l in lines)  # no blank placeholder-only line
    # Primary content still present (content 'P')
    assert 'P' in rendered


def test_missing_file_graceful(tmp_path):
    missing = tmp_path / "nope.txt"
    tmpl = _make_template([])
    rendered = render_template(tmpl, values={"reference_file": str(missing), "secondary_file": ""})
    # no exception and legacy alias line should still appear but empty
    assert "Legacy alias:" in rendered

