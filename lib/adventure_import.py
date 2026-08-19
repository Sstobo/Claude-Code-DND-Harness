#!/usr/bin/env python3
"""Slice an adventure module PDF into its keyed scenes — deterministically.

An adventure module is already cut into scenes by its author: keyed headers like
`1.4 Passage to Eldoria` mark where one encounter ends and the next begins. This
module reads the PDF column-aware (so the two columns of a page are not shuffled
together), finds those headers by regex, and writes one text slice per scene
plus a `spine.json` listing them in document order.

No LLM runs here. The slices are the raw material a later pass converts; this
step must be reproducible, so every decision is a regex or a coordinate.

    uv run python lib/adventure_import.py slice <pdf> --out <workdir>
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.content_extractor import PDFExtractor

# `2.7 Misfit Menagerie of Greenkey Street` — a section number then a title.
KEYED_HEADER = re.compile(r'^(\d{1,2}\.\d{1,2})\s+([^\W\d_"“\'][^\n]*)$')
# `Part 3: The Woodland`, `Chapter 2 - ...`
CHAPTER_HEADER = re.compile(
    r'^((?:Part|Chapter|Act)\s+\d{1,2})\s*[:.–—-]\s*(\S[^\n]*)$', re.I
)
PAGE_MARKER = re.compile(r'^---\s*Page\s+(\d+)\s*---\s*$', re.I)
# Dotted leaders are the signature of a contents listing, not a heading.
DOT_LEADER = re.compile(r'\.{4,}')

MIN_TITLE_CHARS = 3
MAX_TITLE_WORDS = 10
CONTENTS_LEADER_RATIO = 0.25
# A page carrying at least this many keys, most of them with no text of their
# own, is a listing rather than the scenes themselves. The bar is high because
# discarding a page deletes real scenes: after a column reflow a page of three
# short scenes can leave two keys adjacent, and a contents page that small is
# caught by its dotted leaders anyway.
MIN_LISTING_KEYS = 5


def _page_spans(lines):
    """Yield (page_number, start_index, end_index) for each `--- Page N ---` block.

    Text before the first marker (there normally is none) is reported as page 0.
    """
    page, start = 0, 0
    for i, line in enumerate(lines):
        m = PAGE_MARKER.match(line)
        if not m:
            continue
        if i > start:
            yield page, start, i
        page, start = int(m.group(1)), i
    if start < len(lines):
        yield page, start, len(lines)


def is_listing_page(lines) -> bool:
    """True if a page lists scene keys instead of playing them out.

    Two kinds exist. A table of contents shows dotted leaders. An overview page
    or flowchart has none — it is just key after key with a line of gloss
    between them. Both must be skipped, because a key recorded from a listing
    would claim the scene and leave the real one, further into the book,
    discarded as a duplicate.
    """
    body = [ln for ln in lines if ln.strip() and not PAGE_MARKER.match(ln)]
    if not body:
        return False

    leaders = sum(1 for ln in body if DOT_LEADER.search(ln))
    if leaders >= CONTENTS_LEADER_RATIO * len(body):
        return True

    # Discarding a page deletes real scenes, so the listing pattern has to
    # dominate it: most of the keys carrying NO text of their own. A dense
    # dungeon key — a dozen rooms, or three, each with a line of description —
    # keeps its scenes. Every skip is announced so a bad call stays visible.
    at = [i for i, ln in enumerate(body) if _match_header(ln)]
    if len(at) < MIN_LISTING_KEYS:
        return False
    bare = sum(1 for i, start in enumerate(at)
               if (at[i + 1] if i + 1 < len(at) else len(body)) - start == 1)
    return bare > len(at) / 2


def _match_header(line: str):
    """Return (key, title) if the line is a scene or chapter header, else None."""
    if DOT_LEADER.search(line):
        return None
    m = KEYED_HEADER.match(line.strip())
    if m:
        key, title = m.group(1), m.group(2).strip()
    else:
        m = CHAPTER_HEADER.match(line.strip())
        if not m:
            return None
        key = re.sub(r'\s+', '-', m.group(1).lower())
        title = m.group(2).strip()
    # A heading is not a sentence. Body text that happens to start a line with a
    # cross-reference ("proceed to section\n3.13 below.") is prose, not a header.
    # A one-letter title is extraction debris, not a heading: decorative drop
    # caps come out of a PDF as scattered single characters.
    if len(title) < MIN_TITLE_CHARS or len(title.split()) > MAX_TITLE_WORDS:
        return None
    if title.endswith(('.', ',')):
        return None
    return key, title


def detect_headers(text: str):
    """Find every scene header in extracted text, in document order.

    Returns a list of `{key, title, line, page}`. A key that has already been
    seen is skipped: repeated keys are running headers reprinted at a page
    break, and honouring them would cut a scene in half.
    """
    lines = text.splitlines()
    headers, seen = [], set()
    for page, start, end in _page_spans(lines):
        page_lines = lines[start:end]
        if is_listing_page(page_lines):
            skipped = [hit[0] for hit in map(_match_header, page_lines) if hit]
            if skipped:
                print(f"Note: page {page} reads as a listing, not scenes — "
                      f"skipping {', '.join(skipped)}", file=sys.stderr)
            continue
        for offset, line in enumerate(page_lines):
            hit = _match_header(line)
            if not hit or hit[0] in seen:
                continue
            seen.add(hit[0])
            headers.append({
                "key": hit[0],
                "title": hit[1],
                "line": start + offset,
                "page": page,
            })
    return headers


def _drop_trailing_marker(body):
    """The slice minus any page marker left dangling at its end."""
    cut = len(body)
    while cut and (not body[cut - 1].strip() or PAGE_MARKER.match(body[cut - 1])):
        cut -= 1
    return body[:cut]


def slice_scenes(text: str):
    """Cut extracted text into (front_matter, scenes).

    Each scene is `{key, title, pages, text}` running from its header line to
    the line before the next header. Page markers stay inside the slice so a
    scene can cite the page it came from, and `pages` lists every page it spans.
    """
    lines = text.splitlines()
    headers = detect_headers(text)

    front_end = headers[0]["line"] if headers else len(lines)
    front = '\n'.join(lines[:front_end]).strip()

    scenes = []
    for i, header in enumerate(headers):
        end = headers[i + 1]["line"] if i + 1 < len(headers) else len(lines)
        body = lines[header["line"]:end]
        pages = [header["page"]] if header["page"] is not None else []
        # A scene that runs to a page break ends with the next page's marker and
        # no text under it. That page belongs to the following scene.
        for line in _drop_trailing_marker(body):
            m = PAGE_MARKER.match(line)
            if m and int(m.group(1)) not in pages:
                pages.append(int(m.group(1)))
        scenes.append({
            "key": header["key"],
            "title": header["title"],
            "pages": pages,
            "text": '\n'.join(body).strip(),
        })
    return front, scenes


def slice_pdf(pdf_path: str, out_dir: str):
    """Extract, slice, and write `spine.json` + one `scene-<key>.txt` per scene."""
    extractor = PDFExtractor()
    text = extractor.extract(pdf_path, column_aware=True)
    if extractor.last_mode != 'columns':
        print("WARNING: this PDF could not be read column by column. The text is "
              "interleaved and the slices below are unreliable.", file=sys.stderr)
    front, scenes = slice_scenes(text)

    # A pass that finds no scenes writes nothing at all. Writing an empty
    # spine.json next to another book's slices would describe a workdir that
    # does not exist, and clearing the folder on the strength of a failed read
    # would destroy the last good run.
    if not scenes:
        print(f"No keyed scenes found in {pdf_path}; nothing written.", file=sys.stderr)
        return []

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    # Slices this run no longer produces would otherwise linger and be read back
    # as part of this book.
    for stale in out.glob("scene-*.txt"):
        stale.unlink()
    if front:
        (out / "scene-front.txt").write_text(front, encoding='utf-8')
    for scene in scenes:
        (out / f"scene-{scene['key']}.txt").write_text(scene["text"], encoding='utf-8')

    spine = [{k: s[k] for k in ("key", "title", "pages")} for s in scenes]
    (out / "spine.json").write_text(json.dumps(spine, indent=2), encoding='utf-8')
    return spine


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Slice an adventure PDF into keyed scenes")
    sub = parser.add_subparsers(dest="command", required=True)
    slicer = sub.add_parser("slice", help="extract a PDF and cut it into scene slices")
    slicer.add_argument("pdf")
    slicer.add_argument("--out", required=True, help="workdir for spine.json and slices")
    args = parser.parse_args()

    spine = slice_pdf(args.pdf, args.out)
    print(f"{len(spine)} scenes -> {args.out}")
    for entry in spine:
        pages = ', '.join(str(p) for p in entry["pages"])
        print(f"  {entry['key']}  {entry['title']}  (p. {pages})")


if __name__ == "__main__":
    main()
