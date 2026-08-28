---
type: Flow
title: Illustrating a scene
description: Beat to picture — the enablement gate, the background agent, and the two auto-injections that keep a campaign on-model.
sources:
  - { resource: /lib/image_gen.py }
  - { resource: /lib/visual_appearance.py }
  - { resource: /tools/gm-image.sh }
  - { resource: /.claude/agents/scene-illustrator.md }
generated: { by: claude-opus-5, at: 2026-08-28T02:22:39Z }
---

# Illustrating a scene

The image model has no memory between calls. Everything that makes a campaign's gallery
look like one artist drew one cast is state on disk, injected into every prompt.

## The path

1. **Gate.** The session brief reports `Scene images: ENABLED` or `DISABLED` based purely
   on `XAI_API_KEY` (or `OPENAI_API_KEY`) being set. Disabled means never call the tool and never mention
   images — an unmentioned absence, not an apology.
2. **Spawn `scene-illustrator` in the background** with a one-line beat brief and the
   campaign's locked art style passed verbatim. The slow API call stays off the critical
   path; narration continues.
3. The agent pulls appearances (`gm-image.sh appearance "<name>"`), writes the full prompt,
   and calls `gm-image.sh generate --character "<name>"` per character in frame.
4. **Deliver diegetically** — the picture is an artifact made by the in-world chronicler,
   not "here's an image".

## Two injections happen inside `build_prompt`, not in the prompt you write

`build_prompt` (`lib/image_gen.py`) assembles what actually goes to the model, and
`generate_image` calls it. It appends to the caller's prompt:

- **each named character's canonical appearance**, from the 11-field `visual_appearance`
  block, as `Character (render exactly): …`
- **the campaign's locked art style**, from `chronicler.json`, **PREPENDED** so it
  leads the prompt, with the caller's text following as `Scene: …`. It leads rather
  than trails because image models weight the opening far more heavily than the tail;
  a style appended after three sentences of scene description loses to the scene, and
  that is how a locked signature quietly renders as generic art.

Both are belt-and-braces: they fire even on a direct fallback call where the caller forgot.
The art style injection is guarded on the style string not already appearing in the prompt,
which is the right check.

**Both stay on by default, and the default is the right one** — the drift they prevent is
silent and cumulative, so the cost of a redundant injection is nothing and the cost of a
missing one is a gallery that stops looking like one artbook. Two flags open the door for
the beat where the lock is *wrong*, not merely redundant:

- `--no-style-lock` (`gm-image.sh generate`, `image_gen.py`) skips the art-style
  injection — a dream sequence, flashback, or in-world artifact rendered in another
  register.
- `--no-appearance-lock` skips the appearance injection for the **whole frame** — a
  transformation, disguise, or vision where the stored look is deliberately not what's
  in frame.

Use them per-image; neither changes anything on disk, so the next call locks again.

**A flag only governs the auto-append — the prompt author has to cooperate.**
`scene-illustrator` is instructed to open every prompt with the locked style verbatim and
to restate each character's appearance, precisely because the model has no memory. So
suppressing an injection while still writing the suppressed element into the prompt text
changes nothing. `.claude/agents/scene-illustrator.md` carries the matching rule: on a
deliberate break, pass the flag *and* leave that element out of the prompt.

For the common case — **one** character transformed or disguised while the rest of the
frame is normal — the per-character escape is better than the flag: omit `--character` for
that character only, keep it for everyone else, and describe the altered look in prose. The
frame-wide flag is for single-character frames or a whole scene that has left the world's
visual reality.

## The appearance injection fires whenever a character is passed and the lock is on (since 2026-08-13)

`inject_appearances` appends the stored block for every `--character` name, skipping only
an appearance line already present **verbatim** (idempotency). Until 2026-08-13 the guard
tested whether the character's *name* appeared in the prompt — and since beat prompts
naturally name their characters ("Carl swings the club..."), injection was silently
suppressed in the common case and recurring characters drifted off-model. Regression test:
`tests/test_image_prompt_injection.py`.

Practical rule for prompt authors now: just name people and pass `--character` — the
canonical look rides along regardless of how the prompt is worded. The only two ways it
does not ride along are deliberate: not passing `--character` for that person, or
`--no-appearance-lock`.

## The appearance block is a fixed, ordered field list

`VISUAL_FIELDS` is 11 keys in this order: race, sex, size, color, hair, eyes, face, shirt, pants, gear, short_description.
It is fixed so the PC and NPC paths cannot drift apart — one module
(`lib/visual_appearance.py`) normalizes, merges, and formats for both; the CLI flags on
`set-appearance` are generated from the tuple; and the extraction schema mirrors it
deliberately. `color` is skin/hide/chassis colour, "barefoot" belongs under `pants`, and
`short_description` is the silhouette that survives at thumbnail size (one shape, one
colour, one prop). `format_line` emits `key: value` pairs in fixed order — a spec sheet,
not prose — so the same character reaches the model as the same string every time. Legacy
blocks migrate on read: `clothing` → `shirt`, `species` → `race` when race is empty;
`age` appends onto `face` and `demeanor` onto `short_description` (they used to be
dropped — the d28fb34 regression that stripped Conan's age and movement on every render).
The stored data was migrated in place on 2026-08-28 by `lib/appearance_migrate.py
migrate` (idempotent; re-run it after restoring an old save). Any future field-set change
MUST ship a `migrate` pass in the same commit — the read-time shim alone leaves every
stored block losing content silently. `gm-npc.sh appearance-report` lists everyone whose
block is still blank and therefore refuses to render.

Author the block BEFORE the first image, never derived from one afterwards, and freeze it
afterwards — it changes only on an explicit in-world event (new armour, a scar, a
haircut). `generate` FAILS CLOSED: a `--character` with a blank block raises rather than
rendering, because an invented look that is never written down makes the second image of
that character a different person.

## Two gates, both fail closed

`generate_image` refuses rather than rendering something that will drift:

- **No art style locked** (`chronicler.json` has no `style`) → raises. The gallery
  signature is a per-campaign decision the PLAYER makes at world creation (`/new-game`
  Phase A asks, Phase D locks; `/import` Step 4; `/import-module` Step 8), never
  improvised per image. `--no-style-lock` is the deliberate escape for a dream or
  flashback.

`chronicler.json` is `{name, style, era, persona}`. `build_prompt` prepends `style` and
appends `era` and they do different jobs: style is the brush
(references, medium, palette, light), era is the props (century, tech level, what may
and may not appear in frame). Only `style` gates rendering; `era` is optional but is
what stops a modern badge landing on a bronze-age sheriff.
- **A `--character` with a blank `visual_appearance`** → raises, naming them and
  printing the `set-appearance` command. `--no-appearance-lock` is the deliberate
  escape for a transformation or disguise.

Both exist because the failure is silent otherwise: an un-styled render inherits the
image model's house look, and an un-authored character is invented once and forgotten,
so their next appearance is a different person.

## Cost is estimated locally and every render carries a price

`_COST` (`lib/image_gen.py`) is a hardcoded gpt-image-2 table keyed by quality × size,
used only for the spend log — nothing is billed here. The xAI path logs
`XAI_DEFAULT_COST_USD` (0.04, the figure play is budgeted around; `XAI_IMAGE_COST_USD`
overrides) — until 2026-08-28 it logged `None`, which the summer added as $0.00, so seven
real paid renders totalled "free". `gm-image.sh log` now reports any remaining unpriced
entries next to the total instead of silently folding them in. With `XAI_API_KEY` set the backend is xAI Grok Imagine (`XAI_IMAGE_MODEL`, default
`grok-imagine-image-quality`; no size/quality knobs, 3 retries, 90s timeout, and one
moderation-softening retry). Otherwise defaults are `gpt-image-2`, `medium`, `1536x1024`, each overridable
by env var. `gm-image.sh log` reads the per-campaign `_gen-log.jsonl`.

Logging is wrapped so it can never break a successful generation
(`lib/image_gen.py:194`) — so a missing log line does not mean a missing image.

## Related

- [Authoring a world](author-a-world.md) — where the chronicler and art style are locked
- [Scene context](../modules/scene-context.md) — where the ENABLED/DISABLED line comes from
