---
slug: remove-kit-drafting
title: Strip kit-drafting from /new-game, /import, /reset, gm-extract
category: enhancement
kind: afk
priority: p0
lane: agent
parentPrd: 5e-native-fork
blockedBy: [hardcode-5e-ruleset]
claimedBy: null
claimedAt: null
changedFiles: []
resolution: null
reviewRounds: null
implementer: null
createdAt: 2026-08-19T14:10:45Z
updatedAt: 2026-08-19T14:10:45Z
---

## Parent

5e-Native Fork (prds/5e-native-fork.md)

## Category

enhancement

## What to build

Remove ruleset/kit-drafting steps from campaign creation and teardown:
`.claude/commands/new-game.md`, `.claude/commands/import.md`,
`.claude/commands/reset.md`, and `gm-extract.sh draft-ruleset` (plus its
`book_bible.py` backing, including the `--kit` argument). Campaign creation
goes straight to 5e — no kit questions, no ruleset approval gate. An imported
book's signature systems may survive as flavor prose in the overview/bible,
never as mechanics overriding 5e. Update claiming docs
(`docs/flows/*`, `docs/conventions/lean-core-and-skill-routing.md` as
`okf status` names them) same-commit.

## Acceptance criteria

- [ ] `/new-game` and `/import` command docs contain no kit-drafting or ruleset-approval steps
- [ ] `gm-extract.sh draft-ruleset` subcommand removed; script's remaining subcommands still run
- [ ] End-to-end: a fresh campaign can be created and `gm-session.sh context` reports 5e rules with zero kit prompts
- [ ] `/reset` no longer references ruleset.json
- [ ] Claiming docs updated/restamped same-commit

## Verification

Lane: agent

## Blocked by

hardcode-5e-ruleset

---

## QA Reports

## History

- 2026-08-19T14:10:45Z  created → ready  [main]
