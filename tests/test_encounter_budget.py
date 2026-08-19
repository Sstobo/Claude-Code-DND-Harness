"""Tests for the DMG XP-budget encounter math (pure functions, no network)."""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = ROOT / "features" / "dnd-api" / "monsters" / "dnd_encounter_v2.py"

_spec = importlib.util.spec_from_file_location("dnd_encounter_v2", MODULE_PATH)
enc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(enc)


def test_hard_budget_for_four_level_three_characters():
    assert enc.xp_budget(3, 4, "hard") == 900


def test_thresholds_scale_with_party_size():
    assert enc.party_thresholds(3, 4) == {"easy": 300, "medium": 600, "hard": 900, "deadly": 1600}
    assert enc.party_thresholds(1, 1) == {"easy": 25, "medium": 50, "hard": 75, "deadly": 100}
    assert enc.xp_budget(20, 5, "deadly") == 63500


def test_every_level_one_to_twenty_has_ascending_thresholds():
    assert sorted(enc.XP_THRESHOLDS) == list(range(1, 21))
    for level, row in enc.XP_THRESHOLDS.items():
        assert len(row) == 4, level
        assert list(row) == sorted(row), level


def test_bad_inputs_are_rejected():
    with pytest.raises(ValueError):
        enc.xp_budget(21, 4, "hard")
    with pytest.raises(ValueError):
        enc.xp_budget(3, 4, "lethal")
    with pytest.raises(ValueError):
        enc.encounter_multiplier(0)


@pytest.mark.parametrize("count,expected", [
    (1, 1.0), (2, 1.5), (3, 2.0), (6, 2.0), (7, 2.5),
    (10, 2.5), (11, 3.0), (14, 3.0), (15, 4.0), (20, 4.0),
])
def test_multiplier_boundaries_for_a_normal_party(count, expected):
    assert enc.encounter_multiplier(count, party_size=4) == expected
    assert enc.encounter_multiplier(count, party_size=5) == expected


@pytest.mark.parametrize("count,expected", [
    (1, 1.5), (2, 2.0), (3, 2.5), (6, 2.5), (7, 3.0), (15, 4.0),
])
def test_small_party_shifts_one_step_up(count, expected):
    assert enc.encounter_multiplier(count, party_size=2) == expected
    assert enc.encounter_multiplier(count, party_size=1) == expected


@pytest.mark.parametrize("count,expected", [
    (1, 0.5), (2, 1.0), (3, 1.5), (6, 1.5), (7, 2.0), (11, 2.5), (15, 3.0),
])
def test_large_party_shifts_one_step_down(count, expected):
    assert enc.encounter_multiplier(count, party_size=6) == expected
    assert enc.encounter_multiplier(count, party_size=8) == expected


@pytest.mark.parametrize("adjusted,band", [
    (299, "trivial"),
    (300, "easy"),
    (599, "easy"),
    (600, "medium"),
    (899, "medium"),
    (900, "hard"),
    (1599, "hard"),
    (1600, "deadly"),
    (5000, "deadly"),
])
def test_band_classification_for_four_level_three_characters(adjusted, band):
    assert enc.classify_difficulty(adjusted, 3, 4) == band


@pytest.mark.parametrize("difficulty", enc.DIFFICULTIES)
@pytest.mark.parametrize("party_size", range(1, 9))
@pytest.mark.parametrize("level", range(1, 21))
def test_planned_encounters_land_in_the_requested_band(level, party_size, difficulty):
    plan = enc.plan_encounter(level, party_size, difficulty)
    assert plan["adjusted_xp"] == plan["raw_xp"] * plan["multiplier"]
    assert plan["multiplier"] == enc.encounter_multiplier(plan["count"], party_size)

    band = enc.classify_difficulty(plan["adjusted_xp"], level, party_size)
    assert band == plan["band"]
    if band != difficulty:
        # The only licensed miss: no combination exists in the band. Say which
        # band it really is rather than reporting a clean hit.
        assert plan["note"] and band in plan["note"], plan
    else:
        assert "note" not in plan


def test_a_medium_request_never_comes_back_hard():
    # The reported overshoot: one CR 1/4 monster for a solo level 1 character is
    # 75 adjusted XP, which is exactly that party's hard floor.
    plan = enc.plan_encounter(1, 1, "medium")
    assert enc.classify_difficulty(plan["adjusted_xp"], 1, 1) != "hard" or plan.get("note")


@pytest.mark.parametrize("difficulty,expected", [
    ("easy", (300, 600)), ("medium", (600, 900)), ("hard", (900, 1600)),
])
def test_band_window_stops_at_the_next_bands_floor(difficulty, expected):
    assert enc.band_window(3, 4, difficulty) == expected


def test_deadly_window_gets_headroom_instead_of_a_next_floor():
    floor, ceiling = enc.band_window(3, 4, "deadly")
    assert floor == 1600 and ceiling == 2000


def test_in_band_plans_carry_no_note_and_sort_first():
    ranked = enc.rank_plans(5, 4, "medium")
    noted = [i for i, p in enumerate(ranked) if "note" in p]
    clean = [i for i, p in enumerate(ranked) if "note" not in p]
    assert clean and noted
    assert max(clean) < min(noted), "plans that hit the band must all sort ahead of the rest"
    for p in ranked:
        if "note" not in p:
            assert p["band"] == "medium"


def test_planned_encounter_respects_a_cr_hint():
    plan = enc.plan_encounter(5, 4, "hard", cr_hint=2)
    assert plan["cr"] == 2
    assert plan["raw_xp"] == plan["count"] * enc.CR_XP[2]
    assert enc.classify_difficulty(plan["adjusted_xp"], 5, 4) == "hard"


def test_ranked_plans_lead_with_the_in_band_ones():
    ranked = enc.rank_plans(3, 4, "hard")
    assert ranked[0] == enc.plan_encounter(3, 4, "hard")
    in_band = [p for p in ranked if enc.classify_difficulty(p["adjusted_xp"], 3, 4) == "hard"]
    assert ranked[:len(in_band)] == in_band, "in-band plans must all sort ahead of the rest"


def test_empty_cr_pool_falls_back_to_the_next_workable_cr():
    # The SRD really does have zero CR 18 monsters; the planner picks the CR, so
    # an empty pool must fall through instead of blowing up on an empty sample.
    ranked = enc.rank_plans(19, 4, "medium")
    empty_cr = ranked[0]["cr"]
    plan, warnings = enc.select_plan(ranked, lambda cr: [] if cr == empty_cr else ["some-monster"])
    assert plan is not None and plan["cr"] != empty_cr
    assert warnings and f"No SRD monsters at CR {empty_cr}" in warnings[0]


def test_a_workable_top_pick_earns_no_warning():
    ranked = enc.rank_plans(3, 4, "hard")
    plan, warnings = enc.select_plan(ranked, lambda cr: ["goblin"])
    assert plan == ranked[0]
    assert warnings == []


def test_every_cr_pool_empty_reports_rather_than_crashes():
    plan, warnings = enc.select_plan(enc.rank_plans(3, 4, "hard"), lambda cr: [])
    assert plan is None
    assert warnings and "No SRD monsters at any CR" in warnings[0]


@pytest.mark.parametrize("hint,expected", [(2, 2), (2.0, 2), (0.5, 0.5), (3.5, None), (31, None)])
def test_off_table_cr_hints_are_rejected_not_silently_dropped(hint, expected):
    assert enc.normalize_cr(hint) == expected


def test_cr_choices_names_the_fractional_ratings_readably():
    choices = enc.cr_choices()
    assert "1/8" in choices and "1/4" in choices and "1/2" in choices and "30" in choices


def test_summary_rates_the_monsters_in_hand_not_the_plan():
    plan = {"count": 4, "cr": 1, "raw_xp": 800, "multiplier": 2.0, "adjusted_xp": 1600}
    short = [{"name": "Bugbear", "xp": 200, "index": "bugbear"}] * 2
    summary = enc.summarize_encounter(short, plan, 3, 4, "hard")
    assert summary["count"] == 2
    assert summary["raw_xp"] == 400
    assert summary["multiplier"] == 1.5, "two monsters is a x1.5 fight, whatever the plan said"
    assert summary["adjusted_xp"] == 600
    assert summary["resulting_difficulty"] == "medium", "a short encounter must not report as hard"
    assert summary["planned_cr"] == 1


def test_summary_flags_duplicate_monsters():
    monsters = [{"name": "Goblin", "xp": 50}, {"name": "Goblin", "xp": 50}, {"name": "Wolf", "xp": 50}]
    summary = enc.summarize_encounter(monsters, {"count": 3, "cr": 0.25}, 1, 4, "medium")
    assert summary["duplicates"] == {"Goblin": 2}

    solo = enc.summarize_encounter([{"name": "Wolf", "xp": 50}], {"count": 1, "cr": 0.25}, 1, 4, "easy")
    assert "duplicates" not in solo


def test_non_deadly_plans_stay_under_the_deadly_line():
    for level in range(1, 21):
        for difficulty in ("easy", "medium", "hard"):
            plan = enc.plan_encounter(level, 4, difficulty)
            assert plan["adjusted_xp"] < enc.xp_budget(level, 4, "deadly"), (level, difficulty)
