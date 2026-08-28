---
slug: third-door-reachable
title: /import-module is advertised but unreachable — /gm routes modules to /import
category: bug
kind: afk
priority: p0
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

The README sells three ways in. Only two are reachable from the front door, and
the third fails in the worst possible way: silently, by doing the other thing.

`grep -rn "import-module"` returns hits in `README.md` (5), `CLAUDE.md` (1, an
aside inside the image-style paragraph), `tickets/`, and two `docs/` files — and
**zero hits in `.claude/commands/gm.md` or `.claude/commands/help.md`**.

`gm.md:77` offers "IMPORT DOCUMENT (PDF, book, **or module**)" and `gm.md:80`
routes it unconditionally: `- If IMPORT DOCUMENT → Run /import`. A player who
picks the option whose label says "module" gets the RAG book pipeline — chunked,
embedded, world-bible drafted — which is precisely what `/import-module` exists
to avoid. `help.md:24` omits the command from its list and `help.md:57` actively
misdirects with `Import module:    /import`, while README:157 calls `/help` the
full command reference.

Fix the routing, fix the reference, and fix one false sentence about the command.

**The false sentence.** README:90 says `/import-module` involves "No embeddings,
no world-bible drafting." Both are wrong: Step 9 of `import-module.md` is a
required step that runs `gm-extract.sh add` (documented at `tools/gm-extract.sh:83`
as "Additively embed ANOTHER book into a campaign's RAG") and `index-from-module`,
which writes a minimal `confirmed: false` `world-bible.json` when none exists
(`lib/book_bible.py:261-269`). `import-module.md:244-247` explains why the
embeddings are mandatory. Proof on disk: `world-state/campaigns/whispering-wood/`
has a 2.2MB `vectors/` dir and a `world-bible.json`. The true distinction is that
the module is **sliced along the author's own scene boundaries rather than
chunked blindly**, and then embedded afterward so RAG still works at the table.

## Acceptance criteria

- [ ] `gm.md` routes the module case to `/import-module` — either a fourth menu option or a follow-up question when IMPORT DOCUMENT is chosen and the file looks like a keyed module
- [ ] `help.md:24` lists `/import-module` and `help.md:57` no longer routes modules to `/import`
- [ ] README:90's "No embeddings, no world-bible drafting" is replaced with the sliced-not-chunked distinction
- [ ] README's Getting Started paragraph (line 123) either covers the module path or says plainly that it is the one door `/gm` does not open
- [ ] Picking the module option at the `/gm` menu with a keyed module PDF produces an `adventure.json` spine, not a `chunks/` dir

## Out of scope

Auto-detecting module vs novel from the PDF itself. Asking the player is fine.

## Verification

Lane: agent. Run the `/gm` menu path with a keyed module and confirm the spine
is what lands.

## Blocked by

Nothing.

---

## QA Reports

## History

- 2026-08-27T00:00:00Z  created → needs-triage  [readme-audit]
