import json
import os
from pathlib import Path


def _store_path(tmp_path: Path) -> Path:
    # Mirrors history default path under HOME_DIR
    return (tmp_path / ".prompt-automation") / "recent-history.json"


def test_rotation_and_ordering(monkeypatch, tmp_path):
    monkeypatch.setenv('PROMPT_AUTOMATION_HOME', str(tmp_path))
    from prompt_automation import history as hist
    monkeypatch.setattr(hist, 'HOME_DIR', tmp_path / '.prompt-automation', raising=False)
    RecentHistoryStore = hist.RecentHistoryStore

    store = RecentHistoryStore(limit=5)
    # Append 7 entries; expect 5 kept (newest first)
    for i in range(7):
        store.append(template={"id": i, "title": f"T{i}"}, rendered_text=f"r{i}", final_output=f"o{i}")
    ents = store.get_entries()
    assert len(ents) == 5
    # Newest first: last appended is i=6
    assert ents[0]['title'] == 'T6'
    assert ents[-1]['title'] == 'T2'


def test_persistence_across_restart(monkeypatch, tmp_path):
    monkeypatch.setenv('PROMPT_AUTOMATION_HOME', str(tmp_path))
    from prompt_automation import history as hist
    monkeypatch.setattr(hist, 'HOME_DIR', tmp_path / '.prompt-automation', raising=False)
    RecentHistoryStore = hist.RecentHistoryStore

    store = RecentHistoryStore()
    store.append(template={"id": 1, "title": "A"}, rendered_text="a", final_output="A")
    store.append(template={"id": 2, "title": "B"}, rendered_text="b", final_output="B")
    path = _store_path(tmp_path)
    assert path.exists()

    # New instance loads persisted entries
    store2 = RecentHistoryStore()
    ents2 = store2.get_entries()
    titles = [e['title'] for e in ents2]
    assert titles[0] == 'B' and titles[1] == 'A'


def test_redaction_patterns_env(monkeypatch, tmp_path):
    monkeypatch.setenv('PROMPT_AUTOMATION_HOME', str(tmp_path))
    # redact token-like secrets "sk-..."
    monkeypatch.setenv('PROMPT_AUTOMATION_HISTORY_REDACTION_PATTERNS', r'"sk-[A-Za-z0-9]+"|sk-[A-Za-z0-9]+')
    from prompt_automation import history as hist
    monkeypatch.setattr(hist, 'HOME_DIR', tmp_path / '.prompt-automation', raising=False)
    RecentHistoryStore = hist.RecentHistoryStore
    s = RecentHistoryStore()
    s.append(template={"id": 9, "title": "sec"}, rendered_text="prefix sk-ABC123 suffix", final_output="sk-SECRET-456")
    e = s.get_entries()[0]
    assert 'sk-' not in e['rendered']
    assert 'sk-' not in e['output']
    assert '[REDACTED]' in e['rendered'] or '[REDACTED]' in e['output']


def test_disable_toggle_stops_writes(monkeypatch, tmp_path):
    monkeypatch.setenv('PROMPT_AUTOMATION_HOME', str(tmp_path))
    from prompt_automation import history as hist
    monkeypatch.setattr(hist, 'HOME_DIR', tmp_path / '.prompt-automation', raising=False)
    RecentHistoryStore = hist.RecentHistoryStore
    s = RecentHistoryStore()
    s.append(template={"id": 1}, rendered_text="x", final_output="x")
    path = _store_path(tmp_path)
    assert path.exists()

    # Disable and attempt append -> no change (no crash)
    os.environ['PROMPT_AUTOMATION_HISTORY'] = '0'
    s2 = RecentHistoryStore()
    # Keep a snapshot of current file
    size_before = path.read_bytes()
    s2.append(template={"id": 2}, rendered_text="y", final_output="y")
    assert path.exists()
    assert path.read_bytes() == size_before


def test_disable_purge(monkeypatch, tmp_path):
    monkeypatch.setenv('PROMPT_AUTOMATION_HOME', str(tmp_path))
    # Ensure not disabled by previous tests
    monkeypatch.delenv('PROMPT_AUTOMATION_HISTORY', raising=False)
    from prompt_automation import history as hist
    monkeypatch.setattr(hist, 'HOME_DIR', tmp_path / '.prompt-automation', raising=False)
    RecentHistoryStore = hist.RecentHistoryStore
    s = RecentHistoryStore()
    s.append(template={"id": 1}, rendered_text="x", final_output="x")
    path = _store_path(tmp_path)
    assert path.exists()
    os.environ['PROMPT_AUTOMATION_HISTORY'] = '0'
    os.environ['PROMPT_AUTOMATION_HISTORY_PURGE_ON_DISABLE'] = '1'
    s2 = RecentHistoryStore()
    s2.append(template={"id": 2}, rendered_text="y", final_output="y")
    assert not path.exists()


def test_corruption_recovery(monkeypatch, tmp_path):
    monkeypatch.setenv('PROMPT_AUTOMATION_HOME', str(tmp_path))
    # Ensure not disabled by previous tests
    monkeypatch.delenv('PROMPT_AUTOMATION_HISTORY', raising=False)
    from prompt_automation import history as hist
    monkeypatch.setattr(hist, 'HOME_DIR', tmp_path / '.prompt-automation', raising=False)
    RecentHistoryStore = hist.RecentHistoryStore
    path = _store_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{ this is not json', encoding='utf-8')
    s = RecentHistoryStore()
    ents = s.get_entries()  # triggers safe load + quarantine
    assert ents == []
    # A .corrupt-* file should exist
    cor = list(path.parent.glob('recent-history.corrupt-*'))
    assert cor
    s.append(template={"id": 1, "title": "ok"}, rendered_text="r", final_output="o")
    assert path.exists()
