---
type: Module
title: Game core and World Kit
description: The system-agnostic engine and the hardcoded 5e kit that configures it — and the two separate rule surfaces a world actually plays by.
sources:
  - { resource: /lib/game_core.py }
  - { resource: /lib/world_kit.py }
  - { resource: /lib/overview_seed.py }
generated: { by: claude-opus-5[1m], at: 2026-08-19T18:52:46Z }
---

# Game core and World Kit

`game_core.py` is the system-agnostic engine; `WorldKit` is the D&D 5e ruleset bolted
onto it. The rules are **hardcoded in `lib/world_kit.py`** — there is no per-campaign
`ruleset.json`, and a stale one left on disk by an older campaign is ignored. The
docstrings on both modules state their own contracts. What follows is only what spans
files.

## What the kit declares

| Surface | Value |
|---|---|
| `kit()` | `dnd5e` — always; the D&D mechanics Skills no longer check it |
| `stat_schema()` | attributes `str dex con int wis cha`, vitals `["hp"]` |
| `resolution()` | `d20-vs-dc`, no params |
| `progression_model()` | `xp-levels`; the built `progression` attribute carries the standard 5e table (`XP_THRESHOLDS`, levels 2–20) |
| `lethality()` | `death-saves`, massive-damage bar left at max HP |
| `active_agents()` | monster-manual, rules-master, spell-caster, gear-master, loot-dropper |
| `skills()`, `signature_systems()`, `systems()` | empty — see below |

## A world plays by TWO rule surfaces, not one

The mechanics above are fixed for every campaign. A book's own flavor is the *other*
surface, and it lives in a different file read by different code.

| Surface | Lives in | Read by | Holds |
|---|---|---|---|
| **Mechanics** | `lib/world_kit.py` (hardcoded) | `WorldKit` | kit identity, stat schema, progression, resolution, vitals, lethality |
| **World flavor** | `campaign-overview.json` → `campaign_rules` | `WorldKit.campaign_rules()` | loot boxes, viewer counts — the book's own systems |
| **Rules prose** | `rules.md` in the campaign dir | `WorldKit.rules_doc_path()` | long-form rules text, loaded on demand |

`WorldKit.signature_systems()` returns `[]` **by design**, so scene context's YOUR
WORLD'S RULES block always falls through to `campaign_rules()`. That fallback is now the
only path, not a legacy one — it is where an imported book's systems are expected to be.
`overview_seed.seed_overview` exists to fill it when an import left it empty while the
book's systems sat in prose inside a plot description. That module no longer touches
`ruleset.json` at all. See [scene-context](scene-context.md).

`systems()` (the executable primitives) returns `[]` for the same reason: the 5e kit
instantiates none of `game_core`'s named_track / price_roll / reaction_roll /
guarded_payoff, so the ROLL-these block never renders.

## The resolution model is executed, not just declared

A resolution model picks the dice a check is actually rolled on — `resolve_check`
dispatches on the name it is handed, so a 2d6 caller rolls 2d6 rather than a d20 wearing a
2d6 label. Three models ship in the engine:

| Model | Roll | Success | Crit / fumble |
|---|---|---|---|
| `d20-vs-dc` (default) | 1d20 + mod | total ≥ DC | natural 20 / natural 1 |
| `2d6-plus-mod` | 2d6 + mod | total ≥ DC | 12 / 2 |
| `dice-pool` | N d6, N = the modifier (min 1) | successes ≥ DC | all dice hit / none do |

All three return the same keys (`die`, `modifier`, `total`, `dc`, `success`, `margin`,
`critical`), so callers do not branch. In the pool, `die` carries the success count and
`modifier` the pool size, and the DC is **successes required**, not a total to beat. The
face that counts as a success is `target` (default 5), and `advantage`/`disadvantage`
means an extra/fewer die rather than a second d20.

`opposed_check` takes the same optional `model` and rolls both sides on it, ranking them
on that model's own axis — totals for d20 and 2d6, success counts for a pool. A contest
has no DC, so each side is resolved at DC 0 and only its axis value is read.

The `model` argument is optional on both and defaults to `d20-vs-dc`. The kit supplies
`d20-vs-dc` through `WorldKit.resolve()` / `WorldKit.oppose()`, so the other two models are
reachable only by calling `game_core` directly — they stay in the engine because the engine
is not 5e, but nothing in play selects them today.

## Nothing outside `WorldKit` decides the kit's values

`player_manager` asks the kit — vitals from `vitals()`, thresholds off the built
`progression` object (`_xp_thresholds`, `_max_level`) — rather than holding a 5e literal of
its own. Its `DEFAULT_XP_THRESHOLDS` is a fallback that now agrees with the kit's table
rather than competing with it. `level` remains an accepted alias for `xp-levels` in
`make_progression` and `spectacle_award`.

## Failure modes

Two of the three old failure modes came from a campaign half-authoring its own ruleset;
neither can happen now that the rules are a Python literal.

1. **Unrecognized model name → a warning, then the default.** Still live in the engine for
   direct `game_core` callers: `make_progression` falls through to `MilestoneProgression`
   and `resolve_check` falls back to `d20-vs-dc`, each printing a one-line `[WARNING]`
   naming the offending value. The warnings go to **stderr**, never stdout, so `--json`
   output on the tool wrappers stays parseable. `WorldKit` passes only known names, so it
   never trips this.
2. **Missing `rules.md` → `None`.** `rules_doc_path()` returns the campaign's `rules.md`
   when it exists and `None` otherwise. The old `ruleset.rules_doc` pointer is gone, and
   nothing writes one any more — `overview_seed.fix_rules_doc` only reports whether the
   prose file is there, so a rules doc under any other name is simply not found. Rename
   it to `rules.md`.

To check a live campaign rather than trusting any of this:
`uv run python lib/world_kit.py info --json`.

## `spectacle_award` is a calculator, not a transaction

`spectacle_award` (`lib/game_core.py`) computes amounts and returns them. It reads no
files and writes none. Persistence and level-up detection are the caller's job —
`gm-player.sh award` → `player_manager`. Calling the core function directly awards nothing.

Its XP is scaled to the gap to the next level rather than being a flat table, so one tier
stays meaningful at level 1 and level 12. The `followers` amount is only applied when a
secondary follower currency is declared; `player_manager._spectacle_config` declares none
and hands over `DEFAULT_SPECTACLE_TIERS`, so every award is plain XP.

## Signature-system primitives are calculators, too

`game_core` ships four more world-agnostic building blocks a world's signature
systems are assembled from — every name, threshold, and die comes in as an
argument, none of it is book-specific:

- **`named_track(current, delta, config)`** — a meter with threshold
  consequences (corruption, doom, heat); applies a clamped delta and reports
  which thresholds it newly crossed, up or down. The only one that never rolls.
- **`price_roll(severity, config, rng=None)`** — what a marked action costs the
  actor; rolls, subtracts severity, and reads the cost off a ladder.
- **`reaction_roll(track_value, config, rng=None)`** — an NPC's opening
  disposition, shifted by a track/reputation value onto a tier.
- **`guarded_payoff(config, rng=None)`** — rolled before a marked treasure is
  taken; returns `clean` / `guardian_wakes` / `curse_attaches`.

Like `spectacle_award`, all four **compute and return a plain dict — they read no
files and write none**; persistence is the caller's job. Rolls are seedable via
`rng` for deterministic tests, and reuse the module dice roller when it is
omitted. `uv run python lib/game_core.py` runs their edge-case self-check.

`classify_harm(current_hp, max_hp, amount, lethality)` is the same shape — a pure
classifier returning `{new_hp, outcome}` (`ok`/`dying`/`dead`). It still accepts `gritty`
and a lowered `massive_damage_at` from any direct caller, but `WorldKit.lethality()` hands
it `death-saves` unconditionally: 0 HP → dying, overkill of at least max HP → dead. The
death-save ceremony itself stays in `gm-combat` / the Death Protocol — the core only says
whether a hit is survivable, dying, or fatal.

**Nothing binds them per world any more.** `WorldKit.systems()` returns `[]`, so the
**YOUR WORLD'S SIGNATURE SYSTEMS (executable — ROLL these)** block in
`SessionManager.get_full_context` never renders, and nothing authors a `systems` list
any longer — `/import` and `/new-game` write a world's signature systems into
`campaign_rules` as prose instead. The four primitives remain callable directly from
`game_core`.

## The kit decides which mechanics Skills are legitimate

`gm-combat`, `gm-levelup`, and `gm-spellcasting` encode D&D 5e — hit dice, spell slots, a
level-20 XP table. None of that exists in `game_core`, which is why the split survives the
hardcoding: the engine stays system-agnostic and the 5e rules stay in the kit and those
Skills. `kit()` is now always `dnd5e`, so there is no gate left to open: the Skills'
STEP-0 kit checks are gone and scene context no longer carries a KIT block for them to
defer to — a Skill that routes there just plays 5e. See
[lean core and skill routing](../conventions/lean-core-and-skill-routing.md).

## Related

- [Player character](player-character.md) — where progression state is persisted
- [World bible](world-bible.md) — the prose spine a world's `campaign_rules` are drafted from
- [Authoring a world](../flows/author-a-world.md) — how an original world is set up
