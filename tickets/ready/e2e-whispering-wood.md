---
slug: e2e-whispering-wood
title: End-to-end — import the Whispering Wood PDF, verify playable
category: enhancement
kind: hitl
priority: p1
lane: manual
parentPrd: import-module
blockedBy: [module-text-spine, adventure-store, adventure-scene-context, import-module-command]
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

Nothing new — run `/import-module
/Users/seanstobo/Downloads/at-05-the-whispering-wood.pdf` in a live session
(the fan-out needs the main agent's Agent tool) and verify the result is
playable. Fix-forward small issues found during the run; anything structural
becomes a new ticket.

## Acceptance criteria

- [ ] Import completes with ≤6 converter agents on `claude-opus-4-8[1m]`; `adventure.py validate` passes.
- [ ] All keyed scenes detected in the slice step appear in adventure.json in order, with read_aloud and gm_notes populated.
- [ ] Known SRD creatures (the module has a Harpy) carry `srd_index`; homebrew ones carry embedded stat blocks.
- [ ] NPCs from the module exist in the campaign's npcs.json.
- [ ] `gm-session.sh context` shows the ADVENTURE block; `gm-adventure.sh advance` and `jump` move the pointer and the block follows.
- [ ] Human spot-check: read 2–3 scenes against the PDF — content faithful, no column-interleave garbage.

## Out of scope

New features discovered during the run — file them as tickets.

## Verification

Lane: manual

## Blocked by

module-text-spine, adventure-store, adventure-scene-context, import-module-command

---

## QA Reports

## History

- 2026-08-19T18:05:00Z  created → ready  [ship-it]
