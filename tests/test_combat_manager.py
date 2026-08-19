"""Tests for combat-state-persistence: resumable, truthful combat state."""

import json
import os
import subprocess
from pathlib import Path

import pytest

from lib.combat_manager import CombatManager

ROOT = Path(__file__).resolve().parent.parent

# The shape `features/dnd-api/monsters/dnd_monster.py goblin` prints (trimmed).
GOBLIN_SRD = {
    "index": "goblin", "name": "Goblin",
    "armor_class": [{"type": "armor", "value": 15}],
    "hit_points": 7, "hit_dice": "2d6",
    "challenge_rating": 0.25, "xp": 50,
    "actions": [{"name": "Scimitar", "desc": "Melee Weapon Attack: +4 to hit."}],
}

# The condensed `--combat` view of the same creature.
GOBLIN_COMBAT = {
    "name": "Goblin", "cr": 0.25, "xp": 50, "hp": 7,
    "ac": [{"value": 15, "type": "armor"}],
    "attacks": [{"name": "Scimitar", "desc": "Melee Weapon Attack: +4 to hit."}],
}


def test_start_and_add_enemy(dcc_world):
    m = CombatManager(dcc_world)
    m.start()
    c = m.add_combatant("Orc Warrior", hp=22, ac=17, initiative=12)
    assert c["hp_current"] == 22 and c["hp_max"] == 22 and c["ac"] == 17
    assert m.is_active()


def test_hp_survives_a_simulated_resume(dcc_world):
    m = CombatManager(dcc_world)
    m.start()
    m.add_combatant("Orc Warrior", hp=22, ac=17)
    m.modify_hp("Orc Warrior", -5)
    # New manager instance = fresh load from disk (simulates resume/compaction).
    resumed = CombatManager(dcc_world)
    c = resumed._find(resumed._load(), "Orc Warrior")
    assert c["hp_current"] == 17, "enemy HP must persist across a reload"


def test_hp_clamps_and_marks_dead(dcc_world):
    m = CombatManager(dcc_world)
    m.start()
    m.add_combatant("Goblin", hp=7, ac=12)
    c = m.modify_hp("Goblin", -100)
    assert c["hp_current"] == 0
    assert "Goblin" in m.end()["defeated"]


def test_conditions_and_turns(dcc_world):
    m = CombatManager(dcc_world)
    m.start()
    m.add_combatant("A", hp=10, initiative=20)
    m.add_combatant("B", hp=10, initiative=5)
    m.set_condition("A", "add", "prone")
    assert "prone" in m._find(m._load(), "A")["conditions"]
    # A has higher initiative -> first; next-turn moves to B; another wraps to round 2.
    m.next_turn()
    assert m._load()["turn_index"] == 1
    m.next_turn()
    data = m._load()
    assert data["turn_index"] == 0 and data["round"] == 2


def test_end_clears_state(dcc_world):
    m = CombatManager(dcc_world)
    m.start()
    m.add_combatant("Orc", hp=10)
    m.end()
    assert not CombatManager(dcc_world).is_active()


def test_fetched_stat_block_becomes_the_enemy_record(dcc_world):
    m = CombatManager(dcc_world)
    m.start()
    c = m.add_combatant(stat_block=GOBLIN_SRD, initiative=14)
    assert c["name"] == "Goblin"
    assert c["ac"] == 15 and c["hp_max"] == 7 and c["hp_current"] == 7
    assert c["xp"] == 50 and c["cr"] == 0.25
    assert c["attacks"][0]["name"] == "Scimitar"
    assert c["source"] == "srd"
    # ...and it survives a reload, so nobody retypes it after a resume.
    assert CombatManager(dcc_world)._find(CombatManager(dcc_world)._load(), "Goblin")["xp"] == 50


def test_combat_view_stat_block_maps_the_same(dcc_world):
    m = CombatManager(dcc_world)
    m.start()
    c = m.add_combatant(stat_block=GOBLIN_COMBAT)
    assert (c["ac"], c["hp_max"], c["xp"], c["cr"]) == (15, 7, 50, 0.25)


def test_explicit_args_override_the_block(dcc_world):
    m = CombatManager(dcc_world)
    m.start()
    c = m.add_combatant("Goblin Boss Kruk", hp=21, ac=17, stat_block=GOBLIN_SRD)
    assert c["name"] == "Goblin Boss Kruk" and c["hp_max"] == 21 and c["ac"] == 17
    assert c["xp"] == 50, "unoverridden fetched fields still carry"


def test_kill_awards_the_fetched_xp(dcc_world):
    m = CombatManager(dcc_world)
    m.start()
    m.add_combatant(stat_block=GOBLIN_SRD)
    m.add_combatant(stat_block=GOBLIN_SRD | {"name": "Goblin Archer"})
    m.add_combatant("Bandit", hp=11, ac=12)  # no block -> contributes no fetched XP
    m.modify_hp("Goblin", -20)
    m.modify_hp("Bandit", -20)
    summary = m.end()
    assert summary["xp_awarded"] == 50, "only the defeated goblin's fetched XP"
    assert summary["xp_by_enemy"] == {"Goblin": 50}
    assert set(summary["defeated"]) == {"Goblin", "Bandit"}


def test_four_goblins_are_four_damageable_combatants(dcc_world):
    m = CombatManager(dcc_world)
    m.start()
    names = [m.add_combatant(stat_block=GOBLIN_SRD)["name"] for _ in range(4)]
    assert names == ["Goblin", "Goblin 2", "Goblin 3", "Goblin 4"]
    # Each one takes its own damage instead of the first shadowing the rest.
    for i, n in enumerate(names):
        m.modify_hp(n, -(i + 1))
    assert [c["hp_current"] for c in m._load()["combatants"]] == [6, 5, 4, 3]


def test_duplicate_manual_names_are_suffixed_too(dcc_world):
    m = CombatManager(dcc_world)
    m.start()
    assert m.add_combatant("Bandit", 11)["name"] == "Bandit"
    assert m.add_combatant("Bandit", 11)["name"] == "Bandit 2"


def test_xp_fields_agree_for_multiples(dcc_world):
    m = CombatManager(dcc_world)
    m.start()
    for _ in range(4):
        m.add_combatant(stat_block=GOBLIN_SRD)
    for c in list(m._load()["combatants"]):
        m.modify_hp(c["name"], -20)
    summary = m.end()
    assert summary["xp_awarded"] == 200
    assert sum(summary["xp_by_enemy"].values()) == summary["xp_awarded"]
    assert len(summary["xp_by_enemy"]) == 4


def test_manual_signature_still_works(dcc_world):
    m = CombatManager(dcc_world)
    c = m.add_combatant("Orc Warrior", 22, ac=17, initiative=12)
    assert c["hp_max"] == 22 and c["ac"] == 17 and "xp" not in c
    assert m.end()["xp_awarded"] == 0


def _add_enemy_cli(dcc_world, *args):
    """Run the real wrapper against the throwaway world-state."""
    env = {**os.environ, "GM_WORLD_STATE_BASE": dcc_world}
    return subprocess.run(["bash", str(ROOT / "tools" / "gm-combat.sh"), "add-enemy",
                           *args, "--json"],
                          cwd=ROOT, env=env, capture_output=True, text=True)


@pytest.mark.parametrize("content", ["", "not json at all", "{broken"])
def test_bad_stat_block_file_returns_the_error_envelope(dcc_world, tmp_path, content):
    bad = tmp_path / "bad.json"
    bad.write_text(content, encoding="utf-8")
    r = _add_enemy_cli(dcc_world, "--stat-block-file", str(bad))
    assert r.returncode == 1
    assert json.loads(r.stdout or r.stderr)["ok"] is False


def test_good_stat_block_file_via_cli(dcc_world, tmp_path):
    good = tmp_path / "goblin.json"
    good.write_text(json.dumps(GOBLIN_SRD), encoding="utf-8")
    r = _add_enemy_cli(dcc_world, "--stat-block-file", str(good))
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)["data"]
    assert (data["name"], data["ac"], data["hp_max"], data["xp"]) == ("Goblin", 15, 7, 50)


def test_combatant_without_name_or_hp_is_refused(dcc_world):
    m = CombatManager(dcc_world)
    m.start()
    with pytest.raises(ValueError):
        m.add_combatant("Nameless Thing")


def test_combat_is_optional(dcc_world):
    # Never starting combat is a valid state (narrated skirmish).
    assert CombatManager(dcc_world).is_active() is False
    assert CombatManager(dcc_world).header() == "(no active combat)"
