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

from lib.adventure import AdventureError, AdventureManager, validate_adventure

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
