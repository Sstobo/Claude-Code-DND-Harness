---
slug: api-file-cache
title: JSON file cache in dnd_api_core.fetch()
category: enhancement
kind: afk
priority: p0
lane: agent
parentPrd: 5e-native-fork
blockedBy: []
claimedBy: null
claimedAt: null
changedFiles: []
resolution: null
reviewRounds: null
implementer: null
createdAt: 2026-08-19T14:10:45Z
updatedAt: 2026-08-19T14:10:45Z
---

## Parent

5e-Native Fork (prds/5e-native-fork.md)

## Category

enhancement

## What to build

Add a file cache to `fetch()` in `features/dnd-api/dnd_api_core.py`. Key: the
endpoint path (sanitized to a filename). Store: raw JSON under
`features/dnd-api/cache/` (gitignored). No TTL — 2014 SRD data is immutable.
Cache hit skips the network entirely. Error responses (the `{"error": ...}`
dicts) are never written to cache. Keep it ~10-15 lines; other feature dirs
(`features/spells/`, `features/gear/`, `features/rules/`,
`features/character-creation/api/`) have their own API cores — if they
duplicate `fetch()`, point them at the one cached core rather than caching
each copy separately, whichever is the smaller diff.

## Acceptance criteria

- [ ] Second fetch of the same endpoint reads from disk, no network call (verifiable check included, e.g. a `__main__` self-check)
- [ ] HTTP/network errors return as before and leave no cache file
- [ ] `uv run python features/dnd-api/monsters/dnd_monster.py goblin` works and populates the cache
- [ ] Spell/gear/rules feature scripts still run (cached or live)
- [ ] `cache/` gitignored

## Verification

Lane: agent

## Blocked by

None.

---

## QA Reports

## History

- 2026-08-19T14:10:45Z  created → ready  [main]
