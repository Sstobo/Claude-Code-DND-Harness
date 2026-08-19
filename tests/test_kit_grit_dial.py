"""QA eval for the lethality classifier.

`game_core.classify_harm` stays configurable — gritty, `none`, and a lowered
massive-damage bar are all still honored by the core — but the kit no longer
dials it: `WorldKit.lethality()` is hardcoded 5e death saves. Pure calculator;
no death-save ceremony (that's the caller's).
"""

from lib.game_core import classify_harm
from lib.world_kit import WorldKit


def test_death_saves_default_matches_5e():
    # drop to 0 but not massive overkill -> the dying gate, not death
    assert classify_harm(5, 20, 5)["outcome"] == "dying"
    # massive overkill (damage past 0 >= max HP) -> dead outright (5e massive damage)
    assert classify_harm(5, 20, 30)["outcome"] == "dead"          # overkill 25 >= 20
    # survivable hit
    assert classify_harm(20, 20, 5) == {"new_hp": 15, "outcome": "ok"}


def test_gritty_kills_at_zero_no_saves():
    assert classify_harm(5, 20, 5, {"model": "gritty"})["outcome"] == "dead"
    assert classify_harm(20, 20, 5, {"model": "gritty"})["outcome"] == "ok"


def test_lower_massive_threshold_is_more_lethal():
    # default: overkill 8 < 20 -> only dying
    assert classify_harm(5, 20, 13)["outcome"] == "dying"                     # overkill 8
    # kit lowers the massive-damage bar to 8 -> that same hit kills
    assert classify_harm(5, 20, 13, {"massive_damage_at": 8})["outcome"] == "dead"


def test_none_never_instant_kills():
    # huge damage, model 'none' -> still just the dying gate, no instant death
    assert classify_harm(5, 20, 100, {"model": "none"})["outcome"] == "dying"


def test_worldkit_lethality_is_5e_death_saves(dcc_world):
    """The kit is hardcoded 5e: death saves, massive-damage bar left at max HP."""
    assert WorldKit(dcc_world).lethality() == {"model": "death-saves"}
