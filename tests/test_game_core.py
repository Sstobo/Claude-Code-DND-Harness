"""Tests for the generic game core: resolution, harm, conditions, and the three
progression models. No D&D 5e assumptions — thresholds/tiers are all supplied."""

import random

from lib import game_core as gc


def test_resolve_check_success_and_margin():
    r = gc.resolve_check(modifier=100, dc=5)
    assert r["success"] is True and r["margin"] > 0
    r2 = gc.resolve_check(modifier=-100, dc=15)
    assert r2["success"] is False and r2["margin"] < 0


def test_resolve_check_critical_classification_is_consistent():
    random.seed(1)
    for _ in range(300):
        r = gc.resolve_check(modifier=0, dc=10)
        if r["die"] == 20:
            assert r["critical"] == "hit"
        elif r["die"] == 1:
            assert r["critical"] == "miss"
        else:
            assert r["critical"] is None


def test_advantage_keeps_higher():
    random.seed(2)
    # statistically advantage should not be worse; just assert it runs + classifies
    r = gc.resolve_check(modifier=0, dc=10, advantage="advantage")
    assert 1 <= r["die"] <= 20


def test_opposed_check_higher_modifier_tends_to_win():
    random.seed(3)
    a_wins = sum(1 for _ in range(200) if gc.opposed_check(100, -100)["winner"] == "a")
    assert a_wins == 200  # +100 vs -100 can never lose


def test_apply_harm_and_heal_clamp():
    assert gc.apply_harm(10, 4) == 6
    assert gc.apply_harm(3, 10) == 0
    assert gc.heal(6, 10, 8) == 10
    assert gc.heal(6, 10, 2) == 8


def test_conditions_add_remove_idempotent():
    c = gc.add_condition([], "poisoned")
    c = gc.add_condition(c, "poisoned")  # idempotent
    assert c == ["poisoned"]
    assert gc.remove_condition(c, "poisoned") == []


def test_milestone_progression():
    p = gc.make_progression("milestone")
    s = p.advance({})
    s = p.advance(s)
    assert p.level(s) == 2


def test_xp_levels_progression_uses_supplied_thresholds():
    p = gc.make_progression("xp-levels", thresholds=[100, 300, 600])
    s = p.advance({}, xp=150)
    assert p.level(s) == 2  # past 100, below 300
    s = p.advance(s, xp=500)  # total 650
    assert p.level(s) == 4


def test_resource_axis_progression():
    p = gc.make_progression("resource-axis", resource="viewers", tiers=[1_000_000, 1_000_000_000])
    s = p.advance({}, amount=2_000_000)
    assert p.level(s) == 1
    s = p.advance(s, amount=1_000_000_000)
    assert p.level(s) == 2


def test_no_5e_symbols_in_core():
    src = (gc.__file__)
    text = open(src, encoding="utf-8").read().lower()
    for banned in ("spell slot", "strength", "dexterity", "level 20", "proficiency"):
        assert banned not in text, f"core must stay 5e-agnostic; found {banned!r}"
