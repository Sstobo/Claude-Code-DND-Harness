---
slug: extractor-notes-p2
title: Extractor follow-ups — degraded-ratio art pages; spanning-row split exclusion idea
category: enhancement
kind: afk
priority: p2
lane: agent
parentPrd: import-module
blockedBy: []
claimedBy: null
claimedAt: null
changedFiles: []
resolution: null
reviewRounds: null
implementer: null
createdAt: 2026-08-19T20:40:00Z
updatedAt: 2026-08-19T20:40:00Z
---

## Parent

/import-module. Cross-team sweep findings on committed a3f7fe6, post-adjudication.

## Category

enhancement

## What to build

1. (real, small) The degraded-read ratio counts pages that produced no words
   (cover/art pages) in its denominator, so a mostly-art module with 100%
   fallback on its text pages never trips the warning. Count only pages that
   yielded text.
2. (investigate) Page-42 heading split ("Apendix A: Magic" / "Item
   Availability") was adjudicated accepted — every split in the sub-2pt
   clearing cuts it, and the probe alternative is identical. The sweep suggests
   excluding candidate splits that fall inside the horizontal extent of a
   gutter-spanning row; assess whether that can work without vetoing every
   split (a spanning heading covers the whole line) or reintroducing the
   21-row interleave repro. Adopt only with both repros protected by tests.
3. (test debt, from review notes) The sparse-caption veto test is tautological;
   the lone-glyph allow-list escape in the invariant helper is broad.

## Acceptance criteria

- [ ] Degraded warning fires on a synthetic module whose only TEXT pages all fell back, despite a majority of art pages.
- [ ] Item 2 resolved either way with tests for both repros; item 3 tightened.

## Out of scope

Behavior changes beyond these.

## Verification

Lane: agent

## Blocked by

None.

---

## QA Reports

## History

- 2026-08-19T20:40:00Z  created → needs-triage (cross-team sweep on a3f7fe6)  [ss-imod01]
