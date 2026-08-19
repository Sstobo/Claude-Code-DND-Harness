---
slug: spells-levelup-api
title: Spells, slots, and level-up from /classes API
category: enhancement
kind: afk
priority: p1
lane: agent
parentPrd: 5e-native-fork
blockedBy: [unconditional-5e-gates, api-file-cache]
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

Make the /classes API the source of truth for casting resources and
progression. `.claude/skills/gm-spellcasting/` resolves cast spells against
fetched spell data (`features/spells/get_spell.py`: level, damage, save,
components, concentration) and takes spell-slot tables from
`/classes/{class}/levels` instead of any inlined table in the skill.
`.claude/skills/gm-levelup/` pulls features, ASI levels, and slot changes for
the new level from `/classes/{class}/levels/{level}` instead of narrating from
memory; hit-dice-by-class may stay inlined (static, tiny). Add a small helper
script under `features/character-creation/api/` (or reuse an existing one) for
the class-levels lookup so skills call one command. Update claiming docs
same-commit.

## Acceptance criteria

- [ ] gm-spellcasting instructs resolving spell effects from fetched data; its inlined slot table is replaced by the class-levels lookup
- [ ] gm-levelup pulls level features/ASIs/slots from the API (demonstrated: wizard level 3 lookup returns correct slots and features)
- [ ] One command exists to fetch `/classes/{class}/levels/{level}` and is referenced by both skills
- [ ] Claiming docs updated/restamped same-commit

## Verification

Lane: agent

## Blocked by

unconditional-5e-gates, api-file-cache

---

## QA Reports

## History

- 2026-08-19T14:10:45Z  created → ready  [main]
