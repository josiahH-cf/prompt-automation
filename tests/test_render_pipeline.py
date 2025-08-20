from prompt_automation.menus.render_pipeline import (
    apply_defaults,
    apply_file_placeholders,
    apply_formatting,
    apply_global_placeholders,
    apply_post_render,
)
from prompt_automation.menus import render_template


def test_apply_file_placeholders_reads_content(tmp_path):
    f = tmp_path / "ref.txt"
    f.write_text("hello")
    tmpl = {"template": ["{{file}}", "{{file_path}}"]}
    raw_vars = {"file": str(f)}
    vars = {}
    placeholders = [{"name": "file", "type": "file"}]
    apply_file_placeholders(tmpl, raw_vars, vars, placeholders)
    assert vars["file"] == "hello"
    assert vars["file_path"] == str(f)


def test_apply_defaults_inserts_value():
    raw_vars = {}
    vars = {}
    placeholders = [{"name": "x", "default": "42"}]
    apply_defaults(raw_vars, vars, placeholders)
    assert vars["x"] == "42"


def test_apply_global_placeholders_injects_missing():
    tmpl = {"template": ["{{foo}}"], "global_placeholders": {"foo": "bar"}}
    vars = {}
    apply_global_placeholders(tmpl, vars, set())
    assert vars["foo"] == "bar"


def test_apply_formatting_creates_bullets():
    vars = {"items": "a\nb"}
    placeholders = [{"name": "items", "format": "list"}]
    apply_formatting(vars, placeholders)
    assert vars["items"] == "- a\n- b"


def test_apply_post_render_handles_remove_and_reminders():
    tmpl = {
        "template": ["Hello"],
        "global_placeholders": {"reminders": ["r1"], "think_deeply": "TD"},
    }
    placeholders = [{"name": "p", "remove_if_empty": "Extra"}]
    vars = {"p": ""}
    rendered = "Extra."
    result = apply_post_render(rendered, tmpl, placeholders, vars, set())
    assert "Extra" not in result
    assert "Reminders:" in result
    assert result.endswith("TD")


def test_render_template_round_trip():
    tmpl = {
        "template": ["{{greeting}}, {{name}}!", "{{items}}"],
        "placeholders": [
            {"name": "greeting", "default": "Hello"},
            {"name": "name"},
            {"name": "items", "format": "list"},
        ],
        "global_placeholders": {"think_deeply": "TD"},
    }
    result = render_template(tmpl, {"name": "Bob", "items": ["a", "b"]})
    assert result == "Hello, Bob!\n- a\n- b\nTD"
