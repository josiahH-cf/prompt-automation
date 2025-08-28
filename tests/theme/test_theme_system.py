import json
import os
import sys
from pathlib import Path


def _prepare_settings(tmp_path, monkeypatch):
    # Ensure settings live under a writable prompts/Settings directory
    settings_dir = tmp_path / 'prompts' / 'styles' / 'Settings'
    settings_dir.mkdir(parents=True)
    settings_file = settings_dir / 'settings.json'
    # Point variables.storage internals at our temp settings
    import importlib
    st = importlib.import_module('prompt_automation.variables.storage')
    monkeypatch.setattr(st, '_SETTINGS_DIR', settings_dir, raising=False)
    monkeypatch.setattr(st, '_SETTINGS_FILE', settings_file, raising=False)
    # Make overrides path isolated as well
    monkeypatch.setattr(st, '_PERSIST_FILE', tmp_path / 'placeholder-overrides.json', raising=False)
    return settings_file


def _with_sandbox_logs(tmp_path, monkeypatch):
    # Redirect app home/logs so errorlog does not attempt to write to real $HOME
    monkeypatch.setenv('PROMPT_AUTOMATION_HOME', str(tmp_path / '.pa_home'))
    monkeypatch.setenv('PROMPT_AUTOMATION_LOG_DIR', str(tmp_path / '.pa_home' / 'logs'))


def test_theme_persistence_roundtrip(tmp_path, monkeypatch):
    _with_sandbox_logs(tmp_path, monkeypatch)
    settings_file = _prepare_settings(tmp_path, monkeypatch)
    # Lazy import after env/setup
    import importlib
    st = importlib.import_module('prompt_automation.variables.storage')
    # Initially empty -> get should return None/absent
    settings_file.write_text(json.dumps({}), encoding='utf-8')
    from prompt_automation.theme import resolve as tres
    # We set preference to dark and ensure it roundtrips
    tres.set_user_theme_preference('dark')
    assert tres.get_user_theme_preference() == 'dark'


def test_theme_resolution_precedence_cli_over_config(tmp_path, monkeypatch):
    _with_sandbox_logs(tmp_path, monkeypatch)
    settings_file = _prepare_settings(tmp_path, monkeypatch)
    settings_file.write_text(json.dumps({'theme': 'light'}), encoding='utf-8')
    from prompt_automation.theme.resolve import ThemeResolver, get_registry, set_enable_theming, get_enable_theming
    # Enable theming for this test
    set_enable_theming(True)
    r = ThemeResolver(get_registry())
    # CLI override should win over persisted
    assert r.resolve(cli_override='dark') == 'dark'


def test_theme_invalid_name_falls_back_to_light(tmp_path, monkeypatch):
    _with_sandbox_logs(tmp_path, monkeypatch)
    settings_file = _prepare_settings(tmp_path, monkeypatch)
    settings_file.write_text(json.dumps({'theme': 'gothic'}), encoding='utf-8')
    from prompt_automation.theme.resolve import ThemeResolver, get_registry
    r = ThemeResolver(get_registry())
    assert r.resolve() == 'light'


def test_enable_theming_flag_disables_changes(tmp_path, monkeypatch):
    _with_sandbox_logs(tmp_path, monkeypatch)
    _prepare_settings(tmp_path, monkeypatch)
    from prompt_automation.theme.resolve import ThemeResolver, get_registry, set_enable_theming
    set_enable_theming(False)
    r = ThemeResolver(get_registry())
    assert r.resolve(cli_override='dark') == 'light'
    # Toggle should remain light when disabled
    assert r.toggle() == 'light'


def test_gui_applier_applies_dark_tokens(tmp_path, monkeypatch):
    _with_sandbox_logs(tmp_path, monkeypatch)
    from prompt_automation.theme import model, apply

    class RootStub:
        def __init__(self):
            self.opts = []
        def option_add(self, key, value):
            self.opts.append((key, value))

    root = RootStub()
    count = apply.apply_to_root(root, model.get_theme('dark'), initial=True, enable=True)
    assert count > 0
    keys = {k for k, _ in root.opts}
    # Ensure a few key Tk options are set
    assert '*background' in keys
    assert '*foreground' in keys
    assert '*selectBackground' in keys and '*selectForeground' in keys


def test_gui_applier_light_is_noop(tmp_path, monkeypatch):
    _with_sandbox_logs(tmp_path, monkeypatch)
    from prompt_automation.theme import model, apply

    class RootStub:
        def __init__(self):
            self.opts = []
        def option_add(self, key, value):
            self.opts.append((key, value))

    root = RootStub()
    count = apply.apply_to_root(root, model.get_theme('light'), initial=True, enable=True)
    # Light is identity: do not change existing defaults by default
    assert count == 0
    assert root.opts == []


def test_accessibility_contrast_minimums():
    from prompt_automation.theme import model
    dark = model.get_theme('dark')
    cr = model.contrast_ratio
    assert cr(dark['textPrimary'], dark['background']) >= 4.5
    assert cr(dark['textPrimary'], dark['surface']) >= 4.5
    # Selection pair
    assert cr(dark['selectionForeground'], dark['selectionBackground']) >= 4.5


def test_cli_formatter_dark_tty_and_no_color_guards(tmp_path, monkeypatch):
    _with_sandbox_logs(tmp_path, monkeypatch)
    from prompt_automation.theme import apply, model
    text = 'Heading'
    # Force TTY behaviour and NO_COLOR disabled
    out = apply.format_heading(text, model.get_theme('dark'), force_tty=True, no_color_env=False)
    assert '\x1b[' in out and text in out
    # Non-tty or NO_COLOR -> plain
    out2 = apply.format_heading(text, model.get_theme('dark'), force_tty=False, no_color_env=False)
    assert out2 == text
    out3 = apply.format_heading(text, model.get_theme('dark'), force_tty=True, no_color_env=True)
    assert out3 == text


def test_toggle_persists_preference(tmp_path, monkeypatch):
    _with_sandbox_logs(tmp_path, monkeypatch)
    settings_file = _prepare_settings(tmp_path, monkeypatch)
    settings_file.write_text(json.dumps({'theme': 'light', 'enable_theming': True}), encoding='utf-8')
    from prompt_automation.theme.resolve import ThemeResolver, get_registry
    r = ThemeResolver(get_registry())
    n1 = r.toggle()
    assert n1 == 'dark'
    n2 = r.toggle()
    assert n2 == 'light'

