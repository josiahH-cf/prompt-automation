# Uninstall

The uninstaller removes Prompt Automation and related artifacts. It is
enabled by default but can be disabled by setting the
`UNINSTALL_FEATURE_FLAG` environment variable to ``0``. When disabled, any
import of the uninstall module or CLI invocation of ``uninstall`` prints a
message and exits with code ``1``.

## Usage

```bash
prompt-automation uninstall [options]
```

The command also accepts the alias `remove`. To explicitly disable the
command, run with ``UNINSTALL_FEATURE_FLAG=0``.

## Options

- `--all` – remove all detected components
- `--dry-run` – preview actions without executing them
- `--force` – force removal even if components appear in use
- `--purge-data` – delete configuration, cache and log data
- `--keep-user-data` – preserve user data while removing other components
- `--no-backup` – skip automatic backup when purging data
- `--non-interactive` – run without confirmation prompts
- `--verbose` – increase output verbosity
- `--json` – emit a JSON summary of results
- `--platform PLATFORM` – override the target platform for testing

## Behavior

Detected components include the pip installation, editable checkouts, the
Espanso package, systemd units, desktop entries, wrapper scripts and local
configuration directories. Unless `--non-interactive` or `--force` is used,
a confirmation is requested before removing each artifact. When purging data,
files are backed up to `~/.config/prompt-automation.backup.<timestamp>` unless
`--no-backup` is provided. The `--dry-run` flag prints the planned actions
without making changes.

## Exit Codes

- `0` – all requested removals succeeded
- `1` – invalid options (e.g. incompatible flags)
- `2` – a removal operation failed or was skipped

