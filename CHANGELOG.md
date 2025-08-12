# Changelog

## Unreleased
- **Enhanced Hotkey System**: Comprehensive improvements to global hotkey functionality
  - Robust GUI-first with terminal fallback mechanism for all platforms
  - Automatic dependency checking and installation guidance
  - Improved AutoHotkey script generation with multiple execution paths
  - Enhanced Linux espanso integration with proper fallback commands
  - Better macOS AppleScript handling with background execution
  - Added `--update` command to refresh hotkey configuration and verify dependencies
  - Automatic hotkey script placement verification and error reporting
- Support for multiple installation methods (pip, pipx, executable, python -m)
- Added interactive `--assign-hotkey` command with per-user hotkey mapping file
- Added optional `append_file` placeholder to append rendered output to files
### GUI & UX
- New modular selector (`gui/selector/`) replacing monolithic `template_selector.py` (legacy wrapper retained for imports)
- Hierarchical folder navigation with breadcrumb & Backspace up-navigation
- Recursive content-aware search (path, title, placeholders, template body) with optional non-recursive filter
- Instant inline filtering while typing; search box gains initial focus & supports Arrow keys + Enter selection
- Multi-select mode producing a synthetic combined template (id -1) via Finish Multi
- Preview window (button or Ctrl+P) plus toggle; Ctrl+P reuses/ closes existing preview
- Quick shortcuts: `s` focus search box, Backspace (up), Enter (open/select), Ctrl+P (preview), arrow keys in search entry
- Keyboard-first workflow: immediate focus + multiple delayed focus attempts for WM compatibility

### Overrides & Placeholders
- Per-template file path & skip decisions persisted locally and mirrored to `prompts/styles/Settings/settings.json` (two-way sync)
- Manage Overrides dialog (GUI Options menu) to inspect & remove individual entries
- Simplified file placeholder UX; removed legacy global skip flag

### Template System
- Recursive discovery of nested template folders (CLI & GUI)
- Content index built lazily for fast repeated searches
- Multi-template synthesis leaves original templates untouched

### Documentation
- README expanded with selector features, keyboard shortcuts, multi-select, recursive search
- HOTKEYS guide updated with GUI selector cheat sheet
- CODEBASE_REFERENCE updated for modular selector architecture & feature matrix

### Internal / Maintenance
- Introduced `BrowserState` abstraction with lazy recursive index
- Thin wrapper left at `gui/template_selector.py` for backward compatibility
- Added preview toggle logic & improved focus handling

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
