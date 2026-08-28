"""The character sheet shape gate.

Until 2026-08-27 `validate_character` required only name + level, and its one
ability-score check read `data['abilities']` — a key no writer has ever emitted.
Every sheet below passed. They are the regression suite now.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from schemas import (  # noqa: E402
    CharacterShapeError,
    assert_valid_character,
    validate_character,
)


def sheet(**overrides):
    """A minimal sheet the runtime can actually read."""
    base = {"name": "Kordan", "level": 5, "hp": {"current": 39, "max": 50}, "stats": {"str": 18}}
    base.update(overrides)
    return base


def test_a_good_sheet_passes():
    valid, errors = validate_character(sheet())
    assert valid, errors


def test_open_shape_still_accepted():
    """to_flat runs first, so the onboarding shape must keep validating."""
    valid, errors = validate_character({
        "identity": {"name": "Traveler"},
        "vitals": {"hp": {"current": 8, "max": 8}, "ac": 10},
        "attributes": {"dex": 12},
        "progression": {"level": 1},
    })
    assert valid, errors


@pytest.mark.parametrize("bad, because", [
    (sheet(stats=["str", 18]),            "stats as a list"),
    (sheet(stats={"str": "strong"}),      "a non-numeric ability score"),
    (sheet(equipment="a sword"),          "equipment as a string"),
    (sheet(conditions="poisoned"),        "conditions as a string"),
    (sheet(visual_appearance="tall"),     "visual_appearance as a string"),
    (sheet(saves=[1, 2]),                 "saves as a list"),
    ({"name": "Kordan", "level": 5},      "no hp at all"),
    (sheet(hp=39),                        "hp as a bare int"),
    (sheet(hp={"current": "full", "max": 50}), "non-numeric hp"),
    (sheet(level="five"),                 "a non-numeric level"),
    ({"level": 5, "hp": {"current": 1, "max": 1}}, "no name"),
])
def test_degenerate_sheets_are_refused(bad, because):
    valid, errors = validate_character(bad)
    assert not valid, f"should have been refused: {because}"
    assert errors


def test_empty_stats_still_allowed_for_now():
    """A PC with no ability scores is broken, but `dcc` is live with one and the
    backfill belongs to sheet-one-constructor. Pin the current behaviour so that
    ticket has to change this test deliberately."""
    valid, _ = validate_character(sheet(stats={}))
    assert valid


def test_assert_names_the_writer():
    with pytest.raises(CharacterShapeError) as excinfo:
        assert_valid_character(sheet(hp=39), source="gm-player.sh")
    assert "gm-player.sh" in str(excinfo.value)
    assert "hp" in str(excinfo.value)


def test_assert_is_silent_on_a_good_sheet():
    assert_valid_character(sheet(), source="test")


def test_live_campaign_sheets_still_pass():
    """The gate must not brick a campaign that predates it. Every sheet on disk
    was checked green when the gate landed (2026-08-27); a regression here means
    the gate tightened past what live data can satisfy — migrate first."""
    import json
    campaigns = Path(__file__).resolve().parents[1] / "world-state" / "campaigns"
    if not campaigns.exists():
        pytest.skip("no live campaigns")
    checked = 0
    for p in campaigns.glob("*/character.json"):
        valid, errors = validate_character(json.loads(p.read_text()))
        assert valid, f"{p.parent.name}: {errors}"
        checked += 1
    if not checked:
        pytest.skip("no character sheets on disk")
