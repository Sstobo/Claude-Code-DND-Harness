#!/usr/bin/env python3
"""Author per-book campaign-overview fields + campaign_rules.

Import leaves campaign-overview as the default scaffold (genre "Fantasy", no
campaign_rules), so the book's signature systems live nowhere the GM tooling reads
(WorldKit.campaign_rules() reads overview.campaign_rules). `seed_overview` writes
real content into it — and since the World Kit is hardcoded 5e and declares no
signature systems of its own, that block is the ONLY surface a book's systems reach
the model through.
"""

import json
from pathlib import Path


def seed_overview(campaign_dir, fields: dict = None, campaign_rules: dict = None) -> dict:
    """Merge `fields` into campaign-overview.json and set `campaign_rules`.

    Returns the written overview. Existing keys are overwritten only for the keys
    provided (player_position, session_count, etc. are preserved otherwise).
    """
    path = Path(campaign_dir) / "campaign-overview.json"
    overview = json.loads(path.read_text()) if path.exists() else {}
    if fields:
        overview.update(fields)
    if campaign_rules is not None:
        overview["campaign_rules"] = campaign_rules
    path.write_text(json.dumps(overview, indent=2))
    return overview


def fix_rules_doc(campaign_dir) -> dict:
    """Report the campaign's rules prose. Reads nothing else and writes nothing.

    There is no pointer left to dangle: `WorldKit.rules_doc_path()` resolves
    `rules.md` in the campaign dir by convention. This stays because `/import`
    still calls it, and it now only answers whether the prose is there.

    Returns {"rules_doc": "rules.md" | None, "changed": False}.
    """
    doc = Path(campaign_dir) / "rules.md"
    return {"rules_doc": doc.name if doc.exists() else None, "changed": False}


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Seed campaign-overview + fix rules_doc")
    parser.add_argument("campaign_dir")
    parser.add_argument("--fields-json", help="JSON object of overview fields to set")
    parser.add_argument("--rules-json", help="JSON object for campaign_rules")
    parser.add_argument("--fix-rules-doc", action="store_true")
    args = parser.parse_args()

    if args.fields_json or args.rules_json:
        fields = json.loads(args.fields_json) if args.fields_json else None
        rules = json.loads(args.rules_json) if args.rules_json else None
        seed_overview(args.campaign_dir, fields, rules)
        print("overview seeded")
    if args.fix_rules_doc:
        r = fix_rules_doc(args.campaign_dir)
        print(f"rules_doc: {r['rules_doc']} (changed={r['changed']})")


if __name__ == "__main__":
    main()
