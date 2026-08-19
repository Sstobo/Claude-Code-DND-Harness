"""Tests for character-save vitals under the hardcoded 5e World Kit.

The kit declares one vital (hp), so the multi-vital machinery in PlayerManager
is exercised through hp and through the refusal of anything undeclared. The
fixture world is built in tmp_path, so nothing here reads or writes the repo's
world-state (the live active-campaign.txt is never touched).
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from lib.player_manager import PlayerManager

ROOT = Path(__file__).resolve().parent.parent
SAVE_CHARACTER = ROOT / "features" / "character-creation" / "save_character.py"

THORIN = {
    "name": "Thorin",
    "race": "Dwarf",
    "class": "Fighter",
    "level": 1,
    "stats": {"str": 16, "dex": 12, "con": 15, "int": 10, "wis": 13, "cha": 8},
}


def _make_world(tmp_path, slug):
    world = tmp_path / "world-state"
    campaign = world / "campaigns" / slug
    campaign.mkdir(parents=True)
    (world / "active-campaign.txt").write_text(slug, encoding="utf-8")
    return world


@pytest.fixture
def dnd_world(tmp_path):
    return _make_world(tmp_path, "forgotten-realms")


def _save(world, payload):
    """Run save_character.py against `world` (it resolves world-state from cwd)."""
    return subprocess.run(
        [sys.executable, str(SAVE_CHARACTER), json.dumps(payload)],
        capture_output=True, text=True, cwd=str(world.parent), env={**os.environ},
    )


def _sheet(world):
    slug = (world / "active-campaign.txt").read_text(encoding="utf-8").strip()
    return json.loads((world / "campaigns" / slug / "character.json").read_text(encoding="utf-8"))


def test_attributes_is_accepted_as_the_stat_key(dnd_world):
    payload = {k: v for k, v in THORIN.items() if k != "stats"}
    payload["attributes"] = THORIN["stats"]
    r = _save(dnd_world, payload)
    assert r.returncode == 0, r.stdout + r.stderr
    assert _sheet(dnd_world)["stats"] == THORIN["stats"]


def test_stats_is_still_accepted_as_a_legacy_alias(dnd_world):
    r = _save(dnd_world, THORIN)
    assert r.returncode == 0, r.stdout + r.stderr
    assert _sheet(dnd_world)["stats"] == THORIN["stats"]


def test_kit_declares_hp_as_its_only_vital(dnd_world):
    from lib.world_kit import WorldKit
    assert WorldKit(str(dnd_world)).vitals() == ["hp"]


def test_undeclared_vital_is_refused(dnd_world):
    _save(dnd_world, THORIN)
    result = PlayerManager(str(dnd_world)).modify_vital(None, "vigor", -1)
    assert result["success"] is False


def test_hp_keeps_its_dedicated_path(dnd_world):
    """hp is a declared vital, but routes through modify_hp (dying gate + clamp)."""
    _save(dnd_world, THORIN)
    mgr = PlayerManager(str(dnd_world))
    result = mgr.modify_vital(None, "hp", -12)
    assert result["success"] and result["current_hp"] == 0
    assert _sheet(dnd_world)["status"] == "dying"


def test_every_vital_response_has_the_same_shape(dnd_world):
    """hp delegates to modify_hp but still answers with vital/current/max."""
    _save(dnd_world, THORIN)
    mgr = PlayerManager(str(dnd_world))

    hp = mgr.modify_vital(None, "hp", -8)
    read = mgr.modify_vital(None, "hp")

    keys = {"success", "name", "vital", "current", "max"}
    assert keys <= hp.keys() and keys <= read.keys()
    assert hp["vital"] == "hp" and hp["current"] == 4 and hp["max"] == 12
    assert hp["previous"] == 12
    assert hp["current_hp"] == 4 and hp["max_hp"] == 12   # modify_hp's own keys kept


def test_dnd5e_derives_hp_and_saves(dnd_world):
    r = _save(dnd_world, THORIN)
    assert r.returncode == 0, r.stdout + r.stderr
    sheet = _sheet(dnd_world)
    assert sheet["hp"] == {"current": 12, "max": 12}   # d10 hit die + CON +2
    assert sheet["saves"]["str"] == 5                  # +3 mod + proficiency
    assert sheet["saves"]["dex"] == 1


def test_authored_hp_is_preserved_verbatim(dnd_world):
    """Authoring beats deriving — a rolled sheet is not recomputed."""
    r = _save(dnd_world, {**THORIN, "hp": {"current": 7, "max": 14}})
    assert r.returncode == 0, r.stdout + r.stderr
    sheet = _sheet(dnd_world)
    assert sheet["hp"] == {"current": 7, "max": 14}     # not the formula's 12/12
    assert sheet["saves"]["str"] == 5                   # 5e derivation still runs


def test_authored_max_hp_is_preserved(dnd_world):
    """A high authored max survives the save untouched, both fields."""
    r = _save(dnd_world, {**THORIN, "level": 6, "hp": {"current": 58, "max": 58}})
    assert r.returncode == 0, r.stdout + r.stderr
    hp = _sheet(dnd_world)["hp"]
    assert hp["max"] == 58 and hp["current"] == 58


def test_missing_hp_without_a_class_warns_and_defaults_to_10(dnd_world):
    """No class means no hit die: HP persists 10/10 and the save names the fallback."""
    payload = {k: v for k, v in THORIN.items() if k != "class"}
    r = _save(dnd_world, payload)
    assert r.returncode == 0, r.stdout + r.stderr
    result = json.loads(r.stdout)
    assert _sheet(dnd_world)["hp"] == {"current": 10, "max": 10}
    warnings = result["warnings"]
    assert isinstance(warnings, list) and warnings
    assert any("10/10" in w for w in warnings)
    assert any("author" in w.lower() for w in warnings)
