import json
from pathlib import Path

from prompt_automation.shortcuts import renumber_templates, save_shortcuts, load_shortcuts
from prompt_automation.config import PROMPTS_DIR


def _make_template(tmpdir: Path, id_: int, title: str):
    data = {
        "id": id_,
        "title": title,
        "style": "Test",
        "role": "assistant",
        "template": ["Hello {{name}}"],
        "placeholders": [{"name": "name", "default": "X"}],
    }
    fname = f"{id_:02d}_{title.lower()}.json"
    p = tmpdir / fname
    p.write_text(json.dumps(data))
    return p


def test_renumber_basic(tmp_path, monkeypatch):
    # Simulate PROMPTS_DIR to isolated temp
    style_dir = tmp_path / 'Test'
    style_dir.mkdir(parents=True)
    t1 = _make_template(style_dir, 5, 'One')
    t2 = _make_template(style_dir, 6, 'Two')
    t3 = _make_template(style_dir, 7, 'Three')

    # Map digit 1 -> template with id 5 (will cause rename+id change), digit 2 -> id 7
    mapping = {"1": str(t1.relative_to(tmp_path)), "2": str(t3.relative_to(tmp_path))}

    # Monkeypatch PROMPTS_DIR used inside shortcuts module functions
    monkeypatch.setattr('prompt_automation.shortcuts.PROMPTS_DIR', tmp_path)

    renumber_templates(mapping, base=tmp_path)

    # Reload mutated files
    new_files = sorted(tmp_path.rglob('*.json'))
    ids = []
    for f in new_files:
        data = json.loads(f.read_text())
        if 'template' in data:
            ids.append(data['id'])
    # Should contain 1 and 2 among others
    assert 1 in ids and 2 in ids
