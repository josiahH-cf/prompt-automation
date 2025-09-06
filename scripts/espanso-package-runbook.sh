#!/usr/bin/env bash
set -euo pipefail

###############
# PARAMETERS  #
###############
# Package name and initial version. You may adjust these.
PACKAGE_NAME="${PACKAGE_NAME:-prompt-automation}"
INITIAL_VERSION="${INITIAL_VERSION:-0.1.0}"

# If you want to force a version bump on every run, set to "true".
BUMP_VERSION="${BUMP_VERSION:-false}"

########################
# HELPER SUBROUTINES   #
########################
info(){ printf "\n\033[1;34m[INFO]\033[0m %s\n" "$*"; }
warn(){ printf "\n\033[1;33m[WARN]\033[0m %s\n" "$*"; }
err(){  printf "\n\033[1;31m[ERR]\033[0m %s\n"  "$*" >&2; }

require_cmd(){
  command -v "$1" >/dev/null 2>&1 || { err "Missing command: $1"; exit 1; }
}

yaml_bump_patch_version(){
  # Bumps 'version: x.y.z' to 'x.y.(z+1)' in-place for provided file.
  local file="$1"
  if ! grep -qE '^version:\s*[0-9]+\.[0-9]+\.[0-9]+' "$file"; then
    warn "No semantic version found in $file. Skipping bump."
    return 0
  fi
  awk '
    BEGIN{bumped=0}
    /^version:[[:space:]]*[0-9]+\.[0-9]+\.[0-9]+/{
      split($2, v, "."); v[3]=v[3]+1;
      printf("version: %d.%d.%d\n", v[1], v[2], v[3]); bumped=1; next
    }
    {print}
    END{if (bumped==0) exit 1}
  ' "$file" > "$file.tmp" && mv "$file.tmp" "$file"
}

#####################
# PREREQUISITES     #
#####################
info "Checking required tools..."
require_cmd git
require_cmd awk
require_cmd sed
require_cmd powershell.exe

# Optional, but helpful for path conversions (WSL dev flow):
if ! command -v wslpath >/dev/null 2>&1; then
  warn "wslpath not found; Windows path mirroring will be skipped."
fi

#####################
# REPO DISCOVERY    #
#####################
info "Locating repository root..."
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [ -z "${REPO_ROOT}" ]; then
  err "Not inside a Git repo. Please cd into the prompt-automation repository and re-run."
  exit 1
fi
cd "$REPO_ROOT"

# Determine remote URL
REPO_URL="$(git remote get-url origin 2>/dev/null || true)"
if [ -z "${REPO_URL}" ]; then
  warn "No 'origin' remote found. You can set it later. Continuing without it."
fi
info "Repo root: $REPO_ROOT"
info "Origin URL: ${REPO_URL:-<none>}"

##########################################
# CREATE ESPANSO PACKAGE SKELETON        #
##########################################
PKG_DIR="$REPO_ROOT/espanso-package"
MATCH_DIR="$PKG_DIR/match"
mkdir -p "$MATCH_DIR"

# package.yml
PKG_YML="$PKG_DIR/package.yml"
if [ ! -f "$PKG_YML" ]; then
  info "Creating package.yml"
  cat > "$PKG_YML" <<'YAML'
name: prompt-automation
dependencies: []
YAML
else
  info "package.yml exists; leaving as-is."
fi

# Ensure a source manifest exists (canonical version lives here)
SRC_MANIFEST="$PKG_DIR/_manifest.yml"
if [ ! -f "$SRC_MANIFEST" ]; then
  info "Creating espanso-package/_manifest.yml"
  cat > "$SRC_MANIFEST" <<YAML
name: ${PACKAGE_NAME}
title: "Prompt-Automation Snippets"
version: ${INITIAL_VERSION}
description: "Prompt-Automation Espanso snippets packaged for team-wide installation"
author: "Prompt-Automation Team"
homepage: ${REPO_URL:-https://github.com/josiahH-cf/prompt-automation}
license: MIT
YAML
fi

# If manifest exists, prefer its 'name' for PACKAGE_NAME
if [ -f "$SRC_MANIFEST" ]; then
  MF_NAME="$(awk '/^name:[[:space:]]*/{print $2; exit}' "$SRC_MANIFEST" 2>/dev/null || true)"
  if [ -n "$MF_NAME" ]; then
    PACKAGE_NAME="$MF_NAME"
  fi
fi

#############################################
# COPY CURRENT WINDOWS ESPANSO base.yml      #
#############################################
info "Discovering Windows %APPDATA% path via PowerShell..."
# Use PowerShell to get APPDATA and expand to a Windows path string.
WIN_APPDATA="$(powershell.exe -NoProfile -Command '[Environment]::GetFolderPath("ApplicationData")' | tr -d '\r')"
if [ -z "$WIN_APPDATA" ] || ! command -v wslpath >/dev/null 2>&1; then
  warn "Could not resolve %APPDATA% or wslpath unavailable. Skipping Windows seed copy."
else
  info "Windows APPDATA: $WIN_APPDATA"
  WIN_MATCH_DIR="$WIN_APPDATA\\espanso\\match"
  # Copy all *.yml files from Windows match dir into repo (seed)
  info "Seeding repo from Windows match dir: $WIN_MATCH_DIR"
  mapfile -t WIN_FILES < <(powershell.exe -NoProfile -Command "Get-ChildItem -Path '$WIN_MATCH_DIR' -Filter *.yml -File | %% { $_.FullName }" | tr -d '\r')
  for wf in "${WIN_FILES[@]}"; do
    [ -z "$wf" ] && continue
    WSL_FILE="$(wslpath "$wf" 2>/dev/null || true)"
    [ -z "$WSL_FILE" ] && continue
    base="$(basename "$WSL_FILE")"
    src="$WSL_FILE"
    dst="$MATCH_DIR/$base"
    if [ -f "$dst" ]; then
      cp -f "$dst" "$dst.bak.$(date +%s)"
    fi
    cp -f "$src" "$dst"
    info "Copied: $base"
  done
fi

#############################################
# MIRROR TO EXTERNAL-REPO LAYOUT FOR INSTALL #
#############################################
# Espanso expects packages/<name>/<version> with _manifest.yml, package.yml, README.md

# Determine CURRENT_VERSION from external layout if available, else INITIAL_VERSION
find_latest_version_dir(){
  local base="$1"; [ -d "$base" ] || return 1
  ls -1 "$base" 2>/dev/null | grep -E '^[0-9]+\.[0-9]+\.[0-9]+$' | sort -V | tail -n1
}

EXT_BASE="$REPO_ROOT/packages/$PACKAGE_NAME"

# Discover version from source manifest
SRC_VERSION="$(awk '/^version:[[:space:]]*/{print $2; exit}' "$SRC_MANIFEST" 2>/dev/null || true)"
if [ -z "$SRC_VERSION" ]; then
  warn "Could not read version from $SRC_MANIFEST; defaulting to $INITIAL_VERSION"
  SRC_VERSION="$INITIAL_VERSION"
fi

CURRENT_VERSION="$SRC_VERSION"

EXT_PKG_DIR="$EXT_BASE/$CURRENT_VERSION"
info "Syncing package to external repo layout at: $EXT_PKG_DIR"
mkdir -p "$EXT_PKG_DIR/match"

# Ensure external manifest exists and is correct; create if missing
EXT_MANIFEST="$EXT_PKG_DIR/_manifest.yml"
info "Writing external _manifest.yml"
cat > "$EXT_MANIFEST" <<YAML
$(cat "$SRC_MANIFEST")
YAML

# Copy package.yml and match files into external layout
cp -f "$PKG_YML" "$EXT_PKG_DIR/package.yml"
if [ -d "$MATCH_DIR" ]; then
  cp -rf "$MATCH_DIR/"* "$EXT_PKG_DIR/match/" 2>/dev/null || true
fi
if [ ! -f "$EXT_PKG_DIR/README.md" ]; then
  cat > "$EXT_PKG_DIR/README.md" <<EOF
# ${PACKAGE_NAME}

External Espanso package mirrored from the prompt-automation repository.

- Matches live in match/*.yml
- Metadata is in _manifest.yml

EOF
fi

##################################
# VALIDATE (pytest espanso tests) #
##################################
if command -v pytest >/dev/null 2>&1; then
  info "Running espanso tests (pytest tests/espanso)"
  if ! pytest -q tests/espanso; then
    err "Espanso tests failed. Fix YAML or duplicates and re-run."
    exit 1
  fi
else
  warn "pytest not found; skipping test run."
fi

##################################
# OPTIONAL: VERSION BUMP LOGIC   #
##################################
if [ "$BUMP_VERSION" = "true" ]; then
  info "Bumping patch version in source manifest"
  if yaml_bump_patch_version "$SRC_MANIFEST"; then
    NEW_VERSION="$(awk '/^version:[[:space:]]*[0-9]+\.[0-9]+\.[0-9]+/ {print $2; exit}' "$SRC_MANIFEST")"
    if [ "$NEW_VERSION" != "$CURRENT_VERSION" ]; then
      info "Detected new source version: $NEW_VERSION"
      EXT_PKG_DIR="$EXT_BASE/$NEW_VERSION"
      mkdir -p "$EXT_PKG_DIR/match"
      # Rewrite external manifest from updated source
      cat "$SRC_MANIFEST" > "$EXT_PKG_DIR/_manifest.yml"
      cp -f "$PKG_YML" "$EXT_PKG_DIR/package.yml"
      cp -rf "$MATCH_DIR/"* "$EXT_PKG_DIR/match/" 2>/dev/null || true
    fi
  else
    warn "Automatic bump failed or not applicable; keeping version as-is."
  fi
fi

##############################
# GIT COMMIT & PUSH          #
##############################
# Only commit if there are changes
if ! git diff --quiet || ! git diff --cached --quiet; then
  info "Committing changes..."
  git add espanso-package packages scripts/espanso-package-runbook.sh .github/workflows/espanso-package.yml docs/ESPANSO_PACKAGE.md tests/espanso || true
  git commit -m "chore(espanso): add/update package and external layout"
  if [ -n "${REPO_URL:-}" ]; then
    info "Pushing to origin..."
    git push
  else
    warn "No origin set; skipping push."
  fi
else
  info "No changes detected; skipping commit."
fi

#####################################################
# INSTALL/UPDATE PACKAGE INTO WINDOWS ESPANSO       #
#####################################################
# Function to run a PowerShell command from WSL and surface errors.
run_ps(){
  powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$1"
}

info "Ensuring Espanso service is registered and running on Windows..."
run_ps 'espanso --version' || { err "Espanso not available on Windows PATH. Install Espanso on Windows and re-run."; exit 1; }
run_ps 'espanso service register' || true
run_ps 'espanso start' || true

# Install or update the package from the Git repo
if [ -n "${REPO_URL:-}" ]; then
  info "Attempting to install/update package '${PACKAGE_NAME}' from ${REPO_URL} ..."
  # Try install; if it fails because it exists, do update.
  if ! run_ps "espanso package install ${PACKAGE_NAME} --git ${REPO_URL} --external"; then
    warn "Install may already exist; attempting update instead."
    run_ps "espanso package update ${PACKAGE_NAME}" || true
  fi
else
  warn "No repo URL available; skipping package install/update."
fi

info "Restarting Espanso..."
run_ps 'espanso restart' || true
run_ps 'espanso status' || true

##########################################
# FINAL HINTS / NEXT STEPS               #
##########################################
cat <<'NOTE'

Done.

NEXT:
- Validate triggers in a Windows text field (e.g., Notepad) once you migrate/confirm snippets under espanso-package/match/.
- On future changes:
    1) Edit files in espanso-package/match/
    2) Bump version in espanso-package/_manifest.yml (MAJOR.MINOR.PATCH)
    3) git commit && git push
    4) powershell: espanso package update '"'"$PACKAGE_NAME"'"' ; espanso restart

If you previously relied on %APPDATA%\espanso\match\base.yml, your content has been copied into the repo under espanso-package/match/base.yml.
NOTE
