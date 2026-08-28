"""Appearance injection must fire even when the prompt names the character.

Regression: the old guard skipped injection when the character's NAME appeared
in the prompt — the natural way to write a beat brief — so recurring characters
drifted off-model.
"""

import json
from pathlib import Path

from lib.image_gen import inject_appearances


def _campaign_with_appearance(dcc_world):
    campaign = Path(dcc_world) / "campaigns" / "dungeon-crawler-carl"
    char_path = campaign / "character.json"
    char = json.loads(char_path.read_text())
    char["visual_appearance"] = {
        "sex": "male", "age": "late 20s", "race": "Human", "species": "human",
        "hair": "short brown", "face": "stubbled", "eyes": "brown",
        "clothing": "boxer shorts", "gear": "barefoot, spiked gauntlet",
        "demeanor": "scrappy", "size": "average build",
    }
    char_path.write_text(json.dumps(char))
    return campaign, char["name"]


def test_injects_even_when_prompt_names_the_character(dcc_world):
    campaign, name = _campaign_with_appearance(dcc_world)
    prompt = f"{name} swings a club at the Terror Clown"
    out = inject_appearances(prompt, [name], campaign)
    assert "Character (render exactly):" in out
    assert "boxer shorts" in out


def test_injection_is_idempotent(dcc_world):
    campaign, name = _campaign_with_appearance(dcc_world)
    once = inject_appearances("a battle scene", [name], campaign)
    twice = inject_appearances(once, [name], campaign)
    assert once == twice


def test_unknown_character_injects_nothing(dcc_world):
    campaign, _ = _campaign_with_appearance(dcc_world)
    prompt = "a quiet vista"
    assert inject_appearances(prompt, ["Nobody Real"], campaign) == prompt


def test_the_style_lock_leads_the_prompt(dcc_world, monkeypatch):
    """The locked style must PREPEND, not trail the scene description.

    Image models weight the opening of a prompt far more heavily than the tail.
    A cartoon signature appended after three sentences of scene loses to the
    scene, which is exactly how a locked style quietly renders as generic art.
    """
    from lib import image_gen

    monkeypatch.setattr(image_gen, "load_chronicler",
                        lambda *_a, **_k: {"style": "In the style of FLAT CARTOON PLATE"})
    out = image_gen.build_prompt("A boy stands in a ruined hall.", campaign_dir=None)
    assert out.startswith("In the style of FLAT CARTOON PLATE"), out[:80]
    assert "Scene: A boy stands in a ruined hall." in out


def test_style_is_not_doubled_when_the_caller_already_stated_it(dcc_world, monkeypatch):
    from lib import image_gen

    monkeypatch.setattr(image_gen, "load_chronicler",
                        lambda *_a, **_k: {"style": "In the style of FLAT CARTOON PLATE"})
    already = "In the style of FLAT CARTOON PLATE. A boy stands in a hall."
    assert image_gen.build_prompt(already, campaign_dir=None).count("FLAT CARTOON PLATE") == 1
