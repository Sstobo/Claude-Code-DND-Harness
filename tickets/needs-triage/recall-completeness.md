---
slug: recall-completeness
title: Recall never indexes the chronicle, degrades to keyword in silence, and has no relevance floor
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

README:36 promises semantic recall and gives an example. The mechanism is
**genuinely real** — this is not a fake. `lib/campaign_memory.py:146-163` embeds
the query with `all-MiniLM-L6-v2` (384-d, `lib/rag/embedder.py:27`) and ranks
stored vectors by cosine. Tested against a corpus with zero content-word overlap:
`"the smuggler from the docks"` ranked the right entry #1 at cosine +0.431, and
`"who was the criminal we hired at the port"` ranked it #1 at +0.371. Meaning-
based retrieval works.

Three gaps sit around it.

**It never indexes the chronicle.** `gather()` reads only `session-log.md` blocks
containing `### Session Ended:` plus `facts.json`
(`lib/campaign_memory.py:31-64`). `chronicle.md` — the primary narrative record,
the thing CLAUDE.md tells the GM to append to at every scene close — is invisible
to recall. So "it finds the session where you met her" only works if she made the
end-of-session summary or got filed as a fact. A chronicled meeting is
unfindable, which is close to the opposite of the promise.

**It degrades to keyword in silence.** `sentence-transformers` is an optional
extra (`pyproject.toml:43-47`); `_embed_batch` returns `None` on ImportError
(`lib/campaign_memory.py:121-130`) and `recall()` falls through to word-overlap
matching (`:143`). The output carries no indication of which mode ran, so a
`uv sync` without extras gives keyword matching under a README promising
semantics — and nothing tells anyone.

**No relevance floor.** The nonsense query `"quantum chromodynamics tax filing"`
returned 3 confident entries from the semantic path. The keyword path correctly
returned 0. Recall always returns something, which means it can always mislead.

Crash path in the same function: `lib/campaign_memory.py:152` calls
`LocalEmbedder().embed(query)` **outside** its own try/except, so a campaign with
stored embeddings whose `sentence-transformers` was later removed raises instead
of falling back.

**And the arc entry is never written automatically.** `add_arc` is real
(`lib/campaign_memory.py:72-84`), exposed as `gm-recall.sh arc`, and arcs join the
recall index immediately (`:237`). But `end()` writes only the session-log block
and never calls it (`lib/session_manager.py:170-190`); its sole production caller
is the CLI. `tools/gm-session.sh:126-129` merely *prints* `"Arc entry
(REQUIRED …)"` and exits 0 regardless. README:36 says "At session end the GM
writes an arc entry" — a session that ends without the model choosing to run the
command has no arc, and nothing detects that.

## Acceptance criteria

- [ ] `gather()` indexes `chronicle.md` entries alongside session summaries and facts
- [ ] A cosine floor (~0.25) suppresses non-matches; a nonsense query returns nothing
- [ ] The result stamps which mode ran (semantic vs keyword) so a degraded install is visible
- [ ] `sentence-transformers` moves into core deps, or the degraded mode warns loudly on first use
- [ ] `lib/campaign_memory.py:152` falls back instead of raising when the embedder is gone
- [ ] `session_manager.end()` requires or auto-synthesizes the arc entry; ending without one is not silently possible

## Out of scope

Re-ranking or hybrid search. Indexing the right corpus and refusing bad matches
is the deliverable.

## Verification

Lane: agent. The three probe queries above are the regression suite, plus one
chronicle-only event that must become findable.

## Blocked by

Nothing.

---

## QA Reports

## History

- 2026-08-27T00:00:00Z  created → needs-triage  [readme-audit]
