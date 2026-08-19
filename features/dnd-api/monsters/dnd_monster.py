#!/usr/bin/env python3
"""
Get D&D monster details
Usage: uv run python dnd_monster.py <monster-index> [--combat]
Example: uv run python dnd_monster.py goblin
"""

import sys
import argparse
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from dnd_api_core import fetch, output, error_output

def extract_combat_info(monster):
    """Extract just combat-relevant information"""
    combat_data = {
        "name": monster.get("name", "Unknown"),
        "cr": monster.get("challenge_rating", 0),
        "xp": monster.get("xp", 0),
        "hp": monster.get("hit_points", 0),
        "hp_dice": monster.get("hit_dice", ""),
        "ac": [],
        "speed": monster.get("speed", {}),
        "abilities": {},
        "attacks": []
    }
    
    # Extract AC info
    for ac in monster.get("armor_class", []):
        if isinstance(ac, dict):
            combat_data["ac"].append({
                "value": ac.get("value", 0),
                "type": ac.get("type", "natural")
            })
        else:
            combat_data["ac"].append({"value": ac, "type": "natural"})
    
    # Extract ability scores
    for ability in ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]:
        combat_data["abilities"][ability[:3].upper()] = monster.get(ability, 10)
    
    # Extract attacks from actions
    for action in monster.get("actions", []):
        if "damage" in action.get("desc", "").lower() or "attack" in action.get("name", "").lower():
            combat_data["attacks"].append({
                "name": action.get("name", ""),
                "desc": action.get("desc", "")
            })
    
    return combat_data

def main():
    parser = argparse.ArgumentParser(description='Get D&D monster details')
    parser.add_argument('monster', help='Monster index (e.g., goblin)')
    parser.add_argument('--combat', action='store_true', 
                       help='Show only combat-relevant information')
    
    args = parser.parse_args()
    
    # Convert monster name to index format
    monster_index = args.monster.lower().replace(' ', '-')
    
    # Fetch monster data
    data = fetch(f"/monsters/{monster_index}")
    
    # Check for errors
    if "error" in data:
        if data.get("error") == "HTTP 404":
            error_output(f"Monster '{args.monster}' not found")
        else:
            error_output(f"Failed to fetch monster: {data.get('message', 'Unknown error')}")
    
    # Output based on mode
    if args.combat:
        output(extract_combat_info(data))
    else:
        output(data)

if __name__ == "__main__":
    main()