"""Fixes from running every documented tools/ command against a sandbox.

Each of these was a wrapper that accepted a documented invocation and did
something other than what the doc promised — silently. The runs go through the
real bash wrappers, pinned to a tmp world-state so the live campaign is never
touched.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
FIXTURE_CAMPAIGN = Path(__file__).parent / "fixtures" / "world-state" / "campaigns" / "dungeon-crawler-carl"


@pytest.fixture
def campaign(isolated_world_state):
    name = "sweep"
    shutil.copytree(FIXTURE_CAMPAIGN, isolated_world_state / "campaigns" / name)
    (isolated_world_state / "active-campaign.txt").write_text(name + "\n")
    return isolated_world_state / "campaigns" / name


def _run(*args):
    return subprocess.run(["bash", *args], cwd=PROJECT_ROOT, capture_output=True, text=True)


def test_search_takes_a_trailing_integer_as_the_count(campaign):
    """`--rag-only "<q>" 30` is the form the extractor agents use. It used to
    be dropped on the floor: every such call got the default 4."""
    r = _run("tools/gm-search.sh", "--rag-only", "anything", "30")
    # No vectors in the fixture, so retrieval itself stops early — but the
    # count must have been parsed, and a second word must not be.
    assert "unexpected argument" not in r.stderr
    r = _run("tools/gm-search.sh", "anything", "second-query")
    assert r.returncode == 1 and "unexpected argument" in r.stderr


def test_gold_refuses_a_number_where_the_name_goes(campaign):
    """`gold +10` used to take "+10" as the name, print someone's balance, exit 0."""
    r = _run("tools/gm-player.sh", "gold", "+10")
    assert r.returncode == 1
    assert "Usage: gm-player.sh gold <character_name>" in r.stdout


def test_stage_on_an_empty_pack_is_a_nonzero_exit(campaign):
    r = _run("tools/gm-playpack.sh", "stage")
    assert r.returncode == 1, r.stdout
    assert json.loads(r.stdout)["ok"] is False


def test_unify_tags_is_reachable_without_a_name(campaign):
    """The handler existed in npc_manager.py; the wrapper's name gate hid it."""
    r = _run("tools/gm-npc.sh", "unify-tags")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "unified" in r.stdout.lower()


def test_migrate_honours_the_isolation_seam(campaign, isolated_world_state):
    """It hardcoded the live world-state and ignored GM_WORLD_STATE_BASE."""
    r = _run("tools/gm-migrate-campaigns.sh")
    assert r.returncode == 0
    assert str(isolated_world_state) in r.stdout
    assert str(PROJECT_ROOT / "world-state") not in r.stdout


def test_clock_bare_call_shows_argument_shapes():
    r = _run("tools/gm-clock.sh")
    assert r.returncode == 0
    assert "add <name> <segments>" in r.stdout
