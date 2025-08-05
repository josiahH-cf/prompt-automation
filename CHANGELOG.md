# Changelog

## Unreleased
- Added interactive `--assign-hotkey` command with per-user hotkey mapping file

## 0.2.1 - 2025-08-01
- Enhanced cross-platform compatibility for WSL2/Windows environments
- Fixed Unicode character encoding issues in PowerShell scripts  
- Improved WSL path detection and temporary file handling
- Enhanced prompts directory resolution with multiple fallback locations
- Updated all installation scripts for better cross-platform support
- Fixed package distribution to include prompts directory in all installations
- Added comprehensive error handling for missing prompts directory
- Made Windows keyboard library optional to prevent system hook errors
- Improved error handling for keyboard library failures with PowerShell fallback

## 0.2.1 - 2024-05-01
- Documentation overhaul with install instructions, template management guide and advanced configuration.
- `PROMPT_AUTOMATION_PROMPTS` and `PROMPT_AUTOMATION_DB` environment variables allow custom locations for templates and usage log.
