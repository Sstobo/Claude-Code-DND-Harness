---
slug: readme-claim-honesty
title: Decide each prose-only claim — build the mechanism or change the sentence
category: chore
kind: hitl
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

chore

## What to build

The audit found a consistent pattern: every claim containing "enforced" or
"automatic" describes an instruction to the model, not a mechanism. Each one has
two honest endings — build it, or say it differently. Other tickets take the
"build it" ending where it is cheap. This ticket takes the rest, and fixes the
reference-table inaccuracies while it is in the file.

`kind: hitl` because what the product promises is Sean's call, not an agent's.

**Claims needing a decision:**

1. **README:133 "Persist-before-narrate, enforced."** The repo's own doc,
   `docs/conventions/persist-before-narrate.md`, is titled with "the honest state
   of its enforcement, which is advisory" and says "nothing blocks a missed
   persist." Both registered hooks are `set +e` with unconditional `exit 0`
   (`post-tool-state-log.sh:4,25`; `session-autosave.sh:4,13`). The logger's
   matcher is a five-item substring list (`:18`) that does not even cover
   `gm-note.sh`, `gm-plot.sh`, `gm-combat.sh` or `gm-clock.sh`. Recommendation:
   drop "enforced," widen the matcher, and describe it as a convention the tools
   are built around.

2. **README:176 "Spawn automatically during play, invisibly."** Nothing in the
   repo spawns an agent — zero hits for `Agent tool`, `subagent_type`, `Task(`
   across `lib/` and `tools/`; the two "spawn" occurrences are print statements.
   Hooks cannot spawn subagents today, so the honest ending is wording: the GM
   calls these agents as it needs them.

3. **README:269 "One turn per reply."** Instruction only
   (`.claude/skills/gm-combat/SKILL.md:22-30`). Nothing stops two `attack` calls
   in one reply. `pc-attack-from-sheet` could enforce it cheaply (refuse a second
   resolution against the same round/turn without an intervening `next-turn`) —
   decide whether it is worth the rail.

4. **README:44 "They read your world's own rules before reaching for anything
   external."** Book-first is a numbered instruction in each agent body
   (`monster-manual.md:12`, `spell-caster.md:11`, `gear-master.md:11`,
   `rules-master.md:13`), and every one grants `tools: Bash, WebFetch`
   unconditionally, so nothing sequences RAG ahead of the API. Option: drop
   `WebFetch` and route lookups through a `gm-lookup.sh` front door that queries
   the campaign first and returns provenance with the answer. That would also
   make README:273's book-first-then-SRD claim true beyond modules, where it is
   currently real only in `AdventureManager.resolve_monsters`
   (`lib/adventure.py:496-535`).

5. **README:142 "Everything below is handled automatically by `/gm`."** False.
   `/import-module` is unreachable (see `third-door-reachable`), `/setup` runs
   from the boot sequence not `/gm`, and `/reset`, `/world-check`, `/help` are
   never invoked from `gm.md`.

6. **README:102 "All three doors converge on the same campaign shape."** The
   shared scaffold is smaller than the list. `_init_empty_files`
   (`lib/campaign_manager.py:359-421`) writes six things; `character.json`,
   `plots.json` and `threat-clocks.json` are never scaffolded. `plots.json` is
   genuinely absent from both import campaigns. Fix by scaffolding them, or by
   naming the shared core and saying each door adds extras.

**Reference-table corrections (factual, no decision needed):**

- **Agents table omits six that exist**: `plot-weaver` (load-bearing, documented
  at length in CLAUDE.md), `module-converter` (the engine behind the third door),
  and `extractor-npcs` / `-locations` / `-items` / `-plots`.
- **Tools table omits three**: `gm-playpack.sh` (CLAUDE.md routes the play pack
  through it and README's own `/new-game` step 3 is named for it),
  `gm-statusline.sh` (a visible player-facing HUD the README never mentions), and
  `gm-migrate-campaigns.sh` (optional).
- **`gm-adventure.sh` purpose is stale** — commit `cc75e3d` added adaptation;
  actual verbs are `status`, `advance`, `jump`, `validate`, `requires-report`,
  `adapt`.
- **`gm-session.sh` purpose omits** `dossier`, `chronicle`, `context`,
  `world-tick` — all things the README's prose sells.
- **Four command descriptions are wrong**: `/help` is not a full reference (it
  omits `/import-module` and misroutes it); `/import` takes DOCX/TXT/MD too
  (`import.md:15`); `/reset` keeps source and world and clears only the story
  (`reset.md:12`); `/setup` is an installer, not a verifier (`setup.md:3`).
- **README:277 `okf drift`** is a real subcommand but not a command anyone who
  clones this repo has — it lives in the author's `~/.claude/skills/okf/`. Point
  at `docs/log.md` for the invocation.

## Acceptance criteria

- [ ] A decision is recorded for each of the six claims: build or reword
- [ ] Every "build" decision has a ticket; every "reword" decision is applied to the README in this ticket
- [ ] The agents table lists all 16 agents, or says explicitly that it lists the ones that appear during normal play
- [ ] The tools table includes `gm-playpack.sh` and `gm-statusline.sh`, and the two stale purpose lines are current
- [ ] The four wrong command descriptions are corrected, and `help.md` itself is fixed (it is the file being described)
- [ ] No sentence in the README claims enforcement that the code does not perform

## Out of scope

The front-door facts (`readme-front-door-facts`) and the third door
(`third-door-reachable`) — already ticketed.

## Verification

Lane: agent, human sign-off on the six decisions.

## Blocked by

Nothing, but resolve after the "build it" tickets land so the wording describes
the finished state.

---

## QA Reports

## History

- 2026-08-27T00:00:00Z  created → needs-triage  [readme-audit]
