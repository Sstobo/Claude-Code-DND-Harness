---
slug: context-push-hooks
title: "Pushed to the model, not fetched by it" is exactly inverted — nothing pushes context
category: enhancement
kind: afk
priority: p1
lane: agent
parentPrd: readme-promises
blockedBy: []
claimedBy: null
claimedAt: null
changedFiles: []
resolution: null
reviewRounds: 0
implementer: null
createdAt: 2026-08-27T00:00:00Z
updatedAt: 2026-08-27T00:00:00Z
---

## Parent

readme-promises — prds/readme-promises.md

## Category

enhancement

## What to build

README:40 is the harness's central claim: "Claude does not have to remember to
look; the harness puts it on the table." Remembering to look is currently the
*only* delivery mechanism.

The **assembly** half is excellent and fully real. `gm-session.sh context` on a
live campaign emits exactly what the README lists: `PREVIOUSLY ON` (with
`WHERE WE PAUSED` and `OPEN THREADS`), `THE WORLD REMEMBERS`, `STORY THREADS`,
`READY THREADS`, `KEY FACTS`, `CHARACTER`, `PARTY MEMBERS`, `NPC VOICES`,
`PENDING CONSEQUENCES`, `THREAT CLOCKS`. That part of the promise is kept.

The **delivery** half does not exist. `.claude/settings.json` registers exactly
two hooks — a `PostToolUse` state-write logger and a `Stop` autosave. There is
**no `SessionStart`, no `UserPromptSubmit`, and no `PreCompact` hook anywhere in
the repo**. Context reaches the model only when the model chooses to run
`gm-session.sh context` or `dossier`, per instructions in CLAUDE.md and
`.claude/commands/gm.md:167-168`. The one thing the harness invokes on its own is
`tools/gm-statusline.sh`, and that renders a HUD to the user's terminal, not into
the model's context.

All three are supported hook events. This claim is cheap to make literally true.

Two things the pushed context should carry that the assembled context currently
does not:

**Active combat is invisible.** Grepping the whole context path — the
`session_manager.py` context/dossier builders, `scene_context.py`,
`gm-session.sh`, `gm-context.sh` — finds zero references to combat state (only
the snapshot-list entry at `lib/session_manager.py:57` and a narration hint at
`:885`). Neither `context` nor `dossier` says a fight is running, whose turn it
is, or the initiative order. README:36's "Close the laptop mid-fight; pick it up
next week exactly where you left off" depends on the model independently
remembering to run `gm-combat.sh header`.

**Source passages are not in the per-beat brief.** README:134 promises "Scenes
draw on actual passages ... via a local retrieval index." What the brief actually
contains is an *instruction* to go fetch them: "every beat (or every other beat),
run `gm-search.sh … --rag-only` and mine the returned passages"
(`lib/session_manager.py:896-919`). `session_manager.py` has no RAG import, no
vector-store call, no passage rendering. Real passages come only from a separate
explicit `gm-context.sh` call (`lib/scene_context.py:58-66`). Grounding is one
model decision away, every single turn.

## Acceptance criteria

- [ ] A `SessionStart` hook emits the dossier into context automatically
- [ ] A `UserPromptSubmit` hook emits the per-beat context delta automatically
- [ ] A `PreCompact` hook re-emits the dossier, so a compaction cannot drop the world
- [ ] The context builder includes an `ACTIVE COMBAT` block (round, turn, initiative order, HP) whenever `combat_state.json` has combatants
- [ ] `get_full_context` inlines the top 2-3 retrieved passages under a `SOURCE PASSAGES (texture, not fact)` heading, keeping the existing hallucination warnings
- [ ] Hook output stays within a sane token budget — coordinate with `dossier-growth-cap`

## Out of scope

Removing the model-facing instructions; they remain a useful backstop.

## Verification

Lane: agent. Start a fresh session in a sandboxed campaign copy and confirm the
world arrives before the first prompt is answered.

## Blocked by

Nothing, but land `dossier-growth-cap` first or a pushed dossier will be the
thing that blows the budget.

---

## QA Reports

## History

- 2026-08-27T00:00:00Z  created → needs-triage  [readme-audit]
