#!/bin/bash
# gm-condition.sh - Player character condition tracking (thin wrapper for player_manager.py)
# Interface: gm-condition.sh add/remove/check <name> <condition>

source "$(dirname "$0")/common.sh"

if [ "$#" -lt 2 ]; then
    echo "Usage: gm-condition.sh <action> <character_name> [condition]"
    echo ""
    echo "Actions:"
    echo "  add <name> <condition>    - Add condition to character"
    echo "  remove <name> <condition> - Remove condition from character"
    echo "  check <name>              - Show current conditions"
    echo ""
    echo "Examples:"
    echo "  gm-condition.sh add Tandy poisoned"
    echo "  gm-condition.sh remove Tandy poisoned"
    echo "  gm-condition.sh check Tandy"
    exit 1
fi

require_active_campaign

ACTION="$1"
NAME="$2"
CONDITION="$3"

case "$ACTION" in
    add)
        if [ -z "$CONDITION" ]; then
            echo "Error: Condition name required for add"
            exit 1
        fi
        $PYTHON_CMD "$LIB_DIR/player_manager.py" condition "$NAME" add "$CONDITION"
        ;;
    remove)
        if [ -z "$CONDITION" ]; then
            echo "Error: Condition name required for remove"
            exit 1
        fi
        $PYTHON_CMD "$LIB_DIR/player_manager.py" condition "$NAME" remove "$CONDITION"
        ;;
    check)
        $PYTHON_CMD "$LIB_DIR/player_manager.py" condition "$NAME" list
        ;;
    *)
        echo "Unknown action: $ACTION"
        echo "Valid actions: add, remove, check"
        exit 1
        ;;
esac

exit $?
