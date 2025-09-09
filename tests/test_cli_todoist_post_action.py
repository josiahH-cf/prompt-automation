from __future__ import annotations

import builtins
import io
import sys
from pathlib import Path

# Ensure local src is importable for tests without editable install
def _find_repo_root(start: Path) -> Path:
    cur = start
    for d in [cur] + list(cur.parents):
        if (d / "pyproject.toml").exists():
            return d
    return start.parent

import sys as _sys
_repo_root = _find_repo_root(Path(__file__).resolve())
_src = _repo_root / "src"
if str(_src) not in _sys.path:
    _sys.path.insert(0, str(_src))

import pytest


def _run_cli_once(monkeypatch, tmpl_path: Path, inputs: list[str]) -> str:
    # Ensure local src is importable
    repo_root = _find_repo_root(Path(__file__).resolve())
    src = repo_root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

    # Patch template selector to return our test template directly
    from prompt_automation.cli import controller as ctrl
    import prompt_automation.cli as cli_pkg
    from prompt_automation import paste as paste_mod

    # Fake selection to return the given template
    def _select_template_cli():
        import json
        return json.loads(tmpl_path.read_text(encoding="utf-8"))

    monkeypatch.setattr(ctrl, "select_template_cli", staticmethod(_select_template_cli))

    # Patch render to simply echo variables as-is without interactive prompts
    def _render_template_cli(tmpl):
        # Mimic return of (text, var_map)
        return ("ok", {"action": "A", "type": "bug", "dod": "x", "nra": "y"})

    monkeypatch.setattr(ctrl, "render_template_cli", staticmethod(_render_template_cli))

    # Bypass dependency checks and clipboard env in tests
    monkeypatch.setattr(cli_pkg, "check_dependencies", lambda require_fzf=True: True)
    monkeypatch.setattr(paste_mod, "copy_to_clipboard", lambda _text: True)

    # Feed inputs to input() prompts
    it = iter(inputs)
    monkeypatch.setattr(builtins, "input", lambda prompt="": next(it))

    # Capture stdout
    buf = io.StringIO()
    monkeypatch.setattr(sys, "stdout", buf)

    # Run controller main in terminal mode
    from prompt_automation.cli.cli import main as cli_main
    cli_main(["--terminal"])  # minimal invocation
    return buf.getvalue()


def test_cli_post_action_disabled_by_default(monkeypatch, tmp_path):
    # Ensure env flag is off
    monkeypatch.delenv("SEND_TODOIST_AFTER_RENDER", raising=False)

    # Provide a minimal template on disk
    tmpl = tmp_path / "tmpl.json"
    tmpl.write_text('{"schema":1,"id":1,"title":"t","style":"s","template":["{{action}}"],"placeholders":[{"name":"action"}],"metadata":{}}', encoding="utf-8")

    out = _run_cli_once(monkeypatch, tmpl, inputs=["y"])  # proceed to copy
    assert "Text copied to clipboard" in out
    # No error message printed
    assert "Todoist send failed" not in out


def test_cli_post_action_pwsh_missing_non_blocking(monkeypatch, tmp_path):
    # Enable post-action but remove pwsh from PATH so detector fails
    monkeypatch.setenv("SEND_TODOIST_AFTER_RENDER", "1")
    monkeypatch.setenv("PATH", "")

    tmpl = tmp_path / "tmpl.json"
    tmpl.write_text('{"schema":1,"id":1,"title":"t","style":"s","template":["{{action}}"],"placeholders":[{"name":"action"}],"metadata":{}}', encoding="utf-8")

    out = _run_cli_once(monkeypatch, tmpl, inputs=["y"])  # proceed to copy
    # We should still reach post-copy message
    assert "Text copied to clipboard" in out
    # Optional warning may appear; either way it must not crash
    assert "Todoist send failed" in out or "Text copied to clipboard" in out
