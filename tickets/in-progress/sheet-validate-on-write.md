---
slug: sheet-validate-on-write
title: Nothing validates a character sheet on write, and the validator that exists is vacuous
category: bug
kind: afk
priority: p0
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

This is the root cause of every other sheet defect on the board. A canonical
shape is declared (`lib/character_schema.py:5-11`) and documented
(`docs/schema-reference.md:428-481`). Six writers produce six different key sets.
**No write path validates.**

`schemas.validate_character` is called from exactly one place —
`lib/schemas.py:356`, inside `validate_world_state`, i.e. `/world-check`. And it
barely checks anything: it requires only `name` and `level`. Run against real and
degenerate sheets, every one passes:

```
conan / dcc / shattered-sun / whispering-wood   valid=True  errors=[]
stats={}            valid=True      no stats key          valid=True
stats as a LIST     valid=True      hp missing            valid=True
equipment="a sword" valid=True      junk visual_appearance valid=True
```

Worse, `lib/schemas.py:325` type-checks `data.get('abilities', {})`. **No writer
emits `abilities`** and no campaign has the key — ability scores live under
`stats` (`lib/character_schema.py:119`, `features/character-creation/save_character.py:147`).
The only ability-score check in the codebase is dead code pointed at a phantom
field, and `stats` itself is never type-checked at all.

The six writers, none of which share a constructor:

| Writer | file:line | Produces |
|---|---|---|
| `save-json` (create-character) | `features/character-creation/save_character.py:139-176` | 21-key whitelist |
| `onboard canon` | `lib/identity_onboarding.py:50-62` | 10 keys, `stats:{}` |
| `onboard original/nameless` | `lib/identity_onboarding.py:64-84` | 7 keys, `stats:{}` |
| every mutation verb | `lib/player_manager.py:92` | writes back whatever it loaded |
| `become` | `lib/player_manager.py:737` | the NPC's `character_sheet` verbatim |
| `gm-session.sh move` | `lib/session_manager.py:583-585` | injects `current_location` |

The 21-key whitelist also silently drops anything outside it. `/create-character`'s
own documented example at `.claude/commands/create-character.md:198` passes
`"spells":{"cantrips":[],"level_1":[]}` and `save_character.py` discards it —
**PC spells have no home anywhere in the codebase.**

Measured drift across the four live campaigns: `xp`, `race`, `saves`, `skills`,
`id`, `alignment`, `background`, `bonds`, `ideals`, `flaws`, `traits`,
`features`, `notes` all present in three campaigns and absent from `dcc`;
`conditions` present only in `dcc`; `current_location` absent from
`shattered-sun`; `proficiency_bonus` and `speed` absent everywhere while
appearing in exactly one line of the repo (`lib/schemas.py:300`). `xp` is
`{current,next_level}` from `save_character.py:159` and a bare int on a party
sheet — absorbed by `_xp_view` (`lib/player_manager.py:133-139`), but only by
luck.

## Acceptance criteria

- [ ] `validate_character` type-checks `stats`, `hp`, `equipment`, `visual_appearance` and requires the fields `character_schema` declares canonical
- [ ] The dead `abilities` check at `lib/schemas.py:325` points at `stats`, or is deleted
- [ ] All six writers call the validator before persisting; a failing sheet raises with the field named, it does not save
- [ ] The degenerate cases in the table above (`stats` as a list, `equipment` as a string, missing `hp`) all fail validation
- [ ] `save_character.py`'s whitelist either accepts `spells` or the create-character example stops passing it
- [ ] `/world-check` reports the four existing drifted sheets accurately instead of green

## Out of scope

Backfilling the drifted sheets (see `sheet-one-constructor`) and the 5e field
gaps (see `sheet-5e-completeness`). This ticket only makes the check real and
makes it run.

## Verification

Lane: agent. The degenerate-sheet table is the regression suite: each row must
fail after this lands.

## Blocked by

Nothing.

---

## QA Reports

## History

- 2026-08-27T00:00:00Z  created → needs-triage  [readme-audit]
