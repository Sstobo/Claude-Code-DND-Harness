"""Tests for combat-state-persistence: resumable, truthful combat state."""

from lib.combat_manager import CombatManager


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


def test_combat_is_optional(dcc_world):
    # Never starting combat is a valid state (narrated skirmish).
    assert CombatManager(dcc_world).is_active() is False
    assert CombatManager(dcc_world).header() == "(no active combat)"
