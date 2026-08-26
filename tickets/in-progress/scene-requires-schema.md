---
slug: scene-requires-schema
title: Typed requires clauses: schema, validation, converter contract, regex cross-check
category: enhancement
kind: afk
priority: p1
lane: agent
parentPrd: module-fidelity
blockedBy: []
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

Add `requires` to the scene schema (`lib/adventure.py` SCENE_FIELDS): a list of
typed clauses, closed kind set — `party_size` {min}, `npc_with_party` {name},
`npc_known` {name}, `item_held` {name}, `prior_event` {id}, `pc_level` {min},
`narrative` {note} (permanently unsatisfied by design). Every clause carries a
`note` quoting the module text that evidences it. `validate_adventure` enforces
the kind set and per-kind required fields; stubs get `[]` free. Extend the
converter contract (`.claude/agents/module-converter.md`) with the kind list and
the quote rule. Add deterministic `suggest_requires(text)` to
`lib/adventure_import.py` — regexes for second-person-plural/"heroes"/"each
character" (party_size), `refer to AT-\d\d` (prior_event), names seen in earlier
scenes (npc_known) — and have the import step report clauses the regex found
that the converter did not emit. AT-05 scene 1.2 is the fixture: it must yield
party_size, npc_with_party Puck, npc_known Waveshield, item_held Chronometer,
prior_event at-04, pc_level 5.

## Acceptance criteria

- [ ] `requires` accepted and validated on every scene; unknown kind or missing per-kind field fails `validate_adventure` with the scene key named
- [ ] `suggest_requires` finds party_size + prior_event + npc_known signals in the AT-05 1.2 slice text, deterministically (no LLM)
- [ ] Import flow reports converter-vs-regex gaps; a converter emitting `[]` for 1.2 is caught
- [ ] Existing 43 AT-05 scenes still validate (absent requires == [])
- [ ] Converter doc carries the closed kind set + evidence-quote rule

## Out of scope

The differ (requires-differ-brief), adaptation storage (meta-adaptation-binding), deadlines, clues.

## Verification

Lane: agent

## Blocked by

None.

---

## QA Reports

## History

- 2026-08-26T18:50:00Z  created → ready  [ss-modfid]
