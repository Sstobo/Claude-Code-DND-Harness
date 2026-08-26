---
slug: meta-adaptation-binding
title: meta.adaptation: one-time first-PC binding + gm-adventure.sh adapt
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

Adaptation rulings live in `adventure.json meta.adaptation` ({matched_to_pc,
pc, decided_at, rulings: [{kind, ...context, ruling}]}). Binding fires ONCE on
first-PC-exists, copying the `opening_seed` stamp pattern
(`lib/opening_seed.py` / `identity_onboarding.py`): at import the requires
union is provisional; when a PC first exists, `gm-adventure.sh requires-report`
diffs every scene clause union against live state and prints unmet classes with
scene keys and the book quotes; the GM turns each class into one numbered
player question, then persists rulings via `gm-adventure.sh adapt --kind
party_size --ruling "..."`. Re-running the binding is a no-op once stamped
(idempotent); `adapt` remains available to add/update rulings later.

## Acceptance criteria

- [ ] `requires-report` unions clauses across scenes, dedups by kind+value, diffs against character.json/npcs.json/progress, prints unmet with quotes
- [ ] Binding stamps once; second run changes nothing (test proves idempotence)
- [ ] `adapt` writes a ruling; malformed kind rejected with the valid list
- [ ] Rulings survive re-validate and merge (schema-checked under meta)
- [ ] Fixture: solo-newcomer campaign vs AT-05 yields party_size/npc_with_party/prior_event/item_held unmet set

## Out of scope

Rendering in the brief (requires-differ-brief). Front-matter seeding of rulings (front-matter-preservation).

## Verification

Lane: agent

## Blocked by

scene-requires-schema

---

## QA Reports

## History

- 2026-08-26T18:50:00Z  created → ready  [ss-modfid]
