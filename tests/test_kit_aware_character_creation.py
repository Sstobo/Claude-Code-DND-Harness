"""Tests for character creation.

This fork plays D&D 5e only. The create-character command/agent carry a single
5e path — no generic spine, no kit branch — and these tests fail if either
grows one back.
"""

import json
import re
from pathlib import Path

from lib.visual_appearance import VISUAL_FIELDS
from tests.test_kit_vitals import _make_world, _save, _sheet

ROOT = Path(__file__).resolve().parent.parent
COMMAND = ROOT / ".claude" / "commands" / "create-character.md"
AGENT = ROOT / ".claude" / "agents" / "create-character.md"
# The canonical look-of-a-character field set lives in one place; read it from
# there so a schema change can't leave this test asserting a retired shape.
VA_KEYS = VISUAL_FIELDS


def _cmd():
    return COMMAND.read_text(encoding="utf-8")


def _agent():
    return AGENT.read_text(encoding="utf-8")


def _save_json_blobs(text):
    blobs = []
    for m in re.finditer(r"save-json '(\{.*?\})'", text):
        blobs.append(json.loads(m.group(1)))
    return blobs


def test_command_and_agent_carry_no_generic_spine_or_kit_branch():
    for text in (_cmd(), _agent()):
        assert "## Generic spine" not in text
        assert "## dnd5e branch" not in text
        assert "stat_schema" not in text
        for phrase in ("Detect the kit", "active kit", "World Kit", "ruleset.json"):
            assert phrase not in text, phrase


def test_creation_walks_the_five_e_path():
    for text in (_cmd(), _agent()):
        assert "get_races.py" in text
        assert "get_classes.py" in text
        assert "get_spells.py" in text
        assert "Hit Die max + Constitution" in text
        assert "Step 2 - Race" in text
        assert "Step 3 - Class" in text or "Step 4 - Background" in text


def test_no_ascii_art_or_ascii_interface_mandate():
    for text in (_cmd(), _agent()):
        lower = text.lower()
        assert "ascii interface" not in lower
        assert "ascii art" not in lower
        assert "ascii-art" not in lower
        assert "phone-friendly" in lower


def test_step_numbers_do_not_skip_2():
    for text in (_cmd(), _agent()):
        assert "Step 2 -" in text
        # Old bug: Step 1 - Introduction jumped to Step 3 - Background.
        intro = text.find("Step 1 - Introduction")
        assert intro != -1
        window = text[intro:intro + 600]
        assert "Step 2 -" in window
        assert not re.search(
            r"Step 1 - Introduction\s*\n\s*\n\s*\*?Step 3 - Background", text
        )


def test_save_json_examples_include_hp_and_visual_appearance():
    for text in (_cmd(), _agent()):
        blobs = _save_json_blobs(text)
        assert blobs, "expected at least one save-json JSON example"
        for blob in blobs:
            assert "hp" in blob, blob.keys()
            va = blob.get("visual_appearance")
            assert isinstance(va, dict), blob.keys()
            for key in VA_KEYS:
                assert key in va, key


def test_claude_md_death_protocol_routes_new_character_to_five_e_creation():
    text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    start = text.index("SWAP")
    swap = text[start:text.index("## Action Router", start)]
    assert "create-character" in swap
    assert "5e" in swap
    assert "kit" not in swap.lower()


def test_gm_player_banner_is_kit_neutral():
    text = (ROOT / "tools" / "gm-player.sh").read_text(encoding="utf-8")
    assert "D&D Player Character Manager" not in text
    assert "Player Character management for D&D campaign" not in text
    assert "Player Character Manager" in text


def test_nameless_traveler_saves_without_race_or_class(tmp_path):
    """The onboarding route saves a sheet before race/class are chosen, so neither
    may be required — and the missing class must not crash the save derivations."""
    from lib.schemas import validate_character
    from lib.world_kit import WorldKit

    world = _make_world(tmp_path, "forgotten-realms")
    r = _save(world, {
        "name": "Nameless", "level": 1,
        "stats": {"str": 16, "dex": 12, "con": 15, "int": 10, "wis": 13, "cha": 8},
    })
    assert r.returncode == 0, r.stdout + r.stderr
    sheet = _sheet(world)
    assert sheet["race"] == "" and sheet["class"] == ""
    assert sheet["saves"]["str"] == 3          # +3 mod, no class proficiency
    ok, errs = validate_character(sheet, WorldKit(str(world)))
    assert ok, errs


def test_partial_stat_block_does_not_break_saves(tmp_path):
    """An unrolled stat scores as 10 rather than taking the save block out."""
    world = _make_world(tmp_path, "forgotten-realms")
    r = _save(world, {"name": "Half-Rolled", "level": 1, "stats": {"str": 16}})
    assert r.returncode == 0, r.stdout + r.stderr
    saves = _sheet(world)["saves"]
    assert saves["str"] == 3 and saves["cha"] == 0
