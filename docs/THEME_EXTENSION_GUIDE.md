# Theme Extension Guide

This project ships with two built-in themes: `light` (default) and `dark` (accessible, low-glare).
You can add more themes without touching code by dropping JSON definitions in your prompts folder.

## Where themes live

User-editable settings are stored under your prompts directory:

```
<PROMPTS_DIR>/Settings/
```

Create a `themes` subfolder and add JSON files there (one per theme):

```
<PROMPTS_DIR>/Settings/themes/my-theme.json
```

## Theme JSON schema

Each theme defines a set of semantic tokens:

```
{
  "name": "ocean",
  "background": "#0F131A",
  "surface": "#151B23",
  "surfaceAlt": "#10161E",
  "border": "#2C3542",
  "divider": "#2A3340",
  "textPrimary": "#E6ECF3",
  "textSecondary": "#B7C3CF",
  "textMuted": "#8FA0B0",
  "accentPrimary": "#58B2D6",
  "accentHover": "#79C6E6",
  "success": "#4CC38A",
  "warning": "#FFB757",
  "error": "#E5484D",
  "info": "#7AA7FF",
  "selectionBackground": "#264765",
  "selectionForeground": "#F7FAFF",
  "focusOutline": "#6CA4FF"
}
```

Tokens are applied to the GUI via Tk’s option database, so keep colors readable and balanced. Avoid pure black/white for comfort.

## Registering programmatically

Advanced users can register a theme from Python:

```python
from prompt_automation.theme import register_theme
register_theme('ocean', tokens_dict)
```

## Accessibility

Ensure WCAG AA compliance for normal text (contrast ratio ≥ 4.5:1) between `textPrimary` and both `background` and `surface`, and between `selectionForeground` and `selectionBackground`.
Use `prompt_automation.theme.contrast_ratio(fg, bg)` to verify.

## Fallbacks and safety

- Invalid or missing themes fall back to `light` with a warning in logs.
- Theme names are sanitized; stick to `[A-Za-z0-9_-]`.
- No code is executed from theme files; only JSON is parsed.

