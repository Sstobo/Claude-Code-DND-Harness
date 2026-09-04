---
type: Module
title: The World Bible
description: The fidelity spine a world is played from — what it must contain, the draft-then-confirm gate, and the campaign rules drafted out of it.
sources:
  - { resource: /lib/world_bible.py }
  - { resource: /lib/book_bible.py }
  - { resource: /tools/gm-extract.sh }
generated: { by: claude-opus-5, at: 2026-08-25T19:02:00Z }
verified: { by: claude-fable-5, at: 2026-08-13T15:15:27Z }
---

# The World Bible

`world-bible.json` is what makes playing Dune feel like Dune rather than d20-fantasy in a
desert. It is authored once (drafted from the book by `gm-extract.sh draft-bible` on
`/import`, written from the seed on `/new-game`) and then read constantly: the **voice**
block reaches the model every beat, and the **signature systems** become the campaign
rules the GM is told to follow exactly.

## Half deterministic, half authored — and the seam is the point

`draft_bible` (`lib/book_bible.py:137`) writes only what the source can prove: the
verbatim-filtered voice block and the skeleton keys `validate_bible` demands. It also
scaffolds an empty `index` — the named-thing roster, four buckets (`npcs`, `locations`,
`items`, `monsters`), each entry a `{"name","note"}` pair with a one-sentence note (a
later ticket populates it; the drafter only lays the empty structure). `tone`, `themes`,
`factions`, `geography` and `signature_systems` are the **model's** authorship, merged in
by re-running the same verb with `--fields-json`. That is why the verb is idempotent:
scaffold, read the book, merge, merge again.

## A converted module derives its index instead of drafting one

`draft_bible` reads `source/current-document.txt`, which `/import-module` never
produces — it slices a PDF into scenes and converts those, and nothing writes the
book back out as text. So a module campaign had no bible, and with no bible the
WORLD INDEX block in scene context silently did not render: a whole session played
with no roster to check a name against. `derive_index_from_module`
(`lib/book_bible.py`) closes that by building the index out of what the import
already persisted — `npcs.json` plus every scene's `location`, `encounters[].monsters`
and non-coin `treasure` — and seeding a minimal `confirmed: false` bible when none
exists, so a later `draft-bible` can still enrich it. Nothing is hand-authored by an
agent, which is what keeps the index true to the book. Exposed as
`gm-extract.sh index-from-module`, idempotent, and a required step of `/import-module`.

The rail matters because retrieval is the thing it guards against: RAG chunks cross
PDF page columns and will splice two unrelated paragraphs into one fluent sentence,
carrying a **real** name in a **false** arrangement. The index is what lets the GM
catch that before it reaches the page.

As of 2026-08-15 the bible no longer persists a `chapters` array. `draft_bible` used to
write one derived from `segment_into_chapters`; it stopped, in favor of the `index`. The
splitter itself is untouched — see "Chapter segmentation is shared" below.

It refuses to touch a bible whose `confirmed` flag is absent or true
(`lib/book_bible.py:151`) — the same rule `WorldBible.is_confirmed` reads, so a
hand-authored or approved bible can never be flattened by a re-import.

## The bible is upstream of the campaign rules

`bible_to_campaign_rules` wraps the bible's `signature_systems` and tone in a "follow
them exactly" instruction and `write_campaign_rules` lands it on
`campaign-overview.json` → `campaign_rules`, where scene context renders it as YOUR
WORLD'S RULES. From the shell that is `gm-extract.sh campaign-rules`, which is how
`/import` and `/new-game` call it.

This is the **only** mechanical artifact the bible drafts. Mechanics themselves are 5e
for every world — `lib/world_kit.py` returns a hardcoded kit and there is no
per-campaign `ruleset.json` to draft, so a book's signature systems reach the table as
prose the GM plays by, resolved on the same d20. See
[game core and World Kit](game-core-and-world-kit.md).

## Voice is grounded by a verbatim filter

`draft_voice` keeps a sample passage **only if it appears verbatim in the source text**
(`lib/book_bible.py:87-88`). This is the mechanism that stops an imported book's voice
from being the model's impression of the author instead of the author. Two consequences:

- A near-miss passage — reflowed whitespace, smart quotes, an OCR artifact — is silently
  dropped. An empty `sample_passages` after a voice pass usually means the passages were
  paraphrased or the text was normalized, not that the book has no voice.
- `/new-game` worlds have no source text to check against, so their voice block is
  authored rather than filtered.

## The confirm gate blocks fresh drafts only

`is_confirmed()` returns `True` when the flag is **absent** (`lib/world_bible.py:85`).
That default is the whole design: hand-authored and legacy bibles are playable
immediately, and only a freshly auto-drafted bible carrying `confirmed: false` is held
for human review. A campaign with no bible at all is playable — that is the `/new-game`
path before consolidation.

The gate is closed by a person, not by the pipeline: `world_bible.py review` prints the
draft and `world_bible.py confirm` stamps it, and both `/import` and `/new-game` put a
human between them. Nothing in the runtime confirms a bible on its own.

`validate_bible` requires `name`, `voice`, `tone`, `themes`, `factions`, `geography`,
`signature_systems`, with factions and geography shaped as graphs. Missing keys fail
validation but do **not** block play; only the confirm flag does.

## Chapter segmentation is shared, and prefers real markers

`segment_into_chapters` still lives in `lib/book_bible.py`, but as of 2026-08-15 it feeds
only [the coarse index](rag-stack.md) (`lib/rag/coarse_index.py:47`) — it no longer
populates the bible. It needs **two or more** chapter markers before it will split on them; with fewer, the
entire book becomes one span, then gets cut into 20,000-character windows titled
`Part N`. A marker is `Chapter N` / `Part N` / `1. ` at the **end of a line**, or a line
that is a title in caps (`THE TOWER OF THE ELEPHANT`). A caps line that is the rest of a
drop-capped sentence ("ORCHES FLARED MURKILY ON", preceded by the lone initial "T the
revels…" and followed by lowercase) is not a marker at all, and neither is a caps line
sitting directly under running text or verse — that is an epigraph's attribution ("OLD
BALLAD", "THE ROAD OF KINGS"), which until 2026-09-04 stood as a chapter of its own. The
numbered form stops at three digits, so a front-matter "1935. Reprinted by permission…"
is not chapter 1935. Short caps-title spans — the
title line itself, an epigraph attribution — fold into the body that follows, keeping the
first title; a chapter longer than a window is labelled `(i/n)`.

Until 2026-09-04 caps titles were not markers and `part\s+\w+` was unanchored, so the Conan
collection was one span in 20k windows, each titled by its first sixty characters
("Count. There was an edge of") with nine false breaks on sentence-initial "part of the".

## Related

- [Importing a book](../flows/import-a-book.md) — where the bible is drafted and confirmed
- [Authoring a world](../flows/author-a-world.md) — where it is written from a seed instead
- [Scene context](scene-context.md) — how the voice block reaches the model
