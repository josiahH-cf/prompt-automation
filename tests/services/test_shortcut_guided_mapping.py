import json
from pathlib import Path

import types


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


def test_shortcut_guided_options_and_overwrite_confirm(monkeypatch, tmp_path):
    # Arrange: build a fake prompts dir with two templates
    style_dir = tmp_path / 'Test'
    style_dir.mkdir(parents=True)
    t1 = _make_template(style_dir, 11, 'Alpha')
    t2 = _make_template(style_dir, 22, 'Beta')

    # Monkeypatch PROMPTS_DIR used inside shortcuts module functions
    import prompt_automation.shortcuts as sc
    monkeypatch.setattr(sc, 'PROMPTS_DIR', tmp_path)
    monkeypatch.setattr(sc, 'SETTINGS_DIR', tmp_path / 'Settings')
    monkeypatch.setattr(sc, 'SHORTCUT_FILE', tmp_path / 'Settings/template-shortcuts.json')

    # Failing expectations before implementation:
    # 1) A guided options helper should exist and provide structured metadata
    #    for UI (id, title, rel, label). Expect AttributeError now.
    try:
        sc.build_shortcut_options  # type: ignore[attr-defined]
        have_helper = True
    except AttributeError:
        have_helper = False
    assert have_helper is True, "Expected build_shortcut_options helper to exist for UI guidance"

    # If helper exists, validate structure (this part will also fail initially if stubbed incorrectly)
    opts = sc.build_shortcut_options(base=tmp_path)  # type: ignore[attr-defined]
    # Should include both templates
    rels = {o['rel'] for o in opts}
    assert str(t1.relative_to(tmp_path)) in rels and str(t2.relative_to(tmp_path)) in rels
    # Each option should include friendly label for display
    assert all({'id', 'title', 'rel', 'label'} <= set(o.keys()) for o in opts)

    # 2) Overwrite confirmation for remapping an existing digit
    mapping = {"1": str(t1.relative_to(tmp_path))}
    sc.save_shortcuts(mapping)

    # A helper should support confirm-on-overwrite. Expect AttributeError now.
    try:
        sc.update_shortcut_digit  # type: ignore[attr-defined]
        have_update = True
    except AttributeError:
        have_update = False
    assert have_update is True, "Expected update_shortcut_digit with confirm-overwrite support"

    # Simulate user declining overwrite
    def deny(_digit, _old, _new):
        return False

    new_rel = str(t2.relative_to(tmp_path))
    mapping2 = sc.load_shortcuts()
    out = sc.update_shortcut_digit(mapping2, '1', new_rel, confirm_cb=deny)  # type: ignore[attr-defined]
    assert out['1'] == str(t1.relative_to(tmp_path)), "Mapping should remain unchanged when overwrite not confirmed"

    # Simulate user accepting overwrite
    def accept(_digit, _old, _new):
        return True

    out2 = sc.update_shortcut_digit(out, '1', new_rel, confirm_cb=accept)  # type: ignore[attr-defined]
    assert out2['1'] == new_rel, "Mapping should update when overwrite confirmed"

