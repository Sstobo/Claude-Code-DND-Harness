#!/usr/bin/env python3
"""
Get D&D 5e equipment details
Usage: uv run python dnd_equipment.py <equipment-name> [options]
Example: uv run python dnd_equipment.py longsword
         uv run python dnd_equipment.py "plate armor" --combat
"""

import sys
import argparse
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "dnd-api"))

from dnd_api_core import fetch, output, error_output

def extract_combat_info(equipment):
    """Extract just combat-relevant information"""
    combat_data = {
        "name": equipment.get("name", "Unknown"),
        "equipment_category": equipment.get("equipment_category", {}).get("name", "Unknown")
    }
    
    # Weapon combat stats
    if "damage" in equipment:
        combat_data["damage"] = f"{equipment['damage']['damage_dice']} {equipment['damage']['damage_type']['name']}"
        
    if "two_handed_damage" in equipment:
        combat_data["two_handed_damage"] = f"{equipment['two_handed_damage']['damage_dice']} {equipment['two_handed_damage']['damage_type']['name']}"
        
    if "range" in equipment:
        normal_range = equipment["range"].get("normal", 0)
        long_range = equipment["range"].get("long")
        if long_range:
            combat_data["range"] = f"{normal_range}/{long_range} ft"
        else:
            combat_data["range"] = f"{normal_range} ft"
            
    if "thrown_range" in equipment:
        normal = equipment["thrown_range"].get("normal", 0)
        long = equipment["thrown_range"].get("long", 0)
        combat_data["thrown_range"] = f"{normal}/{long} ft"
    
    # Armor combat stats
    if "armor_class" in equipment:
        ac = equipment["armor_class"]
        if ac.get("dex_bonus"):
            if ac.get("max_bonus"):
                combat_data["AC"] = f"{ac['base']} + Dex (max {ac['max_bonus']})"
            else:
                combat_data["AC"] = f"{ac['base']} + Dex"
        else:
            combat_data["AC"] = str(ac.get("base", "Unknown"))
            
    if "stealth_disadvantage" in equipment:
        combat_data["stealth_disadvantage"] = equipment["stealth_disadvantage"]
        
    if "str_minimum" in equipment:
        combat_data["strength_requirement"] = equipment["str_minimum"]
    
    # Properties
    if "properties" in equipment and equipment["properties"]:
        combat_data["properties"] = [prop["name"] for prop in equipment["properties"]]
    
    return combat_data

def format_cost(cost):
    """Format cost object into readable string"""
    if not cost:
        return "Unknown"
    return f"{cost.get('quantity', 0)} {cost.get('unit', 'gp')}"

def main():
    parser = argparse.ArgumentParser(description='Get D&D 5e equipment details')
    parser.add_argument('equipment_name', help='Equipment name to look up')
    parser.add_argument('--combat', action='store_true', 
                       help='Show only combat-relevant information')
    
    args = parser.parse_args()
    
    # Convert equipment name to API format
    equipment_index = args.equipment_name.lower().replace(' ', '-')
    
    # Fetch equipment data
    data = fetch(f"/equipment/{equipment_index}")
    
    # Check for errors
    if "error" in data:
        if data.get("error") == "HTTP 404":
            error_output(f"Equipment '{args.equipment_name}' not found. Try checking the exact name.")
        else:
            error_output(f"Failed to fetch equipment: {data.get('message', 'Unknown error')}")
    
    # Output based on mode
    if args.combat:
        output(extract_combat_info(data))
    else:
        # Add formatted cost for full view
        if "cost" in data:
            data["cost_formatted"] = format_cost(data["cost"])
        output(data)

if __name__ == "__main__":
    main()