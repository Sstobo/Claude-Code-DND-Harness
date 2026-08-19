"""The import chain: source text -> world-bible -> campaign_rules.

Import Step 6.7 used to read a world-bible.json that no step wrote. These cover
the wired chain — every fixture is a throwaway tmp campaign, never a live one.
Kit drafting is gone: the harness is 5e, so nothing here writes a ruleset.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from lib import book_bible
from lib.book_bible import ConfirmedBibleError
from lib.world_bible import validate_bible

REPO = Path(__file__).resolve().parent.parent

VERBATIM = "The Iron Tangle ate the station whole, and the trains kept running."

SOURCE = (
    "Chapter One\n"
    "Carl stood barefoot on the platform, counting the exits.\n"
    f"{VERBATIM}\n\n"
    "Chapter Two\n"
    "The loot box hissed open and the crowd, somewhere far above, screamed for more.\n"
)


@pytest.fixture
def campaign(tmp_path):
    """A bare campaign directory holding only the prepared source text."""
    cdir = tmp_path / "campaigns" / "iron-tangle"
    cdir.mkdir(parents=True)
    (cdir / "current-document.txt").write_text(SOURCE, encoding="utf-8")
    return cdir


def test_draft_bible_writes_an_unconfirmed_grounded_draft(campaign):
    bible = book_bible.draft_bible(
        campaign,
        name="The Iron Tangle",
        voice={
            "style": "clipped, wry, disaster-comic",
            "sample_passages": [VERBATIM, "A wise wizard cast fireball at the goblins."],
            "vocab": ["loot box"],
        },
    )

    on_disk = json.loads((campaign / "world-bible.json").read_text(encoding="utf-8"))
    assert on_disk == bible
    assert bible["confirmed"] is False
    assert bible["name"] == "The Iron Tangle"
    # Verbatim filter: the real excerpt survives, the invented one does not.
    assert bible["voice"]["sample_passages"] == [VERBATIM]
    # Chapters are no longer persisted to the bible (2026-08-15: replaced by the
    # world index). segment_into_chapters still feeds the RAG coarse index only.
    assert "chapters" not in bible
    assert bible["index"] == {"npcs": [], "locations": [], "items": [], "monsters": []}
    # Skeleton keys are present, so the bible validates before the model fills them.
    assert validate_bible(bible) == (True, [])


def test_draft_bible_is_idempotent_and_keeps_authored_fields(campaign):
    book_bible.draft_bible(campaign, name="The Iron Tangle")
    book_bible.draft_bible(campaign, fields={
        "tone": "comedy-horror",
        "signature_systems": ["loot boxes", "viewer counts"],
    })
    bible = book_bible.draft_bible(campaign)  # a third pass must not wipe the above

    assert bible["name"] == "The Iron Tangle"
    assert bible["tone"] == "comedy-horror"
    assert bible["signature_systems"] == ["loot boxes", "viewer counts"]
    assert bible["confirmed"] is False


def test_draft_bible_refuses_a_confirmed_bible(campaign):
    book_bible.draft_bible(campaign, name="The Iron Tangle")
    path = campaign / "world-bible.json"
    approved = json.loads(path.read_text(encoding="utf-8"))
    approved["confirmed"] = True
    path.write_text(json.dumps(approved), encoding="utf-8")

    with pytest.raises(ConfirmedBibleError):
        book_bible.draft_bible(campaign, name="Something Else")
    assert json.loads(path.read_text(encoding="utf-8"))["name"] == "The Iron Tangle"


def test_draft_bible_without_source_text_fails_loudly(tmp_path):
    with pytest.raises(FileNotFoundError):
        book_bible.draft_bible(tmp_path)


def test_campaign_rules_land_in_the_overview(campaign):
    book_bible.draft_bible(campaign, name="The Iron Tangle", fields={
        "tone": "comedy-horror",
        "signature_systems": ["loot boxes", "viewer counts"],
    })
    (campaign / "campaign-overview.json").write_text(
        json.dumps({"player_position": "Platform 9"}), encoding="utf-8")

    book_bible.write_campaign_rules(campaign)

    overview = json.loads((campaign / "campaign-overview.json").read_text(encoding="utf-8"))
    assert overview["player_position"] == "Platform 9"  # existing state preserved
    rules = overview["campaign_rules"]
    assert rules["signature_systems"] == ["loot boxes", "viewer counts"]
    assert rules["tone"] == "comedy-horror"
    assert "follow them exactly" in rules["description"]


def test_chain_without_a_bible_names_the_step_that_writes_it(campaign):
    with pytest.raises(FileNotFoundError, match="draft-bible"):
        book_bible.write_campaign_rules(campaign)


def test_review_survives_string_faction_nodes(dcc_world):
    # The review screen is what the player approves the draft from, and faction
    # nodes are model-authored: conan's live bible lists them as bare strings.
    from lib.world_bible import WorldBible

    path = Path(dcc_world) / "campaigns" / "dungeon-crawler-carl" / "world-bible.json"
    bible = json.loads(path.read_text(encoding="utf-8"))
    bible["factions"] = {"nodes": ["The System", "The Borant Corporation"], "edges": []}
    path.write_text(json.dumps(bible), encoding="utf-8")

    assert WorldBible(dcc_world).review_summary()["factions"] == [
        "The System", "The Borant Corporation"]


def test_cli_drives_the_whole_chain(campaign):
    def run(*args):
        return subprocess.run([sys.executable, str(REPO / "lib" / "book_bible.py"), *args],
                              capture_output=True, text=True)

    assert run("draft-bible", str(campaign), "--name", "The Iron Tangle",
               "--voice-json", json.dumps({"style": "clipped", "sample_passages": [VERBATIM]}),
               "--fields-json", json.dumps({"signature_systems": ["loot boxes"]})).returncode == 0
    assert run("campaign-rules", str(campaign)).returncode == 0

    overview = json.loads((campaign / "campaign-overview.json").read_text(encoding="utf-8"))
    assert overview["campaign_rules"]["signature_systems"] == ["loot boxes"]

    # Kit drafting is gone: argparse rejects the verb outright rather than the
    # command failing for some incidental reason.
    refused = run("draft-ruleset", str(campaign))
    assert refused.returncode == 2
    assert "invalid choice: 'draft-ruleset'" in refused.stderr
    assert not (campaign / "ruleset.json").exists()


@pytest.mark.parametrize("command", ["new-game.md", "import.md"])
def test_creation_commands_carry_no_kit_drafting(command):
    """Campaign creation goes straight to 5e — no kit ceremony in either door."""
    doc = (REPO / ".claude" / "commands" / command).read_text(encoding="utf-8")
    for gone in ("draft-ruleset", "write-systems", "ruleset.json"):
        assert gone not in doc, f"{command} still references {gone}"
    # The surviving surface: a world's signature systems land in campaign_rules.
    assert "campaign-rules" in doc and "campaign_rules" in doc
