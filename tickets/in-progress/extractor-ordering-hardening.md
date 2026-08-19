---
slug: extractor-ordering-hardening
title: Fix retracted-review findings — gutter crossing guarantee, overlap glue, degraded-mode flag
category: bug
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
createdAt: 2026-08-19T19:05:00Z
updatedAt: 2026-08-19T19:05:00Z
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

- [ ] Reviewer's gutter repro (21 rows, left col 40-290, right col 310-560, one left word x1=303): L0..L20 emit as one unbroken block then R0..R20; no row mixes columns.
- [ ] Two 10pt words overlapping 0.3pt render "melee combat", never "meleecombat"; touching (-0.0) display capitals still join to "Part".
- [ ] All pages falling back to plain extraction → last_mode 'plain' and slice_pdf's degraded warning fires (tested).
- [ ] Sample-book page 49 no longer welds the two column captions (skipif-guarded live test or synthetic twin).
- [ ] Slice text never ends with the next scene's page marker.
- [ ] A dropped over-long/punctuated header is announced on stderr.
- [ ] Glued-token invariant is non-circular: patching the seam constant to 5.0 makes the (env-overridable) live test fail; duplicate test removed.
- [ ] Whole-book invariants and live spine (43 entries, part-1..4, 1.4/2.7) unchanged; full suite no new failures; collect-only exit 0.

## Out of scope

lib/adventure.py, the /import-module command files (in flight), dnd-api, RAG.

## Verification

Lane: agent

## Blocked by

None. (Files disjoint from in-flight import-module-command.)

---

## QA Reports

## History

- 2026-08-19T19:05:00Z  created → ready (from review4 retraction)  [ss-imod01]
