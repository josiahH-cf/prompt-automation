import json
from pathlib import Path


def test_reset_requires_confirmation_and_undo(monkeypatch, tmp_path):
    # Patch overrides and settings locations to tmp
    import prompt_automation.variables.values as values
    import prompt_automation.variables.storage as storage
    overrides_file = tmp_path / 'placeholder-overrides.json'
    settings_dir = tmp_path / 'Settings'
    settings_file = settings_dir / 'settings.json'
    monkeypatch.setattr(values, '_PERSIST_FILE', overrides_file, raising=False)
    monkeypatch.setattr(storage, '_PERSIST_FILE', overrides_file, raising=False)
    monkeypatch.setattr(storage, '_SETTINGS_DIR', settings_dir, raising=False)
    monkeypatch.setattr(storage, '_SETTINGS_FILE', settings_file, raising=False)

    # Seed overrides and settings
    payload = {"templates": {"1": {"file": {"path": "foo.txt"}}}, "template_values": {"1": {"name": "Alice"}}}
    overrides_file.write_text(json.dumps(payload))
    settings_dir.mkdir(parents=True, exist_ok=True)
    settings_file.write_text(json.dumps({"file_overrides": {"templates": {"1": {"file": {"path": "foo.txt"}}}}}))

    # New confirm+undo helpers should exist
    try:
        values.reset_file_overrides_with_backup  # type: ignore[attr-defined]
        values.undo_last_reset_file_overrides    # type: ignore[attr-defined]
        have_helpers = True
    except AttributeError:
        have_helpers = False
    assert have_helpers is True, "Expected reset_file_overrides_with_backup and undo_last_reset_file_overrides"

    # Decline confirmation: nothing should change
    def deny():
        return False
    changed = values.reset_file_overrides_with_backup(confirm_cb=deny)  # type: ignore[attr-defined]
    assert changed is False
    assert overrides_file.exists(), "Overrides file should remain when reset declined"

    # Accept confirmation: overrides removed and undo snapshot created
    def accept():
        return True
    changed2 = values.reset_file_overrides_with_backup(confirm_cb=accept)  # type: ignore[attr-defined]
    assert changed2 is True
    assert not overrides_file.exists(), "Overrides file should be removed on reset"

    # Undo restores prior content
    restored = values.undo_last_reset_file_overrides()  # type: ignore[attr-defined]
    assert restored is True
    assert overrides_file.exists(), "Overrides should be restored after undo"
    data = json.loads(overrides_file.read_text())
    assert data.get('templates', {}).get('1', {}).get('file', {}).get('path') == 'foo.txt'

    # Idempotency / edge cases
    # Second reset without intervening changes still safe
    assert values.reset_file_overrides_with_backup(confirm_cb=accept) is True  # type: ignore[attr-defined]
    assert values.undo_last_reset_file_overrides() is True  # type: ignore[attr-defined]
    # No overrides present -> reset no-op
    overrides_file.unlink(missing_ok=True)
    assert values.reset_file_overrides_with_backup(confirm_cb=accept) is False  # type: ignore[attr-defined]

