import subprocess
import sys
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml", reason="PyYAML required for snippet adder tests")


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def test_add_snippet_to_new_file(tmp_path: Path):
    repo = Path(__file__).resolve().parents[2]
    script = repo / "scripts" / "add_espanso_snippet.py"
    # Create isolated match dir in tmp and point SRC dir there by symlink
    match_src = tmp_path / "espanso-package" / "match"
    match_src.mkdir(parents=True)
    # Copy script into tmp to run against tmp tree by manipulating sys.path/ROOT? We invoke with python and rely on ROOT = parents[1]
    # So change cwd to tmp so script resolves ROOT correctly
    # Build directory structure to mimic repo root
    (tmp_path / "scripts").mkdir()
    (tmp_path / "espanso-package").mkdir(exist_ok=True)
    (tmp_path / "espanso-package" / "_manifest.yml").write_text("name: prompt-automation\nversion: 0.0.1\n", encoding="utf-8")
    (tmp_path / "scripts" / "add_espanso_snippet.py").write_text(script.read_text(encoding="utf-8"), encoding="utf-8")

    proc = run([sys.executable, "scripts/add_espanso_snippet.py", "--file", "temp.yml", "--trigger", ":t.tmp", "--replace", "Hello"], tmp_path)
    assert proc.returncode == 0, proc.stderr
    out = (tmp_path / "espanso-package" / "match" / "temp.yml").read_text(encoding="utf-8")
    data = yaml.safe_load(out)
    assert any(m.get("trigger") == ":t.tmp" for m in data.get("matches", []))


def test_add_snippet_duplicate_rejected(tmp_path: Path):
    repo = Path(__file__).resolve().parents[2]
    script = repo / "scripts" / "add_espanso_snippet.py"
    (tmp_path / "scripts").mkdir()
    (tmp_path / "espanso-package" / "match").mkdir(parents=True)
    (tmp_path / "espanso-package" / "_manifest.yml").write_text("name: prompt-automation\nversion: 0.0.1\n", encoding="utf-8")
    (tmp_path / "scripts" / "add_espanso_snippet.py").write_text(script.read_text(encoding="utf-8"), encoding="utf-8")
    # Seed an existing trigger
    (tmp_path / "espanso-package" / "match" / "a.yml").write_text("matches:\n  - trigger: ':dupe'\n    replace: 'x'\n", encoding="utf-8")
    # Attempt to add same trigger
    proc = run([sys.executable, "scripts/add_espanso_snippet.py", "--file", "b.yml", "--trigger", ":dupe", "--replace", "y"], tmp_path)
    assert proc.returncode != 0
    assert "Trigger already exists" in (proc.stderr or proc.stdout)
