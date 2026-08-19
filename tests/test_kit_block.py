"""KIT block in scene context; campaign_rules renders as YOUR WORLD'S RULES."""

import json

from lib.session_manager import SessionManager
from lib.world_kit import WorldKit


def _world(tmp_path, slug, overview=None):
    world = tmp_path / "world-state"
    campaign = world / "campaigns" / slug
    campaign.mkdir(parents=True)
    (world / "active-campaign.txt").write_text(slug, encoding="utf-8")
    (campaign / "campaign-overview.json").write_text(
        json.dumps(overview or {"name": slug}), encoding="utf-8"
    )
    return str(world)


def _kit_section(ctx: str) -> str:
    assert "--- KIT ---" in ctx
    rest = ctx.split("--- KIT ---", 1)[1]
    nxt = rest.find("\n--- ")
    return rest if nxt < 0 else rest[:nxt]


# --- scene context -----------------------------------------------------------

def test_context_kit_block_names_dnd5e_d20_xp_levels(dcc_world):
    ctx = SessionManager(dcc_world).get_full_context()
    kit = _kit_section(ctx)
    assert "kit: dnd5e" in kit
    assert "resolution: d20-vs-dc" in kit
    assert "progression: xp-levels" in kit
    assert "vitals: hp" in kit


def test_campaign_rules_render_as_world_rules(tmp_path):
    world = _world(tmp_path, "legacy", overview={
        "name": "legacy",
        "campaign_rules": {"loot_box_system": "award a distinctive zzyzx box"},
    })
    ctx = SessionManager(world).get_full_context()
    assert "YOUR WORLD'S RULES" in ctx
    assert "loot_box_system" in ctx
    assert "zzyzx" in ctx


def test_dcc_still_renders_campaign_rules(dcc_world):
    ctx = SessionManager(dcc_world).get_full_context()
    assert "loot_box_system" in ctx


def test_kit_block_skipped_when_worldkit_fails(dcc_world, monkeypatch):
    def boom(*_a, **_k):
        raise RuntimeError("no campaign")

    monkeypatch.setattr("lib.session_manager.WorldKit", boom)
    ctx = SessionManager(dcc_world).get_full_context()
    assert "--- KIT ---" not in ctx
    assert "SESSION CONTEXT" in ctx
    assert "loot_box_system" in ctx  # campaign_rules still renders


# --- WorldKit accessors ------------------------------------------------------

def test_worldkit_is_5e_regardless_of_campaign(dcc_world):
    kit = WorldKit(dcc_world)
    assert kit.kit() == "dnd5e"
    assert kit.resolution_model() == "d20-vs-dc"
    assert kit.progression_model() == "xp-levels"
    assert kit.skills() == []
    assert kit.signature_systems() == []


def test_a_stale_ruleset_json_is_ignored(dcc_world):
    """The DCC fixture still ships a resource-axis ruleset.json; the kit is 5e anyway."""
    kit = WorldKit(dcc_world)
    assert kit.name() == "D&D 5e"
    assert kit.stat_schema()["attributes"] == ["str", "dex", "con", "int", "wis", "cha"]
