import json
from prompt_automation import menus


def test_create_new_template(tmp_path, monkeypatch):
    menus.PROMPTS_DIR = tmp_path
    inputs = iter(["Test", "01", "Title", "role", "line", ".", "name"])
    monkeypatch.setattr("builtins.input", lambda *a: next(inputs))
    menus.create_new_template()
    files = list((tmp_path / "Test").glob("*.json"))
    assert files
    data = json.loads(files[0].read_text())
    assert data["id"] == 1
