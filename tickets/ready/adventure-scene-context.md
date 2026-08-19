---
slug: adventure-scene-context
title: ADVENTURE block in scene context
category: enhancement
kind: afk
priority: p1
lane: agent
parentPrd: import-module
blockedBy: [adventure-store]
claimedBy: null
claimedAt: null
changedFiles: []
resolution: null
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

- [ ] With an adventure.json present, `bash tools/gm-session.sh context` includes the ADVENTURE block with current scene material and the next-scene line.
- [ ] Without adventure.json, context output is unchanged (existing tests pass).
- [ ] After `gm-adventure.sh advance`, the block reflects the new current scene.
- [ ] A test covers the block's presence/absence and next-scene line.

## Out of scope

Any change to other context blocks, the RAG path, or /import.

## Verification

Lane: agent

## Blocked by

adventure-store

---

## QA Reports

## History

- 2026-08-19T18:05:00Z  created → ready  [ship-it]
