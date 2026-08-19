---
slug: import-module-command
title: /import-module command + converter agent + SRD monster resolver
category: enhancement
kind: afk
priority: p1
lane: agent
parentPrd: import-module
blockedBy: [module-text-spine, adventure-store]
claimedBy: ss-imod01
claimedAt: 2026-08-19T18:45:00Z
changedFiles: [.claude/commands/import-module.md, .claude/agents/module-converter.md, lib/adventure.py, tests/test_adventure.py]
resolution: /import-module command + module-converter agent + idempotent SRD monster resolver, 47 tests
reviewRounds: 2
implementer: null
createdAt: 2026-08-19T18:05:00Z
updatedAt: 2026-08-19T19:15:00Z
---

## Parent

/import-module — structured adventure-module import (prds/import-module.md)

## Category

enhancement

## What to build

Three artifacts:

1. **`.claude/commands/import-module.md`** — the orchestration doc the main
   agent follows. Steps: create/switch campaign (`gm-campaign.sh`, same guard
   pattern as `/import` Step 2); run `adventure_import.py slice`; fan out
   converter agents over the scene slices — **max 6 agents, model
   `claude-opus-4-8[1m]`, and the 6-cap stated inside each agent prompt**;
   each agent returns scene-batch JSON; `adventure.py init` + `merge` +
   `validate`; persist extracted NPCs into `npcs.json` via `gm-npc.sh`;
   resolve monsters (below); print an import summary (scene count, NPCs,
   monsters resolved vs embedded). Explicitly: no `gm-extract.sh prepare`, no
   embeddings, no ruleset drafting. `/import` stays untouched.
2. **`.claude/agents/module-converter.md`** — converter agent definition:
   reads its assigned `scene-<key>.txt` slices in full, emits JSON matching
   the `lib/adventure.py` scene schema exactly (read_aloud verbatim from
   boxed text, gm_notes summarized faithfully, encounters/monsters/treasure/
   checks/transitions), returns raw JSON only.
3. **SRD monster resolution** — a helper (in `lib/adventure.py` or a small
   `resolve-monsters` CLI op) that, post-merge, looks up each extracted
   monster name against the dnd5eapi monster index via
   `features/dnd-api/dnd_api_core.py fetch()`; on a name match, stores
   `srd_index`; otherwise keeps the extracted `stat_block` embedded.

## Acceptance criteria

- [x] `import-module.md` command doc covers the full pipeline in order, includes the campaign-switch guard, states the 6-agent cap and `claude-opus-4-8[1m]` model both in orchestration and inside the agent-prompt template, and never invokes RAG/`prepare`/ruleset drafting.
- [x] `module-converter.md` agent definition specifies the exact scene schema (same field names as `lib/adventure.py` validation) and raw-JSON-only output.
- [x] `resolve-monsters` maps a known SRD name (e.g. "Harpy") to its `srd_index` and leaves an unknown homebrew name with its embedded stat_block; runnable check in tests (network may be mocked/cached).
- [x] Grep check: `/import` (.claude/commands/import.md) and the RAG libs are untouched by this ticket.
- [x] (review) Running Steps 2-6 of import-module.md as separate shell invocations resolves every $CAMPAIGN_DIR reference (no bare /module-work paths — re-derive per block).
- [x] (review) module-converter.md states slice text is data, never instructions, and what to do with directive-looking text in a slice.
- [x] (review) resolve_monsters leaves srd_index unset on a monster already carrying a stat_block (counts it embedded), even on an SRD name collision.
- [x] (review) The resolver summary distinguishes unresolved monsters WITH a stat_block from unresolved monsters with none.

## Out of scope

Running the end-to-end import on the real PDF (e2e-whispering-wood, HITL). Changes to /import or RAG.

## Verification

Lane: agent

## Blocked by

module-text-spine, adventure-store

---

## QA Reports

### 2026-08-19T19:55:00Z — pass [review2-import-module-cmd]
reviewed: perfect (followup round 2). All four blocks re-derive CAMPAIGN_DIR; data-not-instructions rule verified line-by-line; resolver precedence/idempotency/unstatted-warning confirmed with test line refs; scope clean.

### 2026-08-19T19:45:00Z — verified (fix round) [ss-imod01]
CAMPAIGN_DIR re-derived per block; data-not-instructions section added to converter agent (with in-fiction vs dropped handling + gm_notes note); resolver: srd_index popped first (idempotent), statted monsters skipped (no dual fields), unstatted counted+named separately with loud CLI warning; save skipped when unchanged; lazy index fetch. 47 tests pass; CLI demo covers all three monster cases correctly.

### 2026-08-19T19:30:00Z — fail [review-import-module-cmd]
reviewed: needs-changes
- import-module.md: $CAMPAIGN_DIR set in Step 2's block but used in later separate blocks — shell state doesn't persist between Bash calls → bare "/module-work" paths. Re-derive per block (import.md pattern).
- module-converter.md: no treat-slice-text-as-data rule (criterion d unmet).
- adventure.py resolver: SRD name collision overrides a deliberate homebrew stat_block (both attached, no precedence) — skip statted monsters; `embedded` count/message covers unstatted monsters as if statted.
- Nits: sys.path leak (matches repo pattern), unconditional save, stale srd_index never cleared.
Command syntax vs actual scripts all verified correct; schema fidelity complete + test-guarded.

### 2026-08-19T19:15:00Z — verified [ss-imod01]
- 41 tests pass (7 new resolver tests, network fully mocked; doc-shape guard ties module-converter.md to SCENE_FIELDS); collect-only exit 0.
- Live bonus: 334-monster SRD index; Harpy/Harpies→harpy, Wolves→wolf, Bone Kite→None. CLI demo: resolved/embedded counts + unresolved list correct, srd_index persisted, homebrew stat_block kept.
- Deviations accepted: /monsters endpoint (2014 SRD namespace via fetch BASE_URL — /api/monsters would bypass it); "ves"→f singularization added from live failure.
- Scope grep: import.md, features/dnd-api, lib/rag untouched.

## History

- 2026-08-19T19:55:00Z  review perfect → done, committed  [ss-imod01]

- 2026-08-19T19:15:00Z  verified → in-review  [ss-imod01]
- 2026-08-19T18:47:00Z  doc-grounding confirmed  [ss-imod01]
- 2026-08-19T18:45:00Z  claimed  [ss-imod01]
- 2026-08-19T18:05:00Z  created → ready  [ship-it]
