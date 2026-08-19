"""Regression tests for untruncate-campaign-rules.

The pre-fix code cut every campaign_rules value to 220 chars, starving the GM of
its own world's operating manual (dm_checklist, achievement_checks, ...). These
assert the bespoke rules now render in full under a clear "follow exactly" label.
"""

from lib.session_manager import SessionManager


def _ctx(dcc_world):
    return SessionManager(dcc_world).get_full_context()


def test_rules_block_has_follow_exactly_label(dcc_world):
    assert "YOUR WORLD'S RULES (follow exactly)" in _ctx(dcc_world)


def test_deep_rule_content_survives_no_truncation(dcc_world):
    ctx = _ctx(dcc_world)
    # Each of these lives FAR past the old 220-char cut inside loot_box_system,
    # so their presence proves the value is rendered whole. Fails on pre-fix code.
    for deep in ("achievement_checks", "opening_ceremony", "dm_checklist", "Celestial Quest Box"):
        assert deep in ctx, f"deep rule content {deep!r} must survive (no truncation)"


def test_no_truncation_marker_in_rules_section(dcc_world):
    ctx = _ctx(dcc_world)
    assert "YOUR WORLD'S RULES" in ctx
    rules_section = ctx.split("YOUR WORLD'S RULES", 1)[1]
    assert "use --full" not in rules_section, "rules must never be truncated with a --full pointer"
