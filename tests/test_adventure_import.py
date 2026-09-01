"""Tests for the deterministic spine slicer.

Everything here runs without a PDF: header detection on synthetic extracted
text, and the column geometry on synthetic word boxes. Both have to be
reproducible, and both have silently produced interleaved slices before. The
extraction is then checked against a real book by hand.
"""

import json
import os
import re
from pathlib import Path
from unittest import mock

import pytest

from lib.adventure_import import detect_headers, is_listing_page, slice_scenes, slice_pdf
from lib.content_extractor import (
    PDFExtractor,
    band_bounds,
    find_column_gutter,
    gutter_from_rows,
    page_text_by_rows,
    row_text,
    words_are_glued,
    text_rows,
)


# The sample book is not redistributable, so it lives outside the repo: point
# GM_TEST_MODULE_PDF at your own module PDF to run the live checks, otherwise
# they skip.
TEST_PDF = Path(os.environ.get("GM_TEST_MODULE_PDF", "source-material/_test-module.pdf"))

PAGE_TEXT = """--- Page 1 ---
Introduction
The heroes begin in Saltport.

--- Page 2 ---
1.1 The Whispering Call
The sheriff is waiting.
1.2 Meeting with Lander

--- Page 3 ---
Lander glows.
2.7 Misfit Menagerie of Greenkey
A shop full of odd beasts.
"""


def _stub_extractor(text, mode='columns'):
    """A PDFExtractor stand-in whose column-aware extract returns fixed text."""
    return lambda: type("Stub", (), {
        "last_mode": mode,
        "extract": lambda self, path, column_aware: text,
    })()


def _word(x0, x1, top, text="word"):
    return {"x0": x0, "x1": x1, "top": top, "bottom": top + 10, "text": text}


def _two_column_words(rows=30):
    """Words for a page 600 wide with columns at 40-290 and 310-560."""
    words = []
    for i in range(rows):
        top = 100 + i * 12
        words.append(_word(40, 290, top))
        words.append(_word(310, 560, top))
    return words


def test_headers_found_in_document_order():
    keys = [h["key"] for h in detect_headers(PAGE_TEXT)]
    assert keys == ["1.1", "1.2", "2.7"]


def test_header_titles_and_pages():
    headers = {h["key"]: h for h in detect_headers(PAGE_TEXT)}
    assert headers["1.1"]["title"] == "The Whispering Call"
    assert headers["2.7"]["page"] == 3


def test_front_matter_is_everything_before_the_first_key():
    front, scenes = slice_scenes(PAGE_TEXT)
    assert "Introduction" in front
    assert "The heroes begin in Saltport." in front
    assert "1.1" not in front
    assert scenes[0]["key"] == "1.1"


def test_slice_runs_to_the_next_header_and_keeps_page_markers():
    _, scenes = slice_scenes(PAGE_TEXT)
    by_key = {s["key"]: s for s in scenes}
    assert by_key["1.1"]["text"].splitlines() == [
        "1.1 The Whispering Call",
        "The sheriff is waiting.",
    ]
    assert "--- Page 3 ---" in by_key["1.2"]["text"]
    assert by_key["1.2"]["pages"] == [2, 3]


def test_chapter_headings_are_headers_too():
    text = "--- Page 1 ---\nPart 3: The Woodland\nTrees everywhere.\n"
    headers = detect_headers(text)
    assert [(h["key"], h["title"]) for h in headers] == [("part-3", "The Woodland")]


def test_contents_page_is_skipped():
    toc = (
        "--- Page 2 ---\n"
        "Contents\n"
        "1.1 The Whispering Call ..............................2\n"
        "1.2 Meeting with Lander ..............................2\n"
        "--- Page 3 ---\n"
        "1.1 The Whispering Call\n"
        "The sheriff is waiting.\n"
    )
    assert is_listing_page(toc.splitlines()[:4])
    headers = detect_headers(toc)
    assert [h["page"] for h in headers] == [3], "the real header, not the listing"


# An overview or flowchart page has no dotted leaders at all — just key after
# key. Recording those first would leave every real scene discarded as a
# duplicate, which is how a whole book once collapsed into one entry.
OVERVIEW_TEXT = """--- Page 2 ---
Adventure Overview
1.1 The Whispering Call
1.2 Meeting with Lander
1.3 the Salty Siren
1.4 Passage to Eldoria
2.1 Dockside Hustle

--- Page 3 ---
1.1 The Whispering Call
Location: The Stockade
Sheriff Waveshield has been waiting since dawn, and she does
not look pleased about it.
There are two guards on the stair.

--- Page 4 ---
1.2 Meeting with Lander
Location: The Saltbreeze Stockade
The creature floats amid swirling mists, tendrils swaying.
Lander: "Greetings, heroes."
"""


def test_leaderless_overview_page_does_not_swallow_real_scenes():
    assert is_listing_page(OVERVIEW_TEXT.split("--- Page 3 ---")[0].splitlines())

    _, scenes = slice_scenes(OVERVIEW_TEXT)
    by_key = {s["key"]: s for s in scenes}
    assert sorted(by_key) == ["1.1", "1.2"]
    assert by_key["1.1"]["pages"] == [3]
    assert "Sheriff Waveshield has been waiting" in by_key["1.1"]["text"]
    assert by_key["1.2"]["pages"] == [4]
    assert "Lander:" in by_key["1.2"]["text"]


def test_a_real_scene_page_is_not_mistaken_for_a_listing():
    page = OVERVIEW_TEXT.split("--- Page 3 ---")[1].split("--- Page 4 ---")[0]
    assert not is_listing_page(page.splitlines())


def test_pages_exclude_a_trailing_next_scene_marker():
    text = (
        "--- Page 1 ---\n"
        "1.1 The Call\n"
        "The sheriff is waiting.\n"
        "--- Page 2 ---\n"
        "1.2 The Meeting\n"
        "A jellyfish speaks.\n"
    )
    by_key = {s["key"]: s for s in slice_scenes(text)[1]}
    assert by_key["1.1"]["pages"] == [1], "1.1 has no text on page 2"
    assert by_key["1.2"]["pages"] == [2]


def test_page_zero_is_kept():
    # Text before any marker is page 0 — a falsy page number that must survive.
    _, scenes = slice_scenes("1.1 The Call\nThe sheriff is waiting.\n")
    assert scenes[0]["pages"] == [0]


def test_stale_slices_from_a_previous_run_are_cleared(tmp_path):
    (tmp_path / "scene-9.9.txt").write_text("left over from another book")
    with mock.patch("lib.adventure_import.PDFExtractor", _stub_extractor(PAGE_TEXT)):
        slice_pdf("unused.pdf", tmp_path)
    assert not (tmp_path / "scene-9.9.txt").exists()
    assert (tmp_path / "scene-1.1.txt").exists()


def test_repeated_key_does_not_restart_a_scene():
    text = (
        "--- Page 1 ---\n"
        "1.1 The Whispering Call\n"
        "The sheriff is waiting.\n"
        "--- Page 2 ---\n"
        "1.1 The Whispering Call\n"
        "She is still waiting.\n"
    )
    _, scenes = slice_scenes(text)
    assert len(scenes) == 1
    assert "She is still waiting." in scenes[0]["text"]


def test_prose_that_starts_with_a_section_reference_is_not_a_header():
    text = (
        "--- Page 1 ---\n"
        "1.1 The Call\n"
        "Before the PCs retrieve the fragment, proceed to section\n"
        "3.13 below.\n"
        "3.13 The Chronophage's Hunger\n"
        "The vortex does not close.\n"
    )
    assert [h["title"] for h in detect_headers(text)] == [
        "The Call",
        "The Chronophage's Hunger",
    ]


def test_long_line_beginning_with_a_decimal_is_not_a_header():
    text = (
        "--- Page 1 ---\n"
        "1.1 The Call\n"
        "2.5 miles of road wind north past the ruined mill and on toward the hills\n"
    )
    assert [h["key"] for h in detect_headers(text)] == ["1.1"]


def test_text_with_no_headers_is_all_front_matter():
    front, scenes = slice_scenes("--- Page 1 ---\nJust a cover page.\n")
    assert scenes == []
    assert "Just a cover page." in front


def test_slice_pdf_writes_spine_and_one_file_per_scene(tmp_path, monkeypatch):
    monkeypatch.setattr("lib.adventure_import.PDFExtractor", _stub_extractor(PAGE_TEXT))
    spine = slice_pdf("unused.pdf", tmp_path)

    assert [e["key"] for e in spine] == ["1.1", "1.2", "2.7"]
    assert json.loads((tmp_path / "spine.json").read_text()) == spine
    assert (tmp_path / "scene-front.txt").exists()
    for key in ("1.1", "1.2", "2.7"):
        assert (tmp_path / f"scene-{key}.txt").exists()


# --- page geometry -----------------------------------------------------------
# The column split is measured from the page bbox and from individual text rows.
# These cases are the failure modes that silently produced interleaved slices.


class FakePage:
    """The three members of a pdfplumber page that the row reader touches."""

    def __init__(self, bbox, words):
        self.bbox = bbox
        self._words = words

    def extract_words(self):
        return self._words

    def extract_text(self):
        return '\n'.join(w.get("text", "word") for w in self._words)


class FakePlumber:
    """Stands in for the pdfplumber module: `open(path)` as a context manager."""

    def __init__(self, pages):
        self.pages = pages

    def open(self, path):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _column_aware(page, path):
    path.write_bytes(b"%PDF-1.4")  # extract() stats the file before opening it
    extractor = PDFExtractor()
    extractor.pdfplumber_available = True
    extractor.pdfplumber = FakePlumber([page])
    return extractor.extract(str(path), column_aware=True)


def test_band_bounds_follow_a_shifted_page_origin():
    # A mediabox starting at x=100 puts the page middle at 400, not 300.
    assert band_bounds((0, 600), (0.38, 0.62)) == (228.0, 372.0)
    assert band_bounds((100, 700), (0.38, 0.62)) == (328.0, 472.0)


def test_gutter_found_on_a_page_whose_origin_is_not_zero():
    shifted = [_word(w["x0"] + 100, w["x1"] + 100, w["top"] + 50)
               for w in _two_column_words()]
    lo, hi = band_bounds((100, 700), (0.38, 0.62))
    gutter = gutter_from_rows(text_rows(shifted), lo, hi)
    assert gutter is not None
    assert 390 < gutter < 410, "the shifted gutter, not the unshifted one"


def test_a_wide_heading_cannot_veto_the_column_split():
    # One row crossing the gutter used to make the whole page read as single
    # column, interleaving every slice cut from it.
    words = _two_column_words() + [_word(40, 560, 60)]
    gutter = gutter_from_rows(text_rows(words), 228.0, 372.0)
    assert gutter is not None
    assert 290 < gutter < 310


def test_a_genuinely_full_width_page_has_no_gutter():
    words = [_word(40, 560, 100 + i * 12) for i in range(30)]
    assert gutter_from_rows(text_rows(words), 228.0, 372.0) is None


def test_cross_gutter_rows_are_read_whole_and_in_place():
    words = _two_column_words() + [_word(40, 560, 60, "HEADING")]
    text = page_text_by_rows(FakePage((0, 0, 600, 800), words), 300.0)
    assert text.startswith("HEADING"), "the heading leads, ahead of both columns"
    assert text.count("HEADING") == 1, "and is written exactly once"


def test_rows_group_by_vertical_overlap():
    words = [_word(40, 100, 100), _word(310, 400, 101.5), _word(40, 100, 130)]
    rows = text_rows(words)
    assert len(rows) == 2
    assert len(rows[0][2]) == 2, "a wobbling baseline is still one printed line"


# A chapter divider sets its first letter as a display capital: a taller, deeper
# glyph whose top sits well above the small capitals that finish the word. Their
# tops are far enough apart to look like two rows, and a boundary drawn between
# them cut the heading in half — which is how "Part 1: The Call" reached the
# spine as "Part 1: t", and how the leftovers turned up as debris in both
# columns, since a crop keeps every glyph that merely touches its box.
def _display_capital_heading():
    def cap(x0, x1, text):
        return {"x0": x0, "x1": x1, "top": 57.5, "bottom": 81.5, "text": text}

    def small(x0, x1, text):
        return {"x0": x0, "x1": x1, "top": 62.6, "bottom": 79.4, "text": text}

    return [cap(213.6, 228.0, "P"), small(228.0, 259.6, "art"),
            cap(265.4, 284.1, "1:"), cap(289.0, 304.5, "T"),
            small(304.5, 328.0, "he"), cap(333.7, 350.3, "C"),
            small(350.3, 380.4, "all")]


def test_a_mixed_glyph_heading_is_one_row():
    rows = text_rows(_display_capital_heading())
    assert len(rows) == 1, "display capitals and small capitals share the line"
    assert row_text(rows[0][2]) == "Part 1: The Call"


def test_a_mixed_glyph_heading_is_emitted_once_and_whole():
    words = _display_capital_heading() + _two_column_words()
    text = page_text_by_rows(FakePage((0, 0, 600, 800), words), 297.0)
    assert text.count("Part 1: The Call") == 1
    for debris in ("P art", "art he", "P 1:", "1: T he", "C all"):
        assert debris not in text, f"heading fragment {debris!r} leaked"


def test_a_body_line_is_not_swallowed_by_the_capital_above_it():
    # "Creatures:" starts 0.1pt below the capital's bottom edge. Grouping on
    # bare overlap would fold it into the heading.
    words = _display_capital_heading() + [_word(312.0, 355.9, 81.4, "Creatures:")]
    rows = text_rows(words)
    assert len(rows) == 2
    assert row_text(rows[1][2]) == "Creatures:"


def test_drop_cap_debris_is_not_a_chapter_heading():
    # PDFs render decorative capitals as stray characters: "Part 1: t".
    text = "--- Page 1 ---\nPart 1: t\nThe PCs should be level 5.\n"
    assert detect_headers(text) == []


def test_a_dense_dungeon_key_page_is_not_discarded_as_a_listing():
    # Twelve short rooms on one page: real scenes, not a contents listing.
    rooms = "".join(
        f"2.{i} Room {i}\nLocation: level one.\nA door stands ajar here.\n"
        f"There is rubble on the floor.\n"
        for i in range(1, 13)
    )
    page = f"--- Page 12 ---\n{rooms}"
    assert not is_listing_page(page.splitlines())
    assert len(detect_headers(page)) == 12


def test_a_skipped_listing_page_is_announced(capsys):
    detect_headers(OVERVIEW_TEXT)
    warning = capsys.readouterr().err
    assert "reads as a listing" in warning
    assert "1.1" in warning and "1.3" in warning


def test_an_overhanging_capital_emits_every_row_exactly_once():
    # A capital deep enough to reach past the rows beside it used to make the
    # bands overlap, and an overlapping band repeats the rows it touches.
    text = page_text_by_rows(_overhanging_capital_page(), 300.0)
    for once in ("PART", "left", "right", "THREE", "body0", "body19"):
        assert text.count(once) == 1, f"{once!r} was written more than once"


def _overhanging_capital_page():
    """A page whose display capital hangs past the rows beside it."""
    tall = _word(40, 560, 100, "PART")
    tall["bottom"] = 300
    words = [tall, _word(40, 290, 112, "left"), _word(310, 560, 112, "right"),
             _word(40, 560, 130, "THREE")]
    words += [_word(40, 290, 150 + i * 12, f"body{i}") for i in range(20)]
    return FakePage((0, 0, 600, 800), words)


def test_an_overhanging_capital_does_not_cost_the_page_or_its_marker(tmp_path):
    # Bands taken from neighbours alone gave (206, 126) here — inverted, so the
    # crop raised, the per-page handler swallowed it, and the page vanished from
    # the text. Later scenes then cite page numbers that are off by one.
    text = _column_aware(_overhanging_capital_page(), tmp_path / "book.pdf")
    assert "--- Page 1 ---" in text, "the page marker must survive"
    assert "PART" in text and "body19" in text, "no text may be lost"


def test_a_short_three_scene_page_survives_the_listing_check():
    # Three keys, one line of description each: a real page of short scenes,
    # not a listing. The earlier line-count rule deleted this outright.
    page = (
        "--- Page 9 ---\n"
        "2.1 Grimhammer Forge\nThe smith is at his anvil.\n"
        "2.2 Eldoria Emporium\nShelves of oddments line the walls.\n"
        "2.3 Guard Station\nTwo veterans share a pot of tea.\n"
    )
    assert not is_listing_page(page.splitlines())
    assert [h["key"] for h in detect_headers(page)] == ["2.1", "2.2", "2.3"]


def test_a_drop_cap_does_not_rake_the_page_into_one_row():
    # A capital three body lines deep overlaps every one of them completely.
    # Comparing each word against the row's accumulated extent pulled all three
    # lines — from both columns — into a single row, and reading that row left
    # to right interleaved the columns word by word.
    cap = {"x0": 40, "x1": 70, "top": 100, "bottom": 134, "text": "D"}
    words = [cap]
    for i, (left, right) in enumerate((("Sheriff", "she"), ("Waveshield", "does"),
                                       ("since", "not"))):
        top = 100 + i * 12
        words.append(_word(72, 290, top, left))
        words.append(_word(310, 560, top, right))

    rows = text_rows(words)
    assert len(rows) == 3, "one row per printed line, not one row for the page"
    assert row_text(rows[0][2]) == "D Sheriff she"
    text = page_text_by_rows(FakePage((0, 0, 600, 800), words), 300.0)
    assert "Sheriff\nWaveshield\nsince" in text, "the left column must stay whole"


def test_a_page_that_cannot_be_read_in_columns_keeps_its_marker(tmp_path):
    class Exploding(FakePage):
        def extract_words(self):
            raise RuntimeError("no word boxes on this page")

        def extract_text(self):
            return "plain text of the page"

    text = _column_aware(Exploding((0, 0, 600, 800), []), tmp_path / "book.pdf")
    assert "--- Page 1 ---" in text
    assert "plain text of the page" in text


def test_the_gutter_band_is_measured_from_the_text_not_the_paper():
    # A print-ready page whose mediabox carries 300pt of bleed: its middle is
    # nowhere near the printed middle, so a band taken from the box misses the
    # gutter entirely and the page reads as one column.
    page = FakePage((0, 0, 900, 800), _two_column_words())
    assert band_bounds((0, 900), (0.38, 0.62)) == (342.0, 558.0), "box band misses it"
    gutter = find_column_gutter(page)
    assert gutter is not None and 290 < gutter < 310


def test_a_page_is_measured_and_read_from_one_pass_of_words(tmp_path):
    calls = []

    class Counting(FakePage):
        def extract_words(self):
            calls.append(1)
            return super().extract_words()

    page = Counting((0, 0, 600, 800), _two_column_words())
    _column_aware(page, tmp_path / "book.pdf")
    assert len(calls) == 1, "detection and reading share one pass over the words"


# --- no glued tokens ---------------------------------------------------------
# Two printed lines welded into one row are re-sorted left to right, and words
# that then overlap used to be joined without a separator — producing tokens
# ("Whisperscity") that appear in no line of the book. Grouping is pairwise now,
# and row_text refuses to glue across an overlap even if grouping goes wrong.


def _seam_joined_tokens(rows, source_text):
    """Tokens the reader may legitimately invent: a word split across a seam.

    A display capital arrives as its own word object touching the letters that
    finish the word, and rejoining those is the point. Nothing else may merge.

    The rule is stated in literals, never by calling the library's own
    predicate — an invariant that borrows the rule it is checking proves
    nothing, and would wave through whatever that rule was loosened to allow.
    Two boxes may merge here only if they truly touch (a hair of float noise
    aside, never a real overlap) AND the join is corroborated: either the merged
    string is printed on the page as the extractor's own reader sees it, or the
    run opens with a lone glyph, which is what a display capital looks like
    before its word is closed up. It has to be a glyph rather than a capital:
    the sample book sets its fourth divider as a decorative lowercase "e", and
    pdfplumber's own reader drops all four of those capitals from the page text
    ("art aCk in ldoria"), so neither corroboration alone covers the case.
    """
    allowed = set()
    for _, _, words in rows:
        run = []
        for i, word in enumerate(words):
            touching = run and -0.01 <= word['x0'] - words[i - 1]['x1'] <= 0.5
            run = run + [word] if touching else [word]
            for start in range(len(run) - 1):
                merged = ''.join(w['text'] for w in run[start:])
                lead = run[start]['text']
                if merged in source_text or (len(lead) == 1 and lead.isalpha()):
                    allowed.update(re.findall(r'[A-Za-z]+', merged))
    return allowed


def assert_no_glued_tokens(page):
    """Every alphabetic token read off `page` must come from the page."""
    rows = text_rows(page.extract_words())
    out = page_text_by_rows(page, find_column_gutter(page, rows), rows)
    source_text = page.extract_text() or ''
    allowed = set(re.findall(r'[A-Za-z]+', source_text))
    allowed |= _seam_joined_tokens(rows, source_text)
    invented = sorted(t for t in set(re.findall(r'[A-Za-z]+', out)) if t not in allowed)
    assert invented == [], f"tokens in no printed line: {invented[:5]}"


def test_no_glued_tokens_on_a_staggered_two_column_page():
    # The synthetic twin of page 8: a right-column heading that starts partway
    # down the line beside it, between two left-column lines.
    words = []
    for i in range(14):
        top = 300 + i * 12
        words.append(_word(36, 207, top, f"left{i}"))
        words.append(_word(310, 500, top, f"right{i}"))
    words.append({"x0": 397, "x1": 464, "top": 310.8, "bottom": 322.8,
                  "text": "EldoriaDocks"})
    assert_no_glued_tokens(FakePage((0, 0, 600, 800), words))


@pytest.mark.skipif(not TEST_PDF.exists(), reason="the sample module is not present")
def test_no_glued_tokens_on_any_page_of_the_sample_module():
    import pdfplumber

    with pdfplumber.open(TEST_PDF) as pdf:
        for page in pdf.pages:
            if page.extract_words():
                assert_no_glued_tokens(page)


def test_rows_are_pairwise_never_chained():
    # Page 8: the heading overlaps the line above it by 0.73 and the line below
    # it by 0.78, but those two lines do not overlap each other at all. Judging
    # each word against only the previous arrival chained all three into one row.
    left_above = {"x0": 36, "x1": 207, "top": 308.4, "bottom": 317.4, "text": "above"}
    heading = {"x0": 397, "x1": 464, "top": 310.8, "bottom": 322.8, "text": "Eldoria"}
    left_below = {"x0": 46, "x1": 124, "top": 319.2, "bottom": 328.2, "text": "below"}

    rows = text_rows([left_above, heading, left_below])
    assert len(rows) == 3, "three printed lines, three rows"
    for _, _, words in rows:
        assert len(words) == 1


def test_a_drop_cap_that_sorts_after_the_first_body_line():
    # The capital's top is a point BELOW the line it opens, so it is placed
    # after that line rather than anchoring the row.
    cap = {"x0": 40, "x1": 70, "top": 101, "bottom": 135, "text": "D"}
    words = []
    for i, (left, right) in enumerate((("Sheriff", "she"), ("Waveshield", "does"),
                                       ("since", "not"))):
        top = 100 + i * 12
        words.append(_word(72, 290, top, left))
        words.append(_word(310, 560, top, right))
    words.append(cap)

    rows = text_rows(words)
    assert row_text(rows[0][2]) == "D Sheriff she"
    assert [row_text(r[2]) for r in rows[1:]] == ["Waveshield does", "since not"]


def test_row_text_separates_words_that_overlap():
    # Defence in depth: even a row grouped wrongly must not invent a token.
    out_of_order = [_word(310, 400, 100, "city"), _word(36, 330, 100, "theWhispers")]
    assert row_text(out_of_order) == "theWhispers city"


def test_row_text_still_closes_a_display_capital_seam():
    seam = [{"x0": 213.6, "x1": 228.0, "top": 57.5, "bottom": 81.5, "text": "P"},
            {"x0": 228.0, "x1": 259.6, "top": 62.6, "bottom": 79.4, "text": "art"}]
    assert row_text(seam) == "Part"


def test_a_tall_word_sorting_last_on_its_line_does_not_chain():
    # The other sort order: a bold stat-block name or display glyph whose box is
    # taller than the line and whose x0 puts it last. It overlaps the line below
    # by more than half that line's height, and chaining welded the two.
    words = [_word(36, 120, 100, "L1a"), _word(130, 200, 100, "L1b"),
             {"x0": 210, "x1": 280, "top": 100, "bottom": 130, "text": "TALL"},
             _word(36, 120, 112, "L2a"), _word(130, 200, 112, "L2b")]
    words += [_word(310, 400, 100, "R1"), _word(310, 400, 112, "R2")]

    assert [row_text(r[2]) for r in text_rows(words)] == [
        "L1a L1b TALL R1",
        "L2a L2b R2",
    ]


def test_a_seam_is_where_two_boxes_touch_at_any_type_size():
    # Measured off the sample book. A seam is the extractor splitting one word
    # at a change of font, so the halves touch: all 18 in that book measure
    # 0.000-0.001pt. Word spacing does NOT scale with type there — 18pt display
    # sets its spaces at 1.45pt while 9pt body sets them from 1.30pt — so a
    # height-scaled threshold runs backwards and welds real words.
    seam = [{"x0": 213.6, "x1": 228.0, "top": 57.5, "bottom": 81.5, "text": "P"},
            {"x0": 228.0, "x1": 259.6, "top": 62.6, "bottom": 79.4, "text": "art"}]
    assert row_text(seam) == "Part"

    body = [_word(45.0, 60.7, 100, "Helping"), _word(62.005, 90, 100, "the")]
    assert row_text(body) == "Helping the", "1.30pt at 9pt type is a space"

    display = [{"x0": 100, "x1": 140, "top": 50, "bottom": 68, "text": "Apendix"},
               {"x0": 141.45, "x1": 160, "top": 50, "bottom": 68, "text": "A:"}]
    assert row_text(display) == "Apendix A:", "1.45pt at 18pt type is a space too"


def test_a_degraded_extraction_is_announced_not_shipped_quietly(tmp_path, capsys):
    with mock.patch("lib.adventure_import.PDFExtractor",
                    _stub_extractor(PAGE_TEXT, mode='plain')):
        slice_pdf("unused.pdf", tmp_path)
    assert "could not be read column by column" in capsys.readouterr().err


def test_a_run_that_finds_no_scenes_writes_nothing_at_all(tmp_path):
    (tmp_path / "scene-1.1.txt").write_text("from the real book")
    with mock.patch("lib.adventure_import.PDFExtractor",
                    _stub_extractor("--- Page 1 ---\nNo keys on this page.\n")):
        assert slice_pdf("unused.pdf", tmp_path) == []
    assert (tmp_path / "scene-1.1.txt").read_text() == "from the real book"
    assert not (tmp_path / "spine.json").exists(), "no spine may claim an empty book"
    assert not (tmp_path / "scene-front.txt").exists()


def test_three_scenes_with_two_keys_adjacent_survive():
    # A column reflow can leave one scene's header at the foot of a column and
    # the next one at the head of the following column, with nothing between.
    page = (
        "--- Page 9 ---\n"
        "2.1 Grimhammer Forge\nThe smith is at his anvil.\n"
        "2.2 Eldoria Emporium\n"
        "2.3 Guard Station\nTwo veterans share a pot of tea.\n"
    )
    assert not is_listing_page(page.splitlines())
    assert [h["key"] for h in detect_headers(page)] == ["2.1", "2.2", "2.3"]


def test_a_gap_is_not_manufactured_from_a_handful_of_rows():
    # Four full-width lines with a chance ragged edge near the middle. Trimming
    # even one vote invents a gutter and splits the page mid-sentence.
    words = []
    for i, right_edge in enumerate((560, 300, 560, 560)):
        top = 100 + i * 12
        words.append(_word(40, right_edge, top))
        if right_edge < 560:
            words.append(_word(330, 560, top))
    words += [_word(40, 560, 160 + i * 12) for i in range(6)]
    assert find_column_gutter(FakePage((0, 0, 600, 800), words)) is None


# --- the gutter must be a line no kept row crosses ---------------------------


def _one_overhanging_left_word(rows=21):
    """Two clean columns, plus one left-column word reaching toward the gutter."""
    words = []
    for i in range(rows):
        top = 100 + i * 12
        words.append(_word(40, 290, top, f"L{i}"))
        words.append(_word(310, 560, top, f"R{i}"))
    words[0] = _word(40, 303, 100, "L0")
    return words


def test_a_trimmed_outlier_word_may_not_straddle_the_gutter():
    # The gap is measured with the most intrusive votes discarded, so a single
    # word reaching past the column edge is trimmed away — and the midpoint of
    # what is left lands INSIDE it. The row then reads into both columns, and the
    # left paragraph comes out cut in half around the whole of the right column.
    words = _one_overhanging_left_word()
    gutter = gutter_from_rows(text_rows(words), 237.6, 362.4)
    assert gutter is not None
    for word in words:
        assert not (word['x0'] < gutter < word['x1']), (
            f"{word['text']!r} straddles the gutter at {gutter}")


def test_an_overhanging_word_does_not_interleave_the_columns():
    words = _one_overhanging_left_word()
    page = FakePage((0, 0, 600, 800), words)
    text = page_text_by_rows(page, find_column_gutter(page), text_rows(words))

    left = "\n".join(f"L{i}" for i in range(21))
    right = "\n".join(f"R{i}" for i in range(21))
    assert left in text, "the left column must come out as one unbroken block"
    assert right in text
    assert text.index(left) < text.index(right)


# --- a hairline overlap is not a seam ----------------------------------------


def test_a_hairline_overlap_is_a_space_not_a_seam():
    # pdfplumber hands back boxes that overlap by a fraction of a point on
    # italic and tightly kerned type. Reading that as "touching" welds two real
    # words into one that appears in no printed line.
    overlapping = [_word(45.0, 70.0, 100, "melee"), _word(69.7, 100.0, 100, "combat")]
    assert row_text(overlapping) == "melee combat"
    assert not words_are_glued(*overlapping)


def test_a_seam_that_measures_zero_still_closes():
    # The four chapter dividers in the sample book measure -0.001 to 0.000pt
    # across the seam, which is float noise in the layout, not two words.
    seam = [{"x0": 213.6, "x1": 228.0, "top": 57.5, "bottom": 81.5, "text": "P"},
            {"x0": 227.999, "x1": 259.6, "top": 62.6, "bottom": 79.4, "text": "art"}]
    assert row_text(seam) == "Part"


# --- a book read page by page in plain mode is not a column read -------------


class ExplodingPage(FakePage):
    def extract_words(self):
        raise RuntimeError("no word boxes on this page")

    def extract_text(self):
        return "plain text of the page"


def _plumber_extractor(pages):
    """A real PDFExtractor reading a fake book — factory, as slice_pdf expects."""
    def build():
        extractor = PDFExtractor()
        extractor.pdfplumber_available = True
        extractor.pdfplumber = FakePlumber(pages)
        return extractor
    return build


def test_a_book_where_every_page_fell_back_reports_a_plain_read(tmp_path, capsys):
    pdf = tmp_path / "book.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    pages = [ExplodingPage((0, 0, 600, 800), []) for _ in range(2)]

    extractor = _plumber_extractor(pages)()
    extractor.extract(str(pdf), column_aware=True)
    assert extractor.last_mode == 'plain', "no page was read in columns"

    with mock.patch("lib.adventure_import.PDFExtractor", _plumber_extractor(pages)):
        slice_pdf(str(pdf), tmp_path / "out")
    assert "could not be read column by column" in capsys.readouterr().err


def test_one_bad_page_in_a_book_is_not_a_degraded_read(tmp_path):
    pdf = tmp_path / "book.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    pages = [FakePage((0, 0, 600, 800), _two_column_words())] * 3
    pages.append(ExplodingPage((0, 0, 600, 800), []))

    extractor = _plumber_extractor(pages)()
    extractor.extract(str(pdf), column_aware=True)
    assert extractor.last_mode == 'columns'


# --- a sparse page is not judged by a share of a handful of rows -------------


def test_a_sparse_page_of_captions_still_finds_its_columns():
    # An art page: two full-width lines (a title and a footer) over four rows of
    # two-column text. Two rows out of six is past the spanning share, and the
    # share of six rows is not evidence of anything — the page has columns.
    words = [_word(40, 560, 60, "TITLE"), _word(40, 560, 760, "FOOTER")]
    for i in range(4):
        top = 300 + i * 12
        for j in range(6):
            words.append(_word(40 + j * 40, 75 + j * 40, top, f"l{i}{j}"))
            words.append(_word(310 + j * 40, 345 + j * 40, top, f"r{i}{j}"))

    rows = text_rows(words)
    assert len(rows) == 6
    gutter = gutter_from_rows(rows, 237.6, 362.4)
    assert gutter is not None and 290 < gutter < 310


def test_a_full_width_page_with_room_to_judge_is_still_vetoed():
    # The floor must not disarm the veto on a page big enough to measure: thirty
    # full-width lines are a single column, whatever gap the ragged right edge
    # happens to leave.
    words = [_word(40, 560, 100 + i * 12) for i in range(30)]
    assert gutter_from_rows(text_rows(words), 228.0, 372.0) is None


# --- a slice may not end on the next page's marker ---------------------------


def test_a_trailing_page_marker_is_dropped_from_the_slice_text():
    text = (
        "--- Page 1 ---\n"
        "Introduction\n"
        "--- Page 2 ---\n"
        "1.1 The Call\n"
        "The sheriff is waiting.\n"
        "--- Page 3 ---\n"
        "1.2 The Meeting\n"
        "A jellyfish speaks.\n"
    )
    front, scenes = slice_scenes(text)
    by_key = {s["key"]: s for s in scenes}
    assert not front.endswith("--- Page 2 ---"), "page 2 belongs to 1.1"
    assert front.endswith("Introduction")
    assert by_key["1.1"]["text"].endswith("The sheriff is waiting.")
    assert "--- Page 3 ---" not in by_key["1.1"]["text"]
    assert by_key["1.1"]["pages"] == [2]


# --- a dropped header candidate is said out loud -----------------------------


def test_a_dropped_header_candidate_is_announced(capsys):
    text = (
        "--- Page 1 ---\n"
        "1.1 The Call\n"
        "Before the PCs retrieve the fragment, proceed to section\n"
        "3.13 below.\n"
        "2.5 miles of road wind north past the ruined mill and on toward the hills\n"
    )
    assert [h["key"] for h in detect_headers(text)] == ["1.1"]
    note = capsys.readouterr().err
    assert "'3.13'" in note and "sentence punctuation" in note
    assert "'2.5'" in note and "over 10 words" in note


def test_a_dropped_candidate_is_announced_once_however_often_it_repeats(capsys):
    line = "3.13 below.\n"
    text = "--- Page 1 ---\n1.1 The Call\n" + line + "--- Page 2 ---\n" + line
    detect_headers(text)
    assert capsys.readouterr().err.count("not treating '3.13'") == 1


# --- the live book -----------------------------------------------------------


@pytest.mark.skipif(not TEST_PDF.exists(), reason="the sample module is not present")
def test_the_glued_token_check_bites_when_the_seam_is_widened(monkeypatch):
    # Proof that the invariant above is load-bearing and not self-satisfying: a
    # seam wide enough to weld real words must make the live page check FAIL.
    import pdfplumber

    monkeypatch.setattr("lib.content_extractor.SEAM_MAX", 5.0)
    with pdfplumber.open(TEST_PDF) as pdf:
        for page in pdf.pages:
            if not page.extract_words():
                continue
            try:
                assert_no_glued_tokens(page)
            except AssertionError:
                return
    pytest.fail("a 5pt seam welded no words: the check cannot be failing honestly")


@pytest.mark.skipif(not TEST_PDF.exists(), reason="the sample module is not present")
def test_the_sparse_caption_page_is_not_vetoed_by_its_spanning_share():
    # Page 49 of the sample book: seven rows, most of them full-width. It is the
    # page the row-count floor exists for. (The page still reads whole for
    # another reason — only two of its 49 words sit left of any gutter, so the
    # near-empty-column guard holds — but the share of seven rows no longer
    # decides it.)
    import pdfplumber
    from lib import content_extractor as ce

    with pdfplumber.open(TEST_PDF) as pdf:
        rows = ce.text_rows(pdf.pages[48].extract_words())
    assert len(rows) == 7
    crossings = sum(1 for _, _, ws in rows
                    if any(w['x0'] < 320.6 < w['x1'] for w in ws))
    assert len(rows) < ce.MIN_ROWS_TO_VETO or crossings <= ce.MAX_SPANNING_ROWS * len(rows)


@pytest.mark.skipif(not TEST_PDF.exists(), reason="the sample module is not present")
def test_the_sample_book_reads_in_columns_end_to_end(capsys):
    extractor = PDFExtractor()
    extractor.extract(str(TEST_PDF), column_aware=True)
    assert extractor.last_mode == 'columns', "no page may fall back on this book"
