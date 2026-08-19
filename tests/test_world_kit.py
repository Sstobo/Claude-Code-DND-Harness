"""Tests for the hardcoded 5e World Kit driving the generic core."""

from lib.world_kit import WorldKit


def test_kit_is_5e(dcc_world):
    k = WorldKit(dcc_world)
    assert k.kit() == "dnd5e"
    assert k.name() == "D&D 5e"
    assert k.resolution_model() == "d20-vs-dc"
    assert k.progression_model() == "xp-levels"
    assert k.vitals() == ["hp"]
    assert k.stat_schema()["attributes"] == ["str", "dex", "con", "int", "wis", "cha"]
    assert "monster-manual" in k.active_agents()


def test_resolves_through_generic_core(dcc_world):
    r = WorldKit(dcc_world).resolve(modifier=100, dc=5)
    assert r["success"] is True and "die" in r


def test_progression_is_the_5e_xp_table(dcc_world):
    k = WorldKit(dcc_world)
    assert k.level(k.advance_progression({}, xp=0)) == 1
    assert k.level(k.advance_progression({}, xp=300)) == 2
    assert k.level(k.advance_progression({}, xp=6500)) == 5
    assert k.level(k.advance_progression({}, xp=355000)) == 20


def test_campaign_rules_carry_the_world_flavor(dcc_world):
    rules = WorldKit(dcc_world).campaign_rules()
    assert "loot_box_system" in rules and "audience_system" in rules


def test_rules_doc_loads_on_demand(dcc_world):
    p = WorldKit(dcc_world).rules_doc_path()
    assert p is not None and p.name == "rules.md"
