---
name: gm-combat
description: D&D 5e combat mechanics — the standard combat rail (initiative, the round, attack resolution, death saves, XP), plus the API lookups each step requires. Load when a hostile action is declared or combat starts.
---

# Combat Mechanics

Every fight runs the same rail. The engine owns the arithmetic; you own the fiction.
`bash tools/gm-combat.sh` persists initiative, HP, conditions, and death saves in
`combat_state.json` so a fight survives compaction, resume, and your own memory.

```
0 CAST → 1 ORDER → 2 ROUND → 3 SWING → 4 DOWN → 5 CLEAR
```

**The one hard rule: you never do combat arithmetic in your head.** No comparing a
total to an AC, no picking a damage number, no tallying death saves in prose. Every
one of those goes through `gm-combat.sh` and you narrate what it returns. That is
what makes the dice real.

---

## 0. CAST — nothing enters a fight with invented numbers

**Stat blocks are fetched, never improvised.** If the SRD has the creature, its
fetched block IS its stats. Spawn `monster-manual`, or run it yourself:

```bash
uv run python features/dnd-api/monsters/dnd_monster.py goblin > /tmp/gob.json
```

**Fetch the FULL block, never `--combat`.** The `--combat` view drops `attack_bonus`
and `damage` from every action, so a creature added from it can be hit but cannot
swing — step 3 will refuse it. `add-enemy` warns when the actions it stored carry no
attack bonus; if you see that warning, refetch without `--combat`.

**Book text still wins.** Imported module text first, then your knowledge of the
source, then the SRD. When the module names a creature, stat it from the module; the
SRD fills only what the book leaves open. Non-SRD and homebrew creatures are built by
**analogy** — fetch the nearest-CR SRD block, adapt it, and say which block anchored
it ("statted off the SRD bugbear, CR 1"). No creature ships with numbers from nowhere.

**A fight meant to be fought is built to a budget**, not guessed:

```bash
uv run python features/dnd-api/monsters/dnd_encounter_v2.py \
  --party-level 3 --party-size 4 --difficulty hard [--cr 2]
```

It returns the XP budget, raw and adjusted XP, the multiplier, the band it actually
landed in, and the monsters as SRD indexes — feed each index to `dnd_monster.py`. Read
the `warnings` field before running the fight; it names where the build bent. Creatures
that are scenery (rats, crows, a dog that barks and runs) need no budget.

## 1. ORDER — everyone in the fight is in the order

Initiative is **rolled** (1d20 + DEX mod) on entry unless you pass `--init`.

```bash
bash tools/gm-combat.sh start --pc                                  # PC joins from character.json
bash tools/gm-combat.sh join "Brother Anselm" 24 --ac 16 --dex 12   # an ally
bash tools/gm-combat.sh add-enemy --stat-block-file /tmp/gob.json   # repeat per enemy
bash tools/gm-combat.sh header                                      # the order, HP, conditions
```

Four goblins added four times become "Goblin", "Goblin 2", "Goblin 3", "Goblin 4" —
each takes damage separately, so use those names. `--ac`, `--init`, and a name argument
override a stat block (a scaled elite, a named boss).

`header` renders the round panel — the board the player reads between beats:

```
── ROUND 2 ────────────────────────── the whispering wood ──
 ▸ Giant Spider   [████████████]  26/26  AC14  HEALTHY
   Lion           [███░░░░░░░░░]   7/26  AC12  BLOODIED
   Brother Anselm +[██████████░░]  20/24  AC16  HEALTHY
────────────────────────────────────────────────────────────────
   KORDAN  lvl5 half-orc barbarian  HP [█████████░░░] 39/50  AC13
   status: charmed · raging         XP 8000    GP 46
────────────────────────────────────────────────────────────────
```

Enemies and allies (`+`) sit in initiative order with the turn marker; the hero gets
the block below, and the marker moves down there on their turn. **Show the panel once
per round**, after the last combatant has acted — not after every swing, which turns
the fight into a spreadsheet. Show it again whenever the player has lost the thread.

The panel has no right border on purpose: `█` is an ambiguous-width character, so a
closed box drifts a column on whatever font the player is running. Do not add one.

**The action menu goes below the panel, never inside it.** The three numbered options
and the closing "Or something else..." are prose the player chooses from, and they run
whatever length the beat needs — a long one inside a frame wraps and splits it. The
panel reports the board; the menu asks the question.

The staged attack block above stays **unboxed** for the same reason it has dead air in
it — a frame would collapse the pause that makes the roll land.

## 2. ROUND — one turn at a time, 5e action economy

Each combatant's turn: **move** (their speed, splittable) + **one action** + **one bonus
action** (only if a feature grants one) + **one free object interaction**. A **reaction**
is one per round, on a trigger, and can fire on someone else's turn.

Actions worth naming out loud: Attack · Cast a Spell · Dash · Disengage · Dodge · Help ·
Hide · Ready · Shove/Grapple (Athletics vs Athletics or Acrobatics).

`bash tools/gm-combat.sh next-turn` advances the pointer and rolls the round over. It
steps over the fallen on its own, but a **dying hero still gets a turn** — that turn is
their death save. Call it once per combatant, or the round counter is fiction.
Run the enemies' turns yourself — decide the target from what the creature wants, not
from what is convenient, and swing through step 3 like everyone else.

**Reactions you must not forget:** leaving a hostile's reach without Disengage draws an
**opportunity attack**; a creature holding a Ready trigger fires when it fires.

**Concentration:** a caster who takes damage while concentrating rolls a CON save at
**DC 10 or half the damage, whichever is higher**. Run it as a check:
`uv run python lib/dice.py "1d20+3" --dc 12 --from "constitution:3"`.

## 3. SWING — the only way a d20 meets an AC

```bash
bash tools/gm-combat.sh attack "Goblin" --at "Kordan" --with "Scimitar"
```

An action with no attack bonus (Fey Charm, Web, a breath weapon) is refused rather
than faked — those force a **save**, which the defender rolls with `lib/dice.py --dc`.

The enemy's to-hit and damage dice come straight off its stored block. The target's AC
comes off its record. The engine rolls, compares, doubles the dice on a natural 20,
misses on a natural 1, applies the damage through the 5e dying gate, and hands back the
staged block — target first, dead air, then the result. **Paste that output into
narration as it stands.** Never summarise it, never put the outcome above the target.

For the PC, you supply the numbers from the sheet and attribute every point:

```bash
bash tools/gm-combat.sh attack "Kordan" --at "Goblin" --bonus 8 --damage "2d6+4" \
  --from "strength:4" --from "proficiency:3" --from "the greatsword:1"
```

Building that bonus, from `character.json` — **ability modifier + proficiency bonus**
(2 at levels 1-4 · 3 at 5-8 · 4 at 9-12 · 5 at 13-16 · 6 at 17-20) + any magic or feature
bonus. Damage is the weapon's die + the same ability modifier. If you do not know the
weapon's die or properties, **look it up before you swing** — do not guess:

```bash
uv run python features/gear/dnd_equipment.py "greatsword"
```

Add `--resist`, `--vulnerable` or `--immune` when the target's defences apply — rage,
a damage-type resistance, a creature immune to nonmagical weapons. Resistance halves and
rounds down, and the receipt shows both numbers (`**8** (16 resist)`). **A raging
barbarian resists bludgeoning, piercing and slashing**; forgetting it is the single
easiest way to kill a PC who should have lived.

Add `--adv` or `--dis` for advantage or disadvantage. Sources that grant them:

| Situation | Effect |
|---|---|
| Flanking, prone target (melee), attacker unseen, Reckless Attack | advantage |
| Prone target (ranged), attacker prone, target unseen, long range | disadvantage |
| Half cover +2 AC · three-quarters cover +5 AC | on the target's AC |

Multiple sources never stack, and advantage plus disadvantage cancel to a flat d20.

Spells are cast through `gm-spellcasting`; a spell **attack** still resolves here
(`--bonus <spell attack bonus> --damage <dice>`), while a spell that forces a **save**
is a check the defender rolls with `lib/dice.py`. Spawn `spell-caster` for the spell's
real numbers before you cast it — never half-remember a spell's dice or save DC.

## 4. DOWN — 0 HP is a gate, not an ending

A **monster** at 0 HP is dead. A **hero** at 0 HP is *dying*: unconscious, and rolling
death saves. Only damage past 0 that equals or exceeds max HP kills outright.

```bash
bash tools/gm-combat.sh death-save "Kordan"
```

DC 10 flat, no modifiers. Three successes = stable · three failures = dead · natural 20 =
1 HP and conscious · natural 1 = two failures. The tally persists, so three failures
spread across a resume still kills. Any healing above 0 clears it.

Death is real and reachable — never fudge a save to keep a doomed PC alive. Telegraph a
lethal fight first (an over-CR enemy should *read* as deadly, and there should be an
out), but once the player commits against the odds, let the dice fall. On PC death, run
the **Death Protocol** (CLAUDE.md): persist, narrate with weight, then offer the hand-off.
The session does not end.

## 5. CLEAR — persist the reward before you narrate it

`bash tools/gm-combat.sh end` returns `rounds`, `defeated` (enemies killed), `down`
(heroes at 0), `ally_hp` (what the party NPCs finished on — persist it with
`gm-npc.sh` before the state is cleared; the PC's own HP was written to
`character.json` as it happened), and `xp_awarded` — the sum of the defeated enemies'
**fetched** XP. Award that rather than re-deriving it:

```bash
bash tools/gm-player.sh xp "Kordan" +<xp_awarded>
```

If the summary carries `xp_unreadable`, those enemies' XP could not be read from their
stored block — tell the player and award them from the CR table below. Then loot
(`loot-dropper`, persisted **before** the loot box), and advance time (`gm-time.sh`).

---

## Consult, don't recall

Combat is where half-remembered numbers do the most damage. These lookups are not
optional, and they happen **before** the narration, not after a player objects.

| Moment | Consult | Why |
|---|---|---|
| A creature enters a fight | `monster-manual` / `dnd_monster.py` (full block) | AC, HP, attacks, CR, XP as written |
| You are designing the fight | `dnd_encounter_v2.py --party-level …` | so the difficulty is a decision, not an accident |
| A PC swings an unfamiliar weapon | `gear-master` / `dnd_equipment.py` | damage die, properties, finesse/versatile/reach |
| Any spell is cast | `spell-caster` | slot level, save DC, dice, duration, concentration |
| A rule is contested or you are unsure | `rules-master` | RAW first, then the ruling — say which |
| A condition lands | `gm-conditions` skill, then persist | conditions change what is even rollable |

`rules-master` and `monster-manual` both fall back to dnd5eapi.co when the imported book
is silent. That fallback is **mandatory**: no invented mechanics, ever.

## XP by Challenge Rating

| CR | XP | CR | XP | CR | XP |
|----|-----|----|-----|----|-----|
| 0 | 10 | 4 | 1,100 | 10 | 5,900 |
| 1/8 | 25 | 5 | 1,800 | 11 | 7,200 |
| 1/4 | 50 | 6 | 2,300 | 13 | 10,000 |
| 1/2 | 100 | 7 | 2,900 | 15 | 13,000 |
| 1 | 200 | 8 | 3,900 | 17 | 18,000 |
| 2 | 450 | 9 | 5,000 | 20 | 25,000 |
| 3 | 700 | | | | |

Bonus: clever tactics +25%, creative environment +10-25%, social victory +50%.

**Non-kill wins still earn XP.** A fight won WITHOUT a kill — driving the enemy off a
ledge, baiting two enemies into each other, an environmental kill, a daring escape,
surviving telegraphed over-CR odds — is awarded like a kill:
`bash tools/gm-player.sh award --tier minor|major|legendary --reason "..."` (level-scaled).
See `gm-craft → Reward the spectacle`.

## When the fight is going wrong

Too easy: reinforcements arrive, the creature reveals a held-back ability, the ground
turns against them. Too hard: morale breaks and some flee, an ally arrives, the enemy
makes a real tactical mistake, a weakness shows. Adjust the *situation*, never the roll
that already happened.
