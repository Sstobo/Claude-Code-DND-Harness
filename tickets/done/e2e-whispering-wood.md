---
slug: e2e-whispering-wood
title: End-to-end — import the Whispering Wood PDF, verify playable
category: enhancement
kind: hitl
priority: p1
lane: manual
parentPrd: import-module
blockedBy: [module-text-spine, adventure-store, adventure-scene-context, import-module-command]
claimedBy: ss-imod01
claimedAt: 2026-08-19T20:55:00Z
changedFiles: []
resolution: Whispering Wood imported end-to-end — 43 scenes, 37 NPCs, 24 SRD + 32 embedded monsters, 0 unstatted, ADVENTURE block live
reviewRounds: null
implementer: null
createdAt: 2026-08-19T18:05:00Z
updatedAt: 2026-08-19T18:05:00Z
---

## Parent

/import-module — structured adventure-module import (prds/import-module.md)

## Category

enhancement

## What to build

Nothing new — run `/import-module
/Users/seanstobo/Downloads/at-05-the-whispering-wood.pdf` in a live session
(the fan-out needs the main agent's Agent tool) and verify the result is
playable. Fix-forward small issues found during the run; anything structural
becomes a new ticket.

## Acceptance criteria

- [x] Import completes with ≤6 converter agents on `claude-opus-4-8[1m]`; `adventure.py validate` passes.
- [x] All keyed scenes detected in the slice step appear in adventure.json in order, with read_aloud and gm_notes populated.
- [x] Known SRD creatures (the module has a Harpy) carry `srd_index`; homebrew ones carry embedded stat blocks.
- [x] NPCs from the module exist in the campaign's npcs.json.
- [x] `gm-session.sh context` shows the ADVENTURE block; `gm-adventure.sh advance` and `jump` move the pointer and the block follows.
- [x] Human spot-check: read 2–3 scenes against the PDF — content faithful, no column-interleave garbage.

## Out of scope

New features discovered during the run — file them as tickets.

## Verification

Lane: manual

## Blocked by

module-text-spine, adventure-store, adventure-scene-context, import-module-command

---

## QA Reports

### 2026-08-19T21:00:00Z — pass (HITL run) [ss-imod01]
- 6 converter agents (cap honored), all batches merged, validate green.
- resolve-monsters: 24 SRD, 32 embedded, 0 unstatted after chasing 4 gaps (2.5 guards copied from 2.4's printed block; Grimhammer brothers commoner-grade; Hobgoblin Captain from the module's printed p.39-40 block; Shadow Demon analog block, module cites MM without reprinting).
- 37 NPCs deduped into npcs.json ("Cyrus" merged into Cyrus Lexica; 3 monster names excluded).
- ADVENTURE block renders in gm-session context; advance moved part-1→1.1, jump returned; progress persists.
- Slice quality: read-aloud verbatim and unbroken (1.4 checked against PDF at import time); converters flagged source typos/contradictions in gm_notes instead of guessing; no embedded-instruction events.
- Campaign data lives under world-state/ (not committed content), tracker records the run.

## History

- 2026-08-19T21:00:00Z  HITL run passed → done  [ss-imod01]
- 2026-08-19T20:50:00Z  claimed (HITL, user-approved plan)  [ss-imod01]

- 2026-08-19T18:05:00Z  created → ready  [ship-it]
