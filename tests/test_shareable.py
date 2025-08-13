from pathlib import Path
from prompt_automation.renderer import is_shareable, inject_share_flag

def test_is_shareable_explicit_false(tmp_path: Path):
    data = {"id":1, "title":"x","style":"Test","template":[],"placeholders":[],"metadata":{"share_this_file_openly": False}}
    assert not is_shareable(data, tmp_path / "dummy.json")


def test_is_shareable_local_dir(tmp_path: Path):
    # No explicit flag but path under prompts/local
    data = {"id":2, "title":"x","style":"Test","template":[],"placeholders":[]}
    inject_share_flag(data, tmp_path / "prompts" / "local" / "a.json")
    # Explicit injection should default to False because of path rule after load
    assert not is_shareable(data, tmp_path / "prompts" / "local" / "a.json")


def test_is_shareable_default_true(tmp_path: Path):
    data = {"id":3, "title":"x","style":"Test","template":[],"placeholders":[]}
    inject_share_flag(data, tmp_path / "prompts" / "styles" / "Style" / "a.json")
    assert is_shareable(data, tmp_path / "prompts" / "styles" / "Style" / "a.json")
