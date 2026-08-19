"""Characterization tests for ConsequenceManager.check_pending — seam #2.

Pins the current return contract before the reactivity-engine ticket rewrites it
to fire/expire triggers. Also documents the real consequence schema
(`consequence`/`trigger`/`id`, NOT `event`/`status`).
"""

from lib.consequence_manager import ConsequenceManager


def test_check_pending_returns_a_list(dcc_world):
    pending = ConsequenceManager(dcc_world).check_pending()
    assert isinstance(pending, list)


def test_check_pending_has_active_consequences(dcc_world):
    pending = ConsequenceManager(dcc_world).check_pending()
    assert len(pending) >= 1, "DCC fixture has active consequences"


def test_each_consequence_uses_the_real_schema(dcc_world):
    """Field is `consequence` (not `event`); `trigger` and `id` present.

    This is the schema the reactivity-engine ticket must preserve while adding
    structured trigger fields additively.
    """
    pending = ConsequenceManager(dcc_world).check_pending()
    for c in pending:
        assert isinstance(c, dict)
        assert c.get("consequence"), "each consequence carries non-empty 'consequence' text"
        assert "trigger" in c
        assert "id" in c


def test_known_consequence_present(dcc_world):
    texts = " ".join(
        c.get("consequence", "") for c in ConsequenceManager(dcc_world).check_pending()
    )
    assert ("Squeeks" in texts) or ("Nightstalker" in texts)
