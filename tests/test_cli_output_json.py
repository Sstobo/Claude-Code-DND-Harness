"""Tests for the shared JSON envelope (cli_output) + the search.py --json slice.

Foundation for json-returning-wrappers: a stable {"ok", "data"|"error"} envelope
so callers parse structured data instead of scraping stdout. Per-manager wiring
(session/consequence/player/npc) lands in its own sub-tickets.
"""

import json

from lib.cli_output import emit, emit_error, strip_json_flag, wants_json
from lib.search import WorldSearcher


def test_wants_json_detects_flag():
    assert wants_json(["prog", "q", "--json"]) is True
    assert wants_json(["prog", "q"]) is False


def test_strip_json_flag_removes_only_the_flag():
    assert strip_json_flag(["a", "--json", "b"]) == ["a", "b"]


def test_emit_success_envelope(capsys):
    emit({"k": 1}, json_mode=True)
    assert json.loads(capsys.readouterr().out) == {"ok": True, "data": {"k": 1}}


def test_emit_human_mode_prints_message_not_json(capsys):
    emit(data={"k": 1}, message="hello", json_mode=False)
    assert capsys.readouterr().out.strip() == "hello"


def test_emit_error_envelope_and_exit_code(capsys):
    rc = emit_error("boom", json_mode=True, code=2)
    d = json.loads(capsys.readouterr().out)
    assert d == {"ok": False, "error": "boom", "code": 2}
    assert rc == 1


def test_search_returns_structured_dict(dcc_world):
    results = WorldSearcher(dcc_world).search_all("dragon")
    assert isinstance(results, dict)
    for key in ("facts", "npcs", "locations", "consequences", "plots"):
        assert key in results
