---
slug: image-cost-logging
title: Image spend logs as null on the default path — gm-image.sh log reports $0.00 for real money
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

README:229 promises "Every generation is logged with an estimated cost; run
`gm-image.sh log` for the running total." The logging half works. The cost half
is broken on the path that runs by default, and it under-reports to zero rather
than failing loudly.

`_log_generation` appends a JSON line per render (`lib/image_gen.py:200-206`) and
`tools/gm-image.sh:145-159` sums them. But the `_COST` table at
`lib/image_gen.py:135-139` carries **gpt-image-2 pricing only**. On the xAI path,
`lib/image_gen.py:351-356` sets cost to `None` unless the operator has set
`XAI_IMAGE_COST_USD`, and the summer coerces `None` to `0.0`
(`tools/gm-image.sh:155`). Since xAI is selected whenever `XAI_API_KEY` is
present (`lib/image_gen.py:275-283`), that is the default path.

This is live, not theoretical. All 8 real generations across the four campaigns
carry `est_cost_usd: null`, and `gm-image.sh log` against whispering-wood's 7
real images reports **`Total estimated spend: $0.00`**. CLAUDE.md's own "~$0.04
an image" figure is the gpt-image-2 medium price, which nothing on the live path
uses.

A running total that reads `$0.00` after seven paid renders is worse than no
total, because it reads as "free."

## Acceptance criteria

- [ ] xAI renders log a real `est_cost_usd`; `XAI_IMAGE_COST_USD` becomes an override, not the only source
- [ ] `gm-image.sh log` prints the count of unpriced entries alongside the total, so `$0.00` can never be mistaken for free
- [ ] Existing null-cost entries are either backfilled or reported as "N unpriced" rather than silently summed as zero
- [ ] The per-quality prices in `_COST` cover both providers, and CLAUDE.md's "~$0.04" figure matches whichever provider is actually default

## Out of scope

A spend cap or a budget prompt. Report honestly first.

## Verification

Lane: agent. `gm-image.sh log` against whispering-wood must stop saying $0.00.

## Blocked by

Nothing.

---

## QA Reports

## History

- 2026-08-27T00:00:00Z  created → needs-triage  [readme-audit]
