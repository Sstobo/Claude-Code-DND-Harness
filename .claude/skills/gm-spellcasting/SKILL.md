---
name: gm-spellcasting
description: D&D 5e spellcasting mechanics — spell slots by level, casting resolution, and concentration. Load when a player casts a spell. Spawn the spell-caster agent for spell details.
---

# Spellcasting Mechanics

When a player casts a spell: fetch the spell, check slots, resolve.

## Resolve from Fetched Data — never from memory

```
uv run python features/spells/get_spell.py "<spell name>"
```

That returns the spell's level, casting time, range, components (V/S/M),
duration + whether it needs **concentration**, the damage/healing dice and any
higher-level scaling, and the save or attack it uses. Resolve off those numbers:

- **Attack spells:** d20 + spell attack bonus vs AC, then the fetched damage dice.
- **Save spells:** target rolls the fetched save vs the caster's spell save DC
  (8 + proficiency + casting mod); half damage on a success when the spell says so.
- **Utility:** apply the fetched effect and duration as written.

Spawn the `spell-caster` agent when you want the lookup off the critical path.

## Spell Slots — fetch the caster's level row

Slots are class data. Pull them for the caster's class and level:

```
uv run python features/character-creation/api/get_class_levels.py <class> <level>
```

The `spellcasting` block gives `cantrips_known`, `spell_slots_level_1` …
`spell_slots_level_9` for that exact level (wizard 3: 3 cantrips, 4 first-level
slots, 2 second-level slots). Omit the level to get the whole 1–20 progression.

An **empty `spellcasting: {}`** means the class row carries no casting progression.
For a true non-caster (fighter, barbarian, rogue) that is the answer: no slots.
But an Eldritch Knight fighter or Arcane Trickster rogue casts off the **subclass**
progression, which the SRD class rows don't carry — for them use the third-caster
table: their slots equal a full caster's row at caster level = ceil(class level ÷ 3),
so slots start at class level 3 (2 first-level), 3 first-level at 4, 4 first and 2
second at 7, reaching 4/3/3/1 at 19. Never read an empty block as "cannot cast" for a
character whose subclass is a caster.

`spells_known` is only there for classes that learn a fixed list (bard, ranger,
sorcerer, warlock). Prepared casters — wizard, cleric, druid, paladin — have no
such field: they prepare **casting mod + class level** spells (paladin: half
level), minimum 1, chosen at a long rest.

**Warlocks use Pact Magic.** The API reports their pact slots in one spell level
only, everything below it zero (warlock 5: two 3rd-level slots, nothing at 1st or
2nd). Every warlock spell is cast at that level, and the slots come back on a
**short** rest, not just a long one. The exception is Mystic Arcanum from level 11
(`class_specific.mystic_arcanum_level_6` … `_9`): each of those spells is cast once
per **long** rest without spending a pact slot, at its own level.

Slot consumption: casting at level N spends one slot of level N or higher — up-cast
and the higher slot is gone. Cantrips cost nothing. Slots return on a long rest
(wizards also recover some via Arcane Recovery on a short rest). If the character
has no slot of the required level, the spell cannot be cast — say so before it
happens, don't let them spend what they don't have. Track expended slots in the
narration and session flow, and report what's left when it matters; there is no
slot subcommand. HP, XP, and inventory still persist through `gm-player.sh` before
you narrate.

## Concentration
One concentration spell at a time. On damage: Con save DC 10 or half the damage
(whichever higher) or lose it. A new concentration spell ends the previous.
