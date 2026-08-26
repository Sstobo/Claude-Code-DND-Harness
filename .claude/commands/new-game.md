# /new-game - Create Your World

Author tonight's table, not a planet. Same dream as `/import`: voice, rules
prose, a primer, one street. The campaign file is a **journal of where the table has
been**. The world grows AS YOU PLAY — seed a clock, a thread, or a plot when you
see a long-game opportunity, materialize the next face or place when play walks
toward it. Do not pre-build the universe: author tonight's one stage, then let the
living-world tools grow it from the table.

See `docs/conventions/the-dream.md`.

---

## PHASE A — SEED (genre-aware questionnaire)

Create + switch the campaign first:

```bash
bash tools/gm-campaign.sh create "<CAMPAIGN_NAME>"
bash tools/gm-campaign.sh switch "<CAMPAIGN_NAME>"
CAMPAIGN_DIR=$(bash tools/gm-campaign.sh path)
```
(If the name exists: offer switch / rename / recreate.)

Run the questionnaire with **AskUserQuestion**. Ask for: a one-line **premise**
(free text — "Conan but on a drowned coast"), **tone**, **magic level**, and
**setting type** (reuse the classic options). Then ALWAYS ask the **genre bend** —
the single most important anti-generic lever:

Also ask the **voice** question — *"Whose voice should this world be narrated in?"*
— with genre-adaptive suggestions + free text (e.g. sword-and-sorcery → Robert E.
Howard; high fantasy → Tolkien / Le Guin; sci-fantasy → Gibson; whimsical →
Pratchett). Store as `voice_exemplar`. This is what makes narration read like a
real author instead of a generic narrator.

Then ask the **art direction** question — the player picks how their world LOOKS,
the same way they picked how it sounds. Use **AskUserQuestion**, offer 3 fully-specified
styles drawn from the premise and genre bend they just gave you (never generic
"fantasy art" — name references, medium, palette, light), plus free text. Examples of
the specificity required:

- *Sword-and-sorcery:* "Frazetta oil painting — heavy muscular figures, lurid torch-lit
  shadow, dust and blood, sunset palette of ochre and dried blood."
- *Space opera:* "1977 Star Wars production painting — Ralph McQuarrie gouache, matte
  hard light, lived-in scuffed hardware, bleached desert and gunmetal."
- *Folk horror:* "Wet 1970s British TV film stock — desaturated greens, overcast flat
  light, grain, wrongness at the edge of frame."

Store their pick as `art_style`, and store the **era** it implies as `art_era` — the
world's technological and cultural century, stated as what may and may NOT appear in
frame ("Hyborian bronze age: bronze blades, no steel plate, no gunpowder, no printed
cloth"). The era is a separate rail from the style: style is the brush, era is the
props. Without it the image model reaches for its default century and drops a modern
badge or a Victorian street lamp into a bronze-age scene.

Genre bend options:

- *Sword-and-sorcery (Conan):* magic = blood/curse-priced and villainous; bronze-age
  tech; decadent kingdoms vs. barbarian frontier.
- *High fantasy (Tolkien):* deep lineage/ancestry; a pantheon + old songs; pastoral
  vs. rising dark.
- *Tech / sci-fantasy:* nanomagic or charged tech; infrastructure + corporate/clan
  politics.
- *Folk / cosmic horror:* fragile sanity; small community; a wrongness beneath.

Capture the genre bend as a sentence or two of distinct commitments. You do NOT
need a full axis list to sit down — the world's shape emerges at the table.

Write `world-seed.json` to the campaign dir:

```json
{
  "premise": "...", "tone": "...", "magic": "...", "setting": "...",
  "genre_bend": "<the distinct commitments, in a sentence or two>",
  "voice_exemplar": "<author/work to channel, e.g. 'Robert E. Howard'>",
  "art_style": "<THE PLAYER'S PICK, verbatim — 'In the style of ...', fully specified: references, medium, palette, light. Specific enough that two images read as one artist's hand. This is the campaign's locked gallery signature, set ONCE here.>",
  "art_era": "<the century/tech level the style implies, as what may and may NOT appear in frame — 'Hyborian bronze age: bronze blades, no steel plate, no gunpowder'>",
  "chronicler_name": "<the in-world artist who 'makes' every image, fits the tone>",
  "chronicler_persona": "<their voice/bias — grim, sarcastic, reverent, unreliable>"
}
```

---

## PHASE B — SKELETON (one pass, while the seed is fresh)

YOU (the main GM agent) author the full creative skeleton NOW, in one pass, while
all the seed context is fresh in mind. This is the world's identity — get it right
here; everything else grows from the table.

Write `world-bible.json` to the campaign dir with `confirmed: false` and ALL
required keys (validated by `lib/world_bible.py`): `name`, `voice`
(`style`/`vocab`/`sample_passages`), `tone`, `themes`, `factions`

**Author the `voice` block from `voice_exemplar`** — this is how the GM narrates
in the author's voice at play (surfaced every beat by `get_full_context`):
- `style`: a concrete prose fingerprint imitating the exemplar (sentence rhythm,
  diction, imagery) — not "epic fantasy" but e.g. "Howard's terse, muscular cadence;
  sensory violence; archaic but plain diction."
- `sample_passages`: 2-3 SHORT passages YOU write *in that author's voice* (original
  imitation, NOT copied from the real author's text) so the GM has a concrete target.
- `vocab`: a few signature in-world terms.
Keep geography to the starting street plus a few horizon names. Do not author
the continent. **Wire 2–4 edges** into the `factions`/`geography` graphs (a
tension between two factions, an adjacency between two places) — nodes with no
edges are a cast list, not a world. Signature systems go here — they become the
world's rules prose (Phase C writes them into `campaign_rules`).

Validate, then present for approval:
```bash
uv run python lib/world_bible.py validate
uv run python lib/world_bible.py show
```

Show the user the `name`, voice style, themes, factions, and signature systems.
**Gate play on their approval** — let them edit or accept. Then write the rules
prose and the play pack (Phase C). The bible stays `confirmed: false` until they accept.

---

## PHASE C — PLAY PACK (the default — build the one stage)

Write only what tonight needs:

1. **Write the world's signature systems into `campaign_rules`.** Mechanics are
   5e; what makes this world its own is the prose the GM plays by. Take the
   bible's `signature_systems` (blood-priced sorcery, a Dread that rises, the
   price of a favour) and persist them as campaign rules — they ride into every
   scene as YOUR WORLD'S RULES:
   ```bash
   bash tools/gm-extract.sh campaign-rules
   ```
   (Edit the bible's `signature_systems` and re-run if the wording needs work.)
   If a system needs more room than a one-liner — a duelling procedure, a
   faction-standing ladder — write that long-form prose to `rules.md` in the
   campaign dir; `WorldKit.rules_doc_path()` finds it by name. Most worlds need
   no such file.
2. **Author the World Index** — a scannable one-sentence roster of the named
   figures, places, relics, and monsters this world contains. There is no book to
   extract from, so **you invent it** from the world's tone/themes (same schema as
   an imported world's index). The GM scans it before inventing a name, so the
   world stays consistent. Persist:
   ```bash
   bash tools/gm-extract.sh write-index --index-json '{"npcs":[{"name":"<Name>","note":"one sentence"}],"locations":[...],"items":[...],"monsters":[...]}'
   ```
   Recognizable, not a gazetteer — the faces the player might actually meet.
3. Set the play pack and stage:

```bash
bash tools/gm-playpack.sh set --json '{
  "whose_story": "<who they are or came to meet>",
  "room": "<one street / room / deck>",
  "present": ["<2-4 people here>"],
  "exits": ["<what you can see>"],
  "hook": "<the problem that will not wait>",
  "offstage": ["<horizon names>"],
  "primer": "<GM paragraph: where the plot starts>"
}'
bash tools/gm-playpack.sh stage
```

3b. **Give the story a spine — seed the antagonist's clock.** A stage without a
   countdown is inert. Seed **at least one** threat clock whose aim completes
   off-screen (the looming danger your tone/themes imply), so the world moves on
   the player whether or not they engage:
   ```bash
   bash tools/gm-clock.sh add "<the antagonist's aim>" 4 --on time \
     --consequence "<what happens when it fills>"
   ```
   One clock, not a doom gazetteer — it rides into every scene as a THREAT CLOCK.

4. Optional thin binder: a short `authored-canon.md` of *this street only*, then
   `gm-extract.sh prepare` so RAG has something to pull. Do not author the continent.

When a new name walks on: `gm-playpack.sh from-book "<name>"` then RAG.

---

## PHASE D — HANDOFF (play tonight)

**Lock the chronicler + art style NOW** (the gallery signature is a world-creation
decision, not an in-play improvisation) from the seed's `art_style` /
`chronicler_*` fields:

```bash
bash tools/gm-image.sh chronicler \
  --name "<chronicler_name>" \
  --style "<art_style — MUST start with 'In the style of ...'; the player's pick, verbatim>" \
  --era "<art_era — what may and may NOT appear in frame>" \
  --persona "<chronicler_persona>"
```

The `scene-illustrator` agent READS this locked style and opens every prompt with
it — it never picks its own. Make it specific enough that two images read as one
artist's hand (a surprising mashup is one way there, not the only one). This single
chronicler record carries all three parts of the image identity — the **art style**
(`--style`, the brush), the **era** (`--era`, the props and tech level that bound every
frame), and the **art narrator** (`--name` / `--persona`, the in-world entity who
"makes" every picture). Lock them now; they never change in play, and
`gm-image.sh generate` REFUSES to render until the style is set.

**Author a `visual_appearance` block for every NPC in the play pack** (and the PC
at `/create-character`). It is the locked look every future image renders, with
EXACTLY these 11 keys, in this fixed order: `race, sex, size, color, hair, eyes, face, shirt, pants, gear, short_description`.
Ground each field in the bible; leave unknowns "". Author only the people on this
stage — the rest get a block the first time they walk on (an image REFUSES to
render a named character who has none):
```bash
bash tools/gm-npc.sh set-appearance "<NPC name>" \
  --race "..." --sex "..." --size "..." --color "..." --hair "..." --eyes "..." \
  --face "..." --shirt "..." --pants "..." --gear "..." --short_description "..."
```

Update `campaign-overview.json` (date/time, `session_count: 0`, and
`player_position.current_location` = the play pack's `room`) and append the world
summary to `session-log.md` (starting location, the people on stage, the hook).
Then display a summary box and hand off:

```
Your world awaits its hero. Who are you in this world?
```

Then ask that **one question** — identity first, mechanics later — and offer three doors:

- **someone from this world** → `bash tools/gm-player.sh onboard canon "<NPC name>"`.
  The canon door draws from the NPCs in the play pack, so name a few of them (their
  sheet and their canonical voice come along).
- **someone of their own** → `bash tools/gm-player.sh onboard original "<name>" "<one-line concept>"`
- **no one yet** → `bash tools/gm-player.sh onboard nameless`

**After identity, before you open the scene, ask where/when they want to start.**
Offer a fitting default but let them name their own opening — a specific location,
scene, or point in the timeline — and build the play pack's `room`/`hook` around it.

Persist the answer with `onboard` and open the scene — the play pack's room and
hook are the opening; `onboard` leaves them in place. `/create-character`
remains the **opt-in** full builder for a player who wants to roll a sheet properly
— offer it, don't impose it. If they used `/create-character` (`save-json`), the
first `gm-player.sh set` re-seeds the opening.

---

## COMPLETION CHECKLIST (play tonight)
- [ ] `world-seed.json` (premise, voice, art style)
- [ ] `world-bible.json` approved and confirmed (voice + signature systems, not a planet)
- [ ] `campaign_rules` carrying this world's signature systems as prose
- [ ] `play_pack` set + `gm-playpack.sh stage` (one room, present NPCs, exits, hook)
- [ ] chronicler locked (`gm-image.sh chronicler`)
- [ ] handed off to the one question (`gm-player.sh onboard ...`)

## Growing the world AT THE TABLE (the real "long-term planning")
You do not pre-plan the campaign — you plan it as you run it. When you see a
long-game opportunity, seed it with the living-world tools and let it tick:
- **Threat clocks** (`gm-clock.sh`) — named pressure that advances on its own.
- **Story threads** (`gm-session.sh end --open-thread`) — questions left hanging.
- **Plots** (`plots.json`) — a spine you extend when the story earns a next beat.
- **Consequences** (`gm-consequence.sh add`) — a seed that fires on the right trigger.
These are how the world develops mid- to long-term — reactively, from play, not
from a gazetteer built before anyone sat down.

## ERROR RECOVERY
- Campaign exists → switch / rename / recreate.
- Bible fails validation → fix the missing required key, re-validate before play.
- `prepare` finds no text → confirm the `authored-canon.md` binder is non-empty.
