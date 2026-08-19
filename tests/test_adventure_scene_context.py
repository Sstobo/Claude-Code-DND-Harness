"""Tests for the ADVENTURE block in the session brief.

The block only exists when the campaign is running a converted module, so the
absence case matters as much as the presence one: a campaign with no
adventure.json must get exactly the brief it got before this block existed.
"""

import json
import subprocess
from pathlib import Path

from lib.adventure import AdventureManager
from lib.session_manager import SessionManager

PROJECT_ROOT = Path(__file__).parent.parent

SPINE = [
    {"key": "tavern", "title": "The Sleeping Giant", "pages": [3]},
    {"key": "road", "title": "Ambush on the Road", "pages": [5]},
    {"key": "keep", "title": "The Ruined Keep", "pages": [7]},
]

BODIES = [
    {
        "key": "tavern",
        "location": "Phandalin",
        "read_aloud": "Smoke and spilled ale; the innkeeper will not meet your eye.",
        "gm_notes": "Toblen knows about the ambush but sells the news.",
        "checks": [{"what": "overhear the drovers", "skill": "Perception", "dc": 12}],
    },
    {
        "key": "road",
        "location": "Triboar Trail",
        "encounters": [{"name": "Goblin ambush",
                        "monsters": [{"name": "Goblin", "count": 4, "srd_index": "goblin"}]}],
    },
]


def _built(world_dir):
    m = AdventureManager(world_dir)
    m.init(SPINE, meta={"title": "Lost Mine"})
    m.merge(BODIES)
    return m


def _context(world_dir):
    return SessionManager(world_dir).get_full_context()


def test_no_adventure_leaves_the_brief_untouched(dcc_world):
    ctx = _context(dcc_world)
    assert "ADVENTURE" not in ctx
    assert "gm-adventure.sh" not in ctx


def test_adventure_block_carries_the_current_scene(dcc_world):
    _built(dcc_world)
    ctx = _context(dcc_world)
    assert "--- ADVENTURE: Lost Mine" in ctx
    assert "Current scene: tavern The Sleeping Giant" in ctx
    assert "Location: Phandalin" in ctx
    assert "Toblen knows about the ambush" in ctx
    assert "READ-ALOUD" in ctx
    assert "spilled ale" in ctx
    assert "Check: Perception DC 12 — overhear the drovers" in ctx
    assert "gm-adventure.sh advance" in ctx


def test_next_per_the_book_names_the_following_scene(dcc_world):
    _built(dcc_world)
    assert "Next per the book: road Ambush on the Road" in _context(dcc_world)


def test_next_line_follows_a_transition_over_spine_order(dcc_world):
    m = _built(dcc_world)
    m.merge([{"key": "tavern", "transitions": [{"to_key": "keep", "when": "they ride hard"}]}])
    assert "Next per the book: keep The Ruined Keep" in _context(dcc_world)


def test_block_follows_the_pointer_after_advance(dcc_world):
    m = _built(dcc_world)
    m.advance()
    ctx = _context(dcc_world)
    assert "Current scene: road Ambush on the Road" in ctx
    assert "Encounter: Goblin ambush — Goblin x4" in ctx
    assert "Next per the book: keep The Ruined Keep" in ctx


def test_last_scene_has_no_next_line(dcc_world):
    m = _built(dcc_world)
    m.jump("keep")
    ctx = _context(dcc_world)
    assert "Current scene: keep The Ruined Keep" in ctx
    assert "Next per the book:" not in ctx


def test_unreadable_adventure_does_not_break_the_brief(dcc_world):
    _built(dcc_world)
    active = (Path(dcc_world) / "active-campaign.txt").read_text().strip()
    path = Path(dcc_world) / "campaigns" / active / "adventure.json"
    path.write_text("{ not json at all")
    ctx = _context(dcc_world)
    assert "=== SESSION CONTEXT ===" in ctx
    assert "ADVENTURE" not in ctx


def test_wrapper_context_shows_the_block(isolated_world_state):
    """End to end through the real wrappers, against a throwaway world-state."""
    env = {"GM_WORLD_STATE_BASE": str(isolated_world_state)}
    campaign_dir = isolated_world_state / "campaigns" / "wrapper-test"
    campaign_dir.mkdir(parents=True)
    (campaign_dir / "campaign-overview.json").write_text(json.dumps({"name": "Wrapper Test"}))
    (isolated_world_state / "active-campaign.txt").write_text("wrapper-test")

    spine = campaign_dir / "spine.json"
    spine.write_text(json.dumps(SPINE))
    import os
    run_env = {**os.environ, **env}
    # init is not on the wrapper — the converter calls the module directly.
    subprocess.run(["uv", "run", "python", "lib/adventure.py", "init", str(spine),
                    "--title", "Lost Mine"],
                   cwd=PROJECT_ROOT, env=run_env, check=True, capture_output=True)

    out = subprocess.run(["bash", "tools/gm-session.sh", "context"],
                         cwd=PROJECT_ROOT, env=run_env, check=True,
                         capture_output=True, text=True).stdout
    assert "--- ADVENTURE: Lost Mine" in out
    assert "Current scene: tavern The Sleeping Giant" in out
    assert "Next per the book: road Ambush on the Road" in out

    subprocess.run(["bash", "tools/gm-adventure.sh", "advance"],
                   cwd=PROJECT_ROOT, env=run_env, check=True, capture_output=True)
    out2 = subprocess.run(["bash", "tools/gm-session.sh", "context"],
                          cwd=PROJECT_ROOT, env=run_env, check=True,
                          capture_output=True, text=True).stdout
    assert "Current scene: road Ambush on the Road" in out2
