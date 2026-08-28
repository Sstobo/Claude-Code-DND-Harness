---
slug: hp-ac-one-shape
title: Six encodings of "a thing with HP and AC", one hand-written translator
category: enhancement
kind: afk
priority: p1
lane: agent
parentPrd: readme-promises
blockedBy: [sheet-validate-on-write]
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

enhancement

## What to build

Counted across the codebase, there are six shapes for a creature with hit points
and armour class:

1. PC sheet — flat, `hp: {current,max}`
2. Party NPC — nested under `npc['character_sheet']`
3. Combatant — `hp_current` / `hp_max` flat, plus `ac`, `conditions`, `initiative`, `side` (`lib/combat_manager.py:224`)
4. `lib/npc_stats.py:59-66` proxy — `{hp, cr, difficulty, statless}`, no AC
5. `lib/extraction_schemas.py:22-27` — `{ac, hp, cr, abilities}`
6. SRD block — `armor_class: [{type, value}]`

Shapes 4 and 5 write **two different structures into the same `npc['stats']`
key**, and combat reads neither.

There is exactly one translator, `join_pc` (`lib/combat_manager.py:309-310`), and
it exists only for the PC. `join` for an ally never reads `npcs.json` at all —
every number is retyped on the command line, so a party sheet's `attack_bonus`
and `damage` are invisible to the resolver that the README says owns every
number.

Two silent defaults ride on top:

- **AC missing → 10**, `lib/combat_manager.py:271`, no warning. A hand-added
  creature cannot swing (the attack path fails closed correctly) but *can be
  hit* against an invented defence. Note the adjacent `attacks`-without-
  `attack_bonus` case *does* warn at `:288-290`; AC does not.
- **DEX missing → +0 initiative**, `lib/combat_manager.py:118-124`.

Genuine crash path: `header()` uses bracket access at `lib/combat_manager.py:701-702`
(`c['hp_current']`, `c['hp_max']`, `c['ac']`), as do `:342` and `:654`. A partial
record raises — and `tests/test_save_restore.py:32-34` writes exactly such a
record, with nothing rejecting it.

Two display bugs from the same root: `level`/`race`/`class` are not on the
combatant record, so the panel reaches sideways into `character.json` and renders
them **only if the names match** (`lib/combat_manager.py:712`) — a renamed sheet
gives a blank title with no error. And enemy `conditions` persist but never
display, because roster labels derive purely from the HP ratio (`:194-200`), so
`gm-combat.sh condition "Orc" add prone` saves correctly and is invisible.

## Acceptance criteria

- [ ] One adapter converts both directions between sheet shape and combatant shape; `join_pc` and a new ally path both use it
- [ ] `gm-combat.sh join "<npc>"` reads `npcs.json` — HP, AC, DEX, `attack_bonus`, `damage` — instead of requiring retyped numbers
- [ ] A missing AC warns the way a missing attack bonus already does, rather than defaulting to 10 in silence
- [ ] A missing DEX is reported once at join time, not silently absorbed into every initiative roll
- [ ] `header()` tolerates a partial record, or `add_combatant` refuses to write one
- [ ] Enemy conditions appear on the roster line
- [ ] `npc_stats` and `extraction_schemas` stop writing two shapes into the same `npc['stats']` key

## Out of scope

Unifying the SRD block shape itself — that is the API's shape, and
`_from_stat_block` is the right place to keep absorbing it.

## Verification

Lane: agent. Join a real party NPC to a fight and confirm their stored attack
numbers resolve without being retyped.

## Blocked by

sheet-validate-on-write

---

## QA Reports

## History

- 2026-08-27T00:00:00Z  created → needs-triage  [readme-audit]
