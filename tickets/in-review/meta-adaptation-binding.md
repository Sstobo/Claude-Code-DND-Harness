---
slug: meta-adaptation-binding
title: meta.adaptation: one-time first-PC binding + gm-adventure.sh adapt
category: enhancement
kind: afk
priority: p1
lane: agent
parentPrd: module-fidelity
blockedBy: [scene-requires-schema]
claimedBy: ss-modq26
claimedAt: 2026-08-26T19:40:00Z
changedFiles: [lib/adventure.py, tools/gm-adventure.sh, tests/test_adventure.py]
resolution: null
reviewRounds: 2
implementer: null
createdAt: 2026-08-26T18:50:00Z
updatedAt: 2026-08-26T18:50:00Z
---

## Parent

module-fidelity — prds/module-fidelity.md

## Category

enhancement

## What to build

Adaptation rulings live in `adventure.json meta.adaptation` ({matched_to_pc,
pc, decided_at, rulings: [{kind, ...context, ruling}]}). Binding fires ONCE on
first-PC-exists, copying the `opening_seed` stamp pattern
(`lib/opening_seed.py` / `identity_onboarding.py`): at import the requires
union is provisional; when a PC first exists, `gm-adventure.sh requires-report`
diffs every scene clause union against live state and prints unmet classes with
scene keys and the book quotes; the GM turns each class into one numbered
player question, then persists rulings via `gm-adventure.sh adapt --kind
party_size --ruling "..."`. Re-running the binding is a no-op once stamped
(idempotent); `adapt` remains available to add/update rulings later.

## Acceptance criteria

- [ ] `requires-report` unions clauses across scenes, dedups by kind+value, diffs against character.json/npcs.json/progress, prints unmet with quotes
- [ ] Binding stamps once; second run changes nothing (test proves idempotence)
- [ ] `adapt` writes a ruling; malformed kind rejected with the valid list
- [ ] Rulings survive re-validate and merge (schema-checked under meta)
- [ ] Fixture: solo-newcomer campaign vs AT-05 yields party_size/npc_with_party/prior_event/item_held unmet set

- [ ] (review) "Sheriff Waveshield" + "Sheriff Amelia Waveshield" union to ONE class when npcs.json holds the NPC (a fold plain lower() cannot produce)
- [ ] (review) prior_event "part-5" vs a part-1..part-4 book flags unresolved; "DDAL05-01" and "AT-04 The Cogs of Lost Time" flag other_module
- [ ] (review) requires-report binds and reports real level/equipment on an open-schema character.json
- [ ] (review) A malformed pre-existing ruling is NAMED in the report and does not block adapt from recording

## Out of scope

Rendering in the brief (requires-differ-brief). Front-matter seeding of rulings (front-matter-preservation).

## Verification

Lane: agent

## Blocked by

scene-requires-schema

---

## QA Reports

### 2026-08-26T21:01:59Z — fail [rev-adapt]
reviewed: needs-changes
- _clause_scope dedup claim false: normalize_entity_name does not fold "Sheriff Amelia Waveshield"/"Amelia Waveshield" — the docstring's own example makes two classes; entity_aliases integration effectively untested (only puck/Puck asserted)
- _MODULE_CODE_RE inverts both ways: "part-5" (typo of a real key family) reads other_module/permanent; "DDAL05-01" and "AT-04 The Cogs of Lost Time" read unresolved/typo
- _live_state bypasses character_schema.to_flat: legacy open-schema sheet -> awaiting-pc forever, silently
- One malformed pre-existing ruling raises out of BOTH requires-report and adapt — the report is where the GM would learn what is wrong; no adapt --remove
- nits: hint omits --value for scoped classes; groups/unmet share dicts so --json doubles every class

### 2026-08-26T20:51:35Z — verified [ss-modq26]
158 adventure tests pass (25 new). Live: binding stamped once to Kordan, second run is a standing report re-deciding nothing; unknown kind rejected naming the seven valid; four standing rulings persisted (party_size solo-halve-counts, Puck absent, at-04 newcomer recruit, Chronometer with Lander) and adventure.json validates after each. The improvised-three-times gap from the play-test is now a decided, persisted fact.

## History

- 2026-08-26T19:40:00Z  claimed  [ss-modq26]

- 2026-08-26T18:50:00Z  created → ready  [ss-modfid]
