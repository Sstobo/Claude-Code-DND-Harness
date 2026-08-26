---
slug: deadlines-into-clocks
title: Typed deadlines extracted and materialized into threat clocks
category: enhancement
kind: afk
priority: p1
lane: agent
parentPrd: module-fidelity
blockedBy: [scene-requires-schema]
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

`deadlines` per scene: [{what, when, in, set_in, due_before, miss}] — `miss` is
mandatory when the book prints a miss branch (AT-05 does: 9 days overland, 3
mounted, 85 gp horse). Converter emits them; `suggest_requires`-style regex
sweep flags timing prose the converter skipped ("by dawn", "before sun-up", "N
days"). At import (and on adapt-binding for already-imported campaigns) each
deadline materializes into a threat clock via `lib/threat_clocks.py add_clock`
(advance_on:"time", segments from `ticks_from_duration(in)`, consequence from
`miss`) so `gm-time.sh` moves it and a filled clock fires its consequence. The
dossier horizon renders open deadlines whose `set_in` scene is visited,
regardless of pointer position. Re-import must not duplicate clocks
(idempotent by deadline identity).

## Acceptance criteria

- [ ] AT-05 1.2 yields the Salty Siren deadline typed, with the book's miss branch
- [ ] Import materializes it: threat-clocks.json gains a time clock + consequence; `gm-time.sh --duration "1 day"` advances it; filling fires
- [ ] Re-import/re-bind creates no duplicate clock
- [ ] Dossier horizon lists open deadlines with due/miss once set_in is visited
- [ ] Regex sweep reports timing prose in at least the 8 AT-05 scenes known to carry it

## Out of scope

Event-advanced clocks, pressure-not-rail prose rules (diegetic-adaptation-craft).

## Verification

Lane: agent

## Blocked by

scene-requires-schema

---

## QA Reports

## History

- 2026-08-26T18:50:00Z  created → ready  [ss-modfid]
