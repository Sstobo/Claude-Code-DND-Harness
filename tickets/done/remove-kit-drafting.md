---
slug: remove-kit-drafting
title: Strip kit-drafting from /new-game, /import, /reset, gm-extract
category: enhancement
kind: afk
priority: p0
lane: agent
parentPrd: 5e-native-fork
blockedBy: [hardcode-5e-ruleset]
claimedBy: ss-5efork
claimedAt: 2026-08-19T15:20:53Z
changedFiles: [.claude/commands/new-game.md, .claude/commands/import.md, .claude/commands/reset.md, tools/gm-extract.sh, tools/gm-reset.sh, lib/book_bible.py, tests/test_bible_kit_chain.py, tests/test_kit_systems.py, tests/test_book_bible_import.py, tests/test_reset_archive.py, docs/flows/author-a-world.md, docs/flows/import-a-book.md, docs/modules/world-bible.md, docs/modules/game-core-and-world-kit.md, docs/schema-reference.md]
resolution: kit-drafting ceremony removed — campaigns are 5e from creation; book flavor flows to campaign_rules prose; rules.md authored conditionally
reviewRounds: 2
implementer: null
createdAt: 2026-08-19T14:10:45Z
updatedAt: 2026-08-19T16:19:31Z
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

- [x] `/new-game` and `/import` command docs contain no kit-drafting or ruleset-approval steps
- [x] `gm-extract.sh draft-ruleset` subcommand removed; script's remaining subcommands still run
- [x] End-to-end: a fresh campaign can be created and `gm-session.sh context` reports 5e rules with zero kit prompts
- [x] `/reset` no longer references ruleset.json
- [x] Claiming docs updated/restamped same-commit

## Verification

Lane: agent

## Blocked by

hardcode-5e-ruleset

---

## QA Reports

## History

- 2026-08-19T14:10:45Z  created → ready  [main]
- 2026-08-19T15:20:53Z  claimed  [ss-5efork]
- 2026-08-19T15:27:45Z  doc-grounding confirmed  [ss-5efork]

### 2026-08-19T16:08:29Z — verified [ss-5efork]
draft-ruleset/write-systems gone from book_bible + gm-extract (residue grep clean bar one intentional negative test assert). End-to-end scratch campaign: 5e rules in context, zero kit prompts, no ruleset.json. gm-reset.sh text aligned with reset.md. Owning docs (world-bible, game-core, schema-reference) updated + restamped same sitting; okf 25 conformant (1 pre-existing error elsewhere). Suite: known pre-existing failure + one in-flight failure owned by the other session's adventure ticket.
- 2026-08-19T16:08:29Z  verified → in-review  [ss-5efork]

### 2026-08-19T16:13:32Z — fail [review-kit-drafting]
reviewed: needs-changes (minor; all 5 ACs pass, end-to-end verified in scratch)
- rules.md has no producer but import.md --fix-rules-doc + reset kept-lists still promise it (permanently-negative report line)
- no regression guard keeping kit-drafting language out of new-game.md/import.md
- stale "kit" prose in test_reset_archive.py comments/labels
- weak assert in test_cli_drives_the_whole_chain (any-nonzero passes)
- write-index missing from gm-extract.sh usage though /new-game calls it
- index churn in gotchas/playbooks H1s (okf regen side effect; accepted)
- [x] (review) import.md drops --fix-rules-doc OR a step authors rules.md; kept-lists agree
- [x] (review) doc guard asserts /new-game and /import stay free of kit-drafting language
- [x] (review) test_reset_archive kit labels relabeled legacy; CLI assert tightened to argparse invalid-choice
- [x] (review) gm-extract.sh usage lists every live bible-chain verb

### 2026-08-19T16:16:56Z — verified (fix round) [ss-5efork]
All 5 findings fixed: rules.md conditional author step (import + new-game symmetric), kit-drafting regression guard w/ positive assert, reset test relabeled, CLI assert pinned to argparse invalid-choice, write-index in usage. Guard tests green (28 passed); suite 675 passed / 2 allowed failures. Followup review dispatched.
- 2026-08-19T16:16:56Z  fix round verified — followup review dispatched  [ss-5efork]

### 2026-08-19T16:19:31Z — pass [review-kit-drafting]
reviewed: perfect (followup round 2)
Notes: okf-regen H1 churn in gotchas/playbooks index files accepted as side effect of the required index command.
- 2026-08-19T16:19:31Z  done → committed  [ss-5efork]
