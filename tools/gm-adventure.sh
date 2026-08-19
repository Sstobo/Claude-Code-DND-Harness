#!/bin/bash
# gm-adventure.sh - Where the table is in the book's adventure
# Uses Python modules for validation and data operations

# Source common utilities
source "$(dirname "$0")/common.sh"

# Usage: gm-adventure.sh <action> [args]

if [ "$#" -lt 1 ]; then
    echo "Usage: gm-adventure.sh <action> [args]"
    echo ""
    echo "=== Adventure Progress ==="
    echo "  status                           Current scene + what comes next"
    echo "  advance                          Complete the current scene, move to the next"
    echo "  jump <key>                       Move the pointer to any scene"
    echo "  validate                         Check adventure.json for schema problems"
    echo ""
    echo "All actions take --json for a structured envelope."
    echo ""
    echo "Examples:"
    echo "  gm-adventure.sh status"
    echo "  gm-adventure.sh advance"
    echo "  gm-adventure.sh jump goblin-ambush"
    exit 1
fi

require_active_campaign

ACTION="$1"
shift  # Remove action from arguments

if [ ! -f "$WORLD_STATE_DIR/adventure.json" ]; then
    error "This campaign has no adventure.json — it is not running a converted book."
    echo "  Build one with:  $PYTHON_CMD lib/adventure.py init <spine.json>" >&2
    exit 1
fi

case "$ACTION" in
    status)
        $PYTHON_CMD "$LIB_DIR/adventure.py" status "$@"
        ;;

    advance)
        $PYTHON_CMD "$LIB_DIR/adventure.py" advance "$@"
        ;;

    jump)
        if [ "$#" -lt 1 ]; then
            echo "Usage: gm-adventure.sh jump <key>"
            exit 1
        fi
        $PYTHON_CMD "$LIB_DIR/adventure.py" jump "$@"
        ;;

    validate)
        $PYTHON_CMD "$LIB_DIR/adventure.py" validate "$@"
        ;;

    *)
        echo "Error: Unknown action '$ACTION'"
        echo "Run 'gm-adventure.sh' without arguments to see all available actions"
        exit 1
        ;;
esac

# Exit with the same status as the Python command
exit $?
