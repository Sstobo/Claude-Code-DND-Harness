---
slug: fixed-vs-fluid-marks
title: Per-element fidelity marks: sacred vs staging
category: enhancement
kind: afk
priority: p2
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

Converter marks module elements `fidelity: fixed | fluid`. Fixed = true facts,
identities, geography, the villain's timetable, the ending shape. Fluid =
scene order, staging, who delivers a clue, encounter dressing. Applies to:
scenes (default fluid; gate/chapter scenes and finale default fixed), npcs
(identity fixed, location fluid unless geographically bound), clues
(fact fixed, delivery fluid — clues ticket's `fixed` field folds into this
vocabulary), deadlines (fixed by default). The differ/brief renders the CLASS
when a deviation is recorded: a `spend` or off-book delivery of a fluid
element notes [ADAPTED — fluid, no fidelity cost]; touching a fixed element
warns [FIXED — this changes the book's truth; chronicle it as INVENTED, not
ADAPTED]. The two-sentence fidelity answer ("every name is the book's, two
conversations relocated, nothing fixed contradicted") becomes
`gm-adventure.sh fidelity` reading marks + spent + chronicle stamps.

## Acceptance criteria

- [ ] fidelity field validates on scenes/npcs/clues/deadlines with the stated defaults
- [ ] AT-05: Grimhammer relocation classifies fluid; moving Eldoria itself (geography) classifies fixed
- [ ] spend/clue-drop of fluid vs fixed render the two distinct notes
- [ ] `fidelity` verb prints the campaign fidelity summary from live data

## Out of scope

Blocking fixed deviations (GM freedom stands; the mark informs, never forbids).

## Verification

Lane: agent

## Blocked by

scene-requires-schema

---

## QA Reports

## History

- 2026-08-26T18:50:00Z  created → ready  [ss-modfid]
