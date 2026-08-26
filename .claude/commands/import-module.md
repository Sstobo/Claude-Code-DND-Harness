# /import-module — run a published adventure as written

`/import` puts a *book* on the shelf and opens one door into it. This command is
for the other thing: a **published adventure module** with numbered scenes, boxed
read-aloud text, keyed encounters, and a map. Those are already cut into scenes
by their author, so we convert them into a scene spine the GM walks — no
embeddings, no RAG, no census.

The result is `adventure.json`: an ordered spine, converted scene bodies, and a
pointer at where the table is. It rides into every scene as the ADVENTURE block,
and `bash tools/gm-adventure.sh advance|jump` moves the pointer.

## Usage

```
/import-module <file-path> [campaign-name]
```

- `file-path` — the module PDF
- `campaign-name` — optional (a short name from the module title: `whispering-wood`)

**This command never runs `gm-extract.sh prepare`, never builds embeddings, never
runs the extractor swarm, and never drafts a ruleset.** Mechanics are 5e, hardcoded.

---

## Step 1: Get the file

If arguments weren't provided, check `source-material/`:

```bash
ls -la source-material/ 2>/dev/null | grep -E '\.pdf$'
```

List what you found, or ask them to drop a file / paste a path. Then ask for a
campaign name (or take a short one from the module's title — not the dump filename).

---

## Step 2: Create/switch the campaign

Same guard as `/import` Step 2. Every tool below resolves against the ACTIVE
campaign, so a silent mismatch would write the module into someone else's game.

```bash
bash tools/gm-campaign.sh switch "<campaign-name>"

EXPECTED=$(uv run python lib/campaign_manager.py slugify "<campaign-name>")
ACTIVE=$(bash tools/gm-campaign.sh active)
ACTIVE_SLUG=$(uv run python lib/campaign_manager.py slugify "$ACTIVE")
if [ "$ACTIVE_SLUG" != "$EXPECTED" ]; then
    echo "MISMATCH — active is '$ACTIVE', expected '$EXPECTED'" >&2
    exit 1
fi
CAMPAIGN_DIR=$(bash tools/gm-campaign.sh path)
```

**If this block exits non-zero, STOP.** Do not slice, do not spawn agents.

(If `switch` reports no such campaign, create it first — `bash tools/gm-campaign.sh
create "<campaign-name>"` — then re-run the guard.)

---

## Step 3: Slice the module into scenes

Shell state does not survive between blocks, so re-derive the campaign dir in
every block that needs it (the house pattern — see `/import` Step 4).

```bash
CAMPAIGN_DIR=$(bash tools/gm-campaign.sh path)
uv run python lib/adventure_import.py slice "<file-path>" --out "$CAMPAIGN_DIR/module-work"
```

This writes `spine.json` plus one `scene-<key>.txt` per scene into
`$CAMPAIGN_DIR/module-work/`, and prints the spine it found.

**Read its stderr and tell the player what it says.**

- `WARNING: this PDF could not be read column by column…` — the text is
  interleaved and the slices are unreliable. Say so plainly before converting:
  the conversion will be as garbled as its input. Offer to continue anyway or to
  try a different copy of the PDF.
- Listing-page notes / `No keyed scenes found` — the slicer found nothing to cut.
  Do not fabricate a spine; report it and stop.

Carry any warning through to the final summary. The player should not learn about
a degraded read three sessions in.

---

## Step 4: Init the adventure from the spine

```bash
CAMPAIGN_DIR=$(bash tools/gm-campaign.sh path)
uv run python lib/adventure.py init "$CAMPAIGN_DIR/module-work/spine.json" \
  --title "<Module Title>" --source-file "<file-path>" [--levels "1-3"]
```

`init` refuses to overwrite an existing `adventure.json` (that would throw away
the table's progress). If it refuses, ask the player before passing `--force`.

---

## Step 5: Fan out the converter agents

Spawn `module-converter` agents over the slice files with the Agent tool.

- **MAX 6 AGENTS TOTAL.** Not 6 per batch, not 6 plus helpers — six.
- Model: **`claude-opus-4-8[1m]`**.
- Divide the scene slices **evenly** across however many agents you use (fewer
  scenes than agents → fewer agents; one agent is fine for a short module).
- `scene-front.txt` is front matter, not a scene. Skip it.
- Launch them in **one message** so they run concurrently.

Prompt template (fill in the bracketed parts verbatim otherwise):

```
You are converting scenes of the adventure module "<Module Title>" into
adventure.json scene JSON. Follow your agent definition (.claude/agents/module-converter.md).

Your assigned slice files (read every one IN FULL):
<absolute path>/module-work/scene-<key1>.txt
<absolute path>/module-work/scene-<key2>.txt
...

Take each scene's `key` from its filename (scene-<key>.txt -> <key>). The valid
`to_key` values for transitions are the keys of the other slices in this book:
<comma-separated list of ALL scene keys in the spine>.

Return a RAW JSON ARRAY of scene objects with exactly these fields: key, title,
location, read_aloud (verbatim boxed text), gm_notes (faithful summary),
encounters [{name, monsters [{name, count, stat_block?}], tactics?}], npcs
[names], treasure [...], checks [{what, skill, dc}], transitions [{to_key,
when}], pages. Do NOT set srd_index — the resolver adds it. No prose, no
markdown fences, no commentary: raw JSON only.

You are one of at most 6 agents on this import — a hard cap for the whole run,
each on model claude-opus-4-8[1m]. Do NOT spawn any further agents. Convert your
own slices and return.
```

---

## Step 6: Merge each batch, then validate

Write each agent's returned array to its own file and merge it. Merge is
order-independent — spine order always wins — so batches can land in any order.

```bash
# per batch
CAMPAIGN_DIR=$(bash tools/gm-campaign.sh path)
cat > "$CAMPAIGN_DIR/module-work/batch-1.json" <<'JSON'
<the agent's raw JSON array>
JSON
uv run python lib/adventure.py merge "$CAMPAIGN_DIR/module-work/batch-1.json"
```

If a merge is rejected (an unknown `to_key`, a missing `key`), fix that batch's
JSON and re-merge it — the bad batch did not persist. Do not hand-edit
`adventure.json`.

Then:

```bash
uv run python lib/adventure.py validate
```

Must pass before you go on.

---

## Step 7: Resolve monsters against the SRD

```bash
uv run python lib/adventure.py resolve-monsters
```

A creature with no stat block of its own gets an `srd_index` when the SRD knows
its name, so the GM pulls real stats at the table. A creature the module statted
itself keeps that `stat_block` and is left alone even if the name collides with
an SRD entry — this book's "Goblin" is the one the author printed. Nothing ends
up with both.

The command prints three counts. **`unstatted` — no SRD match and no stat block —
are conversion gaps**: the converter missed a stat block, or the creature's name
is mangled. Chase them now (re-read that scene's slice and re-run the converter
on it) rather than discovering an unstatted monster mid-encounter. Re-running
`resolve-monsters` is safe and idempotent.

---

## Step 8: Persist the module's NPCs

Every name the converters listed in a scene's `npcs` becomes a brief entry in
`npcs.json` — **name, role, first-seen scene. Not a full sheet.** They get fleshed
out when play walks up to them.

```bash
bash tools/gm-npc.sh create "<Name>" "<one-line role, from the module — first seen in <scene key>>" "<friendly|neutral|hostile|suspicious|helpful>"
bash tools/gm-npc.sh tag-location "<Name>" "<the scene's location>"
```

Dedup by name first: one entry per person, even if they appear in five scenes.

Leave `visual_appearance` blank here — a look is authored the first time someone is
actually illustrated, not for 37 names the party may never meet. Images fail closed
on a blank block, so nobody slips through un-authored.

### Lock the chronicler + art style (once, do not skip)

The gallery signature is a per-campaign decision made at import, never improvised
per image — `gm-image.sh generate` REFUSES to render until it is set. Read the
module's own tone and commit:

**Let the player pick** with AskUserQuestion — offer 3 fully-specified looks drawn from
this module's own tone (references, medium, palette, light; never generic "fantasy art")
plus free text.

```bash
bash tools/gm-image.sh chronicler \
  --name "<the in-world artist who 'makes' every image>" \
  --style "In the style of ... — the player's pick, verbatim; specific enough that two images read as one artist's hand" \
  --era "<the module's century/tech level: what may and may NOT appear in frame>" \
  --persona "<their voice/bias — grim, sarcastic, reverent, unreliable>"
```

The `--era` rail is separate from `--style` on purpose: style is the brush, era is
the props. State it as what may and may NOT appear in frame ("Hyborian bronze age:
bronze blades, no steel plate, no gunpowder"). Without it the model reaches for its
default century and drops anachronisms into the scene.

---

## Step 9: Make the source usable at play time (do not skip)

```bash
bash tools/gm-extract.sh add "<the module file>"
bash tools/gm-extract.sh index-from-module
```

The first embeds the module into this campaign's vector store. Slicing and
converting never touch RAG, so without this the store is EMPTY: `gm-search.sh
--rag-only` returns nothing all session while scene context is still telling the
GM to mine the source every beat. Verify with a real query before you hand off.

The second builds the WORLD INDEX — the anti-hallucination rail.

Derives the index mechanically from the `adventure.json` and `npcs.json` this
import just wrote — no agent hand-authors it, so it is true to the book by
construction. It seeds a minimal unconfirmed `world-bible.json` if the campaign
has none (a module import has no `source/current-document.txt`, so `draft-bible`
cannot run). Idempotent; safe to re-run after fixing conversion gaps.

**Why this step exists.** Without a bible the WORLD INDEX block in scene context
silently does not render, and the GM plays a whole session with no way to check a
name. RAG passages are chunked across PDF page columns and will splice two
unrelated paragraphs into one fluent sentence — carrying a REAL name in a FALSE
arrangement. That is not a hypothetical: it put this module's Eldoria smiths on
the docks of the wrong town. The index is what makes the check possible.

---

## Step 10: Import summary

Print it, then hand off.

```
<Module Title> is loaded.

  Scenes:    <N>  (chapters/sections: <M>)
  NPCs:      <N> added to npcs.json
  Monsters:  <N> resolved to SRD stats, <M> using the module's own stat blocks
  [UNSTATTED: <K> with no stats at all — <names>. Conversion gaps; fix before play.]
  Starting:  <current scene key> — <title>
  [Warning:  this PDF could not be read column by column — some scene text is
             interleaved and may need a second pass.]
```

Then hand off to `/gm`. The ADVENTURE block appears in scene context on its own;
`bash tools/gm-adventure.sh status` shows where the table is, `advance` completes
the current scene, `jump <key>` moves anywhere in the book.

The module is the spine, not a cage — the players still write the story.
