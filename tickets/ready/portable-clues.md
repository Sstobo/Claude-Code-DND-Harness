---
slug: portable-clues
title: Per-scene clues: the book's information, deliverable anywhere
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
createdAt: 2026-08-26T18:50:00Z
updatedAt: 2026-08-26T18:50:00Z
---

## Parent

module-fidelity — prds/module-fidelity.md

## Category

enhancement

## What to build

The DM-lens headline feature (Lazy-DM secrets/clues method). Converter
extracts per scene `clues`: [{id, text, about, fixed: bool}] — what can be
LEARNED here, written location-independent ("Cyrus Lexica knows the Wood
better than any living man", "the Siren sails at dawn"), with `about` naming
the entity/thread it serves. The dossier NOW block renders the LIVE CLUE SET:
undelivered clues from visited + adjacent scenes. `gm-adventure.sh clue-drop
<id> --where --how` marks delivery (records where/how, stamps [ADAPTED] into
the chronicle line the GM writes); delivering anywhere is legal by design.
Off-book play draws from the same set — the gap-filler becomes the book's own
information instead of fresh invention.

## Acceptance criteria

- [ ] Schema + validation for clues; AT-05 1.1-1.3 re-extraction yields the Stockade summons, the Siren sailing, Cyruss expertise as portable clues
- [ ] Dossier renders undelivered clues for visited+reachable scenes; delivered ones drop off
- [ ] clue-drop records delivery site + method, idempotent per id
- [ ] A clue delivered off-book renders in the ADVENTURE block as spent-with-provenance

## Out of scope

Auto-suggesting which clue fits the current beat (GM judgment); knowledge-axis tracking beyond delivered/undelivered.

## Verification

Lane: agent

## Blocked by

scene-requires-schema

---

## QA Reports

## History

- 2026-08-26T18:50:00Z  created → ready  [ss-modfid]
