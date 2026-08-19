---
slug: import-module-command
title: /import-module command + converter agent + SRD monster resolver
category: enhancement
kind: afk
priority: p1
lane: agent
parentPrd: import-module
blockedBy: [module-text-spine, adventure-store]
claimedBy: null
claimedAt: null
changedFiles: []
resolution: null
reviewRounds: null
implementer: null
createdAt: 2026-08-19T18:05:00Z
updatedAt: 2026-08-19T18:05:00Z
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

- [ ] `import-module.md` command doc covers the full pipeline in order, includes the campaign-switch guard, states the 6-agent cap and `claude-opus-4-8[1m]` model both in orchestration and inside the agent-prompt template, and never invokes RAG/`prepare`/ruleset drafting.
- [ ] `module-converter.md` agent definition specifies the exact scene schema (same field names as `lib/adventure.py` validation) and raw-JSON-only output.
- [ ] `resolve-monsters` maps a known SRD name (e.g. "Harpy") to its `srd_index` and leaves an unknown homebrew name with its embedded stat_block; runnable check in tests (network may be mocked/cached).
- [ ] Grep check: `/import` (.claude/commands/import.md) and the RAG libs are untouched by this ticket.

## Out of scope

Running the end-to-end import on the real PDF (e2e-whispering-wood, HITL). Changes to /import or RAG.

## Verification

Lane: agent

## Blocked by

module-text-spine, adventure-store

---

## QA Reports

## History

- 2026-08-19T18:05:00Z  created → ready  [ship-it]
