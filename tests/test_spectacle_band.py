"""Spectacle XP scales off the level's full band, never the gap remaining.

The gap basis paid the same act 10x more just after a level-up than just
before it, and made minors a geometric series that could never level anyone.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from game_core import spectacle_award


def test_position_in_the_level_does_not_change_the_award():
    """The bug this exists to pin: fresh-into-L5 vs one-roll-from-L6."""
    band = 7500
    fresh = spectacle_award('minor', progression_model='xp-levels', xp_band=band)
    nearly = spectacle_award('minor', progression_model='xp-levels', xp_band=band)
    assert fresh['xp'] == nearly['xp'] == 375


def test_tiers_ladder_against_level_5_combat_xp():
    """minor ≈ CR 1 kill, major ≈ CR 3-4, legendary ≈ a hard encounter —
    spectacle competes with combat without outbidding it."""
    band = 7500
    xs = {t: spectacle_award(t, progression_model='xp-levels', xp_band=band)['xp']
          for t in ('minor', 'major', 'legendary')}
    assert xs == {'minor': 375, 'major': 1125, 'legendary': 2475}
    assert xs['legendary'] < band, "no single beat is a whole level"


def test_floors_still_protect_low_levels():
    """A level-1 band is 300 XP; 5% of it is 15 — the floor keeps a minor real."""
    a = spectacle_award('minor', progression_model='xp-levels', xp_band=300)
    assert a['xp'] == 50


def test_milestone_and_unknown_tier_paths_unchanged():
    assert spectacle_award('legendary', progression_model='milestone')['milestone'] == 1
    bad = spectacle_award('mythic', progression_model='xp-levels', xp_band=1000)
    assert not bad['ok'] and 'mythic' in bad['error']
