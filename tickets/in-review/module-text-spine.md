---
slug: module-text-spine
title: Column-aware PDF→text + deterministic spine slicing
category: enhancement
kind: afk
priority: p1
lane: agent
parentPrd: import-module
blockedBy: []
claimedBy: null
claimedAt: null
changedFiles: []
resolution: null
reviewRounds: null
implementer: null
createdAt: 2026-08-19T18:05:00Z
updatedAt: 2026-08-19T18:05:00Z
---

## Parent

/import-module — structured adventure-module import (prds/import-module.md)

## Category

enhancement

## What to build

Two pieces, one CLI:

1. **Two-column PDF extraction.** Extend `lib/content_extractor.py` with a
   column-aware mode: for each page, decide whether it is two-column (e.g.
   text-word x-position clustering or a simple midline whitespace heuristic);
   if so, crop into left/right halves via pdfplumber and extract each half in
   order; otherwise extract the full page. Emit `--- page N ---` markers.
   Existing single-column behavior for other callers is unchanged.
2. **Deterministic spine slicing.** New `lib/adventure_import.py` with a CLI:
   `uv run python lib/adventure_import.py slice <pdf> --out <workdir>`. It
   extracts the text (mode above), regex-detects keyed scene headers
   (`^\d+\.\d+\s+Title` plus chapter-level headings), and writes to the
   workdir: `spine.json` (ordered `[{key, title, pages}]`) and one
   `scene-<key>.txt` slice per scene (header through the next header). Front
   matter before the first key goes to `scene-front.txt`. No LLM calls.

## Acceptance criteria

- [ ] On a known two-column page of `/Users/seanstobo/Downloads/at-05-the-whispering-wood.pdf` (e.g. page 6), extracted text does not interleave columns: sentences from the left column are contiguous, and the read-aloud paragraph reads unbroken.
- [ ] `slice` on the Whispering Wood PDF finds the keyed scenes (at minimum `1.4` and `2.7`, which are known to exist) in document order and writes `spine.json` + one slice file per scene, each slice retaining page markers.
- [ ] Pages with no text (cover art) do not crash extraction.
- [ ] A `tests/test_adventure_import.py` covers header-regex detection on synthetic text (ordering, front-matter handling) and runs without the PDF present.
- [ ] Existing callers of `content_extractor` are unaffected (default mode unchanged; existing tests still pass).

## Out of scope

Any LLM conversion of the slices, adventure.json, or campaign integration. Any change to the RAG/embedding pipeline or `/import`.

## Verification

Lane: agent

## Blocked by

None.

---

## QA Reports

## History

- 2026-08-19T18:05:00Z  created → ready  [ship-it]
