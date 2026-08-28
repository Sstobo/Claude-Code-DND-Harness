---
slug: living-world-followthrough
title: World-tick ignores its own cap, clocks miss travel time, the chronicler never reaches the prompt
category: bug
kind: afk
priority: p2
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

bug

## What to build

Four small gaps behind living-world and illustration claims that otherwise hold
up well. The consequence tick, the clock tick, the image gate, the provider
fallback and the file:// link all verified clean by execution — these are the
leftovers.

**1. "a small bounded set of off-screen developments" is unbounded, and never
runs.** `lib/world_tick.py:29-53` documents the cap as advisory and applies every
proposal regardless, warning only past the cap. Proved: six developments with
`cap=3` persisted all six. And `tools/gm-session.sh:131-133` merely *prints*
"optionally advance a few SMALL off-screen developments" and calls nothing —
proved the tick log does not grow across a `session end`. Rollback and provenance
do work (`lib/world_tick.py:72-90`).

**2. Clocks do not advance on movement.** `tools/gm-time.sh:89` ticks time clocks
correctly (`lib/threat_clocks.py:83-105`), but a `move` advances none. Proved: a
clock sat at 0/6 across a move and only ticked on the next explicit
`gm-time.sh`. Travel that takes hours moves no clock unless the GM also calls
the time tool, which CLAUDE.md's movement flow does instruct — but README:42
says clocks tick "whether or not you are watching."

Secondary: the consequence a filled clock writes carries no structured trigger
(`lib/threat_clocks.py:68`), so it fuzzy-matches poorly and generally waits in
the pending list rather than firing.

**3. The chronicler's name and persona never reach the image prompt.** The
*style* lock is real and strong — `lib/image_gen.py:310-315` refuses to render
until a style is set, and `build_prompt` (`:240-257`) injects style + era into
every prompt with `style_lock=True` by default. But `Astreus` and
`court-scholar` are **absent from the built prompt**; they live in
`chronicler.json` and are surfaced only in scene context
(`lib/session_manager.py:942-952`). So README:50's "presented as the work of an
in-world chronicler" is model prose over a style-only lock. Also
`save_chronicler` is an unguarded merge-update (`lib/image_gen.py:100-118`), so
any later call silently rewrites the "locked" style. And CLAUDE.md says every
prompt "opens with" the style; the code appends it.

**4. The appearance guard only inspects `--character`.** `lib/image_gen.py:295-304`
fails closed correctly for names passed via the flag, but a prompt that names a
character in its *text* without the flag passes both guards untouched — proved by
sending one through to the live HTTP request. Image-to-image consistency rests on
the model remembering the flag.

## Acceptance criteria

- [ ] `WorldTick.apply` enforces `cap` by truncating past it, not warning
- [ ] `gm-session.sh end` either calls `world-tick` or stops implying it happens on its own
- [ ] Travel time advances time clocks (either `move` calls the time tick, or clocks read elapsed time)
- [ ] A filled clock's consequence carries a structured trigger so it can actually fire
- [ ] The chronicler's name and persona are injected into the prompt alongside the style, or README:50 is reworded to claim only the style
- [ ] `save_chronicler` refuses to change an existing style without `--force`
- [ ] `generate` scans prompt text for known PC/NPC names and fails closed on a match with no stored appearance
- [ ] CLAUDE.md's "opens with" matches the code's append, or the code moves the style to the front

## Out of scope

Auto-spawning agents — see `readme-claim-honesty`.

## Verification

Lane: agent. Six developments with cap 3 must persist three.

## Blocked by

Nothing. The appearance-scan criterion assumes `appearance-migration` has run,
or it will fail closed on 40 NPCs.

---

## QA Reports

## History

- 2026-08-27T00:00:00Z  created → needs-triage  [readme-audit]
