---
slug: kit-phrasing-followup
title: Sweep dead-branch kit phrasing from docs and tool help text
category: enhancement
kind: afk
priority: p2
lane: agent
parentPrd: 5e-native-fork
blockedBy: [kit-residue-sweep]
claimedBy: null
claimedAt: null
changedFiles: []
resolution: null
reviewRounds: null
implementer: null
createdAt: 2026-08-19T19:12:00Z
updatedAt: 2026-08-19T19:12:00Z
---

## Parent

5e-Native Fork (prds/5e-native-fork.md)

## Category

enhancement

## What to build

Review-round follow-ups from kit-residue-sweep — dead-branch phrasing, not false
statements, so lower urgency:
- docs/modules/player-character.md:52-56 — "writes a 5e saves block only when the
  active kit is dnd5e" / "preserved verbatim in every kit" describes a variable
  kit that cannot vary (the code branch exists but kit() is hardcoded). Also
  consider simplifying the is_dnd5e branch in save_character.py:117 itself
  (mention-only dead code rule applies — ask before removing).
- docs/flows/play-turn.md:30 — "resolve through the active World Kit, never a
  hardcoded rule set" is now precisely inverted.
- tools/gm-session.sh:75 and tools/gm-player.sh:96 — help text names ruleset.json
  / a per-book World Kit that no longer exists.

## Acceptance criteria

- [ ] Neither doc describes a variable per-book kit; restamped after re-read
- [ ] Tool help text no longer names ruleset.json or per-book kits
- [ ] Suite passes (bar the environmental sibling-repo failure)

## Verification

Lane: agent

## Blocked by

kit-residue-sweep

---

## QA Reports

## History

- 2026-08-19T19:12:00Z  created → needs-triage (source: review-kit-residue round 2)  [ss-5efork]

## Additional residue (from the final kit-residue round)

- tools/gm-session.sh:78-79 still READS $CAMPAIGN_DIR/ruleset.json to derive a
  KIT_NAME — a live read, not just help text.
- docs/modules/player-character.md:35/40/79 describe vitals and XP thresholds as
  coming from ruleset.json.
- gm_claude.egg-info/PKG-INFO carries the old README paragraph — build artifact,
  regenerates; ignore.
