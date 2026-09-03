"""SRD lookups must ANSWER what was asked, not name it and stop.

The three tools below shared one bug: an exact-index-or-nothing fetch, then a
"did you mean" listing a name the tool would itself refuse to fetch. Every
lookup here is one a GM makes mid-play.

get_rule.py's version of it:

/rules holds six broad chapters; almost everything a GM asks about mid-play
("cover", "advantage", "saving throws") is a /rule-sections entry. The lookup
used to search only /rules, find the section in a second pass, and print it as a
"did you mean" — so feeding the suggestion straight back in failed too, and five
of the six examples in the rules-master agent doc were unanswerable.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "features" / "rules"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "features" / "dnd-api"))

import get_rule  # noqa: E402

# A cut of the live SRD shape: the two collections and the bodies they serve.
FAKE = {
    "/rules": {"results": [{"index": "combat", "name": "Combat"}]},
    "/rule-sections": {"results": [
        {"index": "cover", "name": "Cover"},
        {"index": "advantage-and-disadvantage", "name": "Advantage and Disadvantage"},
        {"index": "movement", "name": "Movement"},
        {"index": "movement-and-position", "name": "Movement and Position"},
    ]},
    "/rules/combat": {"name": "Combat", "desc": "# Combat"},
    "/rule-sections/cover": {"name": "Cover", "desc": "## Cover"},
    "/rule-sections/advantage-and-disadvantage": {
        "name": "Advantage and Disadvantage", "desc": "## Advantage and Disadvantage"},
    "/rule-sections/movement": {"name": "Movement", "desc": "## Movement"},
}


@pytest.fixture
def srd(monkeypatch):
    monkeypatch.setattr(get_rule, "fetch",
                        lambda ep: FAKE.get(ep, {"error": "HTTP 404"}))


def _lookup(name, capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["get_rule.py", name])
    with pytest.raises(SystemExit):
        get_rule.main()
    return json.loads(capsys.readouterr().out)


def test_a_top_level_rule_still_resolves(srd, capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["get_rule.py", "combat"])
    get_rule.main()
    assert json.loads(capsys.readouterr().out)["name"] == "Combat"


@pytest.mark.parametrize("typed", ["cover", "Cover", "advantage"])
def test_a_rule_section_comes_back_as_the_answer(srd, capsys, monkeypatch, typed):
    """Including 'advantage', which matches no index and one name."""
    monkeypatch.setattr(sys, "argv", ["get_rule.py", typed])
    get_rule.main()
    out = json.loads(capsys.readouterr().out)
    assert out["desc"], out
    assert typed.lower() in out["name"].lower()


def test_the_suggestion_it_prints_is_one_you_can_feed_back_in(srd, capsys, monkeypatch):
    """The old dead end: it named 'Advantage and Disadvantage', then 404'd on it."""
    monkeypatch.setattr(sys, "argv", ["get_rule.py", "Advantage and Disadvantage"])
    get_rule.main()
    assert json.loads(capsys.readouterr().out)["name"] == "Advantage and Disadvantage"


def test_a_genuinely_ambiguous_name_asks_rather_than_guessing(srd, capsys, monkeypatch):
    # "mov" is no index and two names; "movement" is a real index, so that one
    # resolves directly — an exact hit outranks the substring search.
    err = _lookup("mov", capsys, monkeypatch)["error"]
    assert "matches several" in err
    assert "Movement and Position" in err


def test_a_miss_hands_back_the_index_instead_of_a_dead_end(srd, capsys, monkeypatch):
    # "opportunity attacks" is real 5e but the SRD files it under a broader
    # heading, so the useful answer is the list of headings.
    err = _lookup("opportunity attacks", capsys, monkeypatch)["error"]
    assert "not found" in err
    assert "- Cover" in err and "- Combat" in err


# --- dnd_equipment.py: the SRD index is not what anyone says out loud ---

CATALOGUE = {"results": [
    {"index": "longsword", "name": "Longsword"},
    {"index": "studded-leather-armor", "name": "Studded Leather Armor"},
    {"index": "barding-studded-leather", "name": "Barding: Studded Leather"},
]}


def test_equipment_falls_back_to_a_name_search(capsys, monkeypatch):
    """"plate armor" resolves by index; "studded leather" only by name."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "features" / "gear"))
    import dnd_equipment

    served = {
        "/equipment": CATALOGUE,
        "/equipment/studded-leather-armor": {"name": "Studded Leather Armor", "cost": {}},
    }
    monkeypatch.setattr(dnd_equipment, "fetch",
                        lambda ep: served.get(ep, {"error": "HTTP 404"}))
    monkeypatch.setattr(sys, "argv", ["dnd_equipment.py", "Studded Leather Armor"])
    dnd_equipment.main()
    assert json.loads(capsys.readouterr().out)["name"] == "Studded Leather Armor"


# --- combat_rules.py: the topic keys are hyphenated, nobody types them that way ---

@pytest.mark.parametrize("typed,expected", [
    ("two weapon fighting", "Two-Weapon Fighting"),
    ("two-weapon", "Two-Weapon Fighting"),
    ("grappling", "Grappling Rules"),
])
def test_combat_topics_are_hyphen_blind(typed, expected):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "features" / "rules"))
    import combat_rules
    assert combat_rules.get_combat_topic(typed)["name"] == expected


def test_an_unknown_combat_topic_lists_the_real_ones():
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "features" / "rules"))
    import combat_rules
    result = combat_rules.get_combat_topic("teleporting")
    assert "not found" in result["error"]
    assert "Cover Rules" in result["available"]
