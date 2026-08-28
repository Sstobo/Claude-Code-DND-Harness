"""Tests for claudemd-lean-core-router: lean CLAUDE.md + mechanics/craft/framework Skills.

CLAUDE.md was swapped to the lean core (the 1227-line original is in git history).
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALL_SKILLS = ["gm-combat", "gm-spellcasting", "gm-conditions", "gm-levelup",
              "gm-dungeon", "gm-craft", "gm-skills", "gm-social"]


def _claude_md():
    return (ROOT / "CLAUDE.md").read_text(encoding="utf-8")


def test_claude_md_is_lean():
    text = _claude_md()
    assert len(text.splitlines()) < 320, "CLAUDE.md should be the lean core now"
    assert "LEAN CORE" in text


def test_lean_core_keeps_always_on_essentials():
    text = _claude_md()
    assert "## The Core Loop" in text
    assert "Persist" in text
    assert "Action Router" in text
    assert "Golden Rules" in text


def test_lean_core_routes_to_all_skills_not_inline_tables():
    text = _claude_md()
    for skill in ALL_SKILLS:
        assert skill in text, f"CLAUDE.md must route to {skill}"
    assert "25,000" not in text  # no inline XP-by-CR table


def test_lean_core_drops_beat_mandates():
    text = _claude_md()
    assert "exactly 3 numbered" not in text
    assert "AT MOST ONE new world development" not in text
    assert "Test before sending" not in text


def test_gm_md_death_handoff_has_no_verbatim_menu():
    text = (ROOT / ".claude" / "commands" / "gm.md").read_text(encoding="utf-8")
    start = text.index("## CHARACTER DEATH")
    end = text.index("## SAVE SESSION", start)
    death = text[start:end]
    assert "Present exactly" not in death
    assert "1. Take over a PARTY MEMBER" not in death
    assert "2. Roll a NEW character" not in death
    assert "3. Step in as a CANON" not in death


def test_lean_core_keeps_load_bearing_sections():
    # The audit's must-restore-inline items.
    text = _claude_md()
    assert "Movement" in text
    assert "Output Format" in text
    assert "Auto Memory Policy" in text
    assert "uv run python" in text
    assert "Search Guide" in text


def test_all_skills_exist_with_frontmatter():
    for name in ALL_SKILLS:
        p = ROOT / ".claude" / "skills" / name / "SKILL.md"
        assert p.exists(), f"missing skill {name}"
        assert f"name: {name}" in p.read_text(encoding="utf-8")


def test_craft_skill_preserves_the_soul():
    text = (ROOT / ".claude" / "skills" / "gm-craft" / "SKILL.md").read_text(encoding="utf-8")
    assert "Yes, and" in text and "Persist before narrating" in text


def test_craft_skill_holds_the_table_voice():
    """Narration drifted into literary prose in a live session — withheld subjects,
    atmospheric throat-clearing, sentences a listener has to re-read. The rule is
    that a GM speaks aloud to one player who cannot scroll back."""
    text = (ROOT / ".claude" / "skills" / "gm-craft" / "SKILL.md").read_text(encoding="utf-8")
    assert "SPEAK IT, DON'T WRITE IT" in text
    assert "Name the subject before you do anything with it" in text

    # And the always-loaded router carries it too, because a scene can open before
    # the craft skill is ever loaded.
    router = _claude_md()
    assert "not a novelist" in router and 'wait, who?' in router


# This fork plays D&D 5e only: no kit gates, no generic-core fallback.
DND_MECHANICS_SKILLS = ["gm-combat", "gm-levelup", "gm-spellcasting"]

KIT_GUARD_PHRASES = [
    "KIT GUARD",
    "KIT block",
    "active kit",
    "World Kit",
    "ruleset.json",
    "non-D&D",
    "generic core",
    "kit-aware",
]


# The 5e content each skill must still carry. A skill that loses its table, or
# re-hides it behind a kit gate, fails on the positive anchor as well as the
# negative one — deletion and re-gating are both caught.
FIVE_E_ANCHORS = {
    "gm-combat": [
        "## XP by Challenge Rating",
        # Death saves are a FLAT DC 10 — a Constitution save you add nothing to.
        "DC 10 flat, no modifiers",
        "damage past 0 that equals or exceeds max HP kills outright",
        # The rail itself: swings resolve in the tool, not in the model's head.
        "gm-combat.sh attack",
        # The pacing contract. Deleting either of these is how a fight turns back
        # into a wall of numbers the player never got to trigger.
        "ONE TURN PER REPLY",
        "THE SWING IS ITS OWN TURN",
        # An inbound blade is not a menu — offering alternatives beside it lets the
        # player spend the ENEMY's turn escaping the enemy's turn.
        "BRACE, DON'T CHOOSE",
        # The acknowledgement prompt is one fixed shape, 64 wide to match the panel.
        # "press 1" for it is wrong — 1 means option 1, and there is no option 2.
        "──────────────────── ▶ ANY KEY TO CONTINUE ─────────────────────",
    ],
    "gm-levelup": [
        "## XP Thresholds",
        "| 1→2 | 300 |",
        "| 3→4 | 2,700 |",
        "## What the New Level Gives",
        "get_class_levels.py <class> <new level>",
    ],
    "gm-spellcasting": [
        "## Spell Slots — fetch the caster's level row",
        "get_class_levels.py <class> <level>",
        "Con save DC 10 or half the damage",
    ],
    "gm-skills": ["Trivial 5 · Easy 10 · Moderate 15 · Hard 20"],
    "gm-social": ["| Persuasion | 10 / 15 / 20 |"],
    "gm-conditions": ["| Paralyzed |"],
}


def _skill_text(name):
    return (ROOT / ".claude" / "skills" / name / "SKILL.md").read_text(encoding="utf-8")


def test_mechanics_skills_are_unconditionally_active():
    for name in DND_MECHANICS_SKILLS:
        text = _skill_text(name)
        assert "close this skill" not in text, f"{name} must not gate itself shut"
        for phrase in KIT_GUARD_PHRASES:
            assert phrase not in text, f"{name} must not carry a kit guard ({phrase!r})"


def test_no_skill_carries_kit_guard_language():
    for name in ALL_SKILLS:
        text = _skill_text(name)
        assert "world_kit.py info" not in text, (
            f"{name} must not instruct world_kit.py info for what context now carries"
        )
        for phrase in KIT_GUARD_PHRASES:
            assert phrase not in text, f"{name} must not carry a kit guard ({phrase!r})"


def test_skills_still_carry_their_five_e_tables():
    for name, anchors in FIVE_E_ANCHORS.items():
        text = _skill_text(name)
        for anchor in anchors:
            assert anchor in text, f"{name} lost its 5e content: {anchor!r}"


def test_judgment_skills_state_five_e_tables_outright():
    for name in ("gm-skills", "gm-social", "gm-conditions"):
        text = _skill_text(name)
        assert "use them only when" not in text and "apply it only when" not in text, (
            f"{name} must state its 5e tables unconditionally"
        )


def test_world_kit_exposes_kit_identity():
    import json
    import subprocess
    import sys as _sys
    r = subprocess.run([_sys.executable, str(ROOT / "lib" / "world_kit.py"), "info", "--json"],
                       capture_output=True, text=True, cwd=str(ROOT))
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)["data"]
    assert data["kit"] == "dnd5e", data


def test_the_router_hardwires_the_combat_pacing_contract():
    """The always-loaded router must carry the pacing rules, not just the skill.

    The skill loads on demand; a fight can start narrating before it does. Both
    rules were added because a live session lost them: a whole round narrated in
    one message, and a swing resolved in the same reply that announced it.
    """
    row = next(l for l in _claude_md().splitlines() if l.startswith('| "I attack'))
    assert "one turn per reply" in row.lower()
    assert "next message" in row.lower(), "the swing must wait for the player"


def test_images_are_shown_bare():
    """Text wrapped around a picture buries the beat it was meant to illustrate.
    The chronicler stays a style lock; they are never narrated at the player."""
    craft = (ROOT / ".claude" / "skills" / "gm-craft" / "SKILL.md").read_text(encoding="utf-8")
    assert "SHOW THE IMAGE AND NOTHING ELSE" in craft
    assert "STYLE LOCK, not a narrator" in craft
    assert "BEHOLD" not in _claude_md(), "the router must not still demand in-world framing"
    assert "SHOW THE IMAGE AND NOTHING ELSE" in _claude_md()


def test_the_router_demands_the_staged_dice_block_not_a_summary():
    """A live session ran a roll, saw the result, and then wrote fresh prose around
    it instead of pasting the tool's actual output — losing the dead air and the
    margin that make a roll feel real. The router already said not to; nothing
    was anchoring that sentence, so nothing caught the drift."""
    text = _claude_md()
    assert "paste the tool's output straight into narration" in text
    assert "never a one-liner" in text
