import pathlib
from typing import Any, Dict

import pytest

yaml = pytest.importorskip("yaml", reason="PyYAML required for espanso tests")


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
BASE_YML = REPO_ROOT / "espanso-package" / "match" / "base.yml"


def _load_base_yaml() -> Dict[str, Any]:
    assert BASE_YML.exists(), f"Missing {BASE_YML}"
    return yaml.safe_load(BASE_YML.read_text(encoding="utf-8"))


def test_ntsk_snippet_removed_from_base_yaml():
    data = _load_base_yaml()
    matches = data.get("matches") or []
    ntsk = next((m for m in matches if m.get("trigger") == ":ntsk"), None)
    assert ntsk is None, ":ntsk snippet should be removed (migrated to prompt-automation template)"

