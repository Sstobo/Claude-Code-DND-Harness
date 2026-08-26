---
slug: scene-requires-schema
title: Typed requires clauses: schema, validation, converter contract, regex cross-check
category: enhancement
kind: afk
priority: p1
lane: agent
parentPrd: module-fidelity
blockedBy: []
claimedBy: ss-modq26
claimedAt: 2026-08-26T18:43:31Z
changedFiles: [lib/adventure.py, lib/adventure_import.py, .claude/agents/module-converter.md, tests/test_adventure.py, .claude/commands/import-module.md]
resolution: typed requires clauses (7 kinds, evidence-quote rule) with validation naming the scene; unhashable-kind crash fixed; converter contract + Step-5 template both ask for the field with mutation-checked drift guards; regex sweep descoped to requires-sweep-hardening after review found it unsound
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
- [x] Existing 43 AT-05 scenes still validate (absent requires == [])
- [x] Converter doc carries the closed kind set + evidence-quote rule

- [x] (review) A converter batch whose kind is a list/dict/number is rejected with the scene key named; merge CLI exits non-zero with no Traceback
- [x] (review) No reference to suggest_requires/requires_gaps remains in lib/, tests/, or agent docs
- [x] (review) The converter doc's kind table is guarded the same way SCENE_FIELDS is (REQUIRES_KINDS drift test)

## Out of scope

The differ (requires-differ-brief), adaptation storage (meta-adaptation-binding), deadlines, clues.

## Verification

Lane: agent

## Blocked by

None.

---

## QA Reports

### 2026-08-26T19:39:51Z — pass [rev-requires-2]
reviewed: perfect (round 2)
Notes (non-blocking): the per-kind FIELD half of the doc-drift guard is a bare substring test — name/id/note occur as ordinary English, so a field rename to another common word passes vacuously; the kind half bites (mutation-verified).

### 2026-08-26T19:20:33Z — fail [rev-requires]
reviewed: needs-changes (AC 1,2,4,5 verified; AC 3 unmet — sweep unwired)
- adventure.py:132 unhashable kind -> TypeError raw traceback through the real merge CLI path
- requires_gaps has no caller anywhere; converter doc promises a sweep nothing runs; import-module.md Step-5 template omits requires entirely
- party_size cover never compares numbers (min:1 covers min:2); npc_known cover is surname-only (sibling covers sibling)
- _quote can emit ellipses-only notes that validate; the quote-containment test is vacuous on exactly that case
- nits: case-insensitive short-name matching, bare-noun party_size noise, _SWEPT_IDENTITY KeyError trap, seed-dependent determinism test, unguarded REQUIRES_KINDS doc table, sweep tests in the wrong suite
DECISION (user pre-authorized): descope the sweep to tickets/needs-triage/requires-sweep-hardening.md; keep schema+validator+contract; fix the crash + doc guard.

### 2026-08-26T18:56:52Z — verified [ss-modq26]
78/78 adventure tests pass; adversarial checks: unknown kind + missing note rejected with scene key named; sweep on the REAL 1.2 slice file finds npc_known+party_size+prior_event; live 43-scene adventure.json validates with zero requires keys.

## History

- 2026-08-26T19:26:34Z  fix round 1 returned (descope complete, crash fixed); scope expanded one file: import-module.md Step-5 template omits requires — reviewer-flagged as the gap that leaves the field inert on every real import  [ss-modq26]

- 2026-08-26T18:43:31Z  claimed  [ss-modq26]

- 2026-08-26T18:50:00Z  created → ready  [ss-modfid]
