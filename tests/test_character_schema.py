"""Tests for open-character-schema: migration + kit-aware validation + kit-driven XP."""

import json
from pathlib import Path

from lib.character_schema import is_open_schema, to_open_schema
from lib.player_manager import PlayerManager
from lib.schemas import validate_character
from lib.world_kit import WorldKit


def _char(dcc_world):
    p = Path(dcc_world) / "campaigns" / "dungeon-crawler-carl" / "character.json"
    return json.loads(p.read_text(encoding="utf-8"))


def test_migration_to_open_schema(dcc_world):
    new = to_open_schema(_char(dcc_world))
    assert is_open_schema(new)
    assert new["identity"]["name"] == "Tandy"
    assert set(new) >= {"identity", "vitals", "attributes", "progression", "inventory", "conditions"}
    assert isinstance(new["attributes"], dict) and new["attributes"]
    assert "hp" in new["vitals"]


def test_migration_is_idempotent(dcc_world):
    once = to_open_schema(_char(dcc_world))
    assert to_open_schema(once) == once


def test_dcc_character_validates_against_its_kit(dcc_world):
    new = to_open_schema(_char(dcc_world))
    ok, errs = validate_character(new, WorldKit(dcc_world))
    assert ok, errs


def test_non_5e_kit_with_custom_attributes_validates():
    paul = {
        "identity": {"name": "Paul Atreides"},
        "vitals": {"hp": {"current": 10, "max": 10}},
        "attributes": {"prescience": 5, "spice_tolerance": 3},
        "progression": {"level": 1},
        "inventory": {"gold": 0, "items": []},
        "conditions": [],
    }

    class DuneKit:
        def stat_schema(self):
            return {"attributes": ["prescience", "spice_tolerance"]}

    ok, errs = validate_character(paul, DuneKit())
    assert ok, errs


def test_attributes_outside_kit_schema_are_flagged():
    char = {"identity": {}, "vitals": {}, "attributes": {"strength": 1},
            "progression": {}, "inventory": {}, "conditions": []}

    class DuneKit:
        def stat_schema(self):
            return {"attributes": ["prescience"]}

    ok, errs = validate_character(char, DuneKit())
    assert not ok and any("not in active kit" in e for e in errs)


def test_xp_thresholds_delegate_to_kit(dcc_world):
    # Read off the kit's built progression object, not a literal in player_manager.
    # The 5e kit's table happens to equal the manager's default table.
    from lib.world_kit import XP_THRESHOLDS

    pm = PlayerManager(dcc_world)
    assert pm._xp_thresholds() == [0] + XP_THRESHOLDS
    assert pm._xp_thresholds() == PlayerManager.DEFAULT_XP_THRESHOLDS
    assert pm._max_level() == 20


def test_flat_sheet_validates_directly(dcc_world):
    # Regression: the old open-shape validator reported a loaded (flat) sheet as
    # entirely missing. The consolidated validator accepts both shapes.
    ok, errs = validate_character(_char(dcc_world), WorldKit(dcc_world))
    assert ok, errs


def test_nameless_traveler_validates_without_race_or_class():
    ok, errs = validate_character({"name": "A nameless traveler", "level": 1})
    assert ok, errs
