#!/usr/bin/env python3
"""
Get D&D 5e magic item details
Usage: uv run python dnd_magic_item.py <item-name> [options]
Example: uv run python dnd_magic_item.py "bag of holding"
         uv run python dnd_magic_item.py "flame tongue" --summary
"""

import sys
import argparse
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "dnd-api"))

from dnd_api_core import fetch, output, error_output

def extract_summary_info(item):
    """Extract key magic item information"""
    summary = {
        "name": item.get("name", "Unknown"),
        "rarity": item.get("rarity", {}).get("name", "Unknown"),
        "requires_attunement": item.get("attunement", "").replace("requires attunement", "Yes") if item.get("attunement") else "No"
    }
    
    # Get first paragraph of description as summary
    desc = item.get("desc", [])
    if desc:
        summary["brief_description"] = desc[0][:200] + "..." if len(desc[0]) > 200 else desc[0]
    
    # Equipment category if applicable
    if "equipment_category" in item:
        summary["category"] = item["equipment_category"].get("name", "Unknown")
    
    # Variants if any
    if "variants" in item and item["variants"]:
        summary["variants"] = [v["name"] for v in item["variants"]]
    
    return summary

def main():
    parser = argparse.ArgumentParser(description='Get D&D 5e magic item details')
    parser.add_argument('item_name', help='Magic item name to look up')
    parser.add_argument('--summary', action='store_true', 
                       help='Show only summary information')
    
    args = parser.parse_args()
    
    # Convert item name to API format
    item_index = args.item_name.lower().replace(' ', '-').replace("'", "")
    
    # Fetch magic item data
    data = fetch(f"/magic-items/{item_index}")
    
    # Check for errors
    if "error" in data:
        if data.get("error") == "HTTP 404":
            error_output(f"Magic item '{args.item_name}' not found. Try checking the exact name.")
        else:
            error_output(f"Failed to fetch magic item: {data.get('message', 'Unknown error')}")
    
    # Output based on mode
    if args.summary:
        output(extract_summary_info(data))
    else:
        output(data)

if __name__ == "__main__":
    main()