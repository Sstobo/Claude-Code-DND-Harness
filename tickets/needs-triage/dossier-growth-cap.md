---
slug: dossier-growth-cap
title: "Campaigns can run indefinitely" is false — the dossier grows without a cap
category: bug
kind: afk
priority: p1
lane: agent
parentPrd: readme-promises
blockedBy: []
claimedBy: null
claimedAt: null
changedFiles: []
resolution: null
reviewRounds: 0
implementer: null
createdAt: 2026-08-27T00:00:00Z
updatedAt: 2026-08-27T00:00:00Z
---

## Parent

readme-promises — prds/readme-promises.md

## Category

bug

## What to build

README:132 says "Memory is bounded by your filesystem, not the token limit.
Campaigns can run indefinitely." State on disk is indeed bounded by the
filesystem. Delivery is not, and CLAUDE.md requires the dossier be read **whole**
at session start, every scene change, and after every compaction.

Measured dossier sizes on the four real campaigns: `dcc` 1,564 tokens, `conan`
1,640, `shattered-sun` 2,737, `whispering-wood` **8,529** — and whispering-wood
has only **two** chronicle entries. Section breakdown of that 8.5k:

| Section | Tokens | Why it grows |
|---|---|---|
| WORLD INDEX | 2,787 (32.7%) | every named NPC/location/item/monster, uncapped (`lib/session_manager.py:1928-1943`) |
| ADVENTURE + STORY OVERVIEW | 2,451 | iterates every `part*` scene's `gm_notes` |
| PRESENT NPCS (full sheets) | 1,007 | full sheet per present NPC |
| THE STORY SO FAR | 750 | `_chronicle()` returns the file whole, no truncation (`:1801-1805`, rendered `:1847-1850`) |
| KEY FACTS | 425 | `_key_facts(per_category=None)` — explicitly all of them (`:1853`) |

The chronicle grows ~1.5KB per scene close (2,943 bytes across 2 entries) and the
world index grows with every named thing. At ~10 scene closes per session the
chronicle alone passes 35k tokens around session 25, and the dossier becomes
unreadable in a 200k window somewhere around **session 40-60**.

`campaign_memory.memoir()` already implements real tiering
(`lib/campaign_memory.py:181-197`). The dossier does not use it.

Adjacent, same area: `chronicle.md` is **not in the save contract**.
`SNAPSHOT_TEXT_FILES = ("rules.md", "session-log.md")`
(`lib/session_manager.py:61-64`), so `gm-session.sh restore <save>` rolls back
every JSON file and leaves the chronicle at its later state — narrative desynced
from mechanics.

Also worth noting: `campaign-memory.json` is already 73KB against a 1.7KB session
log, because embeddings are stored inline as JSON floats.

## Acceptance criteria

- [ ] The dossier renders recent chronicle entries whole and older ones through the existing `memoir()` compression tiers
- [ ] The WORLD INDEX is paginated or ranked by relevance to the current location rather than dumped entire
- [ ] KEY FACTS respects a per-category cap in the dossier
- [ ] A simulated 60-session campaign produces a dossier that still fits a sane budget; record the measured number in this ticket
- [ ] `chronicle.md` is added to `SNAPSHOT_TEXT_FILES`
- [ ] README:132's claim either holds after this, or is reworded to state the real horizon

## Out of scope

Moving embeddings out of `campaign-memory.json` into a binary store. Note it as a
follow-up if the 73KB becomes a problem.

## Verification

Lane: agent. Generate a synthetic long campaign and measure. The number goes in
the ticket.

## Blocked by

Nothing.

---

## QA Reports

## History

- 2026-08-27T00:00:00Z  created → needs-triage  [readme-audit]
