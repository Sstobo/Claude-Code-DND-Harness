---
slug: requires-sweep-hardening
title: Rebuild the requires regex sweep so its signal beats its noise
category: enhancement
kind: afk
priority: p2
lane: agent
parentPrd: module-fidelity
blockedBy: [scene-requires-schema]
claimedBy: null
claimedAt: null
changedFiles: []
resolution: null
reviewRounds: 0
implementer: null
createdAt: 2026-08-26T19:18:10Z
updatedAt: 2026-08-26T19:18:10Z
---

## Parent

module-fidelity — prds/module-fidelity.md

## Category

enhancement

## What to build

The first cut of the converter cross-check sweep (suggest_requires /
requires_gaps) was descoped out of scene-requires-schema after review: measured
against the real AT-05 slices it false-fired party_size on 32 of 44 scenes
(room names, statues, tavern flavor, "Non-player characters"), flagged 33 of 43
scenes overall (a wall, not a differ), MISSED the book's one explicit
prerequisite sentence in the front matter, and mislabeled rules-supplement
citations (AT-00) as prior events. Its support functions failed open in
several ways (party_size min:1 covers a min:2 gap; surname-only coverage lets
"Tom Waveshield" cover "Sheriff Amelia Waveshield"; None == 'none' string
comparison), its evidence quotes could delete the very phrase that triggered
them or degrade to bare ellipses on dot-leader runs, hyphenated line-break
names ("Sun-\nKissed") broke both match paths, and a hand-copied
_SWEPT_IDENTITY table drifted from REQUIRES_KINDS with a KeyError trap.

A rebuilt sweep must:
- Anchor party_size to ADDRESSED-party phrasing (second-person constructions,
  "each character must", the front matter's "designed for N characters" line —
  which should also emit the actual N, never a floor of 2 quoting text that
  says four), not bare occurrences of heroes/adventurers/characters
- Read the front matter's prerequisite block ("You will also need...") — the
  strongest signal in the book and currently a total miss
- Distinguish prior-ADVENTURE citations from rules-supplement citations, and
  parameterize the module-code pattern instead of hardcoding AT-\d{1,2}
- Quote at sentence boundaries in collapsed text; never emit a note that lacks
  the matched phrase; skip hits inside stat-block/listing lines
  (is_listing_page/_match_header already classify these)
- Name-match through lib/entity_aliases.resolve_or_merge_key first (surname
  fallback second), join hyphen line-breaks in _collapse, case-sensitive and
  length-floored single-word names
- Coverage checks fail CLOSED: compare the identity field from REQUIRES_KINDS
  (no twin table), party_size compares numbers, absent identity never equals
  absent identity
- Be WIRED: a gaps subcommand joining module-work/scene-*.txt slices to
  adventure.json scenes, called from /import-module with its report in the
  import summary — plus the doc-shape guard on the import-module.md prompt
  template that the review found missing

## Acceptance criteria

- [ ] Sweep over the real 44 AT-05 slices flags fewer than 10 scenes, and 1.2 + the front matter are among them
- [ ] The front-matter prerequisite sentence yields prior_event clauses for AT-01 through AT-04 and NOT for the AT-00 rules supplement
- [ ] "An adventure for four 5th-level characters" yields party_size min 4
- [ ] Every emitted note contains its matched phrase; no note is ellipses-only
- [ ] Coverage: min:1 does not cover min:2; Tom Waveshield does not cover Amelia; a fourth swept kind cannot KeyError
- [ ] gaps subcommand exists, joins slices to scenes, runs in /import-module, and the prompt-template doc has a shape guard test

## Out of scope

The schema, validator, and converter contract (landed with scene-requires-schema).

## Verification

Lane: agent

## Blocked by

scene-requires-schema

---

## QA Reports

## History

- 2026-08-26T19:18:10Z  created → needs-triage (descoped out of scene-requires-schema per review evidence; five verified angle streams attached above)  [ss-modq26]
