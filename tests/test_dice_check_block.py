"""The staged check block dice.py renders when a DC is given.

The pause is made of dead air in the GM's streamed message, not a terminal
animation: tool output does not reliably reach the player, so nothing dramatic
can live in a spinner or a carriage return.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from dice import DiceRoller

R = DiceRoller()


def _result(total, rolls, modifier=0, **kw):
    base = {"notation": "1d20", "rolls": rolls, "total": total, "modifier": modifier,
            "natural_20": False, "natural_1": False}
    base.update(kw)
    return base


def test_target_is_stated_before_the_result():
    out = R.format_check(_result(20, [13], 7), dc=15)
    assert out.index("You need to beat") < out.index("You rolled")
    assert "## [ 15 ]" in out and "## [ 20 ]" in out


def test_every_point_of_the_bonus_is_attributed():
    out = R.format_check(_result(20, [13], 7), dc=15,
                         sources=[("strength", 4), ("your training in athletics", 3)])
    assert "13 on the die" in out
    assert "**+4** coming from strength" in out
    assert "**+3** coming from your training in athletics" in out


def test_success_and_failure_report_the_margin():
    assert "SUCCESS — by five." in R.format_check(_result(20, [13], 7), dc=15)
    assert "SUCCESS — on the nose." in R.format_check(_result(15, [8], 7), dc=15)
    assert "FAILURE — short by six." in R.format_check(_result(9, [2], 7), dc=15)


def test_naturals_override_the_total():
    """A nat 1 that still beats the DC is a failure, and a nat 20 that misses is not."""
    assert "NATURAL 1" in R.format_check(_result(8, [1], 7, natural_1=True), dc=5)
    assert "NATURAL 20" in R.format_check(_result(21, [20], 1, natural_20=True), dc=30)


def test_the_roller_flags_naturals_so_format_check_can_honour_them():
    """format_check trusts these flags; the roller is what has to set them."""
    seen = {"nat1": False, "nat20": False}
    for _ in range(400):
        r = R.roll("1d20+7")
        if r["rolls"] == [1]:
            seen["nat1"] = r["natural_1"]
        if r["rolls"] == [20]:
            seen["nat20"] = r["natural_20"]
    assert seen["nat1"] and seen["nat20"], f"roller never flagged a natural: {seen}"


def test_advantage_is_read_from_the_notation_not_the_dice():
    """Two equal dice must not read as disadvantage."""
    out = R.format_check(
        _result(11, [11], 0, notation="2d20kh1", kept=[11], discarded=[11]), dc=10)
    assert "advantage, keep the 11" in out
    out = R.format_check(
        _result(3, [3], 0, notation="2d20kl1", kept=[3], discarded=[18]), dc=10)
    assert "disadvantage, keep the 3" in out
