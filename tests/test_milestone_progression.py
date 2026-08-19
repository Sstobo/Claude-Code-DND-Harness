"""Tests for kit-driven progression on the PC sheet.

The kit is hardcoded 5e, so every campaign levels on the standard XP table and
tops out at 20 — the sheet code still reads both through the kit rather than a
literal of its own, which is what these guard. A campaign with no ruleset.json
(now every campaign) still gets hp as a declared vital.

Every fixture world is built in tmp_path with its own active-campaign.txt, so the
repo's live world-state is never read or written.
"""

import json

import pytest

from lib.player_manager import PlayerManager

PILGRIM = {
    "name": "Pilgrim",
    "level": 1,
    "hp": {"current": 20, "max": 20},
    "stats": {"str": 12, "dex": 14, "con": 12, "int": 10, "wis": 11, "cha": 9},
    "gold": 0,
}


def _world(tmp_path, slug, character=PILGRIM):
    world = tmp_path / "world-state"
    campaign = world / "campaigns" / slug
    campaign.mkdir(parents=True)
    (world / "active-campaign.txt").write_text(slug, encoding="utf-8")
    if character is not None:
        (campaign / "character.json").write_text(json.dumps(character), encoding="utf-8")
    return world


def _sheet(world, slug):
    return json.loads((world / "campaigns" / slug / "character.json").read_text(encoding="utf-8"))


@pytest.fixture
def road(tmp_path):
    return _world(tmp_path, "long-road")


# --- reads write nothing -------------------------------------------------------

def test_reading_level_status_writes_nothing(road):
    mgr = PlayerManager(str(road))
    status = mgr.get_xp_status("Pilgrim")
    assert status["current_xp"] == 0
    assert "xp" not in _sheet(road, "long-road")


def test_vitals_and_hp_changes_leave_xp_alone(road):
    mgr = PlayerManager(str(road))
    assert mgr.modify_hp("Pilgrim", -5)["success"]
    assert "xp" not in _sheet(road, "long-road")


# --- the level ceiling and thresholds are the kit's ----------------------------

def test_kit_thresholds_are_the_5e_table(road):
    mgr = PlayerManager(str(road))
    result = mgr.award_xp("Pilgrim", 300)
    assert result["new_level"] == 2 and result["next_level_xp"] == 900


def test_ceiling_is_level_twenty(tmp_path):
    char = dict(PILGRIM, level=19, xp={"current": 305000, "next_level": 355000})
    world = _world(tmp_path, "top", character=char)
    result = PlayerManager(str(world)).award_xp("Pilgrim", 50000)
    assert result["new_level"] == 20 and result["next_level_xp"] == "MAX"


def test_top_level_is_not_ready_to_level(tmp_path):
    char = dict(PILGRIM, level=20, xp={"current": 355000, "next_level": 355000})
    world = _world(tmp_path, "capped", character=char)
    assert PlayerManager(str(world)).get_xp_status("Pilgrim")["ready_to_level"] is False


def test_spectacle_beat_awards_scaled_xp(road):
    """An xp-levels kit pays a spectacle beat in XP, not a milestone tick."""
    result = PlayerManager(str(road)).award_spectacle("Pilgrim", "major")
    sheet = _sheet(road, "long-road")
    assert result["xp_gained"] > 0
    assert sheet["xp"]["current"] == result["xp_gained"] and "milestone" not in sheet


# --- a campaign with no ruleset.json (every campaign) --------------------------

def test_campaign_can_still_change_hp(tmp_path):
    """The kit declares ['hp'], so the vital is never refused."""
    world = _world(tmp_path, "bare")
    mgr = PlayerManager(str(world))

    assert mgr._kit_vitals() == ["hp"]
    result = mgr.modify_vital(None, "hp", -6)
    assert result["success"] and result["current"] == 14
    assert _sheet(world, "bare")["hp"]["current"] == 14


def test_campaign_refuses_an_undeclared_vital(tmp_path):
    world = _world(tmp_path, "bare")
    assert PlayerManager(str(world)).modify_vital(None, "resolve", -1)["success"] is False
