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
changedFiles: [lib/world_kit.py, lib/overview_seed.py, lib/player_manager.py, lib/session_manager.py, lib/schemas.py, features/character-creation/save_character.py, tests/test_overview_seed.py, tests/test_rules_doc.py, tests/test_world_kit.py, tests/test_kit_block.py, tests/test_kit_grit_dial.py, tests/test_kit_systems.py, tests/test_kit_aware_character_creation.py, tests/test_kit_vitals.py, tests/test_milestone_progression.py, tests/test_resolution_models.py, tests/test_character_schema.py, docs/modules/game-core-and-world-kit.md, docs/modules/scene-context.md, docs/schema-reference.md]
resolution: 5e ruleset hardcoded behind WorldKit accessors; ruleset.json IO gone from lib (book_bible until its ticket); nameless onboarding preserved
reviewRounds: 2
implementer: null
createdAt: 2026-08-19T14:10:45Z
updatedAt: 2026-08-19T15:20:36Z
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

- [x] `WorldKit().kit()` returns `"dnd5e"` with no ruleset.json present
- [x] Stat schema, vitals, lethality, and XP progression match 5e defaults from hardcoded values
- [x] No code path in lib/ reads or writes `ruleset.json`
- [x] Existing test suite passes (`uv run pytest` or the repo's test runner)
- [x] Docs claiming kit behavior updated/restamped in the same commit (okf check clean for touched docs)
- [x] (review) grep ruleset.json in lib/*.py hits only book_bible.py (and comments) — no reads/writes in overview_seed, player_manager, session_manager
- [x] (review) overview_seed.py --fix-rules-doc succeeds with no ruleset.json and creates none
- [x] (review) rules_doc_path() returns campaign rules.md when present, None otherwise, no ruleset.json needed
- [x] (review) save_character: missing hp -> 10/10 + warning; authored hp preserved verbatim (tests restored)
- [x] (review) no doc citing overview_seed.py claims rules_doc pointer unused while code writes it

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

### 2026-08-19T14:50:57Z — verified [ss-5efork]
Live asserts: kit()=dnd5e, 5e attribute schema, vitals [hp], xp-levels progression w/ 5e thresholds, death-saves lethality. world_kit.py no longer reads/writes ruleset.json (book_bible retains it until remove-kit-drafting). Suite: 1 failure only, pre-existing at baseline (test_get_full_context action-menu assert, fails on stashed baseline too). 3 docs rewritten + restamped.
- 2026-08-19T14:50:57Z  verified → in-review  [ss-5efork]

### 2026-08-19T14:58:19Z — fail [review-5e-ruleset]
reviewed: needs-changes
- lib/overview_seed.py:37-61 fix_rules_doc/set_rules_doc read AND write ruleset.json; import.md runs --fix-rules-doc every import. Violates the no-ruleset.json criterion.
- lib/player_manager.py:297 _spectacle_config still load_json("ruleset.json") (harmless but a lib/ read).
- game-core-and-world-kit.md claims rules_doc pointer "gone" while its cited source overview_seed.py still writes it.
- Deleted tests removed live coverage: authored-max-HP preservation + 10/10 fallback warning in save_character.py (not ruleset-dependent).
- session_manager.py:1019 comment now inverted (signature_systems no longer preferred).
- Style nits: SNAPSHOT_FILES name, progression() vs progression_model() in docs.
- Mention (pre-existing dead code, not removed per repo rule): award_spectacle milestone branch + multi-vital machinery now unreachable.
Verified good: XP table exact PHB, fallback chain, suite passes (1 known pre-existing failure).

### 2026-08-19T15:14:21Z — verified (fix round) [ss-5efork]
All 6 findings + snapshot-list residue fixed. Independent re-verify: grep gate holds (ruleset.json IO only book_bible.py), suite 610 passed / 1 pre-existing failure, kit()=dnd5e with signature_systems []. Nameless-onboarding regression fixed with restored + new tests. Followup review dispatched (round 2).
- 2026-08-19T15:14:21Z  fix round verified — followup review dispatched  [ss-5efork]

### 2026-08-19T15:20:36Z — pass [review-5e-ruleset]
reviewed: perfect (followup round 2)
Notes (non-blocking nits):
- docs/modules/scene-context.md line anchors stale (:39/:109/:26/:34/:73 — some inherited drift)
- save_character.py:169 'saves' elif branch now unreachable (pre-existing-dead-code rule: mention only)
- pre-existing unused imports: typing.Optional (schemas.py), os (save_character.py)
New-criterion recorded for a future docs pass: scene-context.md anchors resolve to the constructs they name.
- 2026-08-19T15:20:36Z  done → committed  [ss-5efork]
