---
slug: readme-promises
title: The README is a promise — make the code keep it, or stop making it
status: active
version: 1
supersedes: null
createdAt: 2026-08-27T00:00:00Z
updatedAt: 2026-08-27T00:00:00Z
---

## Problem Statement

The README was rewritten (`808d661`) as a plain description of the harness and
adopted as the promise to players. A six-agent read-only audit then tested every
claim in it against the code. The machinery is largely real and well-tested —
the combat resolver, the consequence tick, the clock tick, campaign_rules
delivery, lazy materialization, the image gate and style lock all do exactly
what the page says. What the audit found is a consistent shape of failure:

**Every claim containing the word "enforced" or "automatic" is an instruction to
the model, not a mechanism.** The repo's own docs already admit two of them.
`docs/conventions/persist-before-narrate.md` says outright that "nothing blocks a
missed persist," while README:133 says "Persist-before-narrate, enforced."
`WorldBible.is_playable()` exists at `lib/world_bible.py:112-116` and is called
by nothing in production, while README and `docs/flows/author-a-world.md:37`
both promise play gates on approval. Nothing anywhere spawns a sub-agent, while
README:176 says they "Spawn automatically during play, invisibly."

Three claims are flatly contradicted by the code or by live data:

- README:111 tells a new user to clone `Claude-Code-Game-Master`, which is a
  live, separate, stale repo — 11 days and an unknown number of commits behind
  this one. `git ls-remote` succeeds against it. There is no error, no redirect,
  and no way for the user to notice.
- README:90 says `/import-module` involves "No embeddings, no world-bible
  drafting." Step 9 of that command mandates both, and `whispering-wood` has a
  2.2MB `vectors/` dir and a `world-bible.json` to prove it.
- README:132 says "Campaigns can run indefinitely." The dossier is read whole at
  every scene change and nothing caps it. Measured: `whispering-wood` is already
  8,529 tokens with **two** chronicle entries. It becomes unreadable around
  session 40-60.

Separately, the third advertised door is unreachable. `/import-module` appears
in `README.md`, `CLAUDE.md`, `tickets/` and `docs/` — and in zero lines of
`.claude/commands/gm.md` or `help.md`. Worse, `gm.md:77` offers "IMPORT DOCUMENT
(PDF, book, **or module**)" and `gm.md:80` routes it unconditionally to
`/import`, so a player who picks "module" gets the RAG book pipeline, which is
the exact outcome `/import-module` exists to prevent.

And the character sheet — asked about directly during the audit — is not
standardized. A canonical shape is declared (`lib/character_schema.py:5-11`) and
documented (`docs/schema-reference.md:428-481`), but no write path validates
against it, six writers produce six different key sets, and the validator that
does exist requires only `name` and `level` and type-checks a key
(`abilities`) that no writer emits and no campaign has. The live `dcc` PC is
playing with `stats: {}` — no ability scores at all, rolling flat d20 for
initiative forever. A `visual_appearance` field-set change (`d28fb34`) shipped a
read-time shim with no data migration, so 40 of 49 NPCs across the four
campaigns cannot be illustrated at all, and 3 of 4 PCs silently lose fields on
every image render.

Audit provenance: six read-only agents, 2026-08-27, one per slice (combat/dice,
memory/persistence, synthesis/doors, living world/images, setup/tables/docs,
character sheets). Findings were verified by execution against sandboxed campaign
copies, not by reading alone. Real `world-state/` was never mutated.

## Solution

Three moves, in this order.

**First, stop lying at the front door.** The clone URL, the prerequisites, the
install claims and the dependency list are wrong in ways that cost a new user
their first hour. These are text and metadata fixes with no design question in
them, and they ship immediately.

**Second, make the third door reachable and standardize the sheet.** These are
the two places where a player hits a real wall today: a module import that
silently becomes a book import, and 40 NPCs that raise on any illustration
attempt. The sheet work starts with validation on write, because the absence of
that check is what let every other sheet defect drift in unnoticed.

**Third, close the enforcement gap — claim by claim, deciding each one.** For
each PROSE-ONLY claim there are exactly two honest endings: build the mechanism,
or change the sentence. The audit found the mechanism is cheap in several cases
(`is_playable()` is already written; a `SessionStart` hook would make
"pushed, not fetched" literally true; reading the PC's attack numbers off
`character.json` is the same pattern `join_pc` already uses for HP and AC), and
genuinely not available in others (nothing in the harness can spawn a subagent,
so "Spawn automatically" must become wording). Each ticket names which ending it
takes and why.

The through-line: a claim the code enforces is a feature. A claim only the model
honours is a hope. The README may keep making the second kind, but it has to say
so, and every place we can cheaply promote a hope to a feature, we should.

## Non-goals

- Rewriting the README's voice or structure. `808d661` settled that.
- Deleting the legacy census machinery (`normalize`, `cap`, `reconcile`,
  `stub-npcs`, `integrity`). Tracked separately; here it is only evidence that
  the "nothing else is pre-built" discipline has no code behind it.
- Chasing the two pre-existing test failures the audit noticed in passing
  (`tests/test_get_full_context.py::test_action_menu_on_is_a_few_numbered_not_exactly_three`,
  stale since `9d85c65`).
