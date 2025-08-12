import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import prompt_automation.config as config


def _reload(monkeypatch):
    return importlib.reload(config)


def test_prompts_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv(config.ENV_PROMPTS, str(tmp_path))
    mod = _reload(monkeypatch)
    assert mod.PROMPTS_DIR == tmp_path


def test_prompts_default_location(monkeypatch, tmp_path):
    monkeypatch.delenv(config.ENV_PROMPTS, raising=False)
    default = tmp_path / ".prompt-automation" / "prompts" / "styles"
    default.mkdir(parents=True)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    mod = _reload(monkeypatch)
    mod.PROMPTS_SEARCH_PATHS = [default]
    assert mod._find_prompts_dir() == default


def test_env_overrides_db_and_log(monkeypatch, tmp_path):
    db = tmp_path / "usage.db"
    log_dir = tmp_path / "logs"
    monkeypatch.setenv(config.ENV_DB, str(db))
    monkeypatch.setenv(config.ENV_LOG_DIR, str(log_dir))
    mod = _reload(monkeypatch)
    assert mod.DB_PATH == db
    assert mod.LOG_DIR == log_dir


def test_default_db_and_log(monkeypatch, tmp_path):
    for env in (config.ENV_DB, config.ENV_LOG_DIR, config.ENV_HOME):
        monkeypatch.delenv(env, raising=False)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    mod = _reload(monkeypatch)
    assert mod.DB_PATH == tmp_path / ".prompt-automation" / "usage.db"
    assert mod.LOG_DIR == tmp_path / ".prompt-automation" / "logs"

