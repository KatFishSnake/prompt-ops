#!/bin/bash

# Package Claude, Codex, and Cursor sessions into a shared folder at repo root.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
OUTPUT_DIR="${1:-$REPO_ROOT/session-packages}"

CLAUDE_SCRIPT="${CLAUDE_SCRIPT:-$REPO_ROOT/dist/package-claude-sessions.sh}"
CODEX_SCRIPT="${CODEX_SCRIPT:-$REPO_ROOT/dist/package-codex-sessions.sh}"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"

mkdir -p "$OUTPUT_DIR"

echo "Using output directory: $OUTPUT_DIR"

claude_status=0
codex_status=0
ran_any=0

SANITIZED_REPO="$(echo "$REPO_ROOT" | sed 's|/|-|g; s|_|-|g; s|\.|-|g')"
CLAUDE_DIR="$HOME/.claude/projects/$SANITIZED_REPO"

if [ -d "$CLAUDE_DIR" ]; then
    ran_any=1
    if [ -x "$CLAUDE_SCRIPT" ]; then
        echo "Running Claude session packager..."
        "$CLAUDE_SCRIPT" "$OUTPUT_DIR" || claude_status=$?
    else
        echo "Claude sessions exist but packager is missing or not executable: $CLAUDE_SCRIPT"
        claude_status=127
    fi
else
    echo "Skipping Claude packaging (no sessions found for this repo)."
fi

if rg -q -F "\"cwd\":\"$REPO_ROOT\"" "$CODEX_HOME/sessions" 2>/dev/null; then
    ran_any=1
    if [ -x "$CODEX_SCRIPT" ]; then
        echo "Running Codex session packager..."
        "$CODEX_SCRIPT" "$OUTPUT_DIR" || codex_status=$?
    else
        echo "Codex sessions exist but packager is missing or not executable: $CODEX_SCRIPT"
        codex_status=127
    fi
else
    echo "Skipping Codex packaging (no sessions found for this repo)."
fi

if [ "$ran_any" -eq 0 ]; then
    echo "No sessions found for this repo. Nothing to package."
    exit 0
fi

if [ "$claude_status" -ne 0 ] || [ "$codex_status" -ne 0 ]; then
    echo "One or more packagers failed."
    if [ "$claude_status" -ne 0 ]; then
        echo "Claude packager failed with status $claude_status."
    fi
    if [ "$codex_status" -ne 0 ]; then
        echo "Codex packager failed with status $codex_status."
    fi
    exit 1
fi

echo "Done. Archives are in: $OUTPUT_DIR"
