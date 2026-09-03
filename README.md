# Game Master Claude

[![tests](https://github.com/Sstobo/Claude-Code-DND-Harness/actions/workflows/tests.yml/badge.svg)](https://github.com/Sstobo/Claude-Code-DND-Harness/actions/workflows/tests.yml)
[![license: CC BY-NC-SA 4.0](https://img.shields.io/badge/license-CC%20BY--NC--SA%204.0-lightgrey)](LICENSE)
[![python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](pyproject.toml)

A harness that turns Claude Code into a persistent D&D 5e Game Master. You sit down, the campaign picks up where it left off, and the world remembers what you did last week.

It is not a chatbot with a fantasy prompt. Every campaign runs on real D&D 5e: attack rolls resolve against stored armor class, damage comes off fetched stat blocks, characters make death saves at 0 HP, and none of that arithmetic happens in the model's head. The dice, HP, and rules resolve in code; Claude narrates from what the code returns. Around that sit the three things a language model is missing when it tries to run a real campaign: durable memory, a rulebook written for your specific world, and a world that keeps moving between sessions.

### Three ways in

- **Author an original world with `/new-game`.** A short genre-aware questionnaire interviews you, then Claude writes original canon and the world's own signature systems, with a pipeline that works to keep the result from collapsing into stock high fantasy. ([details below](#author-an-original-world--new-game))
- **Import a book you own with `/import`.** Drop a novel or sourcebook PDF into `source-material/`. Claude indexes the text, asks who you came to be (or meet), and opens on that page. The rest of the book enters play as you walk toward it. ([details below](#import-a-book--import))
- **Run a published adventure with `/import-module`.** A module with numbered scenes and boxed read-aloud text is converted into a scene spine the GM walks in order, as written. ([details below](#run-a-published-adventure--import-module))

Whatever the door, the world on the other side plays by 5e. An import brings its setting, cast, and voice; the mechanics underneath never change.

---

## How it works

```
        YOU                    THE HARNESS                      CLAUDE
   "I attack the    →   routes the beat, loads only    →   decides, narrates,
    gnoll captain"      the rules it needs, hands           voices the NPC,
                        Claude the scene + memory           rolls the dice
                                    ↑                              ↓
                        reads & writes campaign state   ←   every change saved
                        (HP, NPCs, threads, clocks,         to disk before it
                        consequences) on disk               reaches the story
```

Every turn runs the same loop: gather context, decide, execute, persist state, narrate. The harness enforces the unglamorous part, that nothing happened until it is written to disk, so the story survives across days, machines, and context windows. Claude handles the part it is good at: making the scene feel alive.

---

## What the harness gives the model

- **Memory that outlives the conversation.** NPCs, locations, plot threads, facts, your character sheet, and your whole history are persisted as plain JSON per campaign. At session end the GM writes an arc entry (what changed, who matters now, what debts are open), and recall over your history is semantic: ask about "the smuggler from the docks" and it finds the session where you met her, by meaning rather than keyword. It also tracks what is canon from the book versus what you made happen. Close the laptop mid-fight; pick it up next week exactly where you left off.

- **A rulebook written for your world, on top of 5e.** Whether you import a book or author one, Claude produces a World Bible (voice, tone, factions, geography, timeline) and from it the world's signature systems, carried in the campaign's own `campaign_rules`. A *Dune* import plays like *Dune*; an original world plays like itself. The dice under all of it stay D&D 5e. The book reskins the world, the cast, and the flavor, never the mechanics.

- **Context pushed to the model, not fetched by it.** The usual failure of LLM roleplay is amnesia: the GM remembers your HP but forgets the cliffhanger. Here every scene arrives pre-loaded with the story so far, open threads, key facts, which NPCs are present and how they talk, the clocks ticking in the background, and any consequence about to land. Claude does not have to remember to look; the harness puts it on the table.

- **A world that keeps living.** Consequences you set in motion fire on their own when you return to a place or enough time passes. Named threat clocks tick whether or not you are watching. Between sessions, a small bounded set of off-screen developments advance. The place feels alive because it is still running.

- **Specialist sub-agents on tap.** A fight starts and a monster-manual agent fetches stats; you cast something and a spell-caster looks up the mechanics; you go shopping and a gear-master handles inventory; a striking scene appears and a scene-illustrator paints it in the background. They read your world's own rules before reaching for anything external, and they spin up invisibly so the story never stops.

- **Combat the model cannot fudge.** Every swing goes through one resolver: it reads the attacker's to-hit and damage off the fetched stat block, compares them to the target's stored AC, doubles the dice on a natural 20, and applies the damage through the 5e dying gate. The GM never does the arithmetic, so the numbers cannot drift between the stat block and the story. It fails closed: a creature with no stat block raises an error instead of inventing a bonus. Between beats you get the board as an ASCII panel, and each roll arrives staged, target first, then the result.

- **Real stakes.** The character can die. Death is telegraphed and earned, never GM fiat, but it is a valid outcome, and when it lands the harness runs a hand-off so the show goes on: take over a party member, roll a newcomer, or step in as a canon figure. The world remembers the fallen.

- **An illustrated campaign, drawn in-world.** If you put an `XAI_API_KEY` (or `OPENAI_API_KEY`) in `.env.local`, the GM illustrates big beats, a new location, a boss reveal, your styled flourish, with generated images presented as the work of an in-world chronicler: a named artist with a locked style and persona, designed at world creation to fit your tone. The same hand draws every image, so the gallery reads like one artist's sketchbook of your story. With no key, the GM narrates in text and never mentions images.

---

## Author an original world — `/new-game`

Ask an LLM for "a fantasy setting" and you get the same tavern, the same chosen one, the same five elemental kingdoms. The hard problem is not generating a world; it is generating one that stays itself instead of drifting back to generic. The `/new-game` pipeline is built around that problem.

You do not write the world. You answer a short genre-aware questionnaire, and Claude builds outward from your answers:

- **A one-line premise** in your own words: *"Conan but on a drowned coast,"* *"cozy folk-horror in a town that forgets its dead,"* *"corporate clans fighting over charged ruins."*
- **The genre bend**, the single biggest anti-generic lever. Sword-and-sorcery (magic is blood-priced and villainous), high fantasy (deep lineage and old songs), sci-fantasy (nanomagic and clan politics), folk or cosmic horror (a wrongness beneath a fragile community). Each bend pushes the whole world somewhere specific.
- **A narrative voice.** Whose voice should narrate this world? Howard, Le Guin, Gibson, Pratchett, or your own pick. Claude writes original prose in that author's fingerprint and narrates every beat in it, so the world reads like a book rather than a generic narrator.
- **A locked art style**: a deliberately surprising mashup (*"a gilded medieval illuminated manuscript depicting cyberpunk megacities"*) and an in-world chronicler who draws every image.

From those answers Claude builds one stage, not a planet, in four steps:

1. **Seed.** Your answers become a structured world-seed: premise, tone, genre bend, voice, art style, chronicler. No gazetteer; the world's shape emerges at the table.
2. **Skeleton.** Claude authors the world's spine in one pass while the seed is fresh (name, voice, themes, factions, signature systems), then shows it to you for approval before going further.
3. **Play pack.** Claude writes the signature systems into the world's rules prose (the mechanics stay 5e), then stages exactly what tonight needs: one room you can stand in, the people in it, the exits you can see, and a hook that won't wait.
4. **Handoff.** Claude locks the chronicler and art style, asks who you are in this world, and the story begins.

The world grows as you play. When a long-game opportunity appears, Claude seeds a threat clock, a story thread, or a new plot and lets it tick. That is the campaign's long-term planning, authored at the table rather than pre-built. `/create-character` remains an opt-in full character sheet whenever you want one.

```
You: /new-game
GM:  A few questions first. One line — what's the world?
You: Wandering swordsmen in a desert of glass where the gods drowned.
GM:  Genre bend? (1) sword-and-sorcery  (2) high fantasy  (3) sci-fantasy  (4) folk/cosmic horror
...
```

## Import a book — `/import`

Got a favorite novel, a classic adventure module, a weird pulp paperback from the 70s? Drop the PDF into `source-material/`. Claude indexes the real text, writes a World Bible and the world's signature systems so the room sounds like that book, then asks the only question that matters: who did you come to meet? You get that room, those voices, one hook. When you walk toward Stygia, Stygia is read from the book and written into the journal, not scraped on night zero.

> **Where to find books:** the [Internet Archive](https://archive.org/) has thousands of free books, modules, and old pulp novels. Jump into *IT* and help the bad guys. Drop into *Lord of the Rings* and play from Gollum's perspective. It's your call.

## Run a published adventure — `/import-module`

A published adventure module is a different animal from a novel: the author already cut it into numbered scenes, boxed read-aloud text, and keyed encounters. `/import-module` respects that. Instead of chunking the text blindly, it slices the PDF along the author's own scene boundaries and converts each scene into structured JSON: the read-aloud text, the GM notes, the transitions, the encounters. The result is `adventure.json`, an ordered spine with a pointer at where the table currently is. Each scene rides into play as written, and you advance the pointer as the table clears it. The sliced text is then embedded too, so lookups at the table still reach the module's own words — but the spine, not retrieval, is what drives play. The mechanics are 5e as always.

## How a campaign is synthesized

All three doors converge on the same campaign shape: a folder under `world-state/campaigns/<name>/` holding plain JSON for the character, NPCs, locations, plots, clocks, facts, and the session log. What differs is where the canon comes from.

**From a book (`/import`):** the PDF is extracted, chunked, and embedded into a local vector index, so scenes can quote and paraphrase the actual text. Claude then reads enough of the book to write a **World Bible**, the campaign's identity document: voice, tone, themes, a handful of factions and places, and the world's signature systems. You approve the bible before play. The signature systems are then mapped into `campaign_rules`, the rules prose the GM plays by, which is why a *Dune* import feels like *Dune* at the table while still rolling 5e dice. Finally the harness stages exactly one opening: the room your chosen identity starts in, the people in it, the visible exits, and a hook. Nothing else is pre-built. The rest of the book stays in the index, and each new face or place is read from the book and written into the campaign journal the first time play reaches it.

**From scratch (`/new-game`):** the same pipeline, except the canon is authored instead of extracted. Your questionnaire answers become a world-seed, the seed becomes the World Bible, and the bible becomes `campaign_rules` and one staged opening, with your approval at the skeleton stage before anything is committed.

**From a module (`/import-module`):** no world-bible authoring; the module's own scene structure becomes the spine, the sliced scenes are embedded for table-time lookups, and the GM runs it as published.

In every case the campaign file is a journal of where the table has been, not an encyclopedia of the source. The world grows outward from play, one stage at a time.

### What happens to a document you import

**What it accepts.** Drop the file in `source-material/`. PDF, `.docx`, `.md`, or `.txt`. PDFs go through a column-aware extractor: RPG books are typically two-column, and a naive read interleaves the columns into nonsense, so the page is split at the whitespace gutter and each column read in order. Titles and wide tables that span both columns are detected and kept whole.

**Where the text goes.** The original file is never copied, moved, or modified. It is read where it sits, and everything derived from it is written under `world-state/campaigns/<name>/`:

| | |
|---|---|
| `source/current-document.txt` | The full extracted text, kept for long-context reads |
| `chunks/` | The same text split at section and paragraph boundaries, ~3,000 characters each |
| `vectors/` | A local ChromaDB index of those chunks |

That whole folder is gitignored, along with `source-material/` itself, so nothing about your book is ever committed. Note that the extracted text and vectors are deliberately durable: `/reset` clears the story but keeps them, because the world bible and long-context reads still need the book. To remove them, delete the campaign (`gm-campaign.sh delete <name>`), which takes the whole folder.

**What runs locally.** Extraction, chunking, and search are local. Embeddings are computed on your machine by `all-MiniLM-L6-v2`, a 22 MB sentence-transformers model, which is downloaded once from HuggingFace on first use and then works offline. The vector index is a file on your disk. No document-hosting service is involved at any point, and the harness itself makes outbound calls to exactly three hosts: dnd5eapi.co for SRD rules, and api.x.ai or api.openai.com if you enabled scene images.

**What does reach Anthropic.** Claude Code is Claude, so the passages retrieved for a scene, and the chunks read during import, go into the model's context like anything else it reads. The book is not uploaded anywhere as a file, but the parts of it that come into play do travel to the API as conversation. Import only what you are comfortable sending, and check your source's licence before importing it.

**More than one book.** `/import` replaces the campaign's shelf; `gm-extract.sh add <file>` layers another book onto it. Chunk ids are namespaced per document and every chunk records where it came from, so a world book and a screenplay that shapes your character's voice can sit in the same campaign and be retrieved across at once.

**Retrieval, not recall.** At the table, source lookups run through one front door, `gm-context.sh`, which returns campaign state plus grounded passages. Retrieved text is treated as texture and never as fact: chunks are cut across page columns and can splice two unrelated paragraphs into one fluent-sounding sentence, so a proper noun in a passage is always resolved against the campaign's own world index before it reaches the page. When the index and a passage disagree, the index wins.

---

## Getting started

**Prerequisites:** [Claude Code](https://docs.anthropic.com/en/docs/claude-code) (which needs Node.js 18+), plus `curl` and `git`. On Linux you also need Python 3.11+ and `jq` before you start — the installer will not install those for you.

```bash
git clone https://github.com/Sstobo/Claude-Code-DND-Harness.git
cd Claude-Code-DND-Harness
./install.sh
```

On macOS the install script bootstraps what it needs: Homebrew, Python, uv, jq, and the Python dependencies. On Linux it installs uv and the Python dependencies, and prints the apt/dnf/pacman command for anything else that is missing. It does not install Claude Code itself. (You can also just launch Claude Code and ask it to set things up.)

Then:

1. Run `claude` to launch Claude Code
2. Run `/gm`

`/gm` is the only command you need. It offers a New Adventure (author an original world, import a book or published module from `source-material/`, or spin up a quick one-shot), then builds your character and runs the game. Once a world exists, the first question is "Who are you in this world?": a character lifted from the source, an original of your own, or a nameless traveler who wanders in. The mechanics are handled behind the scenes.

---

## Why a harness, and not just a long prompt

A single mega-prompt can fake a GM for one session. It can't remember your campaign next week, it can't enforce its own rules, and it drowns the model in mechanics it doesn't need this turn. The harness addresses each of those directly:

- **Thin always-on core, heavy rules on demand.** A lean router stays in context; combat, social, skill checks, conditions, leveling, dungeon crawls, and narration craft load only for the moment that needs them. The model spends its attention on the scene, not the manual.
- **State on disk, not in the context window.** Memory is bounded by your filesystem, not the token limit. Campaigns can run indefinitely.
- **Persist-before-narrate, enforced.** Every state change is written before a word reaches you, so a crash or a context reset never loses progress.
- **Grounded in a real corpus.** Scenes draw on actual passages, from your imported book or the canon Claude authored for your original world, via a local retrieval index, so narration stays true to the source until your choices change it.

You never see any of this. You just see the story.

---

## Advanced

Everything below is handled automatically by `/gm`. It is here if you want manual control.

### Commands

| Command | What it does |
|---------|--------------|
| `/gm` | Start or continue your story. Imports, world-building, characters, one-shots, saves, and your sheet all route through it. Shortcuts: `/gm save`, `/gm character`, `/gm overview`. |
| `/import` | Import a novel or sourcebook PDF as a new campaign |
| `/import-module` | Convert a published adventure module into a scene spine and run it as written |
| `/new-game` | Build a world from scratch |
| `/create-character` | Build a character in detail |
| `/enhance` | Enrich entities with source-material passages |
| `/world-check` | Validate campaign consistency |
| `/reset` | Clear campaign state |
| `/setup` | Verify/fix installation |
| `/help` | Full command reference |

### On-demand skills

The lean core loads these only when the moment calls for it:

| Skill | Loaded when |
|-------|-------------|
| `gm-combat` | A fight breaks out |
| `gm-spellcasting` | You cast something |
| `gm-social` | You talk to / read an NPC |
| `gm-skills` | You attempt something uncertain |
| `gm-dungeon` | You enter a cave, ruin, or complex |
| `gm-conditions` | A status effect is applied |
| `gm-levelup` | You hit a milestone |
| `gm-craft` | Narration and pacing wisdom |

### Specialist agents

Spawn automatically during play, invisibly:

| Agent | Triggered by |
|-------|--------------|
| `monster-manual` | Combat encounters |
| `spell-caster` | Casting spells |
| `rules-master` | Mechanical edge cases |
| `gear-master` | Shopping, identifying gear |
| `loot-dropper` | Victory, treasure |
| `npc-builder` | Meeting new NPCs |
| `world-builder` | Exploring new areas |
| `dungeon-architect` | Entering dungeons |
| `scene-illustrator` | High-impact visual beats |
| `create-character` | New characters |

### Bash tools

The harness is plumbing you can poke at: bash wrappers (`tools/`) → Python managers (`lib/`) → per-campaign JSON (`world-state/campaigns/<name>/`). All tools follow the pattern `bash tools/gm-<tool>.sh <command> [args]`. Most accept `--json` for structured output.

| Tool | Purpose |
|------|---------|
| `gm-campaign.sh` | Create, list, switch, delete campaigns |
| `gm-session.sh` | Session lifecycle, party movement, save/restore |
| `gm-context.sh` | Assemble scene context (world state + source passages) |
| `gm-player.sh` | Player stats — health, progression, gold, inventory |
| `gm-npc.sh` | NPCs — creation, updates, mood/goal/voice, party members |
| `gm-location.sh` | Locations and connections |
| `gm-plot.sh` | Quest and storyline tracking |
| `gm-adventure.sh` | Module scene spine — advance or jump the pointer |
| `gm-combat.sh` | The combat rail: initiative, the round panel, attack resolution, death saves |
| `gm-condition.sh` | Player conditions (poisoned, stunned, etc.) |
| `gm-consequence.sh` | Schedule future events and triggers |
| `gm-recall.sh` | Campaign memory — semantic recall, arc entries, memoir |
| `gm-clock.sh` | Threat clocks — pressure that mounts as time passes |
| `gm-lore.sh` | Grounded chapter briefs from the source book |
| `gm-note.sh` | Record world facts by category |
| `gm-time.sh` | Advance in-game time |
| `gm-search.sh` | Search world state and/or source material |
| `gm-enhance.sh` | RAG-powered entity enrichment |
| `gm-extract.sh` | Document import and extraction pipeline |
| `gm-overview.sh` | Quick world-state summary |
| `gm-image.sh` | Generate a scene image and print a clickable link |
| `gm-reset.sh` | Reset campaign data |

### Scene images

At high-impact beats, a new location, a boss reveal, a big find, the GM can illustrate the moment instead of describing it in text:

```bash
bash tools/gm-image.sh generate --title "The Sunken Crypt" \
  --prompt "A flooded stone crypt lit by green torchlight, dark fantasy, cinematic"
```

It calls xAI's Grok Imagine, or OpenAI's `gpt-image-2` when no xAI key is set, saves the image into the campaign's `images/` folder, and prints a clickable `file://` link (the VS Code terminal linkifies the path). Every generation is logged with an estimated cost; run `gm-image.sh log` for the running total. Requires `XAI_API_KEY` or `OPENAI_API_KEY` in `.env.local`; without either the GM narrates in text and never mentions images. Use `--quality low` for quick drafts, `high` for marquee moments.

### Combat

A fight runs on a fixed rail: cast the encounter, roll the order, take one turn, resolve the swing, handle the fallen, clear up. `gm-combat.sh` owns every number in it. Enemies enter as their fetched SRD stat block, so their to-hit and damage are the book's, not a retyped approximation, and initiative is rolled rather than assumed.

Between beats you get the board:

```
── ROUND 2 ────────────────────────── the whispering wood ──
 ▸ Giant Spider   [████████████]  26/26  AC14  HEALTHY
   Lion           [███░░░░░░░░░]   7/26  AC12  BLOODIED
────────────────────────────────────────────────────────────────
   KORDAN  lvl5 half-orc barbarian  HP [█████████░░░] 39/50  AC13
   status: raging                   XP 8000    GP 46
────────────────────────────────────────────────────────────────
```

And the roll arrives staged, never collapsed to a line. You are shown the number you have to beat, then a pause, then what you got:

```
To hit Lion, you need to beat

## [ 12 ]

.
.
.

You rolled

## [ 23 ]

16 and 16 — advantage, keep the 16 · +4 from strength · +3 from proficiency

✓ HIT — past the guard by 11.

🎲 Damage: 2d6+6 [3+2] +6 = 11 ▼ Lion [███████░░░░░] 15/26 ⚠
```

The pause is real, because the message streams. Advantage, resistance (a raging barbarian halves three damage types), crits doubling the dice, death saves that persist across a resume: all of it resolves in the tool and is narrated from what comes back. One turn per reply, and when the dice are yours the swing waits for you to trigger it.

### Where a rule comes from

When a rule question comes up mid-play, the answer is looked up, never recalled. There is a fixed order, and every specialist agent follows it:

1. **Your imported book first.** `gm-search.sh "<term>" --rag-only` retrieves the passage from the source you imported. If the module names its own trap DC, that DC is the one played.
2. **The campaign's own rules prose.** A world's signature systems live in `campaign_rules` and its `rules.md`, written at import or world creation. This is how a *Dune* campaign gets Dune's mechanics on top of 5e dice.
3. **The SRD, via [dnd5eapi.co](https://www.dnd5eapi.co/).** Mandatory, not optional: whatever the book leaves silent is answered from official 5e rather than invented. This is one HTTP host, and it is the only one the game logic ever calls.

The API is wrapped in small scripts under `features/`, one per question a table actually asks, and the agents call these rather than composing URLs:

| Question | Script |
|---|---|
| What are this creature's stats? | `features/dnd-api/monsters/dnd_monster.py "goblin"` |
| What does this spell do? | `features/spells/get_spell.py fireball` |
| What is this item worth, and what does it do? | `features/gear/dnd_equipment.py longsword` · `dnd_magic_item.py "bag of holding"` |
| How does this rule work? | `features/rules/get_rule.py cover` · `combat_rules.py "two weapon fighting"` |
| What does this condition do? | `features/rules/conditions.py stunned` |
| What can this class or race do? | `features/character-creation/api/get_classes.py` · `get_traits.py dwarf` |

Every response is cached to disk on first fetch under `features/dnd-api/cache/`. SRD 2014 data is immutable, so there is no expiry: the second lookup of a goblin is a file read, and a session runs fine offline once its stat blocks are warm.

Two things worth knowing about the scope. The API serves the **SRD**, which is the openly licensed subset of 5e, so it has the goblin and the fireball but not the contents of a specific published hardcover. That is what importing your own book is for. And it is the **2014** ruleset, which is what "D&D 5e" means everywhere else in this README.

### The documentation

How the harness works lives in [`docs/`](docs/index.md), a knowledge layer where every doc declares the source files whose change would make it wrong ([OKF](docs/log.md)). Start with the flows (a play turn, importing a book, authoring a world, the death hand-off) and read `docs/gotchas/` before debugging anything. There is no staleness engine: a doc is verified by reading it against its sources while you work in that area, and updated in the same commit as the code it describes.

### Dependencies

Installed during setup via [uv](https://docs.astral.sh/uv/). The list is short because most of the harness is stdlib: the Claude calls belong to Claude Code, and the HTTP the tools do is `urllib`.

**Core:** `pdfplumber` + `pypdf` (PDF extraction), `python-docx` (Word docs).

**RAG (document import):** `sentence-transformers` (embeddings), `chromadb` (vector index for source lookups). These are the `rag` extra — the default answer at the install prompt, and always installed by `/setup`. Pick "core only" and PDF import will not work.

---

## License

Licensed under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) — free to share and adapt for non-commercial use. See [LICENSE](LICENSE) for details.

---

Built by [Sean Stobo](https://www.linkedin.com/in/sean-stobo/). Run `/gm` to play.
