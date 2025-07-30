from prompt_automation import variables


def test_cli_fallback(monkeypatch):
    ph = {"name": "x"}
    monkeypatch.setattr(variables, "_gui_prompt", lambda *a: None)
    monkeypatch.setattr(variables, "_editor_prompt", lambda: None)
    monkeypatch.setattr("builtins.input", lambda *a: "val")
    vals = variables.get_variables([ph])
    assert vals["x"] == "val"
