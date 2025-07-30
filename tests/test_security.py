import json
import sys
sys.modules.setdefault("pyperclip", type("x", (), {"copy": lambda *a: None}))

import pytest
from prompt_automation import menus, logger, variables, cli
from prompt_automation.utils import safe_run


def test_safe_run_sanitizes(monkeypatch):
    recorded = []

    def fake_run(cmd, **kw):
        recorded.extend(cmd)
        class R:
            returncode = 0
        return R()
    monkeypatch.setattr('subprocess.run', fake_run)
    safe_run(['echo', 'bad;rm'])
    assert ';' not in recorded[1]


def test_duplicate_ids_runtime(tmp_path):
    style = tmp_path / 'A'
    style.mkdir(parents=True)
    data = {'id': 1, 'title': 't', 'style': 'A', 'template': [], 'placeholders': []}
    (style / '01_a.json').write_text(json.dumps(data))
    (style / '02_b.json').write_text(json.dumps(data))
    orig_dir = menus.PROMPTS_DIR
    menus.PROMPTS_DIR = tmp_path
    with pytest.raises(ValueError):
        menus.ensure_unique_ids(tmp_path)
    menus.PROMPTS_DIR = orig_dir


def test_db_lock_warning(tmp_path, capsys):
    orig = logger.DB_PATH
    logger.DB_PATH = tmp_path / 'u.db'
    conn1 = logger._connect()
    conn2 = logger._connect()
    out = capsys.readouterr().out
    assert 'Warning' in out
    conn1.close()
    logger._unlock_db()
    conn2.close()
    logger._unlock_db()
    logger.DB_PATH = orig


def test_is_wsl_env(monkeypatch):
    monkeypatch.setenv('WSL_DISTRO_NAME', 'Ubuntu')
    assert cli._is_wsl()


def test_dependency_check_missing(monkeypatch):
    monkeypatch.setattr(cli, '_check_cmd', lambda x: False)
    monkeypatch.setattr(cli, '_run_cmd', lambda x: False)
    sys.modules.pop('pyperclip', None)
    result = cli.check_dependencies()
    assert result is False


def test_editor_prompt_error(monkeypatch):
    monkeypatch.setattr('prompt_automation.utils.safe_run', lambda *a, **k: (_ for _ in ()).throw(Exception('fail')))
    assert variables._editor_prompt() is None
