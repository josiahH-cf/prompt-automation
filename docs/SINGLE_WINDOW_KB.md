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
