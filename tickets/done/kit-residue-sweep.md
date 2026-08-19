---
slug: kit-residue-sweep
title: Sweep dead kit residue from scene context and docs
category: enhancement
kind: afk
priority: p2
lane: agent
parentPrd: 5e-native-fork
blockedBy: [unconditional-5e-gates]
claimedBy: ss-5efork
claimedAt: 2026-08-19T18:41:05Z
changedFiles: [lib/session_manager.py, tests/test_kit_block.py, docs/modules/game-core-and-world-kit.md, docs/modules/scene-context.md, docs/conventions/the-dream.md, docs/flows/onboarding-and-death.md, README.md]
resolution: dead KIT block gone from scene context; every current-behavior kit claim swept from docs incl. README
reviewRounds: 3
implementer: null
createdAt: 2026-08-19T15:38:00Z
updatedAt: 2026-08-19T19:14:00Z
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

- [x] Scene context output contains no KIT block (verified via gm-session.sh context on a scratch campaign)
- [x] No doc describes per-book kits or STEP-0 KIT deference as current behavior
- [x] Suite passes (bar the known pre-existing failure)

## Verification

Lane: agent

## Blocked by

unconditional-5e-gates

---

## QA Reports

## History

- 2026-08-19T15:38:00Z  created → needs-triage (source: review-5e-gates cross-ticket findings)  [ss-5efork]
- 2026-08-19T18:41:05Z  triaged → claimed  [ss-5efork]
- 2026-08-19T18:51:33Z  doc-grounding confirmed  [ss-5efork]

### 2026-08-19T18:59:04Z — verified [ss-5efork]
KIT block + dead signature-systems branches removed from get_full_context (campaign_rules renders unconditionally, output unchanged); scene context clean in scratch campaign; kit tests rewritten to assert absence; owning docs swept + restamped incl. stale anchors; docs/log.md correctly left as historical record. Suite: only the environmental failure.
- 2026-08-19T18:59:04Z  verified → in-review  [ss-5efork]

### 2026-08-19T19:04:20Z — fail [review-kit-residue]
reviewed: needs-changes (code clean + parity proven in 4 shapes vs HEAD; one doc line must-fix)
- MUST docs/flows/onboarding-and-death.md:94-96 — still claims create-character branches on the KIT block (no such branch exists; verified). Last doc presenting KIT as live.
- NIT scene-context.md:125 anchor off by one (58-66, not 57-66; pre-existing stale).
- NIT scene-context.md stale verified: stamp points at a body that no longer exists.
Informational: truthy-non-dict campaign_rules prints an empty-bodied header — pre-existing, unchanged.
- [x] (review) onboarding-and-death.md carries no kit-branch claim; repo grep for KIT-as-current returns only history entries
- [x] (review) scene-context anchor 58-66; stale verified stamp dropped

### 2026-08-19T19:07:17Z — verified (fix round) [ss-5efork]
onboarding-and-death.md kit claims rewritten (both the flagged step-3 line and a second one at line 74 it found itself); become() anchor fixed; scene-context anchor + stale verified stamp fixed; repo-wide KIT-as-current grep clean (history/past-tense/absence-asserts only). Followup review dispatched.
- 2026-08-19T19:07:17Z  fix round verified — followup review dispatched  [ss-5efork]

### 2026-08-19T19:11:15Z — fail [review-kit-residue]
reviewed: needs-changes (round 2) — checks 1-2 pass; repo-wide criterion fails broadly:
- MUST README.md:41,82,97,237 — user-facing per-book-kit claims, flatly false since 575f5cd; README has no OKF frontmatter so drift never surfaces it.
- NIT onboarding-and-death.md keeps a verified: stamp older than its new generated: (inconsistent with the scene-context treatment).
- Correction: the "ESPIONAGE KIT" allowance was a sibling-repo hit, not in this fork.
- Follow-up (filed separately): player-character.md:52-56 + play-turn.md:30 dead-branch kit phrasing; gm-session.sh:75 + gm-player.sh:96 name ruleset.json.
- [x] (review) README.md carries no per-book-kit claim and no ruleset.json kit instruction
- [x] (review) no doc ships a verified: stamp older than its generated: stamp

### 2026-08-19T19:14:00Z — pass [ss-5efork orchestrator close]
Round-2 review passed checks 1-2; the two remaining items (README kit claims, stamp hygiene) fixed and verified directly by orchestrator: README has zero kit/ruleset hits, no doc ships a verified: stamp older than its generated:, repo-wide KIT-as-current grep returns history/past-tense/absence-asserts only. Round cap reached; narrow mechanical residue closed by direct verification per the spells-levelup precedent.
- 2026-08-19T19:14:00Z  done → committed  [ss-5efork]
