---
slug: pc-attack-from-sheet
title: The PC's own attack numbers are still typed by the model — read them off the sheet
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

README:5 says "none of that arithmetic happens in the model's head" and README:46
says "The GM never does the arithmetic." Both are true for monsters and false for
the player character — the one creature whose numbers the player actually cares
about.

The resolver reads an enemy's to-hit and damage off the fetched stat block
(`lib/combat_manager.py:413-435`, mapped at `_from_stat_block:88-110`) and fails
closed when the block is missing (`:419-435`). That part is genuinely well built
and well tested. But the **PC's** numbers are not read off anything: the GM
computes ability mod + proficiency + magic in its head and types them in as
`--bonus 8 --damage "2d6+4"` (`lib/combat_manager.py:401-402`), a procedure
spelled out step by step in `.claude/skills/gm-combat/SKILL.md:218-228`. Nothing
validates them against `character.json`.

Worse, when the `--from` attribution disagrees with `--bonus`, it is a **stderr
warning only** (`lib/combat_manager.py:444-446`). The swing resolves and the
player is shown a staged breakdown line that does not sum to the total printed
above it — the one place in the whole product where the receipt visibly lies.

Two related holes in the same surface:

**Combat is opt-in.** `attack` raises unless `start` + `add-enemy` ran
(`lib/combat_manager.py:407-410`, `:8`, `tests/test_combat_manager.py:311`), so a
narrated skirmish routes through no resolver at all, and `gm-combat.sh hp` /
`gm-player.sh hp` accept any number the model picks.

**Fetched stat blocks are optional.** `add-enemy "Orc Warrior" 22 --ac 17` is a
first-class signature (`lib/combat_manager.py:750-751`,
`tests/test_combat_manager.py:157`). Whether a creature arrives fetched or
retyped is model discipline (`.claude/skills/gm-combat/SKILL.md:99-111`), not a
tool guarantee — so README:233's "Enemies enter as their fetched SRD stat block"
is a convention, not a rule.

**Rage resistance is a flag the model must remember.** Nothing reads the
`raging` condition; `--resist` must be passed on every incoming bludgeoning/
piercing/slashing hit (`lib/combat_manager.py:767`). Forgetting it is exactly the
arithmetic error that kills a PC who should have lived — and README:269 names the
raging barbarian specifically.

## Acceptance criteria

- [ ] `attack` derives the PC's to-hit and damage from `character.json` (weapon + ability + proficiency) the way `join_pc` already reads HP/AC/DEX; `--bonus` becomes an explicit override
- [ ] A `--from` attribution that does not sum to the total **refuses** instead of warning
- [ ] `add-enemy` without `--stat-block` requires an explicit `--homebrew` / `--adapted-from <srd-index>` flag, and records `source` provenance either way
- [ ] Damage resistance is derived from the target's stored conditions and the damage type (rage → resist B/P/S), with `--resist` as override
- [ ] A PC death sets an explicit `next: "death-protocol"` on the tool's return, and `end` refuses to clear combat while a PC-side combatant sits at 0 with no `kill`/`revive` recorded

## Out of scope

Forcing all combat through `start` (a narrated skirmish is a legitimate GM
choice). The receipt honesty and the sheet-derived numbers are the deliverable.

## Verification

Lane: agent. A swing whose `--from` labels sum to 6 while `--bonus` says 8 must
now fail.

## Blocked by

Nothing. Overlaps `sheet-5e-completeness` — proficiency bonus is one of the
fields this ticket wants to read.

---

## QA Reports

## History

- 2026-08-27T00:00:00Z  created → needs-triage  [readme-audit]
