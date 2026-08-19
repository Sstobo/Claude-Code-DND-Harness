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
