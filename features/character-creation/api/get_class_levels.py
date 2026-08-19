#!/usr/bin/env python3
"""
Get per-level data for a class (features, ASIs, spell slots)
Usage: uv run python get_class_levels.py <class> [level]
Example: uv run python get_class_levels.py wizard 3
         uv run python get_class_levels.py cleric
"""

import sys
import argparse
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from character_creation_core import fetch, output, error_output

def extract_level(level_data):
    """Extract the level entry: features, ASIs, and casting resources"""
    return {
        "level": level_data.get("level", 0),
        "ability_score_bonuses": level_data.get("ability_score_bonuses", 0),
        "prof_bonus": level_data.get("prof_bonus", 0),
        "features": [f.get("name", "") for f in level_data.get("features", [])],
        "spellcasting": level_data.get("spellcasting", {}),
        "class_specific": level_data.get("class_specific", {})
    }

def main():
    parser = argparse.ArgumentParser(description='Get class level data')
    parser.add_argument('class_name', help='Class identifier (e.g., wizard, cleric)')
    parser.add_argument('level', nargs='?', type=int,
                        help='Class level 1-20 (omit for all levels)')

    args = parser.parse_args()

    class_id = args.class_name.lower().replace(' ', '-')
    endpoint = f"/classes/{class_id}/levels"
    if args.level is not None:
        endpoint = f"{endpoint}/{args.level}"

    data = fetch(endpoint)

    if isinstance(data, dict) and "error" in data:
        # An out-of-range level comes back 400, an unknown class 404.
        missing = {"HTTP 404"} | ({"HTTP 400"} if args.level is not None else set())
        if data.get("error") in missing:
            error_output(f"No level data for '{args.class_name}'"
                         + (f" level {args.level}" if args.level is not None else ""))
        else:
            error_output(f"Failed to fetch class levels: {data.get('message', 'Unknown error')}")

    if isinstance(data, list):
        output([extract_level(entry) for entry in data])
    else:
        output(extract_level(data))

if __name__ == "__main__":
    main()
