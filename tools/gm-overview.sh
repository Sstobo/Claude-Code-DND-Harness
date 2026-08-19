#!/bin/bash
# gm-overview.sh - World state overview (thin wrapper for world_stats.py)

source "$(dirname "$0")/common.sh"

require_active_campaign

echo "WORLD STATE OVERVIEW"
echo "===================="

if [ "$1" == "--detailed" ] || [ "$1" == "-d" ]; then
    $PYTHON_CMD "$LIB_DIR/world_stats.py" overview --detailed
    RESULT=$?
else
    $PYTHON_CMD "$LIB_DIR/world_stats.py" overview
    RESULT=$?
fi

echo ""
echo "Use gm-search.sh to search for specific content"
exit $RESULT
