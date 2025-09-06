#!/usr/bin/env bash
set -euo pipefail

###############
# PARAMETERS  #
###############
# Package name and initial version. You may adjust these.
PACKAGE_NAME="${PACKAGE_NAME:-your-pa}"
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

# Optional, but helpful for path conversions:
require_cmd wslpath

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

# _manifest.yml
MANIFEST="$PKG_DIR/_manifest.yml"
if [ ! -f "$MANIFEST" ]; then
  info "Creating _manifest.yml"
  cat > "$MANIFEST" <<YAML
name: ${PACKAGE_NAME}
title: ${PACKAGE_NAME} Snippets
version: ${INITIAL_VERSION}
author: Your Name
description: Unified Espanso snippets managed in the prompt-automation repo.
homepage: ${REPO_URL:-https://example.com}
YAML
else
  info "_manifest.yml exists; leaving as-is."
fi

# package.yml
PKG_YML="$PKG_DIR/package.yml"
if [ ! -f "$PKG_YML" ]; then
  info "Creating package.yml"
  cat > "$PKG_YML" <<'YAML'
# Global defaults can live here; matches typically live in match/*.yml
matches: []
YAML
else
  info "package.yml exists; leaving as-is."
fi

#############################################
# COPY CURRENT WINDOWS ESPANSO base.yml      #
#############################################
info "Discovering Windows %APPDATA% path via PowerShell..."
# Use PowerShell to get APPDATA and expand to a Windows path string.
WIN_APPDATA="$(powershell.exe -NoProfile -Command '[Environment]::GetFolderPath("ApplicationData")' | tr -d '\r')"
if [ -z "$WIN_APPDATA" ]; then
  warn "Could not resolve %APPDATA% from PowerShell. Skipping base.yml copy."
else
  info "Windows APPDATA: $WIN_APPDATA"
  # Convert to WSL path
  WSL_APPDATA="$(wslpath "$WIN_APPDATA")"
  WIN_BASE_YML="$WIN_APPDATA\\espanso\\match\\base.yml"
  WSL_BASE_YML="$(wslpath "$WIN_BASE_YML" 2>/dev/null || true)"

  if [ -n "$WSL_BASE_YML" ] && [ -f "$WSL_BASE_YML" ]; then
    info "Found existing Windows Espanso base.yml at: $WSL_BASE_YML"
    TARGET_BASE="$MATCH_DIR/base.yml"

    # If target exists, back it up once
    if [ -f "$TARGET_BASE" ]; then
      cp -f "$TARGET_BASE" "$TARGET_BASE.bak.$(date +%s)"
      info "Backed up existing $TARGET_BASE -> $TARGET_BASE.bak.*"
    fi

    cp -f "$WSL_BASE_YML" "$TARGET_BASE"
    info "Copied Windows base.yml into repo: $TARGET_BASE"
  else
    warn "No Windows base.yml found at %APPDATA%\\espanso\\match\\base.yml. You can add snippets later under $MATCH_DIR/"
  fi
fi

#############################################
# MIRROR TO EXTERNAL-REPO LAYOUT FOR INSTALL #
#############################################
# Espanso expects packages/<name>/<version> with _manifest.yml, package.yml, README.md
CURRENT_VERSION="$INITIAL_VERSION"
if [ -f "$MANIFEST" ]; then
  # read version from manifest if present
  if awk '/^version:[[:space:]]*[0-9]+\.[0-9]+\.[0-9]+/ {print $2; found=1} END{exit found?0:1}' "$MANIFEST" >/dev/null 2>&1; then
    CURRENT_VERSION="$(awk '/^version:[[:space:]]*[0-9]+\.[0-9]+\.[0-9]+/ {print $2; exit}' "$MANIFEST")"
  fi
fi

EXT_PKG_DIR="$REPO_ROOT/packages/$PACKAGE_NAME/$CURRENT_VERSION"
info "Syncing package to external repo layout at: $EXT_PKG_DIR"
mkdir -p "$EXT_PKG_DIR/match"
cp -f "$MANIFEST" "$EXT_PKG_DIR/_manifest.yml"
cp -f "$PKG_YML" "$EXT_PKG_DIR/package.yml"
if [ -d "$MATCH_DIR" ]; then
  cp -rf "$MATCH_DIR/"* "$EXT_PKG_DIR/match/" 2>/dev/null || true
fi
if [ ! -f "$EXT_PKG_DIR/README.md" ]; then
  cat > "$EXT_PKG_DIR/README.md" <<EOF
# ${PACKAGE_NAME}

This is an external Espanso package mirrored from the prompt-automation repository.

- Matches live in match/*.yml
- Metadata is in _manifest.yml

EOF
fi

##################################
# OPTIONAL: VERSION BUMP LOGIC   #
##################################
if [ "$BUMP_VERSION" = "true" ]; then
  info "Bumping patch version in _manifest.yml"
  if ! yaml_bump_patch_version "$MANIFEST"; then
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
