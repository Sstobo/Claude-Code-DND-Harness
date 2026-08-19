"""Tests for campaign-overview-author: seed overview + campaign_rules, report rules_doc."""

import json
from lib.overview_seed import seed_overview, fix_rules_doc


def test_seed_sets_fields_and_campaign_rules_preserving_others(tmp_path):
    (tmp_path / "campaign-overview.json").write_text(json.dumps({
        "campaign_name": "scaffold", "genre": "Fantasy",
        "player_position": {"current_location": "X"}, "session_count": 3,
    }))
    seed_overview(
        str(tmp_path),
        fields={"campaign_name": "The Iron Tangle", "genre": "LitRPG / Comedy-Horror"},
        campaign_rules={"loot_boxes": "open at saferooms"},
    )
    o = json.loads((tmp_path / "campaign-overview.json").read_text())
    assert o["campaign_name"] == "The Iron Tangle"
    assert o["genre"] == "LitRPG / Comedy-Horror"
    assert o["campaign_rules"]["loot_boxes"] == "open at saferooms"
    # untouched fields preserved
    assert o["session_count"] == 3
    assert o["player_position"] == {"current_location": "X"}


def test_fix_rules_doc_reports_absent_prose_and_writes_nothing(tmp_path):
    r = fix_rules_doc(str(tmp_path))
    assert r == {"rules_doc": None, "changed": False}
    assert list(tmp_path.iterdir()) == [], "must not create a ruleset.json or anything else"


def test_fix_rules_doc_finds_rules_md_by_convention(tmp_path):
    (tmp_path / "rules.md").write_text("# rules")
    r = fix_rules_doc(str(tmp_path))
    assert r == {"rules_doc": "rules.md", "changed": False}
    assert not (tmp_path / "ruleset.json").exists()


def test_campaign_rules_readable_by_worldkit_shape(tmp_path):
    # WorldKit.campaign_rules() does overview.get("campaign_rules", {}) — ensure shape.
    seed_overview(str(tmp_path), fields={"campaign_name": "T"}, campaign_rules={"viewers": "currency"})
    o = json.loads((tmp_path / "campaign-overview.json").read_text())
    assert o.get("campaign_rules", {}).get("viewers") == "currency"
