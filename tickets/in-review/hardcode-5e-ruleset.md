---
slug: hardcode-5e-ruleset
title: Hardcode 5e ruleset in world_kit.py, drop ruleset.json
category: enhancement
kind: afk
priority: p0
lane: agent
parentPrd: 5e-native-fork
blockedBy: []
claimedBy: ss-5efork
claimedAt: 2026-08-19T14:16:37Z
changedFiles: []
resolution: null
reviewRounds: null
implementer: null
createdAt: 2026-08-19T14:10:45Z
updatedAt: 2026-08-19T14:16:37Z
---

## Parent

5e-Native Fork (prds/5e-native-fork.md)

## Category

enhancement

## What to build

Replace `lib/world_kit.py`'s ruleset.json loading with a hardcoded 5e ruleset.
Keep the accessor surface intact (`progression`, `vitals()`, `lethality()`,
`stat_schema()`, `kit()`, `campaign_rules()`, signature systems, `skills()`,
`active_agents()`) so consumers (`player_manager`, `session_manager`,
`game_core`, `book_bible`) change minimally or not at all. `kit()` always
returns `"dnd5e"`. The 5e ruleset: six attributes (str/dex/con/int/wis/cha),
hp vital, XP progression with 5e thresholds, d20-vs-dc resolution, death-saves
lethality with massive damage at max HP. `ruleset.json` is never read or
written; `book_bible.py`'s kit-drafting helpers that only exist to author
ruleset.json lose that responsibility (full command-side removal is the
remove-kit-drafting ticket). Update the docs that claim this behavior
(`docs/modules/game-core-and-world-kit.md` and any others `okf status` names)
in the same commit.

## Acceptance criteria

- [ ] `WorldKit().kit()` returns `"dnd5e"` with no ruleset.json present
- [ ] Stat schema, vitals, lethality, and XP progression match 5e defaults from hardcoded values
- [ ] No code path in lib/ reads or writes `ruleset.json`
- [ ] Existing test suite passes (`uv run pytest` or the repo's test runner)
- [ ] Docs claiming kit behavior updated/restamped in the same commit (okf check clean for touched docs)

## Verification

Lane: agent

## Blocked by

None.

---

## QA Reports

## History

- 2026-08-19T14:10:45Z  created → ready  [main]
- 2026-08-19T14:16:37Z  doc-grounding confirmed  [ss-5efork]
- 2026-08-19T14:16:37Z  claimed  [ss-5efork]
