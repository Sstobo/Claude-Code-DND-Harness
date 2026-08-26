---
slug: converter-defect-sweep
title: Fabrication guard, NPC name canonicalization, pages offset, conversion_flags
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

Four converter/import defects, each with a validator so they stay fixed:
(1) Fabrication guard — a slice that is a bare heading (< ~50 chars of body)
must yield heading-only scene + conversion_flag, never invented prose;
AT-05 part-4 (23-char slice → 140 chars of plausible fiction) is the fixture.
Validator compares scene text against slice text for low-content slices.
(2) Scene NPC names canonicalized through `lib/integrity_gate.py` (module path
never runs it): the nine unresolvable AT-05 names incl. Brint "Salty"
Brineborn (1.1) and Cyrus (3.5) must resolve to npcs.json keys or be created.
(3) `pages` printed-vs-PDF offset detected (24/72 entries exactly 2 low) and
corrected at import; citation helper uses corrected values.
(4) `[extraction unclear: ...]` in-band markers promoted to
`scene.conversion_flags` list; import summary prints them (AT-05 has 7,
including two genuine rules ambiguities: 3.4 blights, 4.1 inverted save).

## Acceptance criteria

- [ ] part-4 regression: re-converted bare heading yields no invented prose, flag set
- [ ] All 43 scenes' npcs resolve to npcs.json keys after the sweep (epithet forms included)
- [ ] Pages offset detected + corrected; spot-check 3 known-off entries
- [ ] conversion_flags populated from existing markers; import summary lists them
- [ ] Each fix has a validator that fails loudly on regression

## Out of scope

Re-writing gm_notes content; two-column extraction internals.

## Verification

Lane: agent

## Blocked by

scene-requires-schema

---

## QA Reports

## History

- 2026-08-26T18:50:00Z  created → ready  [ss-modfid]
