---
slug: module-fidelity
title: Module fidelity — scene contracts, adaptation, deadlines, and the craft layer
status: active
version: 1
supersedes: null
createdAt: 2026-08-26T18:45:00Z
updatedAt: 2026-08-26T18:45:00Z
---

## Problem Statement

A converted module runs, but nothing checks whether its scenes are POSSIBLE in
the campaign playing them. AT-05 scene 1.2 assumes a returning four-person
party, a sprite companion, and an artifact from the prior module; the campaign
has a solo newcomer. The mismatch lived only as prose inside `gm_notes`, so the
GM improvised over the gap silently, every beat, three separate times — each
improvisation inventing new canon to cover the same hole. Deadlines ("the ship
sails at dawn") are buried in prose blobs, invisible to every tool. The scene
pointer models a chain, but Part 2 is a hub of 17 visitable locations with no
transitions; `advance` from the forge lands the party under arrest because
`_next_key` takes `transitions[0]` unconditionally. The module's front matter —
party size, milestone rule, a live mechanic carried in from AT-02 — is sliced
and then discarded by design. And the converter itself committed the sin the
harness guards against: it fabricated 140 chars of plausible prose for a bare
part heading.

Diagnosis provenance: a four-lens review (veteran DM, module-fidelity engineer,
adversarial inquisitor, codebase mapper) of the 2026-08-26 play-test, synthesized
in session; the retrieval-layer fixes it mandated shipped as `2f321d1`.

## Solution

Teach the import to extract what each scene ASSUMES and OFFERS — typed
`requires` clauses, typed `deadlines`, scene kinds, portable clues, fixed-vs-
fluid marks — and teach the runtime to diff those against live campaign state:
a one-time adaptation binding when the PC first exists (never re-improvised per
beat), deadlines materialized into threat clocks, unmet assumptions surfaced as
one explicit GM-private note, and every adaptation resolved diegetically in the
fiction. The converter gets defect fixes (no fabrication, resolvable NPC names,
honest page numbers, promoted uncertainty flags) and the original scene slices
become reachable per scene instead of orphaned.

## User Stories

1. As a player running a published module, I want the GM to know what each
   scene assumes about my party, so a solo newcomer gets a deliberately adapted
   scene instead of silent per-beat improvisation.
2. As a player, I want book deadlines to be real pressure — visible to the GM
   while I shop — so missing the dawn sailing has the book's own consequence.
3. As a player wandering off the written path, I want the module's information
   to reach me wherever I am, so a faithful run never feels like a corridor.
4. As the GM, I want to know which module elements are sacred (facts,
   geography, timetable, ending) and which are staging, so a deviation is a
   choice with a known class, not a guess.
5. As the GM, I want the original scene text one pointer away, so the
   converter's summary is never mistaken for the book's words.

## Implementation Decisions

- `requires` is a typed clause list on the scene schema (`lib/adventure.py`
  SCENE_FIELDS), closed kind set: `party_size`, `npc_with_party`, `npc_known`,
  `item_held`, `prior_event`, `pc_level`, `narrative` (permanently unsatisfied).
  Every clause quotes the module text evidencing it. The converter emits them;
  a deterministic regex cross-check in `lib/adventure_import.py`
  (`suggest_requires`) catches converter omissions at import.
- The differ is pure Python against existing files (character.json, npcs.json
  `is_party_member`/`events`, adventure progress). No LLM in the loop.
- Adaptation rulings live in `adventure.json meta.adaptation`, bound ONCE on
  first-PC-exists via the `opening_seed` stamp pattern; `gm-adventure.sh adapt`
  persists rulings; the ADVENTURE block renders the standing ruling beside any
  unmet clause. Never in facts.json (that channel already proved leaky).
- `deadlines` is a typed per-scene list ({what, when, in, set_in, due_before,
  miss}); import materializes each into a threat clock (`threat_clocks.py`
  advance_on:"time") so `gm-time.sh` moves them; the dossier horizon renders
  open deadlines regardless of pointer position.
- `scene.kind`: beat | hub | site | gate | chapter. `progress` gains `visited`,
  `spent` (content used out of position), `history` (append-only), `off_book`.
  `_next_key` prefers spine order; all transitions render as offers with their
  `when` (partially shipped in the dossier's STORY COMING UP).
- `scene.source` points at the retained `module-work/scene-<key>.txt` slice
  (path + sha); `gm-adventure.sh source [key]` prints it; gm_notes relabeled
  as converter-summary; converter copies GM text verbatim below a length
  threshold and stamps which it did.
- Front matter (`scene-front.txt`) lands in `meta.front` (background, recap,
  progression rule, start date, party-size line) instead of being discarded;
  `meta.levels` derived from it.
- Converter defects: bare-heading parts get the heading only (no fabricated
  prose — flagged instead); scene NPC names canonicalized through
  `lib/integrity_gate.py` (module path never runs it today; nine names
  unresolvable in AT-05 including scene 1's tavernkeeper); `pages` corrected
  for printed-vs-PDF offset; `[extraction unclear: ...]` markers promoted to
  `scene.conversion_flags` and listed in the import summary.
- Craft layer: per-scene `clues` (portable information — what can be LEARNED
  here, deliverable anywhere, delivery marked [ADAPTED]); per-element
  `fidelity: fixed|fluid` marks (fixed = facts, identities, geography,
  villain timetable, ending; fluid = staging, order, delivery); gm-craft +
  CLAUDE.md prose rules — adaptation resolved diegetically, prep ritual at
  session start (must honor / will test / not contradict + one strong start),
  lookahead framed as pressure never rail.
- AT-05 (whispering-wood) is re-imported or migrated as the verification
  vehicle for every extraction-side ticket.

## Testing Decisions

- Agent lane: schema validation, differ correctness against fixture campaign
  states, one-time binding idempotence, clock materialization, `_next_key`
  spine preference, front-matter capture, converter-output validators
  (fabrication guard, name resolution, conversion_flags), clue/fidelity field
  shape. Prior art: tests/test_adventure*.py, tests/test_module_world_index.py.
- Manual lane: the diegetic-adaptation prose rules (a human reads a scene and
  judges the seams invisible), and the re-imported AT-05 spot-check.

## Out of Scope

- The dossier/chronicle/delta architecture (shipped, `2f321d1`).
- Retrieval-layer caps and fact-category gating (shipped, `2f321d1`).
- `--origin` flags on state tools (chronicle stamps cover provenance for now).
- Story planning / pre-authored arcs (rejected by design — the-dream.md).
- Chronicle compression rituals (needed only after many sessions).
- The stale action-menu test and the d28fb34 appearance-schema test breaks
  (other session's surface).

## Further Notes

Review evidence: the party-mismatch class was improvised three times (facts of
08-19 and 08-25/26); scene 2.17 carries 16KB of text (dossier renders whole);
Part 2 has 12 transition-less scenes; 24 of 72 page entries are off by exactly
2; `meta.levels` reads "1-3" for a level-5 module. The DM lens ranked portable
clues the single most valuable missing capability; the inquisitor rated scene
contracts the only proposed system that PREVENTS (rather than records) a
witnessed failure class.
