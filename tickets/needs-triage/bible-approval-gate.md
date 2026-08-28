---
slug: bible-approval-gate
title: "You approve the bible before play" — is_playable() exists and nothing calls it
category: bug
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

bug

## What to build

Two places in the README promise an approval gate — README:68 ("then shows it to
you for approval before going further") and README:96 ("You approve the bible
before play") — and `docs/flows/author-a-world.md:37` states flatly that "play
gates on approval." None of it is enforced, and the switch to enforce it is
already written and unused.

`WorldBible.is_playable()` exists at `lib/world_bible.py:112-116`. A repo-wide
grep finds it in exactly three places: its own definition,
`tests/test_bible_confirm_gate.py`, and docs. No tool, no `require_active_campaign`,
no session-start path consults it.

The `/new-game` flow is worse than unenforced — it never runs the confirm verb at
all. `new-game.md:110-113` runs `validate` and `show`, not `review`/`confirm`,
while its own checklist at `:245` claims the bible ends up "approved and
confirmed." Proof: `world-state/campaigns/conan/world-bible.json` carries
`confirmed: false` and that campaign has a chronicler, a character sheet, a
session log, `campaign_rules` and a play pack. It played unconfirmed, start to
finish.

`/import` is better — `import.md:161-166` does run `world_bible.py review` and
instructs `confirm` "only after they say so" — but an unconfirmed bible still
blocks nothing. `docs/modules/world-bible.md:93-95` is already honest that "the
gate is closed by a person, not by the pipeline," and `:99`'s claim that "only
the confirm flag" blocks play is itself wrong, since the flag blocks nothing
either.

The fix is one call site.

Related, same area: **the "one stage, not a planet" discipline has no cap.**
`apply_stage` does exactly what README:69 describes (`lib/play_pack.py:261-302`)
but `normalize_pack` (`:46-59`) accepts arbitrary-length `present`/`exits`/
`offstage` lists. The "2-4 people, 2-4 exits" rule lives only in prose
(`import.md:192-198`, `new-game.md:150-158`). Nothing stops a 40-name pack.

And the legacy census machinery is still wired: `normalize`, `cap`, `reconcile`,
`stub-npcs`, `integrity` are live verbs (`tools/gm-extract.sh:641-693`) backed by
five libs and four extractor agents. `import.md:311-319` openly admits it. The
only thing keeping a gazetteer from being built is the model choosing not to type
the command — which makes README:96's "Nothing else is pre-built" a hope.

## Acceptance criteria

- [ ] `is_playable()` is called from session start or scene context; an unconfirmed bible refuses with the review + confirm commands rather than playing
- [ ] `/new-game` Phase B actually runs `review` and `confirm`
- [ ] `conan`'s unconfirmed bible is resolved (confirmed retroactively or flagged)
- [ ] `normalize_pack` caps `present`/`exits` (refuse or truncate with a warning above ~6)
- [ ] `docs/flows/author-a-world.md:37` and `docs/modules/world-bible.md:99` match reality after the change
- [ ] The census verbs either move behind an explicit `--repairing-legacy-import` flag or are deleted

## Out of scope

Deleting the extractor agents outright — `write-index` has a sanctioned use.

## Verification

Lane: agent. A fresh campaign with an unconfirmed bible must refuse to start a
scene.

## Blocked by

Nothing.

---

## QA Reports

## History

- 2026-08-27T00:00:00Z  created → needs-triage  [readme-audit]
