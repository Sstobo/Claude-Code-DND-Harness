---
slug: api-file-cache
title: JSON file cache in dnd_api_core.fetch()
category: enhancement
kind: afk
priority: p0
lane: agent
parentPrd: 5e-native-fork
blockedBy: []
claimedBy: ss-5efork
claimedAt: 2026-08-19T14:16:37Z
changedFiles: [features/dnd-api/dnd_api_core.py, features/dnd-api/monsters/dnd_encounter_v2.py, features/dnd-api/monsters/dnd_monsters_api_filter.py, features/spells/spell_api_core.py, features/rules/rules_api_core.py, features/character-creation/character_creation_core.py, .gitignore]
resolution: disk cache for all dnd5eapi fetches — one cached core, atomic writes, corrupt-file recovery, encounter scripts unified
reviewRounds: 2
implementer: null
createdAt: 2026-08-19T14:10:45Z
updatedAt: 2026-08-19T15:14:02Z
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

- [x] Second fetch of the same endpoint reads from disk, no network call (verifiable check included, e.g. a `__main__` self-check)
- [x] HTTP/network errors return as before and leave no cache file
- [x] `uv run python features/dnd-api/monsters/dnd_monster.py goblin` works and populates the cache
- [x] Spell/gear/rules feature scripts still run (cached or live)
- [x] `cache/` gitignored

## Verification

Lane: agent

## Blocked by

None.

---

## QA Reports

## History

- 2026-08-19T14:10:45Z  created → ready  [main]
- 2026-08-19T14:16:37Z  doc-grounding confirmed  [ss-5efork]
- 2026-08-19T14:16:37Z  claimed  [ss-5efork]

### 2026-08-19T14:41:59Z — verified [ss-5efork]
Self-check (__main__) proves cache hit skips network (urlopen patched to raise) and errors leave no cache file. dnd_monster.py goblin populates cache; spells/rules/character-creation/gear scripts all run through the unified cached core. cache/ gitignored.
- 2026-08-19T14:41:59Z  verified → in-review  [ss-5efork]

### 2026-08-19T14:58:04Z — fail [review-api-cache]
reviewed: needs-changes
- self-check error-path assertion is a false proof: 404 fetch runs while urlopen is patched, bare except swallows the sentinel; real HTTPError branch never exercised. Behavior itself verified correct live.
- cache-hit guard weakened the same way: guard should raise something fetch() cannot catch.
- corrupt/truncated cache file raises uncaught JSONDecodeError and bricks the endpoint until hand-deleted; write_text not atomic with concurrent agent writers. Repro'd.
- style nits: sanitizer collision (unreachable today), missing trailing newlines (pre-existing).

### 2026-08-19T15:04:31Z — verified (fix round) [ss-5efork]
Re-verified independently: cold self-check OK (live 404 asserted outside guard; guard raises BaseException subclass, proven non-vacuous); corrupt cache file recovers via network fallthrough; atomic writes leave no .tmp; encounter_v2 + monsters_api_filter now serve from disk with network blocked. All review criteria addressed.
- 2026-08-19T15:04:31Z  fix round verified — followup review dispatched  [ss-5efork]

### 2026-08-19T15:14:02Z — pass [review-api-cache]
reviewed: perfect (followup round 2)
Notes (non-blocking nits, preserved verbatim in spirit):
- mkstemp creates cache files 0600 vs prior umask 0644 (irrelevant for gitignored single-user cache; chmod 644 if tree ever shared)
- no try/finally around temp file (orphan .tmp practically unreachable)
- search/limit filtering moved outside the old try/except; malformed 200 payload would KeyError (not reachable against this API)
- no trailing newline at EOF (pre-existing); removed urllib.parse import was already unused
- self-check now needs network for the live-404 assertion (inherent to testing the real branch)
- 2026-08-19T15:14:02Z  done → committed  [ss-5efork]
