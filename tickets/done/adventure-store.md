---
slug: adventure-store
title: adventure.json schema, merge, progress ops + gm-adventure.sh
category: enhancement
kind: afk
priority: p1
lane: agent
parentPrd: import-module
blockedBy: []
claimedBy: ss-imod01
claimedAt: 2026-08-19T15:15:00Z
changedFiles: [lib/adventure.py, tools/gm-adventure.sh, tests/test_adventure.py]
resolution: adventure.json manager (validate/init/merge/status/advance/jump) + gm-adventure.sh wrapper, 34 tests
reviewRounds: 2
implementer: null
createdAt: 2026-08-19T18:05:00Z
updatedAt: 2026-08-19T16:10:00Z
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

- [x] `validate` rejects: missing key, duplicate keys, transition to unknown key, progress pointer at unknown key — each with a clear error; accepts a well-formed file.
- [x] `init` + `merge` build a full adventure.json from a spine plus scene batches, keeping spine order regardless of merge order.
- [x] `advance` marks the current scene completed and moves the pointer to the next scene (first transition if present, else next in spine order); `jump` moves anywhere valid; both persist.
- [x] `gm-adventure.sh status` prints current scene + next; refuses to run with no active campaign, and says so cleanly when the campaign has no adventure.json.
- [x] `tests/test_adventure.py` covers schema validation and progress ops.
- [x] (review) `validate` rejects a transition entry with no usable `to_key` (missing, empty, or non-string) with a clear per-scene error, and `merge` refuses a batch containing one.
- [x] (review) `init` against a campaign that already has an adventure.json refuses with a clear error unless explicitly forced, leaving the existing progress pointer and completed list intact.

## Out of scope

Scene-context rendering (separate ticket), the /import-module command, PDF handling.

## Verification

Lane: agent

## Blocked by

None.

---

## QA Reports

### 2026-08-19T16:10:00Z — pass [review2-adventure-store]
reviewed: perfect (followup round 2)

### 2026-08-19T16:00:00Z — verified (fix round) [ss-imod01]
- Unusable to_key now rejected (6-case parametrized test incl. missing, wrong field, empty, whitespace, None, int); merge refuses and does not persist.
- init refuses over existing adventure.json (progress intact), --force replaces; both tested. Nits fixed. 34 tests pass.

### 2026-08-19T15:45:00Z — fail [review-adventure-store]
reviewed: needs-changes
- lib/adventure.py:89-91 — transition with missing/empty/non-string `to_key` passes validation silently; `_next_key` ignores it and falls back to spine order (silently reroutes play).
- lib/adventure.py:142-167 — `init` overwrites an existing adventure.json with no guard, wiping progress; needs refusal or explicit `--force`.
- Nits: dead `keys` variable in validate_adventure (:60,74-75); weak assertion `"a" in e` in tests/test_adventure.py:67.

### 2026-08-19T15:35:00Z — verified [ss-imod01]
- `uv run python -m pytest tests/test_adventure.py -q` → 24 passed (validation rejections, init/merge spine-order, progress ops, wrapper subprocess tests).
- Implementer end-to-end run: init 3 scenes → merge out-of-order preserves spine order → status/advance/jump behave; invalid merge batch raises before save; broken file reports all problems at once.
- Wrapper checked live against the active campaign (no adventure.json): clean error + rc=1.

## History

- 2026-08-19T16:10:00Z  review perfect → done, committed  [ss-imod01]

- 2026-08-19T15:35:00Z  verified → in-review  [ss-imod01]
- 2026-08-19T15:15:30Z  doc-grounding confirmed  [ss-imod01]
- 2026-08-19T15:15:00Z  claimed  [ss-imod01]
- 2026-08-19T18:05:00Z  created → ready  [ship-it]
