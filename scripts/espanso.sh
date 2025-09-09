#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PKG_DIR="$ROOT_DIR/espanso-package"

cmd=${1:-help}
shift || true

usage() {
  cat <<'EOF'
Usage: scripts/espanso.sh <command> [args]

Commands:
  lint                     Run YAML/duplicate-trigger tests (pytest tests/espanso)
  mirror                   Mirror source package to packages/<name>/<version>/ (uses runbook)
  update                   Update installed package and restart espanso (local machine)
  sync                     Validate, mirror, and install/update via CLI orchestrator; restart espanso
  add-snippet              Add a simple trigger/replace snippet to a match file
  disable-local-base       Backup and disable %APPDATA%\espanso\match\base.yml on Windows (via PowerShell)
  help                     Show this help

Examples:
  scripts/espanso.sh lint
  BUMP_VERSION=true scripts/espanso.sh mirror
  scripts/espanso.sh update
  PA_SKIP_INSTALL=1 scripts/espanso.sh sync    # dry-run style
  scripts/espanso.sh add-snippet --file base.yml --trigger :hello --replace "Hello"
EOF
}

case "$cmd" in
  lint)
    if command -v pytest >/dev/null 2>&1; then
      pytest -q tests/espanso
    else
      echo "pytest not found. Install dev deps to run tests." >&2
      exit 2
    fi
    ;;
  mirror)
    BUMP_VERSION="${BUMP_VERSION:-false}" bash "$ROOT_DIR/scripts/espanso-package-runbook.sh"
    ;;
  update)
    if command -v espanso >/dev/null 2>&1; then
      PKG_NAME=$(awk '/^name:[[:space:]]*/{print $2; exit}' "$PKG_DIR/_manifest.yml" 2>/dev/null || echo prompt-automation)
      espanso package update "$PKG_NAME" || true
      espanso restart || true
      espanso package list || true
    else
      echo "espanso not found on PATH. Install espanso first." >&2
      exit 1
    fi
    ;;
  sync)
    # Orchestrate full cycle using Python CLI. Prefer installed CLI if present; otherwise python -m fallback.
    AUTO_BUMP_ARG=${AUTO_BUMP_ARG:-}
    if [ -n "${PA_AUTO_BUMP:-}" ]; then AUTO_BUMP_ARG="--auto-bump $PA_AUTO_BUMP"; fi
    SKIP_ARG=""; if [ "${PA_SKIP_INSTALL:-}" = "1" ]; then SKIP_ARG="--skip-install"; fi
    if command -v prompt-automation >/dev/null 2>&1; then
      prompt-automation --espanso-sync ${SKIP_ARG} ${AUTO_BUMP_ARG}
    else
      PYTHONPATH="$ROOT_DIR/src" python3 -m prompt_automation.espanso_sync ${SKIP_ARG} ${AUTO_BUMP_ARG}
    fi
    ;;
  add-snippet)
    python3 "$ROOT_DIR/scripts/add_espanso_snippet.py" "$@"
    ;;
  disable-local-base)
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$ROOT_DIR/scripts/espanso-windows.ps1" -DisableLocalBase || true
    ;;
  help|*)
    usage
    ;;
esac
