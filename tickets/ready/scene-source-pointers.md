---
slug: scene-source-pointers
title: scene.source verbatim slice pointers + converter-summary relabel
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

At `init` from spine.json, stamp `scene.source = {slice:
"module-work/scene-<key>.txt", sha}` for every scene whose slice exists;
`module-work/` is documented as retained, never scratch. `gm-adventure.sh
source [key]` prints the verbatim slice (default: current scene). The
ADVENTURE block and dossier relabel gm_notes as "converter's summary — the
book's words: gm-adventure.sh source <key>" and read_aloud stays "verbatim".
Converter contract: GM-facing text under a length threshold is copied verbatim
(not summarized), and each scene stamps `gm_notes_mode: verbatim | summary`.

## Acceptance criteria

- [ ] init stamps source+sha for all 43 AT-05 scenes; missing slice degrades to absent field, not error
- [ ] `source` verb prints the slice; sha mismatch warns (slice edited after import)
- [ ] Brief/dossier labels distinguish summary vs verbatim, and point at the source verb
- [ ] Converter doc carries the verbatim-below-threshold rule + mode stamp

## Out of scope

Re-summarizing existing scenes; front matter (its own ticket).

## Verification

Lane: agent

## Blocked by

scene-requires-schema

---

## QA Reports

## History

- 2026-08-26T18:50:00Z  created → ready  [ss-modfid]
