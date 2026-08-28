---
slug: sheet-one-constructor
title: One constructor for the sheet — a PC with no ability scores must be impossible
category: bug
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

bug

## What to build

Three writers hold three independent notions of "a complete sheet." Replace them
with one `new_sheet()` that fills every canonical key, and fix the two paths that
produce a crippled character.

**The live casualty.** `dcc` is an actively-played PC with `stats: {}` — level 1,
HP 5/10, standing in a goblin warren, and **zero ability scores**. It came from
`identity_onboarding.original()` (`lib/identity_onboarding.py:68`), whose own
comment reads `"attributes": {},  # inferred silently against the active kit`.
Nothing infers them. No code fills that dict, ever. Consequences measured:

- Initiative is a flat `1d20+0` forever. `lib/combat_manager.py:118-124` catches
  the `TypeError` from a missing DEX and returns modifier 0, silently. The other
  three campaigns roll +3, +1, +1.
- `save_character.py:74` does `calculate_modifier(stats.get(stat, 10))`, so every
  save computes from a phantom 10 across the board.

**`become()` loses half the character.** `lib/player_manager.py:737-742` copies
only `npc['character_sheet']`. `visual_appearance` lives at the NPC top level
(`lib/npc_manager.py:106`) and is therefore **dropped** — so a promoted party
member has no stored look and `gm-image.sh generate --character` fails closed on
them immediately (`lib/image_gen.py:295-304`). Also lost: `gold`, `id`,
`alignment`, `background`, `bonds`, `ideals`, `flaws`, `traits`, `notes`.
Carried in but read by nothing on the PC path: `attack_bonus`, `damage`.

**And the promotion path is dead on arrival anyway.** 0 of 49 NPCs have a
`character_sheet` and 0 of 49 have a `stats` block, so `_party_sheet_for_npc`
returns pure `PARTY_MEMBER_DEFAULTS` (`lib/npc_manager.py:29`) for every one of
them: all abilities hardcoded to 10, all saves 0. Every one of the 49 promotes to
an identical AC 10, HP 10/10 Commoner. That is the Death Protocol's primary
hand-off route.

Latent crash on the same path: `lib/npc_manager.py:512` does `hp['current']` on
`existing_sheet.get('hp', {…})`. A sheet storing `hp` as an int — which
`lib/npc_stats.py:60` writes for the proxy — raises `TypeError: 'int' object is
not subscriptable`. Confirmed by execution.

## Acceptance criteria

- [ ] A single `new_sheet()` fills every canonical key from `character_schema`; `save_character.py`, both `identity_onboarding` builders, and `become()` all go through it
- [ ] A PC cannot be persisted with empty or missing `stats` — either the kit inference the comment promises is implemented, or a real array is assigned and the sheet records that it was defaulted
- [ ] `dcc`'s existing sheet is backfilled and its initiative modifier stops being a silent 0
- [ ] `become()` carries `visual_appearance`, `gold`, `id`, and the identity fields across; a promoted party member is immediately illustratable
- [ ] `lib/npc_manager.py:512` handles an int `hp` without raising
- [ ] `modify_hp` (`lib/player_manager.py:449`) guards a missing `hp` key the way `kill_character` already does at `:599` — same file, currently inconsistent

## Out of scope

Authoring the 49 NPC `character_sheet` blocks. Making promotion produce a valid
sheet from whatever exists is the deliverable.

## Verification

Lane: agent. Promote a real NPC in a sandboxed campaign copy and diff the
resulting `character.json` against the canonical key set.

## Blocked by

sheet-validate-on-write

---

## QA Reports

## History

- 2026-08-27T00:00:00Z  created → needs-triage  [readme-audit]
