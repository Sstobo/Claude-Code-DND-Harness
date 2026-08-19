---
slug: adventure-store
title: adventure.json schema, merge, progress ops + gm-adventure.sh
category: enhancement
kind: afk
priority: p1
lane: agent
parentPrd: import-module
blockedBy: []
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

New `lib/adventure.py` managing a per-campaign `adventure.json`
(path via the same campaign-dir resolution the other managers use):

- **Schema:** `{meta: {title, source_file, levels?}, scenes: [{key, title,
  location, read_aloud, gm_notes, encounters: [{name, monsters: [{name,
  count, srd_index|stat_block}], tactics?}], npcs: [names], treasure: [...],
  checks: [{what, skill, dc}], transitions: [{to_key, when}], pages: [ints]}],
  progress: {current_scene, completed: []}}`. Validation rejects scenes
  missing `key`/`title`, duplicate keys, `transitions.to_key` pointing at
  unknown keys, and a `current_scene` not in `scenes`.
- **Ops (CLI):** `validate`, `merge <scenes.json>` (upsert scene batches from
  converter agents, preserving spine order from an initial `init <spine.json>`),
  `status` (current scene + its title + next per transitions/spine order),
  `advance` (mark current completed, move to next), `jump <key>`, all with
  `--json` variants. Follow the existing manager conventions in `lib/`
  (see `plot_manager.py` / `note_manager.py` for shape).
- **`tools/gm-adventure.sh`:** thin bash wrapper in the style of the other
  `tools/gm-*.sh` (uses `common.sh`, refuses to run without an active
  campaign): `status | advance | jump <key> | validate`.

## Acceptance criteria

- [ ] `validate` rejects: missing key, duplicate keys, transition to unknown key, progress pointer at unknown key — each with a clear error; accepts a well-formed file.
- [ ] `init` + `merge` build a full adventure.json from a spine plus scene batches, keeping spine order regardless of merge order.
- [ ] `advance` marks the current scene completed and moves the pointer to the next scene (first transition if present, else next in spine order); `jump` moves anywhere valid; both persist.
- [ ] `gm-adventure.sh status` prints current scene + next; refuses to run with no active campaign, and says so cleanly when the campaign has no adventure.json.
- [ ] `tests/test_adventure.py` covers schema validation and progress ops.

## Out of scope

Scene-context rendering (separate ticket), the /import-module command, PDF handling.

## Verification

Lane: agent

## Blocked by

None.

---

## QA Reports

## History

- 2026-08-19T18:05:00Z  created → ready  [ship-it]
