# Todoist Integration (:ntsk)

This repository ships a Windows PowerShell script that creates a Todoist task from the `:ntsk` Espanso trigger.

- Script: `scripts/todoist_add.ps1`
- Trigger: `:ntsk` in `espanso-package/match/base.yml`

## How Espanso Calls the Script

- Espanso runs on Windows and invokes PowerShell via `cmd /C`.
- The command resolves the repository path using either:
  1) `PROMPT_AUTOMATION_REPO` (Windows env var), or
  2) `wsl.exe` + `wslpath` to convert a WSL Linux path to a Windows path. It probes `$PROMPT_AUTOMATION_REPO` inside WSL, falling back to `$HOME/github-cf/prompt-automation`.
- If neither resolution succeeds, the command errors with guidance to set the env var or place the repo at the default location.

Result: the final invocation always uses `powershell -File <repo>\scripts\todoist_add.ps1`.

## Token Management (No Secrets in Git)

The script loads the Todoist token with this precedence:

1) `TODOIST_API_TOKEN` environment variable (or a custom name via `TODOIST_TOKEN_ENV` to point at a different variable name).
2) Repo-local secrets file at `<repo>/local.secrets.psd1` with contents:

   ```powershell
   @{ TODOIST_API_TOKEN = '<YOUR_TOKEN>' }
   ```

   A template is provided: `local.secrets.psd1.example`. The real file `local.secrets.psd1` is gitignored.

3) If neither is available, the script fails with a clear, actionable error.

Security: The script never prints the token value and masks sources in logs.

## Usage and Behavior

- Only the “action” field is required. Optional fields (type, DoD, NRA) may be empty.
- The script derives the Todoist `content` from the provided summary (best effort to extract the action). If that fails, it uses the full summary string.
- If provided, the note/NRA becomes the Todoist `description`.

Dry-run options (no network call):

- Pass `-DryRun` to the script, or set `TODOIST_DRY_RUN=1` in the environment. Useful for tests and local smoke checks.

Kill-switch:

- Set `NTSK_DISABLE=1` to disable execution and no-op safely.

## Local Verification

1) Set `TODOIST_API_TOKEN` (Windows), or copy `local.secrets.psd1.example` to `local.secrets.psd1` and fill in your token.
2) Trigger `:ntsk` in any Windows app. Fill only “action” and leave other fields blank to validate minimal behavior.
3) For CI/dry-run, set `TODOIST_DRY_RUN=1` before invoking.

## Troubleshooting

- Repo path error: Set `PROMPT_AUTOMATION_REPO` (Windows) to the Windows path of the repo, or ensure the repo lives under WSL at `$HOME/github-cf/prompt-automation`.
- Token error: Ensure `TODOIST_API_TOKEN` is set or `local.secrets.psd1` exists with the proper key.
- No expansion: Run `espanso restart` and verify the package is installed and active.

