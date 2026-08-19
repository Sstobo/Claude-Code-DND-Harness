"""Tests for rules-doc resolution: rules.md by convention, no pointer file."""

from pathlib import Path


def test_worldkit_resolves_rules_md(dcc_world):
    from lib.world_kit import WorldKit
    camp = Path(dcc_world) / "campaigns" / "dungeon-crawler-carl"
    (camp / "rules.md").write_text("# DCC rules\nHouse systems live here.")
    # active campaign in dcc_world is dungeon-crawler-carl
    p = WorldKit(dcc_world).rules_doc_path()
    assert p is not None and p.name == "rules.md"


def test_worldkit_rules_doc_is_none_without_the_file(tmp_path):
    from lib.world_kit import WorldKit
    world = tmp_path / "world-state"
    (world / "campaigns" / "bare").mkdir(parents=True)
    (world / "active-campaign.txt").write_text("bare", encoding="utf-8")
    assert WorldKit(str(world)).rules_doc_path() is None
