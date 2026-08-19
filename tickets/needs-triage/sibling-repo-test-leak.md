---
slug: sibling-repo-test-leak
title: pytest resolves test modules from the sibling Claude-Code-Game-Master repo
category: bug
kind: afk
priority: p1
lane: agent
parentPrd: null
blockedBy: []
claimedBy: null
claimedAt: null
changedFiles: []
resolution: null
reviewRounds: null
implementer: null
createdAt: 2026-08-19T16:30:00Z
updatedAt: 2026-08-19T16:30:00Z
---

## Parent

None (environment/intake).

## Category

bug

## What to fix

`uv run python -m pytest tests/test_get_full_context.py` in THIS repo executes
the sibling repo's module — the failure traceback resolves to
`../Claude-Code-Game-Master/tests/test_get_full_context.py:44`. Both ship-it
sessions independently confirmed the failure exists at the pristine baseline
(ddee691) and follows the sibling file. Same-named test modules with no
`tests/__init__.py` make pytest's rootdir/import machinery pick the sibling's
cached module, so every agent's "pre-existing failure" signal is polluted.

Likely fixes (pick smallest that works): add `tests/__init__.py`, or set
`consider_namespace_packages`/`importmode=importlib` in pyproject's pytest
config, or clear stale `__pycache__`. Verify by asserting the traceback path
stays inside this repo.

## Acceptance criteria

- [ ] `uv run python -m pytest tests/ -q` imports every test module from THIS repo (no `../Claude-Code-Game-Master` path in any traceback).
- [ ] `test_action_menu_on_is_a_few_numbered_not_exactly_three` passes or fails on this repo's own code, and the outcome is explained.

## Out of scope

Touching the sibling repo.

## Verification

Lane: agent

## Blocked by

None.

---

## QA Reports

## History

- 2026-08-19T16:30:00Z  created → needs-triage (filed during import-module run; confirmed by both active ship-it sessions)  [ss-imod01]
