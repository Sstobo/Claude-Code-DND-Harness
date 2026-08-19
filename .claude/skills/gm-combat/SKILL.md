---
name: gm-combat
description: D&D 5e combat mechanics — initiative, attack/damage resolution, XP-by-CR awards, combat modifiers, and death saves. Load when a hostile action is declared or combat starts.
---

# Combat Mechanics

Persist combat with `bash tools/gm-combat.sh` (start/add-enemy/hp/condition/next-turn/end) so HP and initiative survive resumes.

## Stat blocks are fetched, never improvised
**If the SRD has the creature, its fetched block IS its stats.** Spawn `monster-manual`
or run `uv run python features/dnd-api/monsters/dnd_monster.py "<creature>"` and use
the AC / HP / attacks / CR / XP it returns. Never invent numbers for a creature the SRD
covers, and never round a fetched value "for feel" — scale it explicitly (minion/elite/boss)
and say so.

Feed the fetched JSON straight into combat so the numbers persist as fetched:
```bash
uv run python features/dnd-api/monsters/dnd_monster.py goblin > /tmp/gob.json
bash tools/gm-combat.sh add-enemy --stat-block-file /tmp/gob.json --init 14
```
AC/HP/XP/CR/actions land on the enemy record from the block. `--ac`, `--init` and a
name argument override it (scaled elite, named boss). The manual form
(`add-enemy "Orc Warrior" 22 --ac 17`) still works for creatures with no block.
Add the same creature four times and they come back as "Goblin", "Goblin 2", "Goblin 3",
"Goblin 4" — each one takes damage separately, so use those names with `gm-combat.sh hp`.

**Book text still wins.** Ordering is unchanged: imported module text first, then your
knowledge of the source, then the SRD. When the module names a creature, stat it from
the module; the SRD only fills what the book leaves open.

**Non-SRD / homebrew creatures are built by analogy.** Fetch the nearest-CR SRD block,
adapt it, and **state which block anchored it** ("statted off the SRD bugbear, CR 1").
No creature enters combat with numbers pulled from nowhere.

## Encounters meant to be fought are built to a budget
A fight you intend to run is designed, not guessed. Pick the difficulty the beat wants
(easy / medium / hard / deadly), then run the builder with the party's level and size:
```bash
uv run python features/dnd-api/monsters/dnd_encounter_v2.py \
  --party-level 3 --party-size 4 --difficulty hard [--cr 2]
```
It returns the XP budget, the raw and adjusted XP, the multiplier, the difficulty band it
actually landed in, and the monsters as SRD indexes — feed each one to
`dnd_monster.py <index>` and `gm-combat.sh add-enemy --stat-block-file`. `--cr` is a hint
when the fiction demands a particular creature tier; leave it off and the builder picks.
The old `--cr N --count N` form still works for a fight you have already cast.

Creatures that are scenery — rats in the alley, crows on the gibbet, a dog that barks and
runs — need no budget. Only encounters intended as combat go through the builder.

## Flow
1. Get enemy stats — fetched block per above (`--combat` for the condensed view).
2. Initiative: `uv run python lib/dice.py "1d20+[dex]"` per combatant; order high→low.
3. Each turn: attack `1d20+bonus` vs AC; on hit roll damage; update HP via `gm-combat.sh hp`.
4. Resolution: award XP, handle loot (persist BEFORE narrating), advance time.
   `gm-combat.sh end` returns `xp_awarded` — the sum of the defeated enemies' **fetched**
   XP. Award that (`gm-player.sh xp "<pc>" +<xp_awarded>`) rather than re-deriving from
   the CR table below; the table is for creatures that entered without a block.
   If the summary also carries `xp_unreadable`, those enemies' XP could not be read from
   their stored block — say so to the player and award them from the CR table (or your
   judgment) on top of `xp_awarded`.

## XP by Challenge Rating
| CR | XP | CR | XP | CR | XP |
|----|-----|----|----|----|----|
| 0 | 10 | 4 | 1,100 | 10 | 5,900 |
| 1/8 | 25 | 5 | 1,800 | 11 | 7,200 |
| 1/4 | 50 | 6 | 2,300 | 13 | 10,000 |
| 1/2 | 100 | 7 | 2,900 | 15 | 13,000 |
| 1 | 200 | 8 | 3,900 | 17 | 18,000 |
| 2 | 450 | 9 | 5,000 | 20 | 25,000 |
| 3 | 700 | | | | |

Bonus: clever tactics +25%, creative environment +10-25%, social victory +50%.

**Non-kill wins still earn XP.** When a fight is won WITHOUT a kill — driving the enemy off a ledge, baiting two enemies into each other, an environmental kill, a daring escape from a lethal foe, surviving telegraphed over-CR odds — award it like a kill: `bash tools/gm-player.sh award --tier minor|major|legendary --reason "..."` (level-scaled). See `gm-craft → Reward the spectacle`. Combat's CR→XP is just one source of XP among many.

## Modifiers
Advantage = 2d20 keep high; Disadvantage = keep low. Half cover +2 AC; 3/4 cover +5. Flanking = advantage (melee). Prone: advantage melee / disadvantage ranged. Crit (nat 20) = double damage dice then add mods. Nat 1 = auto-miss.

## Death & Dying
0 HP → unconscious + death saves (DC 10 Con each turn): 3 successes = stable, 3 failures = death. Nat 20 = 1 HP + conscious. Nat 1 = 2 failures. Damage ≥ max HP = instant death.
Death is real and reachable — don't fudge saves to keep a doomed PC alive. Telegraph lethal fights first (an over-CR enemy should *read* as deadly), but once the player commits against the odds, let the dice fall. On PC death, run the **Death Protocol** (CLAUDE.md): persist → narrate → offer the character hand-off. The session does not end.
