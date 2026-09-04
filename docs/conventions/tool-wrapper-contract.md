---
type: Convention
title: The tool wrapper contract
description: Every capability is a bash wrapper over a Python manager over per-campaign JSON — and every manager speaks the same --json envelope.
sources:
  - { resource: /tools/common.sh }
  - { resource: /lib/cli_output.py }
  - { resource: /lib/campaign_manager.py }
  - { resource: /tools/gm-extract.sh }
  - { resource: /lib/agent_extractor.py }
  - { resource: /lib/json_ops.py }
  - { resource: /tests/test_json_wrappers_onboard.py }
generated: { by: claude-opus-5, at: 2026-08-26T18:46:07Z }
verified: { by: claude-fable-5, at: 2026-08-13T15:15:46Z }
---

# The tool wrapper contract

Three layers, no exceptions: **`tools/gm-*.sh` → `lib/*.py` → per-campaign JSON**. The
wrapper resolves the interpreter and the campaign; the manager holds the logic; state lives
on disk as plain JSON under `world-state/campaigns/<name>/`.

Always invoke as `bash tools/gm-<tool>.sh <command>`, never the Python directly — the
wrapper is what supplies the campaign resolution below.

## What `common.sh` guarantees before a manager runs

Every wrapper sources it, and inherits (`gm-migrate-campaigns.sh` did not until
2026-09-03 — it hardcoded the live tree, so a pinned test run migrated the player's
campaign. `gm-statusline.sh` still reads the live tree directly: it is the terminal
status line, not a game tool, and has no campaign to isolate):

- **Environment files** — `.env` then `.env.local` are sourced with `set -a`, so their keys
  reach the Python side as real environment variables. `.env.local` loads second and wins;
  it is the gitignored one, which is where secrets like `XAI_API_KEY` belong.
- **`PYTHON_CMD`** — `uv run python` if `uv` is on PATH, else `python3`, else `python`.
  This is why project instructions say never to call bare `python`: the wrapper already
  chose, and choosing differently skips the venv.
- **Path anchoring** — `PROJECT_ROOT` is derived from the script's own location, and
  `common.sh` then **`cd`s there**, so tools work from any working directory. Deriving the
  root is not enough on its own: with no `GM_WORLD_STATE_BASE` in the environment the
  Python side falls back to the *relative* path `world-state`, which resolves against
  whatever directory the caller was in — `cd /tmp && bash <repo>/tools/gm-note.sh
  categories` reported no active campaign and left a stray `/tmp/world-state/` behind. The
  `cd` is what closes that, for every wrapper at once. Because it moves the process,
  `common.sh` first saves the caller's directory as **`CALLER_PWD`**: any verb taking a
  path argument must resolve a relative one against **two anchors, in order** —
  `CALLER_PWD` first, then `PROJECT_ROOT` — and only then report it missing, naming both
  places it looked. Both anchors are real: a human types a path relative to their own
  directory, while a *tool* emits one relative to the project root every wrapper now
  stands in. A tool that emits a `world-state/campaigns/<name>/authored-canon.md`
  binder and pipes it straight into `gm-extract.sh prepare <document>` (today's only
  such verb) would, with `CALLER_PWD` as the sole anchor, fail from every directory but
  the repo root.
- **`WORLD_STATE_BASE`** — `$PROJECT_ROOT/world-state`, unless `GM_WORLD_STATE_BASE` is
  set in the environment, which wins. That env var is the isolation seam: the Python side
  honours it too (`resolve_world_state_base`, `lib/campaign_manager.py`) whenever a manager
  is constructed without an explicit directory, so exporting it moves a whole wrapper +
  manager run onto another world-state tree. Tests that drive the real wrappers point it at
  a tmp tree instead of mutating the player's live campaign.
  The `cd` sharpens the trap on the other side of that seam: a manager that BYPASSES
  `resolve_world_state_base` (as `AgentExtractor` did — it takes its default raw) resolves
  `world-state` to the **live** tree no matter what the environment says.
  `lib/agent_extractor.py` did exactly that and wrote whole campaigns
  into the developer's world-state during tests, so the rule is that a wrapper hands its
  manager the base explicitly — `--world-state "$WORLD_STATE_BASE"` (`gm-extract.sh`)
  or a `$CAMPAIGN_DIR` built from it.
- **`require_active_campaign`** — multi-campaign support is a single file,
  `world-state/active-campaign.txt`. Every tool reads it; nothing takes a campaign
  argument by default. It is the ONLY campaign guard (`gm-extract.sh`'s `require_campaign`
  is a name *resolver* — explicit-arg-else-active — not a guard copy): wrapper-local copies drift out of
  sync with it (three once did, and kept telling the player to run `/new-game` when the
  real fix was `gm-campaign.sh switch`), so the failure text lives in `common.sh` and names
  both repairs — activate a campaign on disk, or start a fresh adventure. A wrapper adds
  only its own routing around the call: usage and mistyped verbs answer BEFORE the guard so
  a typo reports itself as a typo (`gm-session.sh`), and a verb that legitimately runs
  pre-activation takes an explicit campaign name in any argument position instead
  (`gm-extract.sh`'s campaign-named verbs).

## The `--json` envelope is the machine contract

`lib/cli_output.py` defines two shapes and nothing else:

```json
{"ok": true,  "data": …}
{"ok": false, "error": "…", "code": null}
```

The rationale is in the module's own docstring: it exists to kill stdout-scraping, without
adding an MCP process. The wiring pattern for a new manager is fixed —
`wants_json()` to detect, `strip_json_flag()` before argparse (so argparse never sees
`--json`), `emit()` / `emit_error()` to output. `emit_error` returns `1` so callers write
`sys.exit(emit_error(...))`.

The exit code is part of the envelope: `ok: false` means a nonzero exit, so a script can
gate on `$?` without parsing. A manager that prints its own `{"ok": false}` dict (rather
than going through `emit_error`) has to set the exit itself — `lib/play_pack.py` did not
until 2026-09-03, so `gm-playpack.sh stage` on an empty pack printed a failure and exited 0.

One trap the existing code already works around: a manager whose logic `print()`s human
text must suppress that in JSON mode or the envelope is preceded by garbage.
`consequence_manager` does this with `contextlib.redirect_stdout`
(`lib/consequence_manager.py:430`). Any manager that prints inside its logic needs the
same treatment.

`DM_JSON=1` turns the envelope on globally, which is the easy way to script a whole
sequence.

## Input validation is a manager concern, not a wrapper one

`lib/validators.py` holds the shared input guards (names, attitudes, dice notation) that
managers call before writing. The wrapper layer validates almost nothing — `common.sh` has
a `validate_name`, but the real trust boundary is inside the Python. A manager that skips
`Validators` writes whatever it was handed straight to disk.

## Enforcement point

There is no envelope test family, and the `--json` wiring ticket in
`tests/test_cli_output_json.py`'s docstring — per-manager coverage for session, consequence,
player and npc — was never finished. What exists is one wrapper-level test,
`tests/test_json_wrappers_onboard.py`: it runs `bash tools/gm-player.sh onboard` as a real
subprocess against a hermetic `GM_WORLD_STATE_BASE` tree and asserts both envelope shapes —
`ok: true` with the expected `data`, and `ok: false` with the refusal text on the
clobber guard. One wrapper, one verb.

The rest of the coverage is incidental, and worth knowing the shape of before trusting it:

- `tests/test_adventure.py` and `tests/test_combat_manager.py` also drive real wrappers
  (`gm-adventure.sh advance --json`, `gm-combat.sh add-enemy --json`) and assert the
  envelope, but only on the verbs those suites happen to exercise.
- `tests/test_world_tick.py` and `tests/test_story_escape_hatches.py` assert the envelope
  off `lib/world_tick.py` and `lib/player_manager.py` run directly. That checks `emit`, not
  the wrapper — everything `common.sh` guarantees above is skipped.
- `tests/test_cli_output_json.py` covers the `cli_output` primitives themselves and touches
  no wrapper at all.

So a new manager gets no envelope enforcement unless someone writes it, and most existing
ones have none either. Adding the test is part of adding the tool.

## Related

- [A play turn](../flows/play-turn.md) — where these calls sit in the loop
- [Persist before narrate](persist-before-narrate.md) — when to call them
