---
slug: diegetic-adaptation-craft
title: Prose rules: invisible seams, prep ritual, pressure-not-rail
category: enhancement
kind: afk
priority: p2
lane: manual
parentPrd: module-fidelity
blockedBy: []
claimedBy: ss-modq26
claimedAt: 2026-08-26T18:43:31Z
changedFiles: [.claude/skills/gm-craft/SKILL.md, lib/session_manager.py, CLAUDE.md, docs/flows/play-turn.md, tests/test_dossier.py]
resolution: 4 craft rules with GOOD/BAD pairs in gm-craft; deterministic GM-private prep block at session start (must honor / will test / do not contradict / strong start), guarded per-source; ships with dossier/brief clock-renderer hardening in shared files
reviewRounds: 2
implementer: null
createdAt: 2026-08-26T18:50:00Z
updatedAt: 2026-08-26T18:50:00Z
---

## Parent

module-fidelity — prds/module-fidelity.md

## Category

enhancement

## What to build

The craft-layer prose rules, in gm-craft SKILL.md + CLAUDE.md (no runtime code):
(1) Adaptation is resolved diegetically, every time — fewer guards because of
the fever, never "the module assumes four." The adaptation note is GM-private;
origin tags never appear in narration. (2) Session-start prep ritual: three
generated lines (tonight must honor / will test / must not contradict) + ONE
strong start (a concrete opening image), sourced from dossier + chronicle +
next scene contracts; add to the /gm CONTINUE CAMPAIGN startup and
gm-session.sh start output. (3) Lookahead is pressure, never rail: the STORY
COMING UP section and deadlines inform pacing and foreshadowing; steering the
player toward the next scene is named as the failure mode. (4) The world moves
to the party: getting back on rails is done by moving scenes/clues to the
player and letting the villain's timetable act, never by steering.

## Acceptance criteria

- [x] gm-craft carries the four rules with examples (good/bad pairs)
- [x] gm-session.sh start prints the prep lines + strong start from live state
- [x] CLAUDE.md startup checklist references the prep ritual
- [ ] Manual review: one played scene with an active adaptation reads seam-free (human judgment, QA note)

- [x] (review) On a campaign with chronicle.md and no adventure.json, the strong-start line does not repeat the must-honor line
- [x] (review) start_session exits 0 with malformed clock/consequence/fact/overview values — prints what it can, omits the rest
- [x] (review) The strong-start image draws only from read_aloud; empty read_aloud yields no image rather than gm_notes
- [x] (review) _prep_sentence cuts at the earliest of ./!/? and never returns a leading-abbreviation fragment
- [x] (review) Do-not-contradict draws only from KEY_FACT_CATEGORIES; dropped_references never appears

## Out of scope

Any extraction/schema work; automated seam detection.

## Verification

Lane: manual

## Blocked by

None.

---

## QA Reports

### 2026-08-26T19:33:01Z — pass [rev-craft-2]
reviewed: perfect
Notes (non-blocking): empty consequence body renders an empty pressure clause; a non-string fact/timestamp can displace real facts from do-not-contradict; _PREP_MIN_WORDS counts abbreviations; whole=True still cuts mid-word at the char cap (deferred, noted for requires-sweep-hardening-adjacent cleanup).
[human-judgement] seam-invisibility of a played adapted scene awaits a human QA note.

### 2026-08-26T19:05:32Z — fail [rev-craft]
reviewed: needs-changes
- session_manager _prep_block: no-adventure fallback echoes the chronicle line as the strong start (majority /new-game path); untested combination
- session_manager start_session: _prep_lines unguarded — malformed clock value (non-numeric current) raises and kills the whole start command; every sibling line-builder has try/except-return-[]
- session_manager: empty read_aloud falls back to gm_notes as the opening image — GM bookkeeping offered as the thing to open on
- session_manager _prep_sentence: first-pattern-found instead of earliest boundary; 'Dr. Sallow met them.' truncates to 'Dr.'
- latent: 'Do not contradict' sweeps all categories incl. dropped_references import diagnostics; filter to KEY_FACT_CATEGORIES
- nits: inline scene lookup duplicates _adventure_lines helper; play-turn.md restamp dropped the [1m] suffix

### 2026-08-26T18:56:52Z — verified [ss-modq26]
4 rules with 8 GOOD/BAD lines at gm-craft:43; live prep block verified twice against whispering-wood (must-honor from chronicle, do-not-contradict from facts, strong start from scene 1.2, will-test correctly absent — no clocks); CLAUDE.md 1 ref; play-turn.md restamped, okf check 27/0/0; 7/7 dossier tests. [human-judgement] seam-invisibility of a played adapted scene awaits human QA note.

## History

- 2026-08-26T18:43:31Z  claimed  [ss-modq26]

- 2026-08-26T18:50:00Z  created → ready  [ss-modfid]
