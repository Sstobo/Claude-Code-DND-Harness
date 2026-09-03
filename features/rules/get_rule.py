#!/usr/bin/env python3
"""
Get D&D 5e rule details
Usage: uv run python get_rule.py <rule-name> [options]
Example: uv run python get_rule.py advantage
"""

import sys
import argparse
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from rules_api_core import fetch, output, error_output

def format_rule_output(rule_data):
    """Format rule data for clean display"""
    formatted = {
        "name": rule_data.get("name", "Unknown"),
        "desc": rule_data.get("desc", ""),
    }
    
    # Add subsections if available
    if "subsections" in rule_data and rule_data["subsections"]:
        formatted["subsections"] = []
        for subsection in rule_data["subsections"]:
            formatted["subsections"].append({
                "name": subsection.get("name", ""),
                "url": subsection.get("url", "")
            })
    
    return formatted

def search_rules(search_term):
    """Every /rules and /rule-sections entry whose name contains the term.

    The two are separate collections and most of what a GM asks about mid-play
    ("cover", "advantage", "saving throws") is a rule SECTION, not a top-level
    rule — searching only /rules is why those lookups used to dead-end.
    """
    search_lower = search_term.lower()
    matches = []
    for collection in ("/rules", "/rule-sections"):
        data = fetch(collection)
        if "error" in data:
            continue
        for rule in data.get("results", []):
            if search_lower in rule.get("name", "").lower():
                matches.append({**rule, "collection": collection})
    return matches

def main():
    parser = argparse.ArgumentParser(description='Get D&D 5e rule details')
    parser.add_argument('rule_name', help='Rule name or topic to look up')
    parser.add_argument('--subsection', help='Get specific subsection details')
    
    args = parser.parse_args()
    
    # Convert rule name to API format
    rule_index = args.rule_name.lower().replace(' ', '-')

    # Direct hit in either collection wins.
    data = fetch(f"/rules/{rule_index}")
    if data.get("error") == "HTTP 404":
        data = fetch(f"/rule-sections/{rule_index}")

    # Still nothing: search both collections by name. One match is the answer —
    # RETURN it rather than suggesting it. Naming a section the tool then refused
    # to fetch is what made "advantage" and "cover" unanswerable.
    if data.get("error") == "HTTP 404":
        matches = search_rules(args.rule_name)
        if len(matches) == 1:
            hit = matches[0]
            data = fetch(f"{hit['collection']}/{hit['index']}")
        elif matches:
            error_output(f"'{args.rule_name}' matches several rules. Ask for one:\n" +
                         "\n".join([f"- {m['name']}" for m in matches[:5]]))
        else:
            # A miss is usually a topic the SRD files under a broader heading
            # ("opportunity attacks" lives inside Actions in Combat), so hand back
            # the whole index rather than a dead end.
            names = [r["name"] for r in search_rules("")]
            error_output(f"Rule '{args.rule_name}' not found. Available rules and "
                         f"sections:\n" + "\n".join(f"- {n}" for n in names))

    # Check for other errors
    if "error" in data:
        error_output(f"Failed to fetch rule: {data.get('message', 'Unknown error')}")
    
    # Format and output
    output(format_rule_output(data))

if __name__ == "__main__":
    main()