"""Tests for the adventure store (lib/adventure.py + tools/gm-adventure.sh).

adventure.json is the converted book: an ordered scene spine, scene bodies that
arrive in batches from the converter agents, and the pointer for where the table
currently is. Validation is what keeps a half-converted book from reaching play,
so it is tested rejection-first.

Wrapper tests run the real script but never against the live world-state —
GM_WORLD_STATE_BASE points at a tmp tree (see conftest.isolated_world_state).
"""

import json
import subprocess
import sys
import types
from pathlib import Path

import pytest

from lib.adventure import (REQUIRES_KINDS, AdventureError, AdventureManager,
                           format_requires_report, validate_adventure)
from lib.entity_aliases import normalize_entity_name

PROJECT_ROOT = Path(__file__).parent.parent

SPINE = [
    {"key": "tavern", "title": "The Sleeping Giant", "pages": [3, 4]},
    {"key": "road", "title": "Ambush on the Road", "pages": [5]},
    {"key": "keep", "title": "The Ruined Keep", "pages": [6, 7]},
]


def _adventure_path(world_dir):
    active = (Path(world_dir) / "active-campaign.txt").read_text().strip()
    return Path(world_dir) / "campaigns" / active / "adventure.json"


def _on_disk(world_dir):
    return json.loads(_adventure_path(world_dir).read_text())


def _built(world_dir):
    m = AdventureManager(world_dir)
    m.init(SPINE, meta={"title": "Lost Mine", "source_file": "lmop.pdf"})
    return m


# --- validation ---------------------------------------------------------

def test_valid_adventure_passes():
    adv = {
        "meta": {"title": "Lost Mine"},
        "scenes": [
            {"key": "a", "title": "A", "transitions": [{"to_key": "b", "when": "they leave"}]},
            {"key": "b", "title": "B", "transitions": []},
        ],
        "progress": {"current_scene": "a", "completed": []},
    }
    assert validate_adventure(adv) == []


def test_scene_missing_key_is_rejected():
    adv = {"scenes": [{"title": "Nameless"}], "progress": {}}
    errors = validate_adventure(adv)
    assert any("missing 'key'" in e for e in errors), errors


def test_scene_missing_title_is_rejected():
    adv = {"scenes": [{"key": "a"}], "progress": {}}
    errors = validate_adventure(adv)
    assert "scene 'a': missing 'title'" in errors, errors


def test_titleless_keyless_scene_is_named_by_position():
    errors = validate_adventure({"scenes": [{"key": "a", "title": "A"}, {}], "progress": {}})
    assert "scene #2: missing 'key'" in errors, errors
    assert "scene '#2': missing 'title'" in errors, errors


@pytest.mark.parametrize("transition", [
    {"when": "they leave"},          # no to_key at all
    {"to": "b", "when": "..."},      # the wrong field name
    {"to_key": "", "when": "..."},   # empty
    {"to_key": "   "},               # whitespace only
    {"to_key": None},
    {"to_key": 2},                   # a scene index, not a key
])
def test_transition_without_a_usable_to_key_is_rejected(transition):
    """A to_key-less transition reads as 'fall through to spine order', so a typo
    in the field name would silently drop a branch of the book."""
    adv = {"scenes": [{"key": "a", "title": "A", "transitions": [transition]},
                      {"key": "b", "title": "B"}],
           "progress": {"current_scene": "a"}}
    errors = validate_adventure(adv)
    assert any("transition #1 needs a non-empty string 'to_key'" in e for e in errors), errors


def test_duplicate_keys_are_rejected():
    adv = {"scenes": [{"key": "a", "title": "A"}, {"key": "a", "title": "Also A"}],
           "progress": {"current_scene": "a"}}
    errors = validate_adventure(adv)
    assert any("duplicate scene key 'a'" in e for e in errors), errors


def test_transition_to_unknown_key_is_rejected():
    adv = {"scenes": [{"key": "a", "title": "A", "transitions": [{"to_key": "nowhere"}]}],
           "progress": {"current_scene": "a"}}
    errors = validate_adventure(adv)
    assert any("unknown scene 'nowhere'" in e for e in errors), errors


def test_pointer_at_unknown_key_is_rejected():
    adv = {"scenes": [{"key": "a", "title": "A"}], "progress": {"current_scene": "ghost"}}
    errors = validate_adventure(adv)
    assert any("progress.current_scene 'ghost'" in e for e in errors), errors


def test_scenes_must_be_a_list():
    assert validate_adventure({"scenes": {"a": {}}}) == ["'scenes' must be a list"]


# --- requires clauses ---------------------------------------------------

def _scene_with(requires):
    """One scene carrying `requires`, wrapped as a whole adventure to validate."""
    return {"scenes": [{"key": "1.2", "title": "Meeting with Lander", "requires": requires}],
            "progress": {}}


GOOD_CLAUSES = [
    {"kind": "party_size", "min": 4, "note": "\"When the characters enter the office\""},
    {"kind": "npc_with_party", "name": "Puck", "note": "\"Puck flies forward\""},
    {"kind": "npc_known", "name": "Sheriff Amelia Waveshield",
     "note": "\"Sheriff Waveshield will enter from the door\""},
    {"kind": "item_held", "name": "Chronometer of Harmony",
     "note": "\"have you secured the Chronometer of Harmony?\""},
    {"kind": "prior_event", "id": "at-04", "note": "\"(Refer to AT-04 The Cogs of Lost Time)\""},
    {"kind": "pc_level", "min": 5, "note": "\"an adventure for four 5th-level characters\""},
    {"kind": "narrative", "note": "\"My anticipation for your return has been keen.\""},
]


@pytest.mark.parametrize("clause", GOOD_CLAUSES, ids=lambda c: c["kind"])
def test_every_requires_kind_is_accepted_with_its_own_field(clause):
    assert validate_adventure(_scene_with([clause])) == []


def test_a_scene_converted_before_requires_existed_still_validates():
    """The book already on disk was converted without the field. An absent
    `requires` is a scene that assumes nothing, never a validation failure."""
    adv = {"scenes": [{"key": "1.2", "title": "Meeting with Lander"}], "progress": {}}
    assert validate_adventure(adv) == []


def test_init_gives_every_stub_an_empty_requires(dcc_world):
    _built(dcc_world)
    assert all(s["requires"] == [] for s in _on_disk(dcc_world)["scenes"])


def test_an_unknown_requires_kind_is_rejected_and_names_the_scene():
    """The differ reads these clauses by kind. A kind it does not know is an
    assumption the book made that nothing downstream will ever check."""
    errors = validate_adventure(_scene_with([{"kind": "party_mood", "min": 2, "note": "q"}]))
    assert any("scene '1.2': requires #1 has unknown kind 'party_mood'" in e for e in errors), errors


@pytest.mark.parametrize("clause, wanted", [
    ({"kind": "party_size", "note": "q"}, "needs a positive integer 'min'"),
    ({"kind": "party_size", "min": 0, "note": "q"}, "needs a positive integer 'min'"),
    ({"kind": "party_size", "min": "four", "note": "q"}, "needs a positive integer 'min'"),
    ({"kind": "pc_level", "min": True, "note": "q"}, "needs a positive integer 'min'"),
    ({"kind": "npc_with_party", "note": "q"}, "needs a non-empty string 'name'"),
    ({"kind": "npc_known", "name": "   ", "note": "q"}, "needs a non-empty string 'name'"),
    ({"kind": "item_held", "name": 7, "note": "q"}, "needs a non-empty string 'name'"),
    ({"kind": "prior_event", "note": "q"}, "needs a non-empty string 'id'"),
    ({"kind": "narrative", "note": ""}, "needs a non-empty string 'note'"),
])
def test_a_clause_missing_its_per_kind_field_is_rejected(clause, wanted):
    errors = validate_adventure(_scene_with([clause]))
    assert any(wanted in e and "scene '1.2'" in e for e in errors), errors


def test_a_clause_without_its_evidence_quote_is_rejected():
    """The quote is what tells a converted assumption from an invented one, so
    the validator enforces it like any other required field."""
    errors = validate_adventure(_scene_with([{"kind": "npc_with_party", "name": "Puck"}]))
    assert any("needs a 'note' quoting the module text" in e for e in errors), errors


def test_requires_must_be_a_list():
    errors = validate_adventure(_scene_with({"kind": "party_size", "min": 2, "note": "q"}))
    assert "scene '1.2': 'requires' must be a list" in errors, errors


def test_merge_persists_requires_and_refuses_a_bad_clause(dcc_world):
    m = _built(dcc_world)
    clause = {"kind": "prior_event", "id": "at-04",
              "note": "\"(Refer to AT-04 The Cogs of Lost Time)\""}
    m.merge([{"key": "road", "requires": [clause]}])
    assert _on_disk(dcc_world)["scenes"][1]["requires"] == [clause]

    with pytest.raises(AdventureError, match="unknown kind 'vibes'"):
        m.merge([{"key": "keep", "requires": [{"kind": "vibes", "note": "q"}]}])
    assert _on_disk(dcc_world)["scenes"][2]["requires"] == [], "bad batch did not persist"


# --- adaptation: the book's assumptions vs one real table ----------------

AT05_SPINE = [
    {"key": "1.2", "title": "Meeting with Lander", "pages": [4]},
    {"key": "2.3", "title": "The Cogsmith's Shop", "pages": [9]},
    {"key": "2.17", "title": "The Whispering Grove", "pages": [21]},
]

# Shaped after AT-05: assumptions repeated across scenes, one borrowed from the
# module before it, and a quote on every clause.
AT05_REQUIRES = {
    "1.2": [
        {"kind": "party_size", "min": 4, "note": "\"When the characters enter the office\""},
        {"kind": "npc_with_party", "name": "Puck", "note": "\"Puck flies forward to greet them\""},
        {"kind": "npc_known", "name": "Sheriff Amelia Waveshield",
         "note": "\"Sheriff Waveshield will enter from the door\""},
        {"kind": "pc_level", "min": 1, "note": "\"an adventure for four 1st-level characters\""},
    ],
    "2.3": [
        {"kind": "party_size", "min": 4,
         "note": "\"the four of them crowd the counter while the cogsmith works\""},
        {"kind": "item_held", "name": "Chronometer of Harmony",
         "note": "\"have you secured the Chronometer of Harmony?\""},
    ],
    "2.17": [
        {"kind": "prior_event", "id": "at-04", "note": "\"(Refer to AT-04 The Cogs of Lost Time)\""},
        {"kind": "npc_with_party", "name": "puck", "note": "\"Puck darts ahead\""},
    ],
}


@pytest.fixture
def solo_world(tmp_path):
    """A table of one, against a book written for a party of four.

    A level-1 PC with a starter kit, nobody travelling alongside, one NPC on file
    they have a history with (events on the record) and one they do not. This is
    what a single player importing AT-05 actually walks in with.
    """
    base = tmp_path / "world-state"
    campaign = base / "campaigns" / "solo"
    campaign.mkdir(parents=True)
    (base / "active-campaign.txt").write_text("solo\n")
    (campaign / "character.json").write_text(json.dumps({
        "name": "Wren", "race": "Halfling", "class": "Rogue", "level": 1,
        "hp": {"current": 8, "max": 8},
        "equipment": ["Sling", "Traveler's clothes", "Thieves' tools"],
    }))
    (campaign / "npcs.json").write_text(json.dumps({
        "Puck": {"is_party_member": False, "events": []},
        "Sheriff Amelia Waveshield": {"events": [{"event": "Warned them off the docks"}]},
    }))
    return str(base)


def _at05(world_dir, requires=AT05_REQUIRES):
    m = AdventureManager(world_dir)
    m.init(AT05_SPINE, meta={"title": "The Whispering Wood (AT-05)", "levels": "1-3"})
    if requires:
        m.merge([{"key": k, "requires": r} for k, r in requires.items()])
    return m


def _unmet(report):
    """The unmet classes, derived. The payload carries ONE list of classes, each
    with its own `met` — a second list of the same dicts doubled every class in
    `--json`."""
    return [g for g in report["groups"] if not g["met"]]


def test_requires_report_unions_and_dedups_clauses_across_scenes(solo_world):
    report = _at05(solo_world).requires_report()
    by_kind = {g["kind"]: g for g in report["groups"]}

    assert report["clauses"] == 8, "every clause counted"
    assert len(report["groups"]) == 6, "deduped to one class per kind+value"
    assert by_kind["party_size"]["scenes"] == ["1.2", "2.3"]
    assert "crowd the counter" in by_kind["party_size"]["quote"], "strongest quote wins the group"
    assert by_kind["npc_with_party"]["scenes"] == ["1.2", "2.17"], "'puck' and 'Puck' are one NPC"


def test_two_spellings_of_one_npc_are_one_question(solo_world):
    """The book calls her "Sheriff Waveshield" in one scene and "Sheriff Amelia
    Waveshield" in the next. That is one person, so it is one thing to ask the
    player about — and neither lowercasing nor the normalizer can fold it, because
    "sheriff" is not on the honorific list the normalizer strips. The fold comes
    from the campaign's own record of her, the same identity the judge answers on.
    """
    npcs = Path(solo_world) / "campaigns" / "solo" / "npcs.json"
    npcs.write_text(json.dumps({"Sheriff Amelia Waveshield": {
        "aliases": ["Sheriff Waveshield"],
        "events": [{"event": "Warned them off the docks"}]}}))
    m = _at05(solo_world, requires={
        "1.2": [{"kind": "npc_known", "name": "Sheriff Waveshield",
                 "note": "\"Sheriff Waveshield will enter from the door\""}],
        "2.3": [{"kind": "npc_known", "name": "Sheriff Amelia Waveshield",
                 "note": "\"Sheriff Amelia Waveshield already knows their faces\""}],
    })

    groups = m.requires_report()["groups"]
    assert len(groups) == 1, [g["value"] for g in groups]
    assert groups[0]["scenes"] == ["1.2", "2.3"], "both scenes hang off the one class"
    assert groups[0]["met"] is True, "and the class is judged against that same record"

    lowered = {"Sheriff Waveshield".lower(), "Sheriff Amelia Waveshield".lower()}
    normalized = {normalize_entity_name(n) for n in
                  ("Sheriff Waveshield", "Sheriff Amelia Waveshield")}
    assert len(lowered) == 2 and len(normalized) == 2, \
        "the fold is one neither .lower() nor the normalizer can produce"

    npcs.write_text(json.dumps({}))
    assert len(m.requires_report()["groups"]) == 2, \
        "a name the campaign has no record of stays two strangers, and two questions"


def test_the_solo_newcomer_meets_only_what_this_table_can_meet(solo_world):
    report = _at05(solo_world).requires_report()

    assert {g["kind"] for g in _unmet(report)} == {
        "party_size", "npc_with_party", "item_held", "prior_event"}
    assert {g["kind"] for g in report["groups"] if g["met"]} == {"npc_known", "pc_level"}
    assert report["unmet_count"] == len(_unmet(report))
    assert "unmet" not in report, "no second copy of every class in the payload"

    unmet = {g["kind"]: g for g in _unmet(report)}
    assert "the party numbers 1" in unmet["party_size"]["detail"]
    assert unmet["prior_event"]["flag"] == "other_module", "AT-04 can never be played here"
    assert "Chronometer" in unmet["item_held"]["quote"], "the book's own words reach the question"


def test_binding_stamps_once_and_a_second_run_changes_nothing(solo_world):
    m = _at05(solo_world)
    first = m.requires_report()
    assert first["binding"] == "bound"

    stamp = _on_disk(solo_world)["meta"]["adaptation"]
    assert stamp["matched_to_pc"] is True and stamp["pc"] == "Wren" and stamp["decided_at"]

    text = _adventure_path(solo_world).read_text()
    written_at = _adventure_path(solo_world).stat().st_mtime_ns

    second = m.requires_report()
    assert second["binding"] == "already-bound"
    assert _unmet(second) == _unmet(first), "the standing report says the same thing"
    assert _adventure_path(solo_world).read_text() == text
    assert _adventure_path(solo_world).stat().st_mtime_ns == written_at, "nothing re-decided"


def test_a_report_without_a_pc_is_provisional_and_stamps_nothing(solo_world):
    (Path(solo_world) / "campaigns" / "solo" / "character.json").unlink()
    report = _at05(solo_world).requires_report()

    assert report["binding"] == "awaiting-pc"
    assert report["table"]["party_size"] == 0
    assert {g["kind"] for g in _unmet(report)} == {
        "party_size", "npc_with_party", "item_held", "prior_event", "pc_level"}
    assert "adaptation" not in _on_disk(solo_world)["meta"], "no PC, no binding"
    assert "PROVISIONAL" in format_requires_report(report)


def test_a_legacy_open_schema_sheet_is_a_real_pc(solo_world):
    """identity_onboarding wrote sheets in the open shape, and the runtime reads
    them through character_schema.to_flat on load. Read raw, the name is buried
    under `identity` and the book waits forever for a PC who is already at the
    table — level 0, nothing carried, never bound."""
    (Path(solo_world) / "campaigns" / "solo" / "character.json").write_text(json.dumps({
        "identity": {"name": "Wren", "race": "Halfling", "class": "Rogue"},
        "vitals": {"hp": {"current": 30, "max": 30}, "ac": 15},
        "attributes": {"DEX": 18},
        "progression": {"level": 5, "xp": 6500},
        "inventory": {"gold": 12, "items": ["Sling", "Chronometer of Harmony"]},
        "conditions": [],
    }))
    report = _at05(solo_world).requires_report()

    assert report["binding"] == "bound" and report["pc"] == "Wren"
    assert report["table"]["pc_level"] == 5, "the level lives under `progression`"
    met = {g["kind"] for g in report["groups"] if g["met"]}
    assert "item_held" in met, "and the kit under `inventory.items`"
    assert {g["kind"] for g in _unmet(report)} == {"party_size", "npc_with_party", "prior_event"}


def test_binding_keeps_the_rulings_made_before_it(solo_world):
    """`adapt` is available before a PC exists, and those answers are decisions
    too — the stamp joins them rather than starting the rulings list over."""
    m = _at05(solo_world)
    m.adapt("party_size", "Solo run: halve every enemy count")
    assert m.requires_report()["binding"] == "bound"

    adaptation = _on_disk(solo_world)["meta"]["adaptation"]
    assert adaptation["matched_to_pc"] is True
    assert [r["ruling"] for r in adaptation["rulings"]] == ["Solo run: halve every enemy count"]


def test_adapt_writes_a_ruling(solo_world):
    m = _at05(solo_world)
    result = m.adapt("npc_with_party", "Puck rides with the sheriff; he catches up at 2.17",
                     value="Puck")

    assert result["replaced"] is False and result["rulings"] == 1
    assert _on_disk(solo_world)["meta"]["adaptation"]["rulings"] == [
        {"kind": "npc_with_party", "name": "Puck",
         "ruling": "Puck rides with the sheriff; he catches up at 2.17"}]
    assert m.validate() == []


def test_adapt_rejects_an_unknown_kind_and_lists_the_valid_set(solo_world):
    m = _at05(solo_world)
    with pytest.raises(AdventureError) as exc:
        m.adapt("party_mood", "everyone is cheerful about it")

    assert "unknown adaptation kind 'party_mood'" in str(exc.value)
    missing = [k for k in REQUIRES_KINDS if k not in str(exc.value)]
    assert not missing, f"the error never names: {missing}"
    assert "adaptation" not in _on_disk(solo_world)["meta"], "the bad ruling did not persist"


def test_adapt_refuses_a_ruling_with_no_text(solo_world):
    with pytest.raises(AdventureError, match="a ruling needs text"):
        _at05(solo_world).adapt("party_size", "   ")


def test_re_ruling_the_same_scope_replaces_it(solo_world):
    """Two standing answers to one assumption is a table nobody can read back."""
    m = _at05(solo_world)
    m.adapt("party_size", "Halve every enemy count")
    m.adapt("party_size", "Give Wren a hireling instead")

    rulings = _on_disk(solo_world)["meta"]["adaptation"]["rulings"]
    assert len(rulings) == 1 and rulings[0]["ruling"] == "Give Wren a hireling instead"


def test_rulings_on_different_values_of_one_kind_stand_side_by_side(solo_world):
    m = _at05(solo_world)
    m.adapt("npc_with_party", "Puck joins them at 2.17", value="Puck")
    m.adapt("npc_with_party", "Lander stays in his office", value="Lander")
    assert len(_on_disk(solo_world)["meta"]["adaptation"]["rulings"]) == 2


def test_a_min_kind_takes_its_scope_value_as_a_number(solo_world):
    m = _at05(solo_world)
    m.adapt("party_size", "Halve every enemy count", value="4")
    assert _on_disk(solo_world)["meta"]["adaptation"]["rulings"][0]["min"] == 4

    with pytest.raises(AdventureError, match="takes a number"):
        m.adapt("pc_level", "Level them to 3 before this scene", value="fifth")


def test_rulings_survive_a_later_merge_and_revalidate(solo_world):
    """Converter batches keep arriving after the table has ruled. `merge` rewrites
    scenes; the stamp and its rulings live under `meta` and must come through."""
    m = _at05(solo_world)
    m.requires_report()
    m.adapt("item_held", "The chronometer is in Lander's safe — they have to ask for it",
            value="Chronometer of Harmony")
    m.merge([{"key": "2.3", "read_aloud": "Cogs turn behind the counter."}])

    adaptation = _on_disk(solo_world)["meta"]["adaptation"]
    assert adaptation["matched_to_pc"] is True and adaptation["pc"] == "Wren"
    assert len(adaptation["rulings"]) == 1
    assert m.validate() == [], "the stamp and its rulings pass the schema"


@pytest.mark.parametrize("scene_id, met, flag", [
    ("1.2", True, None),                   # played
    ("2.3", False, "not_yet_played"),      # a scene of this book they have not reached
    ("at-04", False, "other_module"),      # another book's scene — never playable here
    ("1.7", False, "unresolved"),          # matches nothing: a mis-converted key
])
def test_prior_event_says_why_an_earlier_beat_is_missing(solo_world, scene_id, met, flag):
    """Three unmet cases look identical on disk and are nothing alike at the table,
    and the one that means "the converter typo'd a key" is flagged, never a crash."""
    m = _at05(solo_world, requires={"2.17": [
        {"kind": "prior_event", "id": scene_id, "note": "\"(Refer to AT-04)\""}]})
    m.jump("1.2")
    m.advance()

    group = m.requires_report()["groups"][0]
    assert group["met"] is met and group["flag"] == flag


@pytest.mark.parametrize("scene_id, flag", [
    # A typo inside the live book's own part-1..part-4 family. Read as a product
    # code it becomes a standing adaptation — a permanent ruling about a scene
    # that was only ever a mis-typed key.
    ("part-5", "unresolved"),
    # Real product codes, and neither is shaped like a scene key of this book:
    # the season folded into the letters, and a citation carrying the title.
    ("DDAL05-01", "other_module"),
    ("AT-04 The Cogs of Lost Time", "other_module"),
])
def test_a_prior_event_id_is_read_against_this_books_own_key_families(solo_world, scene_id, flag):
    """The whispering-wood book keys its scenes two ways, part-N and N.M. An id
    wearing one of those shapes belongs to this book whatever else it looks like."""
    m = AdventureManager(solo_world)
    m.init([{"key": k, "title": k} for k in
            ("part-1", "1.1", "1.2", "part-2", "2.1", "part-3", "part-4")])
    m.merge([{"key": "2.1", "requires": [
        {"kind": "prior_event", "id": scene_id, "note": "\"they have already done this\""}]}])

    report = m.requires_report()
    group = report["groups"][0]
    assert group["met"] is False
    assert group["flag"] == flag, group["detail"]
    # The next-step hint is pasted verbatim, and this class is about ONE id.
    assert f'--value "{scene_id}"' in format_requires_report(report)


def test_narrative_is_unmeetable_by_design(solo_world):
    m = _at05(solo_world, requires={"1.2": [
        {"kind": "narrative", "note": "\"My anticipation for your return has been keen.\""}]})
    group = m.requires_report()["groups"][0]
    assert group["met"] is False and group["flag"] == "unmeetable"


def test_a_book_whose_scenes_carry_no_requires_still_binds(solo_world):
    """0 of the live book's 43 scenes carry the key. The union has to read that as
    "this book assumes nothing", bind, and stay valid."""
    m = _at05(solo_world, requires=None)
    report = m.requires_report()

    assert report["groups"] == [] and report["clauses"] == 0
    assert report["binding"] == "bound"
    assert "nothing to adapt" in format_requires_report(report)
    assert m.validate() == []


def test_an_unreadable_clause_is_counted_not_silently_dropped(solo_world):
    """A hand-edited book can carry clauses the reader cannot type. The report
    still runs (that IS the adaptation pass) and points at `validate`."""
    m = _at05(solo_world, requires=None)
    adv = _on_disk(solo_world)
    adv["scenes"][0]["requires"] = [{"kind": "party_size", "min": 0, "note": "q"},
                                    "a bare string",
                                    {"kind": "party_mood", "note": "q"}]
    _adventure_path(solo_world).write_text(json.dumps(adv))

    report = m.requires_report()
    assert report["malformed_clauses"] == 3 and report["groups"] == []
    assert report["binding"] == "bound", "a conversion gap does not block the binding"
    assert "run `validate`" in format_requires_report(report)


def test_a_malformed_standing_ruling_is_named_and_blocks_nothing(solo_world):
    """A ruling nobody can act on is law on disk until someone sees it, and the
    report is the only place a GM would look. It used to raise out of BOTH the
    report and `adapt`, so the one command that shows the problem and the one
    command that fixes it were the two commands it broke."""
    m = _at05(solo_world, requires=None)
    adv = _on_disk(solo_world)
    adv["meta"]["adaptation"] = {"rulings": [
        {"kind": "party_mood", "ruling": "everyone is cheerful about it"},
        {"kind": "party_size", "min": 4, "ruling": "Solo run: halve every enemy count"},
    ]}
    _adventure_path(solo_world).write_text(json.dumps(adv))

    report = m.requires_report()
    assert report["binding"] == "bound", "a bad ruling does not block the binding"
    assert any("ruling #1 has unknown kind 'party_mood'" in p
               for p in report["ruling_problems"]), report["ruling_problems"]
    rendered = format_requires_report(report)
    assert "party_mood" in rendered and "[UNREADABLE]" in rendered
    assert "Solo run: halve every enemy count" in rendered, "the good ruling still reads"

    result = m.adapt("npc_with_party", "Puck catches up at 2.17", value="Puck")
    assert result["rulings"] == 3, "the player's answer is recorded regardless"
    assert any("party_mood" in u for u in result["unreadable"]), "and names what it left alone"

    # `adapt` refuses to write an unknown kind, so re-ruling can never replace this
    # one. Removal is the only way back that is not hand-editing JSON.
    assert m.unadapt("party_mood")["rulings"] == 2
    assert [r["kind"] for r in _on_disk(solo_world)["meta"]["adaptation"]["rulings"]] == [
        "party_size", "npc_with_party"]
    assert m.validate() == []

    with pytest.raises(AdventureError, match="no standing party_mood ruling"):
        m.unadapt("party_mood")


def test_remove_drops_only_the_scope_it_names(solo_world):
    m = _at05(solo_world)
    m.adapt("npc_with_party", "Puck catches up at 2.17", value="Puck")
    m.adapt("npc_with_party", "Lander stays in his office", value="Lander")

    m.unadapt("npc_with_party", value="Puck")
    rulings = _on_disk(solo_world)["meta"]["adaptation"]["rulings"]
    assert [r["name"] for r in rulings] == ["Lander"]


# --- adaptation schema --------------------------------------------------

def test_a_well_formed_adaptation_block_validates():
    adv = {"meta": {"adaptation": {"matched_to_pc": True, "pc": "Wren",
                                   "decided_at": "2026-08-26T19:00:00Z",
                                   "rulings": [{"kind": "party_size", "min": 4,
                                                "ruling": "Halve every enemy count"},
                                               {"kind": "narrative",
                                                "ruling": "Wren never met the duke"}]}},
           "scenes": [{"key": "a", "title": "A"}], "progress": {}}
    assert validate_adventure(adv) == []


def test_an_adventure_with_no_adaptation_block_is_valid():
    adv = {"meta": {"title": "Lost Mine"}, "scenes": [{"key": "a", "title": "A"}], "progress": {}}
    assert validate_adventure(adv) == []


def test_a_malformed_ruling_is_named_by_validate():
    """A ruling is law for the rest of the campaign. One nobody can act on is
    worse than none, so the schema names it the way it names a bad clause."""
    adv = {"meta": {"adaptation": {"matched_to_pc": True, "rulings": [
        {"kind": "party_mood", "ruling": "cheerful"},
        {"kind": "party_size", "ruling": ""},
        {"kind": "npc_with_party", "name": "   ", "ruling": "Puck joins later"},
        "a bare string",
        {"kind": ["party_size"], "ruling": "halve it"},
    ]}}, "scenes": [{"key": "a", "title": "A"}], "progress": {}}
    errors = validate_adventure(adv)

    assert any("ruling #1 has unknown kind 'party_mood'" in e for e in errors), errors
    assert any("ruling #2 (party_size) needs a non-empty string 'ruling'" in e for e in errors), errors
    assert any("ruling #3 (npc_with_party) needs a non-empty string 'name'" in e for e in errors), errors
    assert any("ruling #4 must be an object" in e for e in errors), errors
    assert any("ruling #5 needs a string 'kind'" in e for e in errors), errors


@pytest.mark.parametrize("adaptation, wanted", [
    ("bound", "meta.adaptation must be an object"),
    ({"rulings": {"party_size": "halve it"}}, "meta.adaptation.rulings must be a list"),
])
def test_an_unusable_adaptation_container_is_rejected(adaptation, wanted):
    adv = {"meta": {"adaptation": adaptation}, "scenes": [{"key": "a", "title": "A"}],
           "progress": {}}
    assert wanted in validate_adventure(adv), validate_adventure(adv)


# --- init + merge -------------------------------------------------------

def test_init_writes_stub_scenes_in_spine_order(dcc_world):
    m = _built(dcc_world)
    adv = _on_disk(dcc_world)
    assert [s["key"] for s in adv["scenes"]] == ["tavern", "road", "keep"]
    assert adv["progress"] == {"current_scene": "tavern", "completed": []}
    assert adv["meta"]["title"] == "Lost Mine"
    stub = adv["scenes"][0]
    assert stub["title"] == "The Sleeping Giant" and stub["pages"] == [3, 4]
    assert stub["read_aloud"] == "" and stub["encounters"] == [] and stub["checks"] == []
    assert m.validate() == []


def test_init_refuses_a_spine_entry_without_a_key(dcc_world):
    m = AdventureManager(dcc_world)
    with pytest.raises(AdventureError, match="missing 'key'"):
        m.init([{"title": "Nameless"}])


def test_merge_out_of_order_keeps_spine_order(dcc_world):
    m = _built(dcc_world)
    m.merge([{"key": "keep", "title": "The Ruined Keep", "read_aloud": "Ivy chokes the gate.",
              "encounters": [{"name": "Ghoul pack",
                              "monsters": [{"name": "Ghoul", "count": 3, "srd_index": "ghoul"}]}]}])
    m.merge([{"key": "tavern", "location": "Phandalin",
              "checks": [{"what": "overhear the drovers", "skill": "Perception", "dc": 12}],
              "transitions": [{"to_key": "keep", "when": "they take the north track"}]}])

    adv = _on_disk(dcc_world)
    assert [s["key"] for s in adv["scenes"]] == ["tavern", "road", "keep"], "spine order held"
    assert adv["scenes"][2]["read_aloud"] == "Ivy chokes the gate."
    assert adv["scenes"][2]["encounters"][0]["monsters"][0]["srd_index"] == "ghoul"
    assert adv["scenes"][0]["location"] == "Phandalin"
    assert adv["scenes"][0]["checks"][0]["dc"] == 12
    assert m.validate() == []


def test_merge_appends_a_genuinely_new_scene(dcc_world):
    m = _built(dcc_world)
    m.merge([{"key": "cellar", "title": "Under the Keep"}])
    assert [s["key"] for s in _on_disk(dcc_world)["scenes"]][-1] == "cellar"


def test_merge_rejects_a_transition_to_an_unknown_scene(dcc_world):
    m = _built(dcc_world)
    with pytest.raises(AdventureError, match="unknown scene 'atlantis'"):
        m.merge([{"key": "road", "transitions": [{"to_key": "atlantis", "when": "never"}]}])
    assert _on_disk(dcc_world)["scenes"][1]["transitions"] == [], "bad batch did not persist"


def test_merge_rejects_a_transition_without_a_to_key(dcc_world):
    m = _built(dcc_world)
    with pytest.raises(AdventureError, match="needs a non-empty string 'to_key'"):
        m.merge([{"key": "tavern", "transitions": [{"to": "road", "when": "they ride out"}]}])
    assert _on_disk(dcc_world)["scenes"][0]["transitions"] == [], "bad batch did not persist"


def test_init_refuses_to_wipe_an_existing_adventure(dcc_world):
    m = _built(dcc_world)
    m.advance()  # some progress worth protecting
    with pytest.raises(AdventureError, match="already has an adventure.json"):
        m.init([{"key": "other", "title": "A Different Book"}])

    adv = _on_disk(dcc_world)
    assert adv["progress"] == {"current_scene": "road", "completed": ["tavern"]}
    assert [s["key"] for s in adv["scenes"]] == ["tavern", "road", "keep"]


def test_init_force_replaces_the_adventure(dcc_world):
    m = _built(dcc_world)
    m.advance()
    m.init([{"key": "other", "title": "A Different Book"}], force=True)

    adv = _on_disk(dcc_world)
    assert [s["key"] for s in adv["scenes"]] == ["other"]
    assert adv["progress"] == {"current_scene": "other", "completed": []}


def test_merge_without_an_adventure_says_so(dcc_world):
    m = AdventureManager(dcc_world)
    with pytest.raises(AdventureError, match="No adventure.json"):
        m.merge([{"key": "a", "title": "A"}])


# --- progress -----------------------------------------------------------

def test_status_reports_current_and_next_in_spine_order(dcc_world):
    status = _built(dcc_world).status()
    assert status["current_scene"] == "tavern"
    assert status["current_title"] == "The Sleeping Giant"
    assert status["next_scene"] == "road"
    assert status["total_scenes"] == 3 and status["at_end"] is False


def test_next_prefers_the_first_transition_over_spine_order(dcc_world):
    m = _built(dcc_world)
    m.merge([{"key": "tavern", "transitions": [{"to_key": "keep", "when": "they ride north"}]}])
    assert m.status()["next_scene"] == "keep"


def test_advance_completes_current_and_moves_the_pointer(dcc_world):
    m = _built(dcc_world)
    result = m.advance()
    assert result["advanced_from"] == "tavern" and result["current_scene"] == "road"

    saved = _on_disk(dcc_world)["progress"]
    assert saved == {"current_scene": "road", "completed": ["tavern"]}, "persisted"


def test_advance_follows_a_transition(dcc_world):
    m = _built(dcc_world)
    m.merge([{"key": "tavern", "transitions": [{"to_key": "keep", "when": "they ride north"}]}])
    m.advance()
    assert _on_disk(dcc_world)["progress"]["current_scene"] == "keep"


def test_advance_at_the_last_scene_reports_the_end(dcc_world):
    m = _built(dcc_world)
    m.jump("keep")
    result = m.advance()
    assert result["at_end"] is True
    saved = _on_disk(dcc_world)["progress"]
    assert saved["current_scene"] == "keep", "pointer stays put at the end"
    assert saved["completed"] == ["keep"]


def test_advance_does_not_double_list_a_completed_scene(dcc_world):
    m = _built(dcc_world)
    m.jump("keep")
    m.advance()
    m.advance()
    assert _on_disk(dcc_world)["progress"]["completed"] == ["keep"]


def test_jump_moves_anywhere_valid_and_persists(dcc_world):
    m = _built(dcc_world)
    assert m.jump("keep")["current_scene"] == "keep"
    assert _on_disk(dcc_world)["progress"]["current_scene"] == "keep"


def test_jump_to_an_unknown_key_is_refused(dcc_world):
    m = _built(dcc_world)
    with pytest.raises(AdventureError, match="unknown scene 'atlantis'"):
        m.jump("atlantis")
    assert _on_disk(dcc_world)["progress"]["current_scene"] == "tavern"


# --- SRD monster resolution ---------------------------------------------

FAKE_SRD = {"count": 3, "results": [{"index": "harpy", "name": "Harpy"},
                                    {"index": "goblin", "name": "Goblin"},
                                    {"index": "wolf", "name": "Wolf"}]}


@pytest.fixture
def fake_srd(monkeypatch):
    """Stand in for features/dnd-api's fetch so the resolver never hits the network."""
    calls = []

    def fetch(endpoint):
        calls.append(endpoint)
        return FAKE_SRD

    monkeypatch.setitem(sys.modules, "dnd_api_core",
                        types.SimpleNamespace(fetch=fetch, __name__="dnd_api_core"))
    return calls


def _with_monsters(world_dir, monsters):
    m = _built(world_dir)
    m.merge([{"key": "road", "encounters": [{"name": "Ambush", "monsters": monsters}]}])
    return m


def _monsters_on_disk(world_dir, scene_index=1):
    return _on_disk(world_dir)["scenes"][scene_index]["encounters"][0]["monsters"]


def test_resolve_monsters_maps_a_known_srd_name(dcc_world, fake_srd):
    m = _with_monsters(dcc_world, [{"name": "goblin", "count": 4}])
    assert m.resolve_monsters()["resolved"] == 1
    assert _monsters_on_disk(dcc_world)[0]["srd_index"] == "goblin", "persisted"


def test_resolve_monsters_singularizes_a_plural(dcc_world, fake_srd):
    m = _with_monsters(dcc_world, [{"name": "Harpies", "count": 2},
                                   {"name": "Goblins", "count": 3},
                                   {"name": "Wolves", "count": 2}])
    result = m.resolve_monsters()
    assert result["resolved"] == 3 and result["embedded"] == 0
    saved = _monsters_on_disk(dcc_world)
    assert saved[0]["srd_index"] == "harpy"
    assert saved[1]["srd_index"] == "goblin"
    assert saved[2]["srd_index"] == "wolf"
    assert saved[0]["name"] == "Harpies", "the book's own wording is left alone"


def test_resolve_monsters_leaves_homebrew_with_its_stat_block(dcc_world, fake_srd):
    stat_block = {"ac": 13, "hp": 22, "cr": "1"}
    m = _with_monsters(dcc_world, [{"name": "Bone Kite", "count": 1, "stat_block": stat_block},
                                   {"name": "Harpy", "count": 2}])
    result = m.resolve_monsters()

    assert result == {"resolved": 1, "embedded": 1, "unstatted": 0, "unstatted_names": []}
    homebrew = _monsters_on_disk(dcc_world)[0]
    assert homebrew["stat_block"] == stat_block, "the module's own stats survive"
    assert "srd_index" not in homebrew


def test_a_statted_monster_wins_over_its_srd_namesake(dcc_world, fake_srd):
    """The module printing its own "Goblin" means this book's goblin is not the
    SRD's. The converter's block is the authority; nothing gets both."""
    stat_block = {"ac": 17, "hp": 40, "cr": "3"}
    m = _with_monsters(dcc_world, [{"name": "Goblin", "count": 2, "stat_block": stat_block}])
    result = m.resolve_monsters()

    assert result["embedded"] == 1 and result["resolved"] == 0
    saved = _monsters_on_disk(dcc_world)[0]
    assert saved["stat_block"] == stat_block
    assert "srd_index" not in saved


def test_a_monster_with_neither_stats_nor_an_srd_match_is_flagged_unstatted(dcc_world, fake_srd):
    """No srd_index and no stat_block is a conversion gap, not an embedded monster."""
    m = _with_monsters(dcc_world, [{"name": "Bone Kite", "count": 1},
                                   {"name": "Harpy", "count": 2}])
    result = m.resolve_monsters()

    assert result == {"resolved": 1, "embedded": 0, "unstatted": 1,
                      "unstatted_names": ["Bone Kite"]}
    gap = _monsters_on_disk(dcc_world)[0]
    assert "srd_index" not in gap and "stat_block" not in gap


def test_resolve_monsters_clears_a_stale_srd_index(dcc_world, fake_srd):
    """Re-running after a scene was re-converted must not leave the old answer
    behind — a name that no longer resolves loses its index."""
    m = _with_monsters(dcc_world, [{"name": "Bone Kite", "count": 1, "srd_index": "harpy"},
                                   {"name": "Goblin", "count": 2, "srd_index": "harpy"}])
    result = m.resolve_monsters()

    assert result["unstatted"] == 1 and result["resolved"] == 1
    saved = _monsters_on_disk(dcc_world)
    assert "srd_index" not in saved[0], "the stale index is gone"
    assert saved[1]["srd_index"] == "goblin", "and a wrong one is corrected"


def test_resolve_monsters_is_idempotent_and_skips_a_no_op_save(dcc_world, fake_srd):
    m = _with_monsters(dcc_world, [{"name": "Harpies", "count": 2},
                                   {"name": "Bone Kite", "count": 1, "stat_block": {"hp": 22}}])
    first = m.resolve_monsters()
    after_first = _adventure_path(dcc_world).read_text()
    stamp = _adventure_path(dcc_world).stat().st_mtime_ns

    assert m.resolve_monsters() == first, "same counts on a second pass"
    assert _adventure_path(dcc_world).read_text() == after_first
    assert _adventure_path(dcc_world).stat().st_mtime_ns == stamp, "nothing changed, nothing written"


def test_resolve_monsters_reads_the_index_once_for_the_whole_book(dcc_world, fake_srd):
    m = _built(dcc_world)
    m.merge([{"key": "road", "encounters": [{"name": "A", "monsters": [{"name": "Goblin"}]}]},
             {"key": "keep", "encounters": [{"name": "B", "monsters": [{"name": "Harpy"}]}]}])
    assert m.resolve_monsters()["resolved"] == 2
    assert len(fake_srd) == 1, f"one index fetch, got {fake_srd}"


def test_a_fully_statted_book_never_calls_the_api(dcc_world, fake_srd):
    m = _with_monsters(dcc_world, [{"name": "Goblin", "count": 2, "stat_block": {"hp": 7}}])
    assert m.resolve_monsters()["embedded"] == 1
    assert fake_srd == [], "no monster needed the SRD, so it was never fetched"


def test_resolve_monsters_survives_a_book_with_no_encounters(dcc_world, fake_srd):
    assert _built(dcc_world).resolve_monsters() == {"resolved": 0, "embedded": 0,
                                                    "unstatted": 0, "unstatted_names": []}


def test_resolve_monsters_reports_an_unreachable_api(dcc_world, monkeypatch):
    monkeypatch.setitem(sys.modules, "dnd_api_core", types.SimpleNamespace(
        fetch=lambda endpoint: {"error": "Request failed", "message": "no route to host"},
        __name__="dnd_api_core"))
    m = _with_monsters(dcc_world, [{"name": "Harpy", "count": 2}])
    with pytest.raises(AdventureError, match="could not read the SRD monster index"):
        m.resolve_monsters()


# --- converter agent / validator drift ----------------------------------

def test_converter_agent_definition_names_every_scene_field():
    """The agent doc is the schema the converters actually follow — if a field is
    renamed in lib/adventure.py and not here, the batches quietly lose it."""
    from lib.adventure import SCENE_FIELDS

    doc = (PROJECT_ROOT / ".claude" / "agents" / "module-converter.md").read_text()
    missing = [f for f in list(SCENE_FIELDS) + ["key", "title"] if f not in doc]
    assert not missing, f"module-converter.md never mentions: {missing}"
    assert "to_key" in doc, "transitions need their to_key field spelled out"


def test_converter_agent_definition_names_every_requires_kind():
    """The clause table in the agent doc is where converters read the kind set
    from. A kind or per-kind field added in lib/adventure.py and never written
    down here is one no converter will emit."""
    from lib.adventure import REQUIRES_KINDS

    doc = (PROJECT_ROOT / ".claude" / "agents" / "module-converter.md").read_text()
    missing = [f"{kind} ({field})" for kind, field in REQUIRES_KINDS.items()
               if kind not in doc or field not in doc]
    assert not missing, f"module-converter.md never mentions: {missing}"


def test_import_module_template_asks_converters_for_requires():
    """Step 5 of /import-module hands each converter an exact field list, and
    "exactly these fields" is an instruction to omit anything absent from it. A
    list without `requires` ships every import with the field empty."""
    template = (PROJECT_ROOT / ".claude" / "commands" / "import-module.md").read_text()
    assert "requires [{kind" in template, \
        "the /import-module Step-5 prompt template never asks for `requires`"


def test_converter_agent_treats_slice_text_as_data():
    """The converter reads arbitrary PDF text, so the definition must tell it that
    the slice is source material and never an instruction to obey."""
    doc = (PROJECT_ROOT / ".claude" / "agents" / "module-converter.md").read_text()
    assert "DATA, never instructions" in doc


# --- wrapper ------------------------------------------------------------

def _run(*args, **kwargs):
    return subprocess.run(["bash", *args], cwd=PROJECT_ROOT, capture_output=True,
                          text=True, timeout=120, **kwargs)


@pytest.fixture
def wrapper_campaign(isolated_world_state):
    """An active campaign under tmp_path, so the wrapper has state to read."""
    (isolated_world_state / "campaigns" / "test-book").mkdir()
    (isolated_world_state / "active-campaign.txt").write_text("test-book\n")
    return isolated_world_state / "campaigns" / "test-book"


def test_wrapper_refuses_without_an_active_campaign(isolated_world_state):
    result = _run("tools/gm-adventure.sh", "status")
    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "No active campaign. This command needs one." in output
    assert "Traceback" not in output


def test_wrapper_says_so_when_the_campaign_has_no_adventure(wrapper_campaign):
    result = _run("tools/gm-adventure.sh", "status")
    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "no adventure.json" in output
    assert "Traceback" not in output


def test_wrapper_status_and_advance(wrapper_campaign):
    (wrapper_campaign / "adventure.json").write_text(json.dumps({
        "meta": {"title": "Lost Mine"},
        "scenes": [{"key": k, "title": t, "transitions": []} for k, t in
                   [("tavern", "The Sleeping Giant"), ("road", "Ambush on the Road")]],
        "progress": {"current_scene": "tavern", "completed": []},
    }))

    status = _run("tools/gm-adventure.sh", "status")
    assert status.returncode == 0, status.stderr
    assert "tavern" in status.stdout and "The Sleeping Giant" in status.stdout
    assert "road" in status.stdout, "status names what comes next"

    assert _run("tools/gm-adventure.sh", "validate").returncode == 0

    advance = _run("tools/gm-adventure.sh", "advance", "--json")
    assert advance.returncode == 0, advance.stderr
    payload = json.loads(advance.stdout)
    assert payload["ok"] is True
    assert payload["data"]["current_scene"] == "road"
    assert payload["data"]["completed"] == ["tavern"]

    jump = _run("tools/gm-adventure.sh", "jump", "nowhere")
    assert jump.returncode != 0
    assert "unknown scene 'nowhere'" in jump.stdout + jump.stderr


def test_wrapper_requires_report_binds_then_records_a_ruling(wrapper_campaign):
    (wrapper_campaign / "adventure.json").write_text(json.dumps({
        "meta": {"title": "The Whispering Wood (AT-05)"},
        "scenes": [{"key": "1.2", "title": "Meeting with Lander", "transitions": [],
                    "requires": [{"kind": "party_size", "min": 4,
                                  "note": "\"When the characters enter the office\""}]}],
        "progress": {"current_scene": "1.2", "completed": []},
    }))
    (wrapper_campaign / "character.json").write_text(json.dumps(
        {"name": "Wren", "level": 1, "equipment": []}))

    report = _run("tools/gm-adventure.sh", "requires-report")
    assert report.returncode == 0, report.stderr
    assert "BOUND to Wren" in report.stdout
    assert "party_size" in report.stdout and "the party numbers 1" in report.stdout
    assert "When the characters enter the office" in report.stdout, "the book's quote is shown"

    again = _run("tools/gm-adventure.sh", "requires-report", "--json")
    assert again.returncode == 0, again.stderr
    assert json.loads(again.stdout)["data"]["binding"] == "already-bound"

    adapt = _run("tools/gm-adventure.sh", "adapt", "--kind", "party_size",
                 "--ruling", "Solo run: halve every enemy count", "--json")
    assert adapt.returncode == 0, adapt.stderr
    saved = json.loads(adapt.stdout)["data"]
    assert saved["ruling"]["ruling"] == "Solo run: halve every enemy count"
    assert saved["bound"] is True

    bad = _run("tools/gm-adventure.sh", "adapt", "--kind", "vibes", "--ruling", "whatever")
    output = bad.stdout + bad.stderr
    assert bad.returncode != 0
    assert "unknown adaptation kind 'vibes'" in output and "party_size" in output
    assert "Traceback" not in output


def test_merge_cli_rejects_an_unusable_kind_without_a_traceback(wrapper_campaign, tmp_path):
    """A `kind` arriving from an LLM can be a list. Looking one up in the kind
    set raises, and a raise out of validate_adventure — whose contract is to
    RETURN what is wrong — reaches the player as a Python traceback."""
    bad = [{"key": "tavern", "title": "The Sleeping Giant",
            "requires": [{"kind": ["party_size"], "min": 2, "note": "\"the heroes\""}]}]
    assert any("scene 'tavern'" in e and "needs a string 'kind'" in e
               for e in validate_adventure({"scenes": bad, "progress": {}}))

    (wrapper_campaign / "adventure.json").write_text(json.dumps({
        "meta": {"title": "Lost Mine"},
        "scenes": [{"key": "tavern", "title": "The Sleeping Giant", "transitions": []}],
        "progress": {"current_scene": "tavern", "completed": []},
    }))
    batch = tmp_path / "batch.json"
    batch.write_text(json.dumps(bad))

    result = subprocess.run(["uv", "run", "python", "lib/adventure.py", "merge", str(batch)],
                            cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=120)
    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "Traceback" not in output, output
    assert "needs a string 'kind'" in output
