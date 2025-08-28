Single-Window GUI: Formatting, Reference Picker, Scroll
======================================================

Overview
--------
- Bullet/checklist formatting is restored for multiline placeholders that declare `"format": "bullet"` or `"format": "checklist"`.
- The Reference File picker appears only if the active template includes a `reference_file` placeholder and is rendered inline beneath that field.
- Focus changes auto-scroll the collection form so the focused widget is fully visible (Tab/Shift+Tab and mouse focus).

How To Use
----------
- Declare list formatting in templates:
  - Bullet: `{ "name": "notes", "multiline": true, "format": "bullet" }`
  - Checklist: `{ "name": "tasks", "multiline": true, "format": "checklist" }`
- Reference picker:
  - Include `{ "name": "reference_file", "type": "file", "label": "Reference File" }` to show the inline global picker below this field.
  - The inline picker supports Browse/View and persists the global path across sessions.

Behavior Details
----------------
- Bullets: Press Enter after a line starting with `- <text>` inserts a new line prefilled with `- `. Pressing Enter on a blank `- ` line does not insert another dash.
- Checklist: Enter after `- [ ] <text>` inserts `- [ ] ` on the next line. Enter on a blank `- [ ] ` line does not insert another marker.
- Scroll: When focus moves to a control outside the current viewport, the form scrolls just enough to reveal the full control with minimal movement.

Debug Logging
-------------
Enable debug-level logs using your preferred logging configuration; the following keys are emitted at debug level:
- `bullet_insert` (extra: `format`, `inserted`)
- `inline_reference_ui` (extra: `template_id`)
- `scroll_adjust` (extra: `delta`, `widget_top`, `widget_bottom`)

Rollback / Feature Flag
-----------------------
Set `PA_DISABLE_SINGLE_WINDOW_FORMATTING_FIX=1` to disable the new behaviors:
- Disables bullet/checklist return-key insertion.
- Disables focus-based auto-scroll.
- Restores the legacy global Reference File picker in the top toolbar.

Review Auto-Open Toggle
-----------------------
The Review window auto-opens the reference viewer once when a `reference_file` value is present.
- Disable this auto-open via `PA_REVIEW_AUTO_OPEN_REFERENCE=0` (the "View Reference" button remains available).

Windows Global Hotkey (Ctrl+Shift+J)
------------------------------------
- Default hotkey: `Ctrl+Shift+J` focuses or launches the GUI.
- Generated script path (Windows Startup): `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\prompt-automation.ahk`
- Status check: `prompt-automation --hotkey-status` shows whether the script exists and the current hotkey.
- Enable verbose logs: set `PROMPT_AUTOMATION_DEBUG=1` and run `prompt-automation --assign-hotkey` or `prompt-automation --hotkey-status` to see `hotkey_registration_*` messages.
- CLI event logs: with `PROMPT_AUTOMATION_DEBUG=1`, invoking `prompt-automation --focus` writes `hotkey_event_received` and `hotkey_handler_invoked` entries to `~/.prompt-automation/logs/cli.log`.

Troubleshooting Checklist (Windows)
-----------------------------------
- Ensure AutoHotkey is installed and on PATH (`AutoHotkey` executable).
- Verify the Startup script exists at the path above; reassign via `prompt-automation --assign-hotkey` if missing.
- Conflicts: temporarily disable other global hotkey tools (e.g., Espanso, AHK scripts) that may capture `Ctrl+Shift+J`.
- Re-run with debug: set `PROMPT_AUTOMATION_DEBUG=1` and check for `hotkey_registration_success` and `hotkey_handler_invoked` logs.
- As a quick test, run `prompt-automation --focus`; if it logs focus and returns, the handler path is healthy.
