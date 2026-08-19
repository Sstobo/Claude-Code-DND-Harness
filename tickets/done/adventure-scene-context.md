---
slug: adventure-scene-context
title: ADVENTURE block in scene context
category: enhancement
kind: afk
priority: p1
lane: agent
parentPrd: import-module
blockedBy: [adventure-store]
claimedBy: ss-imod01
claimedAt: 2026-08-19T16:12:00Z
changedFiles: [lib/session_manager.py, tests/test_adventure_scene_context.py, docs/modules/scene-context.md]
resolution: ADVENTURE block in scene context (current scene + next per the book), doc updated same commit
reviewRounds: 1
implementer: null
createdAt: 2026-08-19T18:05:00Z
updatedAt: 2026-08-19T16:35:00Z
---

## Parent

/import-module — structured adventure-module import (prds/import-module.md)

## Category

enhancement

## What to build

When the active campaign has an `adventure.json`, the scene-context assembly
in `lib/session_manager.py` (the same builder that emits `--- WORLD INDEX ---`
around line 766) appends an `--- ADVENTURE ---` block:

- Current scene: `key title` + location, its `gm_notes`, `read_aloud`
  (marked as read-aloud), encounters (monster names/counts), and checks
  (skill + DC).
- One line: `Next per the book: <key> <title>` (from transitions, else spine
  order; omit if at the end).
- A hint line that `gm-adventure.sh advance|jump` moves the pointer.

Read via `lib/adventure.py` — no schema logic duplicated in
session_manager. When `adventure.json` is absent, output is byte-identical to
today.

## Acceptance criteria

- [x] With an adventure.json present, `bash tools/gm-session.sh context` includes the ADVENTURE block with current scene material and the next-scene line.
- [x] Without adventure.json, context output is unchanged (existing tests pass).
- [x] After `gm-adventure.sh advance`, the block reflects the new current scene.
- [x] A test covers the block's presence/absence and next-scene line.

## Out of scope

Any change to other context blocks, the RAG path, or /import.

## Verification

Lane: agent

## Blocked by

adventure-store

---

## QA Reports

### 2026-08-19T16:45:00Z — pass [review-adv-scene-context]
reviewed: perfect
Notes (non-blocking nits): broad `except Exception` around the block could hide adventure.py programming errors (suggest narrowing); uses private manager._scene(); adventure.json read twice per context; encounters/checks render uncapped.

### 2026-08-19T16:35:00Z — verified [ss-imod01]
- 8 new tests pass (absence unchanged, presence, next-in-spine-order, next-via-transition, tracks advance, no-next at end, corrupt adventure.json guarded, end-to-end wrapper).
- Existing context tests: no new failures (only the pre-existing sibling-leak failure, ticketed as sibling-repo-test-leak).
- Live demo: ADVENTURE block renders read-aloud/checks/encounters, next line, follows advance, omits next at last scene.
- Doc ingest done same sitting: scene-context.md block list + design note + sources + restamp.

## History

- 2026-08-19T16:45:00Z  review perfect → done, committed  [ss-imod01]

- 2026-08-19T16:35:00Z  verified → in-review  [ss-imod01]
- 2026-08-19T16:13:00Z  doc-grounding confirmed  [ss-imod01]
- 2026-08-19T16:12:00Z  claimed  [ss-imod01]
- 2026-08-19T18:05:00Z  created → ready  [ship-it]
