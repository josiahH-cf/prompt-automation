import io
import logging
from pathlib import Path
import json

from prompt_automation.services import hierarchy as hmod


def _w(p: Path):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"id": 1, "title": "T", "style": p.parent.name, "template": [], "placeholders": []}), encoding="utf-8")


def test_scan_emits_observability_and_uses_time_fn(tmp_path, monkeypatch):
    root = tmp_path / "styles"
    _w(root / "Code" / "01_a.json")
    monkeypatch.setenv("PROMPT_AUTOMATION_PROMPTS", str(root))

    # Inject a predictable time function
    times = [0.0, 0.150]
    def time_fn():
        return times.pop(0)

    scanner = hmod.TemplateHierarchyScanner(root, time_fn=time_fn)

    # Attach a capture handler to the module logger
    log = hmod._log
    stream = io.StringIO()
    sh = logging.StreamHandler(stream)
    sh.setLevel(logging.INFO)
    log.addHandler(sh)
    try:
        scanner.scan()
        out = stream.getvalue()
        assert "hierarchy.scan.success" in out
        assert "duration_ms" in out
    finally:
        log.removeHandler(sh)

