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
