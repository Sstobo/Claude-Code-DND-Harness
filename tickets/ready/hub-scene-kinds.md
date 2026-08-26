---
slug: hub-scene-kinds
title: scene.kind + visited/spent/history/off_book + _next_key spine fix
category: enhancement
kind: afk
priority: p1
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

`scene.kind`: beat | hub | site | gate | chapter (converter-set; default beat;
part-* headers become chapter; the 17 transition-less Part 2 Eldoria locations
become hub members / site). `progress` gains `visited {key: {first_seen,
last_seen}}` (distinct from completed = resolved), `spent [{key, where, note}]`
(content used out of position — the Grimhammer case), `history [{key, at,
via}]` append-only (advance AND jump both record), `off_book {since, location}`
set by the differ when player_position matches no scene location. Fix
`_next_key` (lib/adventure.py:325): prefer spine order for "next"; a hub is
never auto-"skipped"; `advance` from a hub-member scene returns to the hub
context rather than chaining transitions[0] (the 2.2→2.4 arrest mis-wire is
the regression test). `gm-adventure.sh spend <key> --where --note` records
out-of-position use.

## Acceptance criteria

- [ ] Kinds validate; AT-05 re-import classifies part headers chapter, Part 2 locations hub/site, chain scenes beat
- [ ] advance from 2.2 no longer lands on 2.4; regression test pins it
- [ ] jump and advance both append history; visited stamps on arrival
- [ ] spend records the Grimhammer-style transplant and the differ/brief shows 2.1 unspent
- [ ] off_book sets when location matches no scene, clears on return

## Out of scope

Rendering all transitions as offers (shipped in dossier STORY COMING UP). Requires evaluation (differ ticket).

## Verification

Lane: agent

## Blocked by

scene-requires-schema

---

## QA Reports

## History

- 2026-08-26T18:50:00Z  created → ready  [ss-modfid]
