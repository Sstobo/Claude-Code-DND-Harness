#!/bin/bash
# gm-combat.sh - Persisted combat state (optional; for fights worth tracking)
#
#   gm-combat.sh start
#   gm-combat.sh add-enemy "Orc Warrior" 22 --ac 17 --init 12
#
#   An SRD creature goes in as its FETCHED stat block — never retyped numbers:
#     uv run python features/dnd-api/monsters/dnd_monster.py goblin > /tmp/gob.json
#     gm-combat.sh add-enemy --stat-block-file /tmp/gob.json --init 14
#     gm-combat.sh add-enemy --stat-block "$(cat /tmp/gob.json)"   # or inline JSON
#   AC/HP/XP/CR/actions land on the record as fetched; --ac/--init/a name still
#   override (a scaled elite, a named boss). `end` reports xp_awarded from the
#   stored fetched XP — award that with gm-player.sh xp.
#
#   gm-combat.sh hp "Orc Warrior" -5
#   gm-combat.sh condition "Orc Warrior" add prone
#   gm-combat.sh next-turn
#   gm-combat.sh header        # render the combat header
#   gm-combat.sh end           # clear state (award XP/loot via gm-player afterwards)
#
# Add --json to any command for a structured envelope.

source "$(dirname "$0")/common.sh"

require_active_campaign

$PYTHON_CMD "$LIB_DIR/combat_manager.py" "$@"
