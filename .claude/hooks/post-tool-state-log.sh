#!/bin/bash
# Advisory PostToolUse hook: log state-writing tool calls so missed persists can
# be audited. ADVISORY ONLY — never blocks; always exits 0 even on any error.
set +e

DIR="${CLAUDE_PROJECT_DIR:-.}"
INPUT=$(cat 2>/dev/null)

# Best-effort extract of the bash command (no jq dependency).
CMD=$(printf '%s' "$INPUT" | python3 -c "import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('tool_input', {}).get('command', ''))
except Exception:
    print('')" 2>/dev/null)

case "$CMD" in
    *gm-player.sh*|*gm-npc.sh*|*gm-session.sh*move*|*gm-consequence.sh*add*|*gm-condition.sh*)
        mkdir -p "$DIR/.ship-it" 2>/dev/null
        printf '%s STATE-WRITE: %s\n' "$(date -u +%FT%TZ 2>/dev/null)" "$CMD" \
            >> "$DIR/.ship-it/state-writes.log" 2>/dev/null
        ;;
esac

# A --dc roll is a promise: the model committed to paste this exact staged block
# into narration (CLAUDE.md → Dice). This can't be enforced on the model's outgoing
# text (no hook inspects that), so it's logged instead — every rolled DC is provable
# after the fact, and a skipped block shows up as a roll with no matching narration.
case "$CMD" in
    *dice.py*--dc*)
        mkdir -p "$DIR/.ship-it" 2>/dev/null
        printf '%s DC-ROLL: %s\n' "$(date -u +%FT%TZ 2>/dev/null)" "$CMD" \
            >> "$DIR/.ship-it/dice-rolls.log" 2>/dev/null
        ;;
esac

exit 0
