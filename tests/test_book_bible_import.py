"""Tests for import-longcontext-read: retention + segmentation + bible auto-draft.

The world-bible subagent read is orchestrated by /import (model call, not
hermetic); these cover the deterministic core that the AC can verify.
"""

from pathlib import Path

from lib import book_bible
from lib.world_bible import validate_bible


SAMPLE = (
    "Chapter One\nThe spice must flow. Paul looked across the dunes.\n\n"
    "Chapter Two\nThe Fremen watched from the rocks, patient as stone.\n\n"
    "Chapter Three\nArrakis taught the lesson of the knife: cutting away the incomplete.\n"
)


def test_segmentation_keeps_large_spans_not_tiny_chunks():
    chapters = book_bible.segment_into_chapters(SAMPLE)
    assert len(chapters) == 3  # one per chapter marker
    assert all("text" in c and "index" in c for c in chapters)
    assert "spice must flow" in chapters[0]["text"]


def test_segmentation_falls_back_to_size_windows():
    big = "no markers here. " * 4000  # ~68k chars, no chapter marks
    chapters = book_bible.segment_into_chapters(big, max_chars=20000)
    assert len(chapters) >= 3 and all(len(c["text"]) <= 20000 for c in chapters)


def test_bible_to_campaign_rules_carries_signature_systems():
    bible = {"name": "DCC", "tone": "comedy-horror",
             "signature_systems": ["loot boxes", "viewer counts"]}
    rules = book_bible.bible_to_campaign_rules(bible)
    assert rules["signature_systems"] == ["loot boxes", "viewer counts"]
    assert "follow them exactly" in rules["description"]


def test_token_estimate_is_observable_not_a_cap():
    n = book_bible.log_token_estimate("abcd" * 100, label="test")
    assert n == 100  # 400 chars // 4; never truncates


def test_extractor_no_longer_deletes_source_text():
    src = Path(__file__).resolve().parent.parent / "lib" / "agent_extractor.py"
    text = src.read_text(encoding="utf-8")
    # current-document.txt must NOT be in the active cleanup list (retained now).
    assert "'current-document.txt',  # Source text" not in text


CAPS_BOOK = (
    "THE TOWER OF THE ELEPHANT\n\n"
    + "Torches flared murkily on the revels in the Maul. " * 60 + "\n\n"
    + "THE SCARLET CITADEL\n\n"
    + "They trailed a wolf pack through the snow.\n"
    + "OLD BALLAD\n\n"
    + "T battle had died away; the shout of victory mingled\n"
    + "HE ROAR OF THE\n"
    + "with the cries of the dying. " * 100 + "\n\n"
    + "This part of the world is made up of tiny realms. " * 60 + "\n"
    # An afterword whose drop-cap opens a LONG section with no title above it:
    # the caps remainder must not become that section's title.
    + "By Stephen Jones\n"
    + "R was born in the fading ex-cowtown of Peaster, Texas, about\n"
    + "OBERT ERVIN HOWARD\n"
    + "forty-five miles west of Fort Worth. " * 100 + "\n"
)


def test_caps_story_titles_are_chapter_markers_and_epigraphs_fold_forward():
    """A scanned collection names its stories in caps. Until 2026-09-04 those were
    not markers, so a whole book was one span cut into 20k windows titled by
    their first sixty characters. A title-only span, an epigraph attribution
    ("OLD BALLAD") fold into the body that follows, keeping the first title;
    a drop-cap remainder ("HE ROAR OF THE", "OBERT ERVIN HOWARD") is never a
    marker at all — it is the rest of a sentence whose initial the printer
    dropped — so even a long untitled afterword does not get one as its title;
    a sentence-initial "part of the" is not a Part marker."""
    titles = [c["title"] for c in book_bible.segment_into_chapters(CAPS_BOOK)]
    assert titles == ["THE TOWER OF THE ELEPHANT", "THE SCARLET CITADEL"], titles


def test_explicit_chapters_never_fold_and_split_pieces_are_labelled():
    chapters = book_bible.segment_into_chapters(SAMPLE)
    assert [c["title"] for c in chapters] == ["Chapter One", "Chapter Two", "Chapter Three"]
    big = "Chapter One\n" + "words " * 9000 + "\nChapter Two\nshort.\n"
    titles = [c["title"] for c in book_bible.segment_into_chapters(big, max_chars=20000)]
    assert titles[:2] == ["Chapter One (1/3)", "Chapter One (2/3)"] and titles[-1] == "Chapter Two"
