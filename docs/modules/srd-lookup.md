---
type: Module
title: The SRD lookup layer
description: How features/ answers a rules question — one cached HTTP host, one script per question a table asks, and the resolution rule every one of them has to follow.
sources:
  - { resource: /features/dnd-api/dnd_api_core.py }
  - { resource: /features/rules/get_rule.py }
  - { resource: /features/rules/list_rules.py }
  - { resource: /features/rules/combat_rules.py }
  - { resource: /features/gear/dnd_equipment.py }
  - { resource: /.claude/agents/rules-master.md }
  - { resource: /.claude/agents/monster-manual.md }
  - { resource: /tests/test_srd_lookup_resolution.py }
generated: { by: claude-opus-5, at: 2026-09-03T00:00:00Z }
verified: { by: claude-opus-5, at: 2026-09-03T00:00:00Z }
---

# The SRD lookup layer

Everything under `features/` exists so that no number in the game is recalled from
the model's memory. It is a thin shell over one host.

## One host, one fetch, one cache

`dnd_api_core.fetch()` is the only thing that opens a socket. `features/rules/` and
`features/spells/` import it rather than defining their own client, so there is a
single place where the host, the timeout and the cache live.

- Host: `https://www.dnd5eapi.co`, base path `/api/2014`.
- Cache: `features/dnd-api/cache/<slugified-endpoint>.json`, written atomically via
  a tempfile and `os.replace`. **No TTL** — the SRD 2014 corpus is immutable, so a
  cached response is never refetched. Delete the file to force a refetch.
- Errors are returned, never raised: `{"error": "HTTP 404", ...}`. Callers branch on
  `data.get("error")`, which is why the resolution rule below is written the way it is.

The cache directory is gitignored. Warm it once and the table runs offline.

## The resolution rule

**A lookup returns the answer, or it returns the list. It never returns a name it
would itself refuse to fetch.**

This is not style. Three scripts violated it in the same way and every one of them
produced a dead end mid-play: fetch an exact index, take the 404, find the entry in
a second pass, and print its name as a "did you mean" — at which point feeding that
name back in 404'd too, because the name was in a collection the tool never fetched
from.

The shape that works, in `get_rule.py`, `dnd_equipment.py` and `combat_rules.py`:

1. Exact index hit wins.
2. On a miss, search by NAME across every collection that could hold it.
3. Exactly one match is the answer — fetch it and return it.
4. Several matches: return them and ask, since guessing between "Longsword" and
   "Shortsword" is worse than one more round trip.
5. No match: return the full index of what does exist. A miss is usually a topic the
   SRD files under a broader heading, so the list is the useful reply.

`tests/test_srd_lookup_resolution.py` pins all five branches against a stubbed
`fetch`, offline.

## The trap: /rules is not the rules

The API splits rules across two collections that read like the same thing:

| Endpoint | Holds | Count |
|---|---|---|
| `/rules` | Broad chapters — Combat, Equipment, Spellcasting, Adventuring, Appendix, Using Ability Scores | 6 |
| `/rule-sections` | The specific ones — Cover, Advantage and Disadvantage, Saving Throws, Actions in Combat | 33 |

Almost everything a GM asks about mid-play is a **section**, not a chapter. A lookup
or a search that reads only `/rules` is searching six chapter titles and will find
nothing; that is exactly why `list_rules.py --search stealth` used to return zero.
Anything that resolves or searches rules must span both.

Note also what has no entry at all. "Opportunity attacks" is real 5e prose living
inside `Actions in Combat`'s body text, and name search cannot reach body text — so
the honest reply is the heading list, and the caller picks. Skills are the same
story: stealth is not a rule section, it is `features/rules/skills.py stealth`.

## The book outranks all of this

The SRD is the **fallback**, never the first stop. Every agent with API access
(`rules-master`, `monster-manual`, `spell-caster`, `gear-master`) carries the same
BOOK-GROUNDED ORDERING block, and the order is: the imported book via
`gm-search.sh --rag-only`, then the campaign's own `campaign_rules` / `rules.md`,
then the SRD for whatever the book left silent. A module that names its own trap DC
has named it; the SRD does not get a vote. What the SRD is for is making sure the
answer is never *invented* when the book is quiet.

Keep that ordering in the agent files when you touch them. It is the only thing
stopping a generic goblin from overwriting the one the book described.
