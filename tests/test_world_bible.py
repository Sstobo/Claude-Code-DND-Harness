"""Tests for world-bible-schema: structured fidelity spine (voice/factions/geography/...)."""

from lib.world_bible import WorldBible, validate_bible


def test_dcc_bible_loads_and_validates(dcc_world):
    wb = WorldBible(dcc_world)
    assert wb.exists()
    ok, errs = wb.validate()
    assert ok, errs
    assert wb.bible["name"] == "Dungeon Crawler Carl"


def test_factions_and_geography_parse_as_graphs(dcc_world):
    wb = WorldBible(dcc_world)
    fac = wb.factions()
    geo = wb.geography()
    assert {n["id"] for n in fac["nodes"]} >= {"crawlers", "system"}
    assert any(e["relation"] for e in fac["edges"])
    assert {n["id"] for n in geo["nodes"]} >= {"floor1", "floor4"}
    assert any("stairwell" in e["adjacency"] for e in geo["edges"])


def test_voice_and_signature_systems_present(dcc_world):
    wb = WorldBible(dcc_world)
    assert wb.voice().get("style")
    assert any("loot box" in s.lower() for s in wb.signature_systems())


def test_validator_rejects_missing_graph():
    bad = {"name": "X", "voice": {}, "tone": "t", "themes": [],
           "factions": {"nodes": []}, "geography": {"nodes": [], "edges": []},
           "signature_systems": []}
    ok, errs = validate_bible(bad)
    assert not ok and any("factions must be a graph" in e for e in errs)
