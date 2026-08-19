"""Signature-system primitives are no longer a kit surface.

The 5e kit instantiates none, so `WorldKit.systems()` is always empty and the
ROLL-these block never renders. Nothing authors a `systems` list any more either
— a world's signature systems survive as campaign_rules prose.
"""

from lib.session_manager import SessionManager
from lib.world_kit import WorldKit


def test_kit_declares_no_systems_and_no_block_renders(dcc_world):
    assert WorldKit(dcc_world).systems() == []
    assert "SIGNATURE SYSTEMS (executable" not in SessionManager(dcc_world).get_full_context()
