from promptpilot.renderer import load_template

def test_load_template(tmp_path):
    p = tmp_path / "t.json"
    p.write_text('{"id":1, "title":"t", "template":[], "placeholders":[]}')
    data = load_template(p)
    assert data["id"] == 1
