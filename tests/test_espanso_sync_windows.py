import types
from pathlib import Path
import importlib


def test_windows_git_path_never_uses_local_path(monkeypatch):
    import sys
    from pathlib import Path
    here = Path(__file__).resolve()
    repo_root = None
    for d in [here.parent] + list(here.parents):
        if (d / "src" / "prompt_automation").exists():
            repo_root = d
            break
    assert repo_root is not None
    src = repo_root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    import prompt_automation.espanso_sync as es
    importlib.reload(es)

    # Simulate Windows environment
    monkeypatch.setattr(es.platform, "system", lambda: "Windows")

    # espanso is on PATH; powershell exists; wsl may be absent
    def fake_which(name):
        n = name.lower()
        if n in ("espanso", "powershell.exe"):
            return f"C:\\fake\\bin\\{name}"
        return None

    monkeypatch.setattr(es.shutil, "which", fake_which)

    calls = []

    def fake_run(cmd, cwd=None, check=False, timeout=None):
        # Record for inspection
        calls.append(cmd)
        # Simulate behavior:
        if isinstance(cmd, list):
            # PowerShell command invocations
            if cmd[0].lower().endswith("powershell.exe"):
                ps = cmd[-1]  # -Command string
                if "espanso package list" in ps:
                    # No-op listing output
                    return (0, "- prompt-automation - version: 0.1.0 (git: https://github.com/josiahH-cf/prompt-automation.git)\n", "")
                if "espanso package update" in ps:
                    return (0, "", "")
                if "espanso package install" in ps:
                    # Return "already installed" non-zero to trigger update fallback
                    return (1, "", "unable to install package: package prompt-automation is already installed")
            # Direct espanso binary (not used on Windows path for install in this test)
            if len(cmd) >= 2 and cmd[0] == "espanso" and cmd[1] == "package":
                return (0, "", "")
        return (0, "", "")

    monkeypatch.setattr(es, "_run", fake_run)

    # Run with a UNC-like local_path but repo_url provided, ensuring mode='git'
    es._install_or_update(
        pkg_name="prompt-automation",
        repo_url="https://github.com/josiahH-cf/prompt-automation.git",
        local_path=Path(r"\\wsl.localhost\Ubuntu\home\me\prompt-automation\packages\prompt-automation\0.1.0"),
        git_branch="main",
    )

    # Assert no call attempted '--path' (Windows must not use local --path)
    textified = " ".join([(" ".join(c) if isinstance(c, list) else str(c)) for c in calls])
    assert "--path" not in textified
    # Ensure update fallback executed
    assert "espanso package update prompt-automation" in textified


def test_windows_skips_local_when_no_git(monkeypatch, tmp_path):
    import importlib
    import sys
    from pathlib import Path
    here = Path(__file__).resolve()
    repo_root = None
    for d in [here.parent] + list(here.parents):
        if (d / "src" / "prompt_automation").exists():
            repo_root = d
            break
    assert repo_root is not None
    src = repo_root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    import prompt_automation.espanso_sync as es
    importlib.reload(es)

    # Force Windows behavior
    monkeypatch.setattr(es.platform, "system", lambda: "Windows")

    # Pretend espanso + powershell present
    def fake_which(name):
        n = name.lower()
        if n in ("espanso", "powershell.exe"):
            return f"C:\\fake\\bin\\{name}"
        return None

    monkeypatch.setattr(es.shutil, "which", fake_which)

    calls = []

    def fake_run(cmd, cwd=None, check=False, timeout=None):
        calls.append(cmd)
        # Simulate success for restart/list commands
        return (0, "", "")

    monkeypatch.setattr(es, "_run", fake_run)

    # Provide a local path but no repo_url -> must not attempt any --path installs
    es._install_or_update(
        pkg_name="prompt-automation",
        repo_url=None,
        local_path=tmp_path / "packages" / "prompt-automation" / "0.1.0",
        git_branch=None,
    )

    textified = " ".join([(" ".join(c) if isinstance(c, list) else str(c)) for c in calls])
    assert "--path" not in textified
    # Should still try to refresh service state via powershell
    assert "powershell.exe" in textified


def test_run_uses_home_cwd_on_unc(monkeypatch, tmp_path):
    import importlib
    import sys
    from pathlib import Path
    here = Path(__file__).resolve()
    repo_root = None
    for d in [here.parent] + list(here.parents):
        if (d / "src" / "prompt_automation").exists():
            repo_root = d
            break
    assert repo_root is not None
    src = repo_root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    import prompt_automation.espanso_sync as es
    importlib.reload(es)

    monkeypatch.setattr(es.platform, "system", lambda: "Windows")
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    (tmp_path / "home").mkdir(parents=True, exist_ok=True)

    # Force current working directory to be a UNC path
    monkeypatch.setattr(es.os, "getcwd", lambda: r"\\\\wsl.localhost\\Ubuntu\\home\\user\\repo\\install")

    captured = {}

    class FakePopen:
        def __init__(self, args, cwd=None, shell=False, stdout=None, stderr=None, text=None):  # noqa: D401
            captured["cwd"] = cwd
            self.returncode = 0
        def communicate(self, timeout=None):
            return ("", "")

    monkeypatch.setattr(es.subprocess, "Popen", FakePopen)

    es._run(["espanso", "version"])  # any command
    assert captured.get("cwd") == str(tmp_path / "home")
