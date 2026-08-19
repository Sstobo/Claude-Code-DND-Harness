---
slug: 5e-native-fork
title: 5e-Native Fork — strip the kit system, API as source of truth
status: active
version: 1
createdAt: 2026-08-19T00:00:00Z
updatedAt: 2026-08-19T00:00:00Z
---

## Problem Statement

This fork exists to play D&D 5e specifically. The parent project is kit-generic
(any book becomes its own ruleset via `ruleset.json`), which means 5e is one
branch behind conditionals, campaign creation runs a kit-drafting ceremony that
is pure ceremony here, and the GM improvises stat blocks and spell effects from
memory when the real numbers exist in the dnd5eapi.co SRD API. Every API call
is also a live network round-trip with no cache, so combat depends on
dnd5eapi.co being up mid-session.

## Solution

Make 5e the engine, not a branch. Hardcode the 5e ruleset behind the existing
WorldKit accessor surface so consumers barely change, delete the per-campaign
`ruleset.json` and kit-drafting steps, make every "only if kit is dnd5e" gate
unconditional, cache SRD responses to disk forever (2014 SRD data is
immutable), and make the API the mandatory source of truth for monster stat
blocks, spells and slots, level-up features, and encounter CR budgets.

## User Stories

1. As the player, I want every new campaign to be 5e out of the box, so that I never answer kit questions.
2. As the GM, I want SRD monsters, spells, slots, and class features resolved from fetched API data, so that the numbers are real 5e, not improvisation.
3. As the player, I want the API cached locally, so that sessions are fast and an API outage never bricks combat.
4. As the GM, I want encounters budgeted by CR math, so that difficulty is deliberate.

## Implementation Decisions

- `lib/world_kit.py` keeps its accessor surface (`progression`, `vitals()`, `lethality()`, `stat_schema()`, `kit()`, `campaign_rules()`, signature systems) but returns a hardcoded 5e ruleset; `kit()` always returns `"dnd5e"`. `ruleset.json` is no longer read or written. Consumers (`player_manager`, `session_manager`, `game_core`, `book_bible`) are untouched or minimally touched.
- `/new-game`, `/import`, `/reset`, and `gm-extract.sh draft-ruleset` drop ruleset drafting. Signature-systems flavor from an imported book may remain as prose, but never as mechanics that override 5e.
- Agent and skill kit-gates ("only when the active kit is dnd5e") become unconditional 5e instructions.
- `features/dnd-api/dnd_api_core.py fetch()` gains a JSON file cache keyed by endpoint path, no TTL. All feature scripts share `fetch()`, so one edit caches everything.
- API-authoritative mandates land in the owning skills/agents: `gm-combat` + `monster-manual` (SRD creatures use fetched blocks; homebrew built by analogy to nearest fetched CR block), `gm-spellcasting` + `spell-caster` (fetched spell data; slot tables from `/classes/{class}/levels`), `gm-levelup` (features/ASIs/slots from `/classes/{class}/levels`), encounter generation through `dnd_encounter_v2.py` CR budgets.
- Docs claiming kit behavior are updated in the same commit as the code they describe (OKF policy), not as a separate ticket.

## Testing Decisions

- Python-level changes (world_kit hardcoding, fetch cache) get small runnable checks: existing tests must pass; cache verified by asserting the second fetch reads no network.
- Prose-mandate changes (skills/agents) are verified by grep (no kit-conditional language survives) plus the referenced scripts running successfully.
- End-to-end: create a fresh campaign and confirm it plays 5e with no kit prompts.

## Out of Scope

- Importing non-D&D books as their own kits — this fork deliberately gives that up.
- 2024 rules / non-SRD content; the API serves 2014 SRD only.
- Rewriting `game_core.py` — it stays as the resolution engine under the 5e ruleset.

## Further Notes

- No commits existed before this work; baseline commit `ddee691` snapshots the fork pre-conversion.
- Repo is OKF-managed: run `okf status` before editing, update claiming docs same-commit.
