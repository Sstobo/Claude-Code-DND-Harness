#!/bin/bash
# gm-combat.sh - Persisted, adjudicated combat. The engine owns the arithmetic.
#
#   THE RAIL:  cast -> order -> round -> swing -> down -> clear
#
#   gm-combat.sh start [--pc]        # --pc rolls the active PC into the order
#   gm-combat.sh join "Anselm" 24 --ac 16 --dex 12 [--side ally|pc] [--init N]
#   gm-combat.sh add-enemy "Orc Warrior" 22 --ac 17
#
#   An SRD creature goes in as its FETCHED stat block — never retyped numbers.
#   Fetch the FULL block, not --combat: the condensed view drops attack_bonus and
#   damage, so a creature added from it cannot swing.
#     uv run python features/dnd-api/monsters/dnd_monster.py goblin > /tmp/gob.json
#     gm-combat.sh add-enemy --stat-block-file /tmp/gob.json
#     gm-combat.sh add-enemy --stat-block "$(cat /tmp/gob.json)"   # or inline JSON
#   AC/HP/XP/CR/actions land on the record as fetched; --ac/--init/a name still
#   override (a scaled elite, a named boss). Initiative is ROLLED (1d20+DEX)
#   unless --init is given.
#
#   ATTACKS RESOLVE HERE, NEVER IN YOUR HEAD:
#     gm-combat.sh attack "Goblin" --at "Kordan" --with "Scimitar"
#     gm-combat.sh attack "Kordan" --at "Goblin" --bonus 8 --damage "2d6+4" \
#         --from "strength:4" --from "proficiency:3" --from "the greatsword:1"
#   Enemy to-hit/damage come off the stored block; the PC's come from the sheet
#   and must be attributed with --from. Add --adv / --dis. Prints the staged
#   block (target first, pause, verdict) — paste it into narration as it stands.
#
#   gm-combat.sh death-save "Kordan"   # DC 10 flat, tally persists
#   gm-combat.sh hp "Orc Warrior" -5   # damage outside an attack (spell, fall)
#   gm-combat.sh condition "Orc Warrior" add prone
#   gm-combat.sh next-turn
#   gm-combat.sh header                # the order, HP, conditions, death saves
#   gm-combat.sh end                   # xp_awarded, defeated, down, ally_hp
#
# A hero at 0 HP is dying (death saves); a monster at 0 is dead. The PC's HP is
# mirrored to character.json as it changes — `end` clears the combat state.
#
# Add --json to any command for a structured envelope.

source "$(dirname "$0")/common.sh"

require_active_campaign

$PYTHON_CMD "$LIB_DIR/combat_manager.py" "$@"
