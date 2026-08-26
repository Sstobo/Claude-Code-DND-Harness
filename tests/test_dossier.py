"""The dossier — the living campaign document — and the chronicle behind it.

Abundance architecture: sections render whole (the scarcity caps live nowhere in
this path), the chronicle is append-only narrative with origin stamps, and the
write-time category gate replaces the read-side whitelist that silently hid
three campaigns' facts.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from session_manager import SessionManager
from note_manager import NoteManager


def _world(tmp_path):
    c = tmp_path / "campaigns" / "t"
    c.mkdir(parents=True)
    (tmp_path / "active-campaign.txt").write_text("t")
    (c / "campaign-overview.json").write_text(json.dumps({
        "campaign_name": "T", "current_date": "1st", "time_of_day": "Dawn",
        "player_position": {"current_location": "The Gate"}}))
    (c / "character.json").write_text(json.dumps({"name": "Hero", "level": 1,
                                                  "hp": {"current": 5, "max": 5}}))
    (c / "npcs.json").write_text(json.dumps({
        "Keeper": {"description": "gatekeeper", "goal": "keep the gate",
                   "tags": {"locations": ["The Gate"]},
                   "visual_appearance": {"hair": "", "eyes": "grey"}}}))
    (c / "adventure.json").write_text(json.dumps({
        "meta": {"title": "M", "levels": "1"},
        "scenes": [
            {"key": "1.1", "title": "In", "location": "The Gate",
             "gm_notes": "N" * 2000, "read_aloud": "R" * 1200,
             "transitions": [{"to_key": "1.2", "when": "they pass"}]},
            {"key": "1.2", "title": "Beyond", "location": "The Road",
             "gm_notes": "the road goes on", "read_aloud": "", "transitions": []},
        ],
        "progress": {"current_scene": "1.1", "completed": []}}))
    return tmp_path


def test_dossier_renders_whole_scene_and_horizon(tmp_path):
    d = SessionManager(str(_world(tmp_path))).get_dossier()
    assert "N" * 2000 in d, "current scene gm_notes must be whole"
    assert "R" * 1200 in d, "read_aloud must be whole"
    assert "THE STORY COMING UP" in d and "the road goes on" in d, \
        "the next scene's full text rides in the horizon"
    assert "when: they pass" in d


def test_present_npc_gets_full_sheet_with_empty_fields_dropped(tmp_path):
    d = SessionManager(str(_world(tmp_path))).get_dossier()
    assert "keep the gate" in d, "present NPC inner life renders"
    assert '"eyes": "grey"' in d and '"hair"' not in d, "empty appearance fields drop"


def test_chronicle_appends_and_renders(tmp_path):
    m = SessionManager(str(_world(tmp_path)))
    m.chronicle_add("[INVENTED] a first entry", scene="1.1")
    m.chronicle_add("[BOOK 1.1] a second entry")
    d = m.get_dossier()
    assert "THE STORY SO FAR" in d
    assert d.index("[INVENTED] a first entry") < d.index("[BOOK 1.1] a second entry"), \
        "chronicle is append-only, oldest first"


def test_fact_category_gate(tmp_path):
    w = _world(tmp_path)
    n = NoteManager(str(w))
    assert n.add_fact("add", "muscle-memory verb") is False, \
        "the 'add' verb-as-category mistake is rejected"
    assert n.add_fact("plot_local", "a real fact") is True
    facts = json.loads((w / "campaigns" / "t" / "facts.json").read_text())
    assert "add" not in facts and len(facts["plot_local"]) == 1


def test_key_facts_render_every_stored_category(tmp_path):
    w = _world(tmp_path)
    (w / "campaigns" / "t" / "facts.json").write_text(json.dumps({
        "plot_local": [{"fact": "in-list fact"}],
        "legacy_bucket": [{"fact": "orphaned but stored"}]}))
    facts = SessionManager(str(w))._key_facts()
    assert "in-list fact" in facts and "orphaned but stored" in facts, \
        "read side renders everything; the gate lives at write time"


def test_prep_block_degrades_to_whatever_sources_exist():
    assert SessionManager._prep_block() == [], "no sources, no header over nothing"

    only_clock = "\n".join(SessionManager._prep_block(
        clocks={"Thanatos stirs": {"current": 4, "max": 4},
                "A slow one": {"current": 1, "max": 6}}))
    assert "Tonight will test" in only_clock and "Thanatos stirs" in only_clock
    assert "A slow one" not in only_clock, "clocks below half are not yet pressure"
    assert "Tonight must honor" not in only_clock and "Do not contradict" not in only_clock

    whole = "\n".join(SessionManager._prep_block(
        chronicle="## 2026-01-01 — 1.1\n\nfirst line of the entry\nthe line they stopped on",
        facts=["the newest fact", "the second newest"],
        consequences={"active": [{"consequence": "Someone heard the name.",
                                 "trigger": "the Tipsy Marlin"}]},
        scene={"key": "1.2", "title": "1.2 Meeting with Lander",
               "location": "The Stockade", "read_aloud": "Lander floats in mist."}))
    assert "Tonight must honor: the line they stopped on" in whole, \
        "the tail is the last LINE of the chronicle, not the first of the last entry"
    assert "the Tipsy Marlin" in whole and "the newest fact" in whole
    assert "One strong start" in whole and "1.2 Meeting with Lander at The Stockade" in whole, \
        "a scene titled with its own key is not double-keyed"
    assert "GM-PRIVATE" in whole


def test_session_start_prints_the_prep_block_from_live_state(tmp_path, capsys):
    m = SessionManager(str(_world(tmp_path)))
    m.chronicle_add("[BOOK 1.1] the gate stood open", scene="1.1")
    m.start_session()
    out = capsys.readouterr().out
    assert "TONIGHT'S PREP" in out and "GM-PRIVATE" in out
    assert "the gate stood open" in out
    assert "One strong start" in out and "The Gate" in out


def test_clocks_and_consequences_render_in_the_dossier(tmp_path):
    """Both shipped silently broken behind bare excepts: a wrong class name
    (ThreatClocks vs ThreatClockManager) and a guessed store shape
    ("consequences" key vs {"active": [...]}, "description" vs "consequence")."""
    w = _world(tmp_path)
    c = w / "campaigns" / "t"
    (c / "threat-clocks.json").write_text(json.dumps(
        {"Doom": {"current": 2, "max": 4, "advance_on": "time"}}))
    (c / "consequences.json").write_text(json.dumps(
        {"active": [{"id": "x", "consequence": "the roof falls", "trigger": "dawn"}],
         "resolved": []}))
    d = SessionManager(str(w)).get_dossier()
    assert "Doom: 2/4" in d
    assert "the roof falls (trigger: dawn)" in d


def test_one_malformed_clock_costs_its_line_not_the_section(tmp_path):
    """The first hardening pass moved the silent-death from wrong-class-name to
    unguarded int(): one hand-edited null erased the section, healthy clocks
    included. A zero-segment clock must also never read FULL."""
    w = _world(tmp_path)
    c = w / "campaigns" / "t"
    (c / "threat-clocks.json").write_text(json.dumps({
        "Doom": {"current": 2, "max": 4},
        "Hand-edited": {"current": None, "max": 4},
        "Zero": {"current": 0, "max": 0}}))
    d = SessionManager(str(w)).get_dossier()
    assert "Doom: 2/4" in d, "the healthy clock survives its bad neighbour"
    assert "Hand-edited" not in d
    assert "FULL" not in d.split("THREAT CLOCKS")[1].split("---")[0],         "0/0 is not a due beat"
    ctx = SessionManager(str(w)).get_full_context()
    assert "Doom" in ctx, "the per-beat brief also survives the malformed clock"


# --- the prep block's five review criteria -------------------------------
# Each of these shipped once: an opening image that echoed the must-honor
# line, a hand-edited clock that killed `start`, GM bookkeeping offered as
# the thing to open on, "Dr." returned as a sentence, and the importer's own
# diagnostics rendered as campaign continuity.

def _strong_start(block) -> str:
    return next(ln for ln in block if ln.startswith("One strong start"))


def test_strong_start_never_echoes_the_must_honor_line():
    tail = "the lantern went out and nobody moved"
    block = SessionManager._prep_block(chronicle=f"## 2026-01-01 - 1.1\n{tail}",
                                       location="The Gate")
    joined = "\n".join(block)
    assert f"Tonight must honor: {tail}" in joined
    assert tail not in _strong_start(block), \
        "with no adventure.json the chronicle tail is not recycled as the image"
    assert "open mid-motion at The Gate" in _strong_start(block)


def test_strong_start_without_a_module_is_location_only(tmp_path, capsys):
    w = _world(tmp_path)
    (w / "campaigns" / "t" / "adventure.json").unlink()
    m = SessionManager(str(w))
    m.chronicle_add("[INVENTED] the gate stood open", scene="1.1")
    m.start_session()
    out = capsys.readouterr().out
    start = next(ln for ln in out.splitlines() if ln.startswith("One strong start"))
    assert "The Gate" in start
    assert "the gate stood open" not in start, "the headline line is not an echo"


def test_a_malformed_clock_drops_its_own_line_not_the_block():
    block = SessionManager._prep_block(
        chronicle="## 2026-01-01 - 1.1\nthe line they stopped on",
        clocks={"Hand-edited": {"current": "four", "max": 4},
                "Doom": {"current": 3, "max": 4}})
    joined = "\n".join(block)
    assert "Tonight must honor: the line they stopped on" in joined
    assert "Doom" in joined and "Hand-edited" not in joined


def test_malformed_top_level_shapes_do_not_raise():
    joined = "\n".join(SessionManager._prep_block(
        clocks=["not a mapping"], consequences="not a mapping",
        scene="not a mapping", location="The Gate"))
    assert "open mid-motion at The Gate" in joined


def test_start_survives_a_malformed_clock_and_an_unreadable_source(tmp_path, capsys, monkeypatch):
    w = _world(tmp_path)
    (w / "campaigns" / "t" / "threat-clocks.json").write_text(json.dumps(
        {"Hand-edited": {"current": "four", "max": 4}}))
    m = SessionManager(str(w))
    assert m.start_session()["current_location"] == "The Gate"
    assert "TONIGHT'S PREP" in capsys.readouterr().out

    monkeypatch.setattr(SessionManager, "_prep_sources",
                        lambda self: (_ for _ in ()).throw(RuntimeError("boom")))
    assert m._prep_lines() == [], "prep is a courtesy; it never costs the start command"
    assert m.start_session()["current_location"] == "The Gate"


def test_gm_notes_are_never_the_opening_image():
    block = SessionManager._prep_block(scene={
        "key": "1.5", "title": "1.5 The Barred Door", "location": "The Road",
        "read_aloud": "",
        "gm_notes": "If the party failed the check in 1.4, the door is barred."})
    start = _strong_start(block)
    assert "1.5 The Barred Door at The Road" in start
    assert "failed the check" not in start and "—" not in start, \
        "no read_aloud yields a start line with no quoted image"


def test_prep_sentence_cuts_at_the_earliest_real_boundary():
    assert SessionManager._prep_sentence(
        "Dr. Sallow met them at the pier and would not look up."
    ) == "Dr. Sallow met them at the pier and would not look up.", \
        "an abbreviation is not a sentence boundary"
    assert SessionManager._prep_sentence(
        "The bolt struck the post! Then the door opened. And nobody spoke."
    ) == "The bolt struck the post!", "earliest boundary wins, whichever mark it is"


def test_import_diagnostics_never_render_as_continuity(tmp_path):
    w = _world(tmp_path)
    (w / "campaigns" / "t" / "facts.json").write_text(json.dumps({
        "dropped_references": [{
            "fact": "Import dropped a location reference that named no "
                    "destination: 'see area 3' (a connection routing rule, or blank).",
            "timestamp": "2030-01-01T00:00:00+00:00"}],
        "plot_local": [{"fact": "The Keeper owes the party a debt.",
                        "timestamp": "2020-01-01T00:00:00+00:00"}]}))
    joined = "\n".join(SessionManager(str(w))._prep_lines())
    assert "The Keeper owes the party a debt." in joined
    assert "Import dropped" not in joined, \
        "location_reconcile's bucket is diagnostics, not continuity"
