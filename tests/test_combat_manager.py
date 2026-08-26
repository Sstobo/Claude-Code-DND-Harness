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
    # By name, not by position: the roster is sorted by rolled initiative.
    hp = {c["name"]: c["hp_current"] for c in m._load()["combatants"]}
    assert hp == {"Goblin": 6, "Goblin 2": 5, "Goblin 3": 4, "Goblin 4": 3}


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


def test_null_primary_keys_fall_back_to_the_sibling(dcc_world):
    """Homebrew-adapted blocks carry explicit nulls where the SRD omits the key."""
    m = CombatManager(dcc_world)
    m.start()
    c = m.add_combatant(stat_block={
        "name": "Null-HP Horror",
        "armor_class": [{"value": 17}], "hit_points": None, "hp": 30,
    })
    assert c["hp_max"] == 30 and c["hp_current"] == 30, "null hit_points must fall back to hp"
    assert c["ac"] == 17
    c = m.add_combatant(stat_block={
        "name": "Null-AC Horror", "hp": 12,
        "armor_class": None, "ac": 17,
        "challenge_rating": None, "cr": 2,
        "actions": None, "attacks": [{"name": "Claw"}],
    })
    assert c["ac"] == 17, "null armor_class must fall back to ac, not default to 10"
    assert c["cr"] == 2
    assert c["attacks"][0]["name"] == "Claw"


@pytest.mark.parametrize("armor_class", [[], "17 (natural armor)", {}, None])
def test_unreadable_armor_class_still_falls_back_to_ac(dcc_world, armor_class):
    """A present-but-unreadable armor_class must not shadow the `ac` sibling."""
    m = CombatManager(dcc_world)
    m.start()
    c = m.add_combatant(stat_block={
        "name": "Adapted Brute", "hp": 12, "armor_class": armor_class, "ac": 17,
    })
    assert c["ac"] == 17, f"armor_class={armor_class!r} should fall through to ac"


def test_empty_or_zero_primaries_yield_to_populated_siblings(dcc_world):
    m = CombatManager(dcc_world)
    m.start()
    c = m.add_combatant(stat_block={
        "name": "Zero-HP Brute", "hit_points": 0, "hp": 30,
        "actions": [], "attacks": [{"name": "Slam"}],
    })
    assert c["hp_max"] == 30 and c["hp_current"] == 30, "0 hit_points must not arrive dead"
    assert c["attacks"] == [{"name": "Slam"}], "empty actions must not shadow attacks"


def test_zero_xp_and_cr_are_kept_as_written(dcc_world):
    """Empty is meaningful for xp/cr, so those keep the plain non-null fallback."""
    m = CombatManager(dcc_world)
    m.start()
    c = m.add_combatant(stat_block={"name": "Harmless Rat", "hp": 1, "xp": 0, "cr": 0})
    assert c["xp"] == 0 and c["cr"] == 0


def test_comma_formatted_xp_is_coerced(dcc_world):
    m = CombatManager(dcc_world)
    m.start()
    c = m.add_combatant(stat_block={"name": "Homebrew Wyrm", "hp": 40, "xp": "1,100"})
    assert c["xp"] == 1100
    m.modify_hp("Homebrew Wyrm", -100)
    assert m.end()["xp_awarded"] == 1100


def test_non_numeric_xp_is_refused(dcc_world):
    m = CombatManager(dcc_world)
    m.start()
    with pytest.raises(ValueError):
        m.add_combatant(stat_block={"name": "Vague Beast", "hp": 10, "xp": "lots"})


def test_non_numeric_xp_returns_the_error_envelope_via_cli(dcc_world, tmp_path):
    block = tmp_path / "vague.json"
    block.write_text(json.dumps({"name": "Vague Beast", "hp": 10, "xp": "lots"}), encoding="utf-8")
    r = _add_enemy_cli(dcc_world, "--stat-block-file", str(block))
    assert r.returncode == 1
    assert json.loads(r.stdout or r.stderr)["ok"] is False


def test_non_finite_xp_returns_the_error_envelope_via_cli(dcc_world, tmp_path):
    """`json.loads` accepts bare Infinity, and `int(inf)` raises OverflowError."""
    block = tmp_path / "endless.json"
    block.write_text('{"name": "Endless Horror", "hp": 10, "xp": Infinity}', encoding="utf-8")
    r = _add_enemy_cli(dcc_world, "--stat-block-file", str(block))
    assert r.returncode == 1
    assert json.loads(r.stdout or r.stderr)["ok"] is False


def test_end_survives_a_legacy_save_with_unvalidated_xp(dcc_world):
    """Saves written before xp validation may hold junk; the summary must still land."""
    m = CombatManager(dcc_world)
    m.start()
    m.add_combatant("Old Save Ghoul", hp=10)
    m.add_combatant("Good Ghoul", hp=10)
    data = m._load()
    m._find(data, "Old Save Ghoul")["xp"] = "lots"
    m._find(data, "Good Ghoul")["xp"] = "1,100"
    m._save(data)
    m.modify_hp("Old Save Ghoul", -50)
    m.modify_hp("Good Ghoul", -50)
    summary = m.end()
    assert summary["xp_awarded"] == 1100
    assert summary["xp_by_enemy"] == {"Good Ghoul": 1100}
    assert set(summary["defeated"]) == {"Old Save Ghoul", "Good Ghoul"}
    # Named, not silently dropped: end() clears the state, so this is the only
    # chance the GM has to notice the award is short.
    assert summary["xp_unreadable"] == ["Old Save Ghoul"]


def test_clean_end_reports_no_unreadable_xp(dcc_world):
    m = CombatManager(dcc_world)
    m.start()
    m.add_combatant(stat_block=GOBLIN_SRD)
    m.modify_hp("Goblin", -20)
    assert "xp_unreadable" not in m.end()


def test_combatant_without_name_or_hp_is_refused(dcc_world):
    m = CombatManager(dcc_world)
    m.start()
    with pytest.raises(ValueError):
        m.add_combatant("Nameless Thing")


def test_combat_is_optional(dcc_world):
    # Never starting combat is a valid state (narrated skirmish).
    assert CombatManager(dcc_world).is_active() is False
    assert CombatManager(dcc_world).header() == "(no active combat)"


# --- the attack resolver: the engine owns the math, so nobody can retype it ---

GOBLIN_ARMED = dict(
    GOBLIN_SRD,
    dexterity=14,
    actions=[{
        "name": "Scimitar",
        "desc": "Melee Weapon Attack: +4 to hit, reach 5 ft. Hit: 5 (1d6 + 2) slashing damage.",
        "attack_bonus": 4,
        "damage": [{"damage_type": {"name": "Slashing"}, "damage_dice": "1d6+2"}],
    }],
)


def _fixed(monkeypatch, *totals):
    """Force the next rolls, in order, so a resolution test is not a coin flip."""
    from lib import combat_manager as cm
    queue = list(totals)

    def fake(notation):
        total = queue.pop(0)
        die = total - _modifier(notation)
        out = {"notation": notation, "rolls": [die], "kept": [die],
               "modifier": _modifier(notation), "total": total}
        if "d20" in notation:
            if die == 20:
                out["natural_20"] = True
            elif die == 1:
                out["natural_1"] = True
        return out

    monkeypatch.setattr(cm._DICE, "roll", fake)


def _modifier(notation):
    for sep in ("+", "-"):
        if sep in notation:
            return int(notation[notation.index(sep):])
    return 0


def test_attack_uses_the_fetched_block_not_retyped_numbers(dcc_world, monkeypatch):
    m = CombatManager(dcc_world)
    m.start()
    m.add_combatant("Kordan", hp=50, ac=13, initiative=20, side="pc")
    m.add_combatant(stat_block=GOBLIN_ARMED, initiative=10)
    # to-hit 14 (10 + the block's +4), then 5 damage (3 + the block's +2)
    _fixed(monkeypatch, 14, 5)
    out = m.attack("Goblin", "Kordan", with_action="Scimitar")
    assert out["hit"] is True and out["target_ac"] == 13
    assert out["damage"] == 5
    assert m._find(m._load(), "Kordan")["hp_current"] == 45


def test_attack_fails_closed_with_no_block_and_no_explicit_numbers(dcc_world):
    m = CombatManager(dcc_world)
    m.start()
    m.add_combatant("Kordan", hp=50, ac=13, initiative=20, side="pc")
    m.add_combatant("Shadow", hp=10, ac=12, initiative=10)
    with pytest.raises(ValueError, match="no attack bonus"):
        m.attack("Shadow", "Kordan")


def test_nat_1_misses_and_nat_20_hits_whatever_the_ac(dcc_world, monkeypatch):
    m = CombatManager(dcc_world)
    m.start()
    m.add_combatant("Kordan", hp=50, ac=30, initiative=20, side="pc")
    m.add_combatant(stat_block=GOBLIN_ARMED, initiative=10)
    _fixed(monkeypatch, 24, 9)  # natural 20 against AC 30
    out = m.attack("Goblin", "Kordan", with_action="Scimitar")
    assert out["critical"] and out["hit"]
    assert out["damage_rolls"][0]["dice"] == "2d6+2", "a crit doubles the dice, not the modifier"
    _fixed(monkeypatch, 5)  # natural 1 against AC 30
    assert m.attack("Goblin", "Kordan", with_action="Scimitar")["hit"] is False


def test_zero_hp_downs_a_hero_but_kills_a_monster(dcc_world):
    m = CombatManager(dcc_world)
    m.start()
    m.add_combatant("Kordan", hp=50, ac=13, initiative=20, side="pc")
    m.add_combatant(stat_block=GOBLIN_ARMED, initiative=10)
    assert m.modify_hp("Goblin", -7)["outcome"] == "dead"
    hero = m.modify_hp("Kordan", -50)
    assert hero["outcome"] == "dying"
    assert hero["death_saves"] == {"successes": 0, "failures": 0}


def test_death_saves_tally_and_stop(dcc_world, monkeypatch):
    m = CombatManager(dcc_world)
    m.start()
    m.add_combatant("Kordan", hp=50, ac=13, initiative=20, side="pc")
    m.modify_hp("Kordan", -50)
    _fixed(monkeypatch, 2, 3, 4)
    for _ in range(2):
        m.death_save("Kordan")
    assert m.death_save("Kordan")["status"] == "dead"
    with pytest.raises(ValueError, match="no more death saves"):
        m.death_save("Kordan")


def test_a_nat_20_death_save_stands_the_hero_up(dcc_world, monkeypatch):
    m = CombatManager(dcc_world)
    m.start()
    m.add_combatant("Kordan", hp=50, ac=13, initiative=20, side="pc")
    m.modify_hp("Kordan", -50)
    _fixed(monkeypatch, 20)
    out = m.death_save("Kordan")
    assert out["status"] == "revived"
    assert m._find(m._load(), "Kordan")["hp_current"] == 1


def test_end_does_not_count_a_downed_hero_as_a_kill(dcc_world):
    m = CombatManager(dcc_world)
    m.start()
    m.add_combatant("Kordan", hp=50, ac=13, initiative=20, side="pc")
    m.add_combatant(stat_block=GOBLIN_ARMED, initiative=10)
    m.modify_hp("Kordan", -50)
    m.modify_hp("Goblin", -7)
    summary = m.end()
    assert summary["defeated"] == ["Goblin"]
    assert summary["down"] == ["Kordan"]
    assert summary["xp_awarded"] == 50


def test_join_pc_reads_the_sheet_and_damage_writes_back_to_it(dcc_world):
    """combat_state.json is deleted by `end` — the PC's HP has to live on the sheet."""
    from lib.player_manager import PlayerManager

    m = CombatManager(dcc_world)
    m.start()
    pc = m.join_pc(initiative=15)
    assert pc["name"] == "Tandy" and pc["hp_current"] == 72 and pc["hp_max"] == 80
    m.modify_hp("Tandy", -12)
    assert PlayerManager(dcc_world)._load_character()["hp"]["current"] == 60


def test_next_turn_steps_over_the_fallen_but_not_the_dying(dcc_world):
    """A corpse has no turn; a dying hero's turn is when they roll a death save."""
    m = CombatManager(dcc_world)
    m.start()
    m.add_combatant("Kordan", hp=50, ac=13, initiative=30, side="pc")
    m.add_combatant("Goblin", hp=7, ac=15, initiative=20)
    m.add_combatant("Anselm", hp=24, ac=16, initiative=10, side="ally")
    m.modify_hp("Goblin", -7)   # dead — skipped
    m.modify_hp("Anselm", -24)  # dying — still gets a turn

    order = [m.next_turn()["turn_index"] for _ in range(3)]
    names = [m._load()["combatants"][i]["name"] for i in order]
    assert names == ["Anselm", "Kordan", "Anselm"], names
    assert m._load()["round"] == 2, "one wrap in three turns, so one new round"


def test_the_round_panel_shows_the_board_and_stays_open_on_the_right(dcc_world):
    """The HUD is deliberately borderless on the right — a closed box drifts on
    fonts that render █ double-width."""
    m = CombatManager(dcc_world)
    m.start()
    m.add_combatant(stat_block=GOBLIN_ARMED, initiative=20)
    m.add_combatant("Bandit", hp=11, ac=12, initiative=15)
    m.join_pc(initiative=1)
    m.modify_hp("Bandit", -11)
    m.modify_hp("Goblin", -4)

    panel = m.header()
    assert "── ROUND 1 " in panel
    assert "Bandit" in panel and "DEAD" in panel
    assert "WOUNDED" in panel or "BLOODIED" in panel
    assert "TANDY" in panel, "the PC gets the hero block, not a roster row"
    for line in panel.splitlines():
        assert not line.endswith(("│", "║")), f"no right border: {line!r}"


def test_the_panel_marks_the_heros_turn_and_their_death_saves(dcc_world):
    m = CombatManager(dcc_world)
    m.start()
    m.add_combatant(stat_block=GOBLIN_ARMED, initiative=1)
    m.join_pc(initiative=20)
    # Exactly to 0: no overkill, so this is the dying gate rather than massive damage.
    m.modify_hp("Tandy", -72)

    panel = m.header()
    assert "▸ TANDY" in panel, "the turn marker moves to the hero block"
    assert "death saves 0✓/0✗" in panel


def test_resistance_halves_and_immunity_zeroes_the_damage(dcc_world, monkeypatch):
    """A raging barbarian is the commonest resistance case at the table; doing it
    by hand is the arithmetic this resolver exists to take."""
    m = CombatManager(dcc_world)
    m.start()
    m.add_combatant("Kordan", hp=50, ac=13, initiative=20, side="pc")
    m.add_combatant(stat_block=GOBLIN_ARMED, initiative=10)

    _fixed(monkeypatch, 24, 7)  # hit, then 7 damage
    out = m.attack("Goblin", "Kordan", with_action="Scimitar", defence="resist")
    assert out["damage"] == 3, "halved and rounded DOWN"
    assert out["damage_raw"] == 7
    assert m._find(m._load(), "Kordan")["hp_current"] == 47

    _fixed(monkeypatch, 24, 7)
    assert m.attack("Goblin", "Kordan", with_action="Scimitar", defence="immune")["damage"] == 0
