---
slug: extractor-ordering-hardening
title: Fix retracted-review findings — gutter crossing guarantee, overlap glue, degraded-mode flag
category: bug
kind: afk
priority: p1
lane: agent
parentPrd: import-module
blockedBy: []
claimedBy: ss-imod01
claimedAt: 2026-08-19T19:06:00Z
changedFiles: [lib/content_extractor.py, lib/adventure_import.py, tests/test_adventure_import.py]
resolution: gutter clamp guarantee + signed seam + degraded-mode flag + slice-text marker trim + announced header drops + non-circular invariant test
reviewRounds: 1
implementer: null
createdAt: 2026-08-19T19:05:00Z
updatedAt: 2026-08-19T20:10:00Z
---

## Parent

/import-module (prds/import-module.md). Follow-up to module-text-spine: review4 retracted its perfect verdict post-commit (917b292) with reproduced findings.

## Category

bug

## What to fix

Blocking (reproduced by the reviewer):
1. `find_column_gutter` returns `split=(start+end)/2` from the TRIMMED gap; a trimmed-away outlier word can straddle split, making `_row_runs` read that row across both columns and split the left column's paragraph with the entire right column. Fix: return a gutter no kept row crosses (`probe`, or clamp split into the untrimmed [max left edge, min right edge]).
2. `words_are_glued` uses `abs(gap) <= SEAM_MAX`, so a sub-0.5pt OVERLAP (italic/kerned boxes) glues words ("meleecombat"). Fix: `0 <= gap <= SEAM_MAX` (negative beyond FP noise is never a seam).

Non-blocking but included:
3. `last_mode` stays 'columns' when every page fell back to plain extract_text — slice_pdf's degraded warning never fires. Set 'plain' when all (or a majority of) pages fell back; test asserts the warning.
4. `MAX_SPANNING_ROWS` bare ratio with no row-count floor: sample-book page 49 (7 rows) welds the two column captions ("Clockwork Guardian Thanatos' Avatar"). Add a floor.
5. `_drop_trailing_marker` applied to `pages` but not `text` — slices end with the next scene's page marker.
6. `_match_header` drops >10-word titles and trailing-punctuation titles silently — announce on stderr like the listing-page skip.
7. Test debt: `assert_no_glued_tokens` allow-list must not call `words_are_glued` (currently circular — mutating the seam constant to 5.0 must fail the live test); remove the subsumed duplicate no-scenes test; make TEST_PDF path overridable via env var so the live test isn't machine-bound.

## Acceptance criteria

- [x] Reviewer's gutter repro (21 rows, left col 40-290, right col 310-560, one left word x1=303): L0..L20 emit as one unbroken block then R0..R20; no row mixes columns.
- [x] Two 10pt words overlapping 0.3pt render "melee combat", never "meleecombat"; touching (-0.0) display capitals still join to "Part".
- [x] All pages falling back to plain extraction → last_mode 'plain' and slice_pdf's degraded warning fires (tested).
- [x] Sample-book page 49 no longer welds the two column captions (skipif-guarded live test or synthetic twin).
- [x] Slice text never ends with the next scene's page marker.
- [x] A dropped over-long/punctuated header is announced on stderr.
- [x] Glued-token invariant is non-circular: patching the seam constant to 5.0 makes the (env-overridable) live test fail; duplicate test removed.
- [x] Whole-book invariants and live spine (43 entries, part-1..4, 1.4/2.7) unchanged; full suite no new failures; collect-only exit 0.

## Out of scope

lib/adventure.py, the /import-module command files (in flight), dnd-api, RAG.

## Verification

Lane: agent

## Blocked by

None. (Files disjoint from in-flight import-module-command.)

---

## QA Reports

### 2026-08-19T20:25:00Z — pass [review-extractor-hardening]
reviewed: perfect. Clamp correctness proven by construction; page-42 heading split accepted (only changed page book-wide, no loss/glue, no alternative preserves both properties); page-49 non-repro confirmed by measurement (MIN_COLUMN_SHARE, correct single-column). Notes for later: tautological sparse-caption test (documents, not tests); lone-glyph allow-list escape is broad but test-only.

### 2026-08-19T20:10:00Z — verified [ss-imod01]
61/61 tests; collect-only exit 0; full suite only the pre-existing sibling-leak failure. Gutter clamped into untrimmed clearing (repro fixed; documented cost: page-42 appendix heading splits — inherent to the correct fix, non-spine, 1 char diff book-wide). Signed seam with -0.01 epsilon (0.3pt overlap unglued, dividers still join; byte-identical on sample). last_mode 'plain' at ≥half fallback pages + warning. Trailing marker trimmed from slice TEXT. Header drops announced deduped (one line on the real book, a correct rejection). Non-circular glued-token check (lone-GLYPH amendment — the "e"/"ldoria" divider; bites under SEAM_MAX=5.0, tested). Duplicate test removed; GM_TEST_MODULE_PDF env override.
Finding-4 non-repro: page 49 is decided by MIN_COLUMN_SHARE (2/49 words left of any split — genuinely one column beside art), NOT the spanning veto; caption weld is correct behavior. Row-count floor (MIN_ROWS_TO_VETO=8) added anyway; no-op on this book, fixes the sparse-caption class.
Whole-book invariants: all zeros; spine byte-identical (43 entries).

## History

- 2026-08-19T20:25:00Z  review perfect → done, committed  [ss-imod01]

- 2026-08-19T19:05:00Z  created → ready (from review4 retraction)  [ss-imod01]
