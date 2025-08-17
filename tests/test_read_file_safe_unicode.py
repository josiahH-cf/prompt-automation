from prompt_automation.renderer import read_file_safe
from pathlib import Path


def test_read_file_safe_emoji(tmp_path: Path):
    # Write a UTF-8 file with emoji and dashes
    content = "Heading – with dash and emoji 👍\nLine 2: 🚀"
    p = tmp_path / "emoji.txt"
    p.write_bytes(content.encode("utf-8"))  # raw bytes
    read_back = read_file_safe(str(p))
    assert "👍" in read_back and "🚀" in read_back
    assert "ðŸ" not in read_back  # ensure no mojibake
