#!/bin/bash
# Stop hook: autosave the active session so progress is never lost when a turn
# ends. ADVISORY ONLY — never blocks; always exits 0.
set +e

DIR="${CLAUDE_PROJECT_DIR:-.}"
cd "$DIR" 2>/dev/null || exit 0

if [ -f world-state/active-campaign.txt ]; then
    bash tools/gm-session.sh save autosave >/dev/null 2>&1
fi

exit 0
