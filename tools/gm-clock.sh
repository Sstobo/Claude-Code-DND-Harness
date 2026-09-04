#!/bin/bash
# gm-clock.sh - Threat clocks (thin wrapper for threat_clocks.py)
#
#   gm-clock.sh list                          Show all clocks
#   gm-clock.sh add "Name" 6 [--on time|event] [--consequence "..."] [--linked-plot "..."]
#                                             New clock with N segments; the
#                                             consequence fires into the world when it fills
#   gm-clock.sh advance "Name" [--ticks 2]    Advance one clock by hand
#   gm-clock.sh tick-time                     Advance all time-clocks (auto-run by gm-time.sh)
#   gm-clock.sh beats                         Filled clocks = dramatic beats due
#   gm-clock.sh remove "Name"                 Remove a clock
#   gm-clock.sh choose "prompt" "fork" [--trigger ...]  Record a dramatic-choice fork
#
# All commands accept --json.

source "$(dirname "$0")/common.sh"

if [ $# -eq 0 ] || [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    cat <<'EOF'
Usage: gm-clock.sh <action> [args]

Named pressure. A clock fills toward a beat; time-clocks advance on gm-time.sh,
event-clocks by hand.

  add <name> <segments> [--on time|event] [--consequence "..."] [--linked-plot "<plot>"]
  advance <name> [--ticks N]       Move an event-clock by hand
  tick-time [--ticks N]            Advance every time-clock (gm-time.sh does this)
  list                             Every clock and where it stands
  beats                            Full clocks = beats due now
  choose "<prompt>" "<chosen>" [--trigger T --trigger-type on_npc|on_location|on_time|on_event --match M]
                                   Record a dramatic-choice fork as a consequence
  remove <name>

Examples:
  gm-clock.sh add "The Butcher hunts" 4 --on time --linked-plot "The Stairs"
  gm-clock.sh advance "The Butcher hunts"
  gm-clock.sh choose "Fight or flee?" "fight"
EOF
    exit 0
fi

require_active_campaign

$PYTHON_CMD "$LIB_DIR/threat_clocks.py" "$@"
