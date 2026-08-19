---
slug: adventure-block-hardening
title: Narrow the ADVENTURE block's exception guard; read adventure.json once
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
createdAt: 2026-08-19T16:50:00Z
updatedAt: 2026-08-19T16:50:00Z
---

## Parent

/import-module (prds/import-module.md) — follow-up hardening from two independent reviews.

## Category

enhancement

## What to build

`_adventure_block` in lib/session_manager.py (committed in adventure-scene-context) wraps load AND render in a broad `except Exception`, so a renderer bug silently removes the ADVENTURE block from every brief. Narrow the guard to load/parse errors (or log the swallowed exception to stderr), and stop reading adventure.json twice per context call (load once, derive status from the loaded doc). Optionally cap encounters/checks lines like neighbouring blocks.

Flagged as nits by review-adv-scene-context and independently (LOW) by the 5e team's reviewer.

## Acceptance criteria

- [ ] A deliberate rendering bug (e.g. monkeypatched scene with bad type) surfaces on stderr or raises, rather than silently dropping the block; a missing/corrupt adventure.json still degrades to no block.
- [ ] adventure.json is read once per get_full_context call.
- [ ] Existing tests in tests/test_adventure_scene_context.py still pass.

## Out of scope

Any content/format change to the block itself.

## Verification

Lane: agent

## Blocked by

None.

---

## QA Reports

## History

- 2026-08-19T16:50:00Z  created → needs-triage (from review nits + cross-team sweep)  [ss-imod01]
