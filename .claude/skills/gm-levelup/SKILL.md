---
name: gm-levelup
description: D&D 5e leveling — XP thresholds, the level-up ceremony, hit dice by class, and ASI/feat/subclass handling. Load when gm-player.sh xp reports LEVEL_UP.
---

# Level Up

Trigger: when `gm-player.sh xp` outputs **LEVEL_UP**. Thresholds come from `player_manager._xp_thresholds` and match the 5e table below.

## XP Thresholds
| Level | XP | Milestone |
|-------|------|-----------|
| 1→2 | 300 | first level-up |
| 2→3 | 900 | often subclass |
| 3→4 | 2,700 | first ASI/feat |
| 4→5 | 6,500 | extra attack, 3rd-level spells |
| 5→6 | 14,000 | subclass feature |
| 6→7 | 23,000 | 4th-level spells |
| 7→8 | 34,000 | second ASI/feat |
| 8→9 | 48,000 | 5th-level spells |
| 9→10 | 64,000 | major features |

## Hit Dice by Class
Barbarian d12 · Fighter/Paladin/Ranger d10 · Bard/Cleric/Druid/Monk/Rogue/Warlock d8 · Sorcerer/Wizard d6.

## What the New Level Gives — fetch it, don't recall it

```
uv run python features/character-creation/api/get_class_levels.py <class> <new level>
```

Returns that level's `features` (named class features gained), `prof_bonus`, the
`spellcasting` block (cantrips known and slots per spell level — wizard 3: 3 cantrips,
4 first-level, 2 second-level), `class_specific` counters (rage uses, sneak attack
dice, Arcane Recovery, etc.), and `ability_score_bonuses`. Announce exactly what
that row lists. If a feature's text matters, look it up before describing it; never
invent a feature the level row doesn't name.

**Reading the ASI signal:** `ability_score_bonuses` is a running total of ASIs taken
so far, not a flag for this level — wizard 4 through 7 all report 1, 8 through 11
report 2. The level grants an ASI when **"Ability Score Improvement" appears in
`features`** (fighter 6, rogue 10), equivalently when the total is higher than the
previous level's. Wizard 5 reports 1 and gains nothing.

**Subclass** likewise comes from `features`, under each class's own name and level —
"Arcane Tradition" at wizard 2, "Divine Domain" at cleric 1, "Pact Boon" at warlock 3.
Don't assume level 3.

## Ceremony
Announce new level → roll/average HP + Con mod → new class features (from the level
row above) → spellcasting gains (the fetched `spellcasting` block) → ASI/feat when
`features` names one (wait for player choice, then edit `abilities` in
character.json) → subclass choice when `features` names that class's subclass feature.
