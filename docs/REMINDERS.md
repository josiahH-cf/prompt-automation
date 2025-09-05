Reminders Schema and Usage
==========================

Overview
--------
Reminders are short, read‑only instructional strings you declare in JSON to help users remember important constraints or tips while filling placeholders.

Where to Declare
----------------
- Template root: add `"reminders": ["…"]` to a template JSON.
- Placeholder-level: add `"reminders": ["…"]` to any placeholder object.
- Global defaults: add `global_placeholders.reminders` in `prompts/styles/globals.json`.

Behavior
--------
- GUI
  - Inline: Placeholder reminders render beneath the input with muted styling.
  - Collapsible panel: Template/global reminders appear in a top panel; expanded on first open per session; toggle remembered for the session.
- CLI
  - During variable collection: template/global reminders print once before the first prompt; placeholder reminders print before each placeholder.
  - One‑shot inspection: `prompt-automation --terminal --show-reminders` lets you select a template and prints its reminders without prompting for values.
- Read‑only: No editing at runtime; sourced from JSON only.

Schema Snippets
---------------
Template root and placeholders:

```jsonc
{
  "id": 123,
  "title": "Demo",
  "reminders": [
    "Keep responses concise",
    "Cite sources when possible"
  ],
  "placeholders": [
    { "name": "summary", "multiline": true, "reminders": ["Bullet points", "≤ 5 lines"] },
    { "name": "severity", "type": "options", "options": ["low","medium","high"], "reminders": ["Default: medium"] }
  ]
}
```

Global defaults (`prompts/styles/globals.json`):

```jsonc
{
  "global_placeholders": {
    "reminders": [
      "Verify numerical assumptions",
      "List uncertainties explicitly"
    ]
  }
}
```

Feature Flags
-------------
- Enable/disable: `PROMPT_AUTOMATION_REMINDERS=1|0` or `Settings/settings.json: { "reminders_enabled": true|false }`.
- Dev timing: `PROMPT_AUTOMATION_REMINDERS_TIMING=1` logs a single `reminders.timing_ms` entry.

Notes
-----
- Large strings are truncated to 500 chars; max 25 reminders per scope.
- Deduplication removes placeholder reminders that duplicate template/global items.
- Observability: one `reminders.summary` log per template load (counts only; no content).

