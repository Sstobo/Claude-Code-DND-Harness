---
slug: appearance-migration
title: 40 of 49 NPCs cannot be illustrated — the visual_appearance field change never got a data migration
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

The README promises a gallery that "reads like one artist's sketchbook of your
story," and CLAUDE.md mandates that any image containing a character render their
stored appearance. Right now most characters cannot be rendered at all.

The boundary enforcement is genuinely good: `lib/visual_appearance.py:27-39`
fixes the 11 fields and their order, `normalize()` reorders and drops unknowns,
CLI flags are generated from `VISUAL_FIELDS` (`lib/player_manager.py:1105`,
`lib/npc_manager.py:969`) so `set-appearance` cannot write an off-schema field,
and `save_character.py:161` normalizes on create. `generate` fails closed on a
missing block (`lib/image_gen.py:295-304`) exactly as documented.

The problem is the stored data. `git log -S` shows commit `d28fb34` **changed
the field set** — out went `clothing`, `species`, `age`, `demeanor`; in came
`color`, `shirt`, `pants`, `short_description` — and shipped `_LEGACY_MAP` as a
read-time shim **with no data migration**. `tools/gm-migrate-campaigns.sh` does
not touch appearance.

Measured across the real campaigns. Only `shattered-sun` matches the CLAUDE.md
order. For `conan`, `dcc` and `whispering-wood`, every read does this:

```
DROPPED on normalize  : ['age', 'demeanor']
BLANK after normalize : ['color', 'pants', 'short_description']
```

Conan loses "young, late teens" and his entire movement description on every
single image call, and `short_description` — which the module docstring calls the
silhouette at thumbnail size — renders empty.

NPC side: 45 of 49 have a block and **36 are fully blank** (legacy-shaped empty
templates). Authored counts are conan 0/5, whispering-wood 1/36, dcc 3/3,
shattered-sun 5/5. So **40 of 49 NPCs raise `ImageGenError` on any `--character`
render** — the mandated flow for every image containing an NPC.

## Acceptance criteria

- [ ] A one-shot migration runs `normalize()` over every campaign's PC and NPC blocks, mapping legacy vocabulary forward rather than dropping it
- [ ] `age` and `demeanor` content is preserved into whichever canonical field carries it (or the field set gains a home for it), not discarded
- [ ] After migration, no PC loses fields on read; `conan` renders with his movement description intact
- [ ] The 36 blank NPC blocks are either authored or explicitly marked unauthored so `gm-npc.sh` can list what still needs a look written
- [ ] `gm-npc.sh stale`-style reporting exists for missing appearances, so this cannot silently accumulate again
- [ ] A field-set change in future requires a migration step; note it in the module doc

## Out of scope

Authoring 36 NPC looks by hand in this ticket. Producing the worklist and the
migration is the deliverable; authoring can follow.

## Verification

Lane: agent. Count renderable NPCs before and after: 9/49 → 49/49 (or → 13/49
plus an explicit authored-needed list).

## Blocked by

Nothing.

---

## QA Reports

## History

- 2026-08-27T00:00:00Z  created → needs-triage  [readme-audit]
