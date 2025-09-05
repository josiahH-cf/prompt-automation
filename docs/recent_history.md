Recent History

Overview
- Stores the last N (default 5) successful template executions to `~/.prompt-automation/recent-history.json`.
- Accessible via GUI Options → Recent history, with preview + Copy action.
- Non-intrusive: CLI/GUI flows unchanged except for appending after success.

Data Shape
- JSON object with `schema_version: 1`, `limit`, and `entries` (newest→oldest).
- Entry fields: `entry_id` (uuid4), `template_id`, `title`, `ts` (UTC ISO), `rendered`, `output`.
- Redaction applied at write time using configured regex patterns.

Configuration
- Enable/disable: env `PROMPT_AUTOMATION_HISTORY` or `Settings/settings.json: recent_history_enabled` (default true).
- Purge on disable: env `PROMPT_AUTOMATION_HISTORY_PURGE_ON_DISABLE` or `recent_history_purge_on_disable` (default false).
- Redaction patterns: env `PROMPT_AUTOMATION_HISTORY_REDACTION_PATTERNS` (JSON array or comma-separated regexes) or settings key `recent_history_redaction_patterns`.

Reliability
- Atomic writes (temp+rename), defensive load, corrupt file quarantine (renamed to `recent-history.corrupt-<ts>`).
- Append rotation maintains cap; oldest discarded on overflow.

Privacy/Observability
- No raw content in INFO logs; DEBUG includes SHA-256 fingerprint prefixes only.

