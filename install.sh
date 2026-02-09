#!/usr/bin/env bash
# resumeX - Cursor Installation Script
# Usage: Run from your PROJECT ROOT directory
#
#   git clone https://github.com/sputnicyoji/resumeX .cursor/skills/resumex
#   bash .cursor/skills/resumex/install.sh
#

set -e

# Detect skill root (where this script lives)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$SCRIPT_DIR"

# Detect project root (3 levels up: .cursor/skills/resumex/)
PROJECT_ROOT="$(cd "$SKILL_ROOT/../../.." && pwd)"

# Verify we're in the right place
RELATIVE_PATH="${SKILL_ROOT#$PROJECT_ROOT/}"
EXPECTED_PATH=".cursor/skills/resumex"

if [ "$RELATIVE_PATH" != "$EXPECTED_PATH" ]; then
    echo "[ERROR] Skill must be cloned to .cursor/skills/resumex/"
    echo "  Expected: <project>/$EXPECTED_PATH"
    echo "  Actual:   $SKILL_ROOT"
    echo ""
    echo "Fix: git clone https://github.com/sputnicyoji/resumeX .cursor/skills/resumex"
    exit 1
fi

# Create .cursor/rules/ if not exists
RULES_DIR="$PROJECT_ROOT/.cursor/rules"
mkdir -p "$RULES_DIR"
echo "[OK] Rules directory ready: .cursor/rules/"

# Copy .mdc to rules directory
MDC_SOURCE="$SKILL_ROOT/cursor/resumex.mdc"
MDC_TARGET="$RULES_DIR/resumex.mdc"

if [ ! -f "$MDC_SOURCE" ]; then
    echo "[ERROR] .mdc file not found: $MDC_SOURCE"
    exit 1
fi

cp "$MDC_SOURCE" "$MDC_TARGET"
echo "[OK] Installed .mdc -> .cursor/rules/resumex.mdc"

# Verify Python available
PYTHON_CMD=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        PYTHON_CMD="$cmd"
        break
    fi
done

if [ -n "$PYTHON_CMD" ]; then
    echo "[OK] Python found: $PYTHON_CMD"
else
    echo "[WARN] Python not found. Pipeline (scripts/pipeline.py) requires Python 3.8+"
fi

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Skill root:  .cursor/skills/resumex/"
echo "Cursor rule: .cursor/rules/resumex.mdc"
echo ""
echo "Usage in Cursor: Ask the AI to extract structured information from any resume."
echo "The rule will be automatically loaded when relevant."
