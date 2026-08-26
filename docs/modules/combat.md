---
type: Module
title: The combat rail
description: How a fight is adjudicated — the persisted initiative order, the attack resolver that owns every to-hit and damage roll, and the dying gate the PC's sheet shares with it.
sources:
  - { resource: /lib/combat_manager.py }
  - { resource: /lib/dice.py }
  - { resource: /tools/gm-combat.sh }
  - { resource: /.claude/skills/gm-combat/SKILL.md }
generated: { by: claude-opus-5, at: 2026-08-26T18:29:22Z }
---

# The combat rail

Combat is the one place where a half-remembered number does visible damage: an AC
compared in the model's head, a damage die picked to suit the moment, a death-save
tally kept in prose. `combat_manager.py` closes that by owning the arithmetic. The
model decides *what happens*; the manager decides *what the numbers are*.

The rail is six steps — cast, order, round, swing, down, clear — and `gm-combat`
(the Skill) is the procedure. This doc covers what spans files.

## Where a combatant's numbers come from

| Field | Enemy | PC | Ally |
|---|---|---|---|
| HP, AC, CR, XP, actions | the fetched SRD block (`_from_stat_block`) | `character.json` via `join_pc` | passed on the command line |
| Initiative | rolled `1d20 + DEX mod` on entry unless `--init` | same | same |
| To-hit and damage | the stored action's `attack_bonus` / `damage_dice` | `--bonus` / `--damage`, attributed with `--from` | same as PC |

`attack()` **fails closed**: no stored bonus and no `--bonus` raises rather than
inventing a number. That is the whole point of the resolver, so the error is the
feature — refetch the block or read the sheet.

**The `--combat` view of `dnd_monster.py` is not enough to fight with.** It keeps each
action's name and prose but drops `attack_bonus` and `damage`, so a creature added from
it can be attacked but cannot swing. `add_combatant` returns a `warning` when the
actions it stored carry no attack bonus; the full block is the fix.

## Two places hold HP, and only one is authoritative

`end()` deletes `combat_state.json`. Anything recorded only there is healed by the
fight ending, so:

- **PC** — `_apply_delta` mirrors every change to `character.json` through
  `PlayerManager.modify_hp` as it happens. The sheet is the source of truth; the
  combat record is a mirror that exists so the header and the death saves are real.
  The mirror is best-effort and warns on stderr rather than aborting a swing.
- **Ally** — party NPCs live in `npcs.json`, which this manager does not write.
  `end()` reports `ally_hp` so the GM can persist it with `gm-npc.sh` before the state
  is cleared.
- **Enemy** — dies with the fight. Nothing to carry.

## The dying gate

`game_core.classify_harm` owns the 5e judgment (0 HP opens *dying*; only overkill at or
past max HP kills outright), so combat and the Death Protocol cannot disagree. On top of
it `_apply_delta` applies the table-level default the core deliberately does not encode:
**a monster at 0 HP is dead, a hero at 0 HP is dying.** Only `side` in `pc`/`ally` opens
a `death_saves` counter.

That counter persists on the combatant record, so three failures spread across a
compaction or a resume still kill. `death_save()` refuses to roll once the record is
`stable` or `dead` — a stabilised hero has left the sequence, and re-rolling them was
the old way the tally quietly reset.

## One staged block for every d20

`DiceRoller.format_staged` renders the target first, then dead air, then the roll and
the verdict. The pause is real because the message streams. `format_check` (skill
checks) and `_render_attack` / `death_save` (combat) both go through it, so a swing and
a lockpick read identically at the table — only the label and the verdict differ.

`roll()` flags `natural_20` / `natural_1` on the **kept** die of an advantage or
disadvantage roll, not just on a bare `1d20`. Without that a crit rolled with advantage
— Reckless Attack, flanking, a prone target, which is most crits a barbarian ever
rolls — came back as an ordinary hit and never doubled its dice.

## What the resolver deliberately does not track

Action economy, reactions and opportunity attacks, concentration, and monster tactics
are the model's job under the Skill, not state. They are judgment calls that read
better from the fiction than from a counter, and every one of them still resolves its
dice through `attack` or `lib/dice.py`.
