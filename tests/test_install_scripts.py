from pathlib import Path
import os

def test_install_script_contains_hotkey():
    # Get the project root directory
    project_root = Path(__file__).parent.parent
    
    # Test bash install script
    install_sh = project_root / 'scripts' / 'install.sh'
    if install_sh.exists():
        data = install_sh.read_text()
        assert 'espanso restart' in data
    
    # Test PowerShell install script with cross-platform path handling
    install_ps1 = project_root / 'scripts' / 'install-dependencies.ps1'
    if install_ps1.exists():
        # Handle WSL path issues if needed
        if str(install_ps1).startswith("\\\\wsl.localhost"):
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.ps1', delete=False) as tmp:
                tmp_path = tmp.name
            try:
                import shutil
                shutil.copy2(str(install_ps1), tmp_path)
                ps = Path(tmp_path).read_text()
                os.unlink(tmp_path)  # Clean up temp file
            except Exception:
                ps = install_ps1.read_text()  # Fallback to direct read
        else:
            ps = install_ps1.read_text()
        
        assert 'AutoHotkey' in ps

