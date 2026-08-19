---
slug: import-module
title: /import-module — structured adventure-module import (no RAG)
status: active
version: 1
supersedes: null
createdAt: 2026-08-19T18:00:00Z
updatedAt: 2026-08-19T18:00:00Z
---

## Problem Statement

The harness can only ingest a book as prose-for-RAG (`/import`), which suits
novels: index the text, improvise in the world. A published D&D adventure
module (50–100 pages) is a different artifact — it has keyed scenes ("1.4
Passage to Eldoria"), an intended order, encounters with stat blocks,
read-aloud boxes, DCs, and treasure. RAG retrieval loses that spine, so the GM
can search the book but cannot *run the adventure*: it never knows which scene
the party is in or what the module says happens next.

## Solution

A new `/import-module <pdf>` path that converts the module once, fully, into
structured JSON the harness runs from directly. No embeddings, no vector
store. Pipeline: PDF → clean text (two-column-aware extraction) →
deterministic spine detection from keyed headers → a team of large-context
agents (max 6, `claude-opus-4-8[1m]`) each reads scene slices and emits schema
JSON → merge/validate into `adventure.json` plus the existing campaign stores
(NPCs into `npcs.json`; monsters as SRD API references where the creature is
SRD, embedded stat blocks otherwise). At runtime, scene context gains an
ADVENTURE block (current scene's GM notes + what the book says comes next) and
`gm-adventure.sh` moves a progress pointer (`status` / `advance` / `jump`).

`/import` (the novel/RAG path) is untouched.

## User Stories

1. As the player, I want to drop a module PDF and say `/import-module`, so that the campaign that comes out actually runs the adventure as written.
2. As the GM, I want the current scene's read-aloud, GM notes, encounters, and DCs in scene context, so that I run the book's content instead of improvising over search results.
3. As the GM, I want to know the module's intended next scene, so that pacing and transitions follow the adventure while the party can still go off-script.
4. As the GM, I want extracted monsters resolved to SRD stat blocks via the dnd5eapi (per the 5e-native fork), so that combat numbers are real.

## Implementation Decisions

- **Text extraction:** extend `lib/content_extractor.py` with a two-column
  mode (crop each page into left/right halves via pdfplumber before
  `extract_text`, with a single-column fallback when a page isn't two-column).
  Output keeps page markers (`--- page N ---`) so scenes cite their source pages.
- **Spine detection is deterministic** — a regex pass for keyed headers
  (`^\d+\.\d+\s+Title`, chapter headings) splits the text into ordered scene
  slices. No LLM in this step. Lives in a new `lib/adventure_import.py` with a
  CLI (`slice <pdf>`), writing slices + a draft spine to a workdir.
- **Conversion is agent-read, not RAG.** The `/import-module` command (a
  `.claude/commands/import-module.md` orchestration doc plus a converter agent
  definition) fans out at most 6 agents on `claude-opus-4-8[1m]`; each reads
  its assigned scene slices in full and returns schema JSON per scene:
  `{key, title, location, read_aloud, gm_notes, encounters, npcs, monsters,
  treasure, checks, transitions}`.
- **Storage:** one `adventure.json` per campaign — `meta`, ordered `scenes[]`,
  `progress: {current_scene, completed: []}`. Managed by a new
  `lib/adventure.py` (schema validation, merge, progress ops). Extracted NPCs
  are persisted into `npcs.json` via the existing manager; monsters carry an
  `srd_index` when the name resolves against the dnd5eapi monster list
  (via `features/dnd-api` fetch, which is gaining a file cache), else an
  embedded stat block.
- **Runtime:** `tools/gm-adventure.sh` wraps `lib/adventure.py`
  (`status`/`advance`/`jump <key>`); scene context assembly in
  `lib/session_manager.py` appends an `--- ADVENTURE ---` block when
  `adventure.json` exists: current scene's GM material plus a one-line "next
  per the book".
- No ruleset/kit drafting anywhere in this path (the 5e-native fork hardcodes
  dnd5e); no embedding index is built.

## Testing Decisions

- `adventure_import.py` and `adventure.py` get small runnable checks
  (`test_*.py` in `tests/`): column extraction produces non-interleaved text on
  a known two-column page, spine detection finds the expected keys on the test
  PDF, schema validation rejects malformed scenes, progress ops
  advance/jump correctly.
- End-to-end is a manual run: `/import-module
  /Users/seanstobo/Downloads/at-05-the-whispering-wood.pdf` (50 pages) in a
  live session — the fan-out needs the main agent's Agent tool, so this is
  HITL. Pass = adventure.json validates, all keyed scenes present, scene
  context shows the ADVENTURE block, `gm-adventure.sh advance` moves the pointer.

## Out of Scope

- Changing `/import` (novel/RAG path) or any RAG machinery.
- Non-D&D modules and non-PDF inputs (the text path can come later).
- Map/image extraction from the PDF.
- Automatic detection of "is this a module vs a novel" — the user picks the command.

## Further Notes

- Runs alongside the 5e-native-fork effort; shares its direction (SRD API as
  stat authority) but touches different files. `session_manager.py` is clean
  in the working tree at planning time.
- Agent count is capped at 6 per operator rule; agents must be told the cap
  inside their prompts (subagents self-fan-out).
