#!/bin/bash
# gm-location.sh - Location management (thin wrapper for location_manager.py)

source "$(dirname "$0")/common.sh"

if [ "$#" -lt 1 ]; then
    echo "Usage: gm-location.sh <action> [args]"
    echo ""
    echo "Actions:"
    echo "  add <name> <position>              - Add new location"
    echo "  connect <from> <to> <path>         - Connect two locations"
    echo "  describe <name> <description>      - Set location description"
    echo "  get <name>                         - Get location info"
    echo "  list                               - List all locations"
    echo "  connections <name>                 - Show location connections"
    echo ""
    echo "Examples:"
    echo "  gm-location.sh add \"Volcano Temple\" \"north of village\""
    echo "  gm-location.sh connect \"Village\" \"Volcano Temple\" \"rocky path\""
    echo "  gm-location.sh describe \"Volcano Temple\" \"Ancient obsidian structure\""
    exit 1
fi

require_active_campaign

ACTION="$1"
shift

case "$ACTION" in
    add)
        if [ "$#" -lt 2 ]; then
            echo "Usage: gm-location.sh add <name> <position>"
            exit 1
        fi
        $PYTHON_CMD "$LIB_DIR/location_manager.py" add "$1" "$2"
        ;;

    connect)
        if [ "$#" -lt 3 ]; then
            echo "Usage: gm-location.sh connect <from> <to> <path>"
            exit 1
        fi
        $PYTHON_CMD "$LIB_DIR/location_manager.py" connect "$1" "$2" "$3"
        ;;

    describe)
        if [ "$#" -lt 2 ]; then
            echo "Usage: gm-location.sh describe <name> <description>"
            exit 1
        fi
        $PYTHON_CMD "$LIB_DIR/location_manager.py" describe "$1" "$2"
        ;;

    get)
        if [ "$#" -lt 1 ]; then
            echo "Usage: gm-location.sh get <name>"
            exit 1
        fi
        $PYTHON_CMD "$LIB_DIR/location_manager.py" get "$1"
        ;;

    list)
        echo "Locations"
        echo "========="
        $PYTHON_CMD "$LIB_DIR/location_manager.py" list
        ;;

    connections)
        if [ "$#" -lt 1 ]; then
            echo "Usage: gm-location.sh connections <name>"
            exit 1
        fi
        $PYTHON_CMD "$LIB_DIR/location_manager.py" connections "$1"
        ;;

    *)
        echo "Unknown action: $ACTION"
        echo "Valid actions: add, connect, describe, get, list, connections"
        exit 1
        ;;
esac

# Propagate Python exit code
exit $?
