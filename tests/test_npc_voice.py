"""Tests for npc-voice-surfacing.

The NPC `context` field stores verbatim book/source dialogue (the canonical
voice). Pre-fix it was loaded by nothing during play. These assert the voice is
now retrievable via the manager and surfaced for present NPCs in the context,
without ever mutating the stored lines.
"""

import json
from pathlib import Path

from lib.npc_manager import NPCManager
from lib.session_manager import SessionManager


def _npcs_path(dcc_world):
    return Path(dcc_world) / "campaigns" / "dungeon-crawler-carl" / "npcs.json"


def test_get_voice_returns_canonical_lines(dcc_world):
    voice = NPCManager(dcc_world).get_voice("Mordecai")
    assert isinstance(voice, list) and voice
    assert any("ain't allowed in here" in line for line in voice)


def test_get_voice_missing_npc_returns_none(dcc_world):
    assert NPCManager(dcc_world).get_voice("NopeMcGhost") is None


def test_context_surfaces_present_npc_voices(dcc_world):
    ctx = SessionManager(dcc_world).get_full_context()
    assert "NPC VOICES" in ctx
    assert "Carl:" in ctx  # party member, present every scene


def test_get_voice_is_read_only(dcc_world):
    path = _npcs_path(dcc_world)
    before = path.read_text(encoding="utf-8")
    NPCManager(dcc_world).get_voice("Mordecai")
    SessionManager(dcc_world).get_full_context()  # also surfaces voice
    assert path.read_text(encoding="utf-8") == before, "voice surfacing must not mutate npcs.json"
