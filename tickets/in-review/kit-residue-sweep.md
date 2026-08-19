---
slug: kit-residue-sweep
title: Sweep dead kit residue from scene context and docs
category: enhancement
kind: afk
priority: p2
lane: agent
parentPrd: 5e-native-fork
blockedBy: [unconditional-5e-gates]
claimedBy: null
claimedAt: null
changedFiles: []
resolution: null
reviewRounds: null
implementer: null
createdAt: 2026-08-19T15:38:00Z
updatedAt: 2026-08-19T15:38:00Z
---

## Parent

5e-Native Fork (prds/5e-native-fork.md)

## Category

enhancement

## What to build

Cross-ticket findings from the unconditional-5e-gates review:
- lib/session_manager.py:613-625 still assembles a `--- KIT ---` block into
  scene context; nothing reads it now that the skills' STEP-0 guards are gone.
  Remove the dead output (and any test asserting it).
- docs/log.md:47 and any surviving passage in docs/modules/game-core-and-world-kit.md
  still describe the per-book kit / STEP-0 KIT deference. Sweep to match the
  5e-native reality; restamp rewritten bodies.

## Acceptance criteria

- [ ] Scene context output contains no KIT block (verified via gm-session.sh context on a scratch campaign)
- [ ] No doc describes per-book kits or STEP-0 KIT deference as current behavior
- [ ] Suite passes (bar the known pre-existing failure)

## Verification

Lane: agent

## Blocked by

unconditional-5e-gates

---

## QA Reports

## History

- 2026-08-19T15:38:00Z  created → needs-triage (source: review-5e-gates cross-ticket findings)  [ss-5efork]
