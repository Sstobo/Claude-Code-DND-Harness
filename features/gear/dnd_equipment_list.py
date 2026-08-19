#!/usr/bin/env python3
"""
List and search D&D 5e equipment
Usage: uv run python dnd_equipment_list.py [options]
Examples:
    uv run python dnd_equipment_list.py                    # List first 10 items
    uv run python dnd_equipment_list.py --search sword     # Search for swords
    uv run python dnd_equipment_list.py --category weapon  # List weapons
"""

import sys
import argparse
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "dnd-api"))

from dnd_api_core import fetch, output, error_output

def get_equipment_categories():
    """Fetch all available equipment categories"""
    data = fetch("/equipment-categories")
    if "error" in data:
        return []
    return [cat["index"] for cat in data.get("results", [])]

def filter_equipment(equipment_list, args):
    """Apply filters to equipment list"""
    results = []
    
    for item in equipment_list:
        # Search filter
        if args.search:
            if args.search.lower() not in item["name"].lower():
                continue
        
        # Category filter - need to fetch each item to check category
        if args.category:
            # For performance, we'll skip fetching individual items
            # and rely on naming conventions or pre-knowledge
            # This is a limitation but keeps the script fast
            pass
        
        results.append(item)
    
    return results

def fetch_equipment_by_category(category):
    """Fetch equipment for a specific category"""
    # Fetch the category details which includes equipment list
    data = fetch(f"/equipment-categories/{category}")
    
    if "error" in data:
        return []
    
    # Return the equipment list from this category
    return data.get("equipment", [])

def main():
    parser = argparse.ArgumentParser(description='List and search D&D 5e equipment')
    parser.add_argument('--search', help='Search equipment by name')
    parser.add_argument('--category', help='Filter by equipment category')
    parser.add_argument('--limit', type=int, default=10, help='Maximum results (default: 10)')
    parser.add_argument('--list-categories', action='store_true', help='List all available categories')
    
    args = parser.parse_args()
    
    # List categories if requested
    if args.list_categories:
        categories = get_equipment_categories()
        output({
            "count": len(categories),
            "categories": categories
        })
        return
    
    # Handle category-specific requests
    if args.category:
        # Normalize category name
        category_index = args.category.lower().replace(' ', '-')
        equipment = fetch_equipment_by_category(category_index)
        
        if not equipment:
            error_output(f"Category '{args.category}' not found or has no equipment. Use --list-categories to see available options.")
        
        # Apply search filter if provided
        if args.search:
            equipment = [item for item in equipment if args.search.lower() in item["name"].lower()]
        
        # Apply limit
        if args.limit and len(equipment) > args.limit:
            equipment = equipment[:args.limit]
        
        output({
            "category": args.category,
            "count": len(equipment),
            "results": equipment
        })
        return
    
    # Fetch all equipment
    data = fetch("/equipment")
    
    if "error" in data:
        error_output(f"Failed to fetch equipment: {data.get('message', 'Unknown error')}")
    
    equipment = data.get("results", [])
    
    # Apply filters
    if args.search:
        equipment = filter_equipment(equipment, args)
    
    # Apply limit
    total_count = len(equipment)
    if args.limit and len(equipment) > args.limit:
        equipment = equipment[:args.limit]
    
    # Format output
    output({
        "count": len(equipment),
        "total": total_count,
        "results": equipment
    })

if __name__ == "__main__":
    main()