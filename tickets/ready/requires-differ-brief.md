---
slug: requires-differ-brief
title: The differ: requires vs live state, unmet + standing ruling in the brief
category: enhancement
kind: afk
priority: p1
lane: agent
parentPrd: module-fidelity
blockedBy: [scene-requires-schema, meta-adaptation-binding]
claimedBy: null
claimedAt: null
changedFiles: []
resolution: null
reviewRounds: 0
implementer: null
createdAt: 2026-08-26T18:50:00Z
updatedAt: 2026-08-26T18:50:00Z
---

## Parent

module-fidelity — prds/module-fidelity.md

## Category

enhancement

## What to build

Pure-Python differ (no LLM): evaluate the CURRENT scene's `requires` against
live state — party_size vs character.json + npcs.json is_party_member count;
npc_with_party vs is_party_member; npc_known vs non-empty NPC events;
item_held vs character.json equipment through `resolve_entity_name`
(lib/entity_aliases.py); prior_event vs progress.completed (out-of-book ids
never satisfied); pc_level vs character.json; narrative always unsatisfied.
Render in the ADVENTURE block and dossier NOW block: one line per unmet clause
with the book quote, and beside it the standing ruling from meta.adaptation
when one exists ("unmet: party of 4 (\"Greetings, heroes\") — RULING: solo,
halve counts, keep DCs"). Zero unmet clauses adds zero lines. GM-private
framing: the note instructs adaptation, never narration of the mismatch.

## Acceptance criteria

- [ ] Each of the seven kinds evaluates against the documented file, fixture-tested satisfied AND unsatisfied
- [ ] Unmet clause without ruling renders quote + "no standing ruling — bind one via gm-adventure.sh adapt"
- [ ] Unmet clause with ruling renders both; satisfied scene renders nothing
- [ ] item_held matches through entity aliases (not raw string equality)
- [ ] Live AT-05 scene 1.2 + whispering-wood state shows the four real unmet clauses

**Implementation notes from review tracing (2026-08-26):** every consumer reads
`scene.get('requires', [])` — the every-scene-carries-every-field invariant is
FALSE on disk (whispering-wood: 0/43 scenes carry the key, and merge only
defaults it on genuinely new keys). And a `prior_event` id may be a scene key,
a foreign module code (at-04), or a converter typo of a scene key — the differ
treats an id that matches no completed scene and no known module pattern as
unmet-with-a-flag, never as a crash or a silent pass.

## Out of scope

One-scene-ahead horizon (shipped in dossier). Diegetic prose rules (diegetic-adaptation-craft).

## Verification

Lane: agent

## Blocked by

scene-requires-schema, meta-adaptation-binding

---

## QA Reports

## History

- 2026-08-26T18:50:00Z  created → ready  [ss-modfid]
