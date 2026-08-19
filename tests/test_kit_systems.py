"""Signature-system primitives are no longer a kit surface.

The 5e kit instantiates none, so `WorldKit.systems()` is always empty and the
ROLL-these block never renders. `book_bible.write_systems` still authors the
`systems` list onto disk (its own ticket owns that file), so its validation is
tested against the file it writes rather than through the kit.
"""

import json
from pathlib import Path

from lib.session_manager import SessionManager
from lib.world_kit import WorldKit


def test_kit_declares_no_systems_and_no_block_renders(dcc_world):
    assert WorldKit(dcc_world).systems() == []
    assert "SIGNATURE SYSTEMS (executable" not in SessionManager(dcc_world).get_full_context()


def test_write_systems_roundtrips_and_drops_malformed(dcc_world):
    from lib import book_bible
    active = (Path(dcc_world) / "active-campaign.txt").read_text().strip()
    cdir = Path(dcc_world) / "campaigns" / active
    book_bible.write_systems(str(cdir), [
        {"primitive": "named_track", "name": "Dread", "config": {"max": 4}},
        {"name": "bad — no primitive"},   # dropped
        {"primitive": "price_roll"},        # dropped — no name
    ])
    got = json.loads((cdir / "ruleset.json").read_text())["systems"]
    assert [s["name"] for s in got] == ["Dread"], "round-trips one, drops the malformed two"
    assert got[0]["config"] == {"max": 4}
