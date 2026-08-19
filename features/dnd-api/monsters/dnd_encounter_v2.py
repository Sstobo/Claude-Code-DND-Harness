#!/usr/bin/env python3
"""
Quick D&D encounter helper using API CR filtering
Usage: uv run python dnd_encounter_v2.py --cr <CR> [--count <number>]
Example: uv run python dnd_encounter_v2.py --cr 2 --count 3
"""

import sys
import argparse
import random
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from dnd_api_core import fetch, output, error_output

def get_monsters_by_cr(target_cr):
    """Get all monsters of a specific CR using API filtering"""
    data = fetch(f"/monsters?challenge_rating={target_cr}")

    if "error" in data:
        if data["error"] == "HTTP 429":
            error_output("Rate limited. Please wait a moment and try again.")
        elif data["error"].startswith("HTTP "):
            error_output(f"{data['error']}: {data['message']}")
        else:
            error_output(data["message"])

    if "results" in data:
        # Extract monster indices from URLs
        return [m["url"].split("/")[-1] for m in data["results"]]
    return []

def main():
    parser = argparse.ArgumentParser(description='Quick D&D encounter helper')
    parser.add_argument('--cr', type=float, required=True, help='Challenge rating')
    parser.add_argument('--count', type=int, default=1, help='Number of monsters')
    parser.add_argument('--quick', action='store_true', help='Just return monster names')
    
    args = parser.parse_args()
    
    # Get available monsters for this CR
    available = get_monsters_by_cr(args.cr)
    
    if not available:
        error_output(f"No monsters found for CR {args.cr}")
    
    # Select random monsters
    if args.count > len(available):
        # If we need more than available, allow duplicates
        selected = [random.choice(available) for _ in range(args.count)]
    else:
        # Otherwise, select unique monsters
        selected = random.sample(available, args.count)
    
    if args.quick:
        # Just output the names
        output({
            "cr": args.cr,
            "count": args.count,
            "monsters": selected
        })
    else:
        # Fetch full details
        monsters = []
        for monster_index in selected:
            data = fetch(f"/monsters/{monster_index}")
            if "error" not in data:
                # Extract combat info
                monsters.append({
                    "name": data.get("name"),
                    "hp": data.get("hit_points"),
                    "ac": data.get("armor_class", [{}])[0].get("value", 10),
                    "cr": data.get("challenge_rating"),
                    "xp": data.get("xp")
                })
        
        output({
            "cr": args.cr,
            "count": args.count,
            "encounter_xp": sum(m.get("xp", 0) for m in monsters),
            "monsters": monsters
        })

if __name__ == "__main__":
    main()