---
slug: readme-front-door-facts
title: The clone URL, prerequisites, install claims and dependency list are all wrong
category: bug
kind: afk
priority: p0
lane: agent
parentPrd: readme-promises
blockedBy: []
claimedBy: fable-readme1
claimedAt: 2026-08-28T00:30:00Z
changedFiles: [README.md, pyproject.toml, install.sh, uv.lock, CLAUDE.md, docs/playbooks/install-and-setup.md]
resolution: null
reviewRounds: 0
implementer: fable-readme1
createdAt: 2026-08-27T00:00:00Z
updatedAt: 2026-08-28T01:10:00Z
---

## Parent

readme-promises — prds/readme-promises.md

## Category

bug

## What to build

Four factual corrections in the first fifteen lines a new user reads, plus the
metadata behind them. Text and `pyproject.toml` only, no runtime code.

**1. The clone URL sends people to a different repo.** README:111-112 says
`Claude-Code-Game-Master`; `git remote -v` says `Claude-Code-DND-Harness`. The
old URL is not dead and does not redirect — it is a live stale repo (HEAD
`dea99314`, pushed 2026-08-16, carries a `refs/pull/1/head`) while local HEAD is
`808d6617`. A new user clones something 11 days behind with no error. Fix both
README lines and the four stale URLs at `pyproject.toml:64-67`
(Homepage/Documentation/Repository/Issues).

**2. Prerequisites are backwards.** README:108 lists Claude Code, which is the
one thing `install.sh` does *not* require (it warns and continues,
`install.sh:358-365`). Unlisted and actually required: Python 3.11+ on Linux
(hard `exit 1` at `install.sh:168`), `jq` on Linux, `curl` on both, `git`, and
Node.js 18+ for Claude Code itself.

**3. The install claim is false on Linux.** README:116 says the script "sets up
Python, uv, jq, and all dependencies, on macOS and Linux, with no prior setup."
On Linux it installs **only uv** (`install.sh:186`). It detects a package
manager at `install.sh:117-127` and never calls it. Python missing → prints the
apt command and aborts. jq missing → prints the command and skips. macOS is
genuinely handled (Homebrew at `:104`, `brew install python@3.12` at `:155`,
`brew install jq` at `:216`). Also `install.sh:15`'s own header claims it
installs Claude Code; it does not.

**4. Three of five listed core dependencies are dead.** Verified by grep over
`lib/ features/ tools/ tests/` with `.venv` excluded:

| README name | imported anywhere? |
|---|---|
| `anthropic` — billed as "(Claude API client)" | **no** — zero imports; the harness never calls the API, Claude Code does |
| `python-dotenv` | **no** — zero occurrences of `dotenv` in any `.py` |
| `requests` — billed as "(D&D 5e API)" | **no** — `lib/image_gen.py:13` is explicit that it uses stdlib `urllib`; the 5e API is reached by agent WebFetch |
| `pdfplumber`, `pypdf2`, `python-docx` | yes, all in `lib/content_extractor.py` |

`pypdf2` is the correct name (`lib/content_extractor.py:311` does `import
PyPDF2`), so leave it. Also: `sentence-transformers` and `chromadb` are the
optional `rag` extra (`pyproject.toml:42-46`), not automatic — `install.sh:255`
offers "core only," after which PDF import does not work. And `elevenlabs`
(`pyproject.toml:39`) has zero imports while `install.sh:242` advertises "voice
(ElevenLabs TTS)" as an install option for a feature that does not exist.

Replacement text for each is drafted in the audit and reproduced in the
acceptance criteria below.

## Acceptance criteria

- [x] README:111-112 and `pyproject.toml:64-67` all name `Claude-Code-DND-Harness`
- [x] Prerequisites line names Node.js 18+, `curl`, `git`, and (Linux) Python 3.11+ and `jq`
- [x] Install paragraph states the macOS and Linux paths separately and says Claude Code is not installed by the script
- [x] Dependencies section lists only deps that are actually imported, and describes the `rag` extra as the default install answer rather than automatic
- [x] `anthropic`, `python-dotenv`, `requests` either removed from `pyproject.toml:27-34` or annotated with why they are pinned; same decision recorded for `elevenlabs`
- [x] `install.sh:15` header no longer claims it installs Claude Code
- [x] A clean-machine reading of the install section matches what the script does on that platform

## Out of scope

Making `install.sh` actually install Python/jq on Linux. That is a real option,
but this ticket only makes the documentation true; file a separate ticket if we
want the behaviour to change instead of the text.

## Verification

Lane: agent. `git remote -v` against README, grep every listed dep for a real
import, read `install.sh` top to bottom against the paragraph.

## Blocked by

Nothing.

---

## QA Reports

## History

- 2026-08-27T00:00:00Z  created → needs-triage  [readme-audit]
- 2026-08-28T01:10:00Z  in-progress → in-review  URLs fixed, install text truthful per-platform, 4 dead deps dropped, canary now pdfplumber  [fable-readme1]
