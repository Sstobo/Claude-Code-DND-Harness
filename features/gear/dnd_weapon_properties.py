#!/usr/bin/env python3
"""
Get D&D 5e weapon property explanations
Usage: uv run python dnd_weapon_properties.py [property-name]
Examples:
    uv run python dnd_weapon_properties.py              # List all properties
    uv run python dnd_weapon_properties.py finesse      # Explain finesse property
    uv run python dnd_weapon_properties.py versatile    # Explain versatile property
"""

import sys
import argparse
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "dnd-api"))

from dnd_api_core import fetch, output, error_output

def main():
    parser = argparse.ArgumentParser(description='Get D&D 5e weapon property explanations')
    parser.add_argument('property_name', nargs='?', help='Specific property to explain')
    
    args = parser.parse_args()
    
    # If no property specified, list all properties
    if not args.property_name:
        data = fetch("/weapon-properties")
        
        if "error" in data:
            error_output(f"Failed to fetch weapon properties: {data.get('message', 'Unknown error')}")
        
        # Format the list nicely
        properties = data.get("results", [])
        output({
            "count": len(properties),
            "properties": [{"name": prop["name"], "index": prop["index"]} for prop in properties]
        })
        return
    
    # Fetch specific property
    property_index = args.property_name.lower().replace(' ', '-')
    data = fetch(f"/weapon-properties/{property_index}")
    
    # Check for errors
    if "error" in data:
        if data.get("error") == "HTTP 404":
            # List available properties on error
            all_props = fetch("/weapon-properties")
            if "results" in all_props:
                prop_names = [p["name"] for p in all_props["results"]]
                error_output(f"Property '{args.property_name}' not found. Available properties: {', '.join(prop_names)}")
            else:
                error_output(f"Property '{args.property_name}' not found.")
        else:
            error_output(f"Failed to fetch property: {data.get('message', 'Unknown error')}")
    
    # Output the property details
    output(data)

if __name__ == "__main__":
    main()