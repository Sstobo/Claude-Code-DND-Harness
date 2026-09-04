#!/usr/bin/env python3
"""
Book Bible import helpers — long-context reading instead of chunk-and-delete.

The import flow keeps the book text (not deleted on cleanup), a world-bible
subagent reads LARGE spans (whole chapters via long context, not 3000-char
chunks) and emits a structured world-bible.json, and that bible feeds the
campaign_rules prose the GM plays by. This module holds the deterministic,
testable pieces: chapter segmentation, the bible→campaign_rules draft, the world
index, and token observability. The subagent read itself is orchestrated by the
/import command.
"""

import copy
import json
import re
import sys
from pathlib import Path
from typing import Tuple, Any, Dict, List

sys.path.insert(0, str(Path(__file__).parent))

from overview_seed import seed_overview

# A marker is "Chapter N" / "Part N" / "1. " — or a line that is a TITLE IN
# CAPS ("THE TOWER OF THE ELEPHANT"), which is how a scanned collection names
# its stories. Before 2026-09-04 the caps form was not recognised, so a whole
# 2.4M-char Conan collection was one span cut into 20k windows, each titled by
# its first sixty characters ("Count. There was an edge of").
# "chapter"/"part" are anchored to the END of the line: unanchored, `part\s+\w+`
# fired on every sentence-initial "part of the ..." — nine false breaks in Conan.
# The numbered form takes at most three digits: "1935. Reprinted by permission
# of ..." in the front matter is a year, not chapter 1935.
_CHAPTER_RE = re.compile(
    r"^\s*(chapter\s+\w+\s*$|part\s+\w+\s*$|\d{1,3}\.\s|[A-Z][A-Z'\u2019,:\-]*(?: [A-Z][A-Z'\u2019,:\-]*){1,9}\s*$)",
    re.IGNORECASE | re.MULTILINE)
_ALLCAPS_TITLE = re.compile(r"^[A-Z][A-Z'\u2019,:\- ]+$")
# A span shorter than this is a title, an epigraph or a drop-cap line, not a
# chapter: it folds into the span that follows, keeping the earliest title.
_MIN_SPAN = 2000


class ConfirmedBibleError(RuntimeError):
    """Raised when drafting would clobber a bible a human already approved."""


def _is_drop_cap(text: str, start: int, end: int) -> bool:
    """A caps line that is the REST of a sentence whose first letter the printer
    dropped into a big initial — "ORCHES FLARED MURKILY ON", "OBERT ERVIN HOWARD".

    The extractor renders the initial as its own line just before ("T the revels
    in the Maul", "R was born"), and the sentence carries on in lowercase just
    after. Either tell is enough; a real title has neither.
    """
    prev = text[:start].rstrip("\n").rsplit("\n", 1)[-1].strip()
    nxt = text[end:].lstrip("\n").split("\n", 1)[0].strip()
    return bool(re.match(r"^[\u2018\u201c'\"]?[A-Z] ", prev)) or bool(nxt[:1].islower())


def _is_epigraph_attribution(text: str, start: int) -> bool:
    """A caps line sitting DIRECTLY under a line of prose or verse — "OLD BALLAD"
    under "If ever the Lion stalks again!", "THE ROAD OF KINGS" under a couplet —
    names the source of the epigraph above it. It is not a chapter.

    A real title sits under a page marker, a blank line, a bare chapter number,
    or (a wrapped heading) another caps line — never under running text.
    """
    before = text[:start]           # `start` is the caps line's own first char
    if not before.endswith("\n"):
        return False                # text start
    prev = before[:-1].rsplit("\n", 1)[-1].strip()   # the line DIRECTLY above
    if not prev or prev.startswith("--- Page") or prev.isdigit() or prev.isupper():
        return False
    return True


def segment_into_chapters(text: str, max_chars: int = 20000) -> List[Dict[str, Any]]:
    """Split book text into large spans for long-context reading.

    Prefers real chapter markers; falls back to size-based windows so a span is
    never an arbitrary 3000-char chunk. Returns [{index, title, text}].
    """
    if not text:
        return []
    # The regex is case-insensitive for "chapter"/"part"; the caps-title
    # alternative must NOT be, or every sentence-initial line would match.
    marks = []  # (offset, is_caps_title)
    for m in _CHAPTER_RE.finditer(text):
        g = m.group(1).strip()
        # startswith("part") is not enough — "particularly ..." is not Part N.
        explicit = not g[0].isalpha() or re.match(r"(chapter|part)\s+\w+\s*$", g, re.I) is not None
        # m.start() may sit on a blank line the regex's leading \s* swallowed;
        # the tells need the caps line's OWN start, which is the group's.
        line_start = m.start(1)
        if explicit:
            marks.append((m.start(), False))
        elif (_ALLCAPS_TITLE.match(g) and not _is_drop_cap(text, line_start, m.end())
              and not _is_epigraph_attribution(text, line_start)):
            marks.append((m.start(), True))
    titled: List[Tuple[str, str, bool]] = []  # (title, text, foldable)
    if len(marks) >= 2:
        bounds = [o for o, _ in marks] + [len(text)]
        for i, (_, caps) in enumerate(marks):
            span = text[bounds[i]:bounds[i + 1]]
            titled.append((span.strip().splitlines()[0].strip()[:60], span, caps))
    else:
        titled = [("", text, False)]

    # Fold a short CAPS-TITLE span into what follows it, so "THE SCARLET
    # CITADEL" + verse + "OLD BALLAD" + drop-cap line + body is ONE chapter
    # titled by the first of those. An explicit "Chapter N" is never folded,
    # however short — a one-line chapter is still the author's chapter.
    merged: List[Tuple[str, str]] = []
    carry_title, carry_text = "", ""
    for title, span, foldable in titled:
        carry_title = carry_title or title
        carry_text += span
        if not foldable or len(carry_text.strip()) >= _MIN_SPAN:
            merged.append((carry_title, carry_text))
            carry_title, carry_text = "", ""
    if carry_text.strip():
        if merged:
            t0, x0 = merged[-1]
            merged[-1] = (t0, x0 + carry_text)
        else:
            merged.append((carry_title, carry_text))

    # Further split any span that exceeds max_chars (keep spans large, not tiny).
    chapters: List[Dict[str, Any]] = []
    idx = 0
    for title, span in merged:
        span = span.strip()
        if not span:
            continue
        if len(span) <= max_chars:
            pieces = [span]
        else:
            pieces = [span[i:i + max_chars] for i in range(0, len(span), max_chars)]
        for n, piece in enumerate(pieces, 1):
            base = title or f"Part {idx + 1}"
            label = base if len(pieces) == 1 else f"{base} ({n}/{len(pieces)})"
            chapters.append({"index": idx, "title": label, "text": piece})
            idx += 1
    return chapters


def bible_to_campaign_rules(bible: Dict[str, Any]) -> Dict[str, Any]:
    """Map a world-bible's signature systems into a campaign_rules block."""
    systems = bible.get("signature_systems", []) or []
    return {
        "description": f"{bible.get('name', 'This world')} runs on its own systems — follow them exactly.",
        "signature_systems": list(systems),
        "tone": bible.get("tone", ""),
    }


def draft_voice(style: str, sample_passages: List[str], source_text: str,
                vocab: List[str] = None) -> Dict[str, Any]:
    """Build a world-bible `voice` block for an imported book, GROUNDED in the source.

    The GM narrates in the author's voice only if the bible carries it (surfaced by
    `get_full_context`). To keep the voice faithful (not invented), sample passages
    are kept ONLY when they appear verbatim in the source text — so an imported
    book's voice is real excerpts of that author's prose, not paraphrase.
    """
    src = source_text or ""
    grounded = [p.strip() for p in (sample_passages or [])
                if p and p.strip() and p.strip() in src]
    return {
        "style": (style or "").strip(),
        "sample_passages": grounded,
        "vocab": [v.strip() for v in (vocab or []) if v and v.strip()],
    }


def log_token_estimate(text: str, label: str = "import") -> int:
    """Observable (never a cap) token estimate, emitted to stderr."""
    approx = len(text or "") // 4
    print(f"[{label}] ~{approx} tokens ({len(text or '')} chars)", file=sys.stderr)
    return approx


# --- the import chain: bible -> campaign_rules ---
#
# The split is deliberate. This module writes only what the SOURCE can prove: the
# chapter map, the verbatim-filtered voice block, and the skeleton keys
# validate_bible requires. The creative fields (tone, themes, factions, geography,
# signature_systems) are the MODEL's authorship during /import, merged in by
# re-running the same verb. Everything stays `confirmed: false` until a human
# approves it, which is what the WorldBible confirm gate reads.

_SKELETON = (
    ("tone", ""),
    ("themes", []),
    ("factions", {"nodes": [], "edges": []}),
    ("geography", {"nodes": [], "edges": []}),
    ("signature_systems", []),
    # Named-thing roster the GM scans before inventing a name. Populated by a
    # later ticket; each entry is {"name": str, "note": str}.
    ("index", {"npcs": [], "locations": [], "items": [], "monsters": []}),
)


def _bible_path(campaign_dir) -> Path:
    return Path(campaign_dir) / "world-bible.json"


def load_bible(campaign_dir) -> Dict[str, Any]:
    """Read a campaign's world-bible.json, or raise with the step that writes it."""
    path = _bible_path(campaign_dir)
    if not path.exists():
        raise FileNotFoundError(
            f"no world-bible.json in {campaign_dir} — run `gm-extract.sh draft-bible` first")
    return json.loads(path.read_text(encoding="utf-8"))


def draft_bible(campaign_dir, name: str = None, voice: Dict[str, Any] = None,
                fields: Dict[str, Any] = None) -> Dict[str, Any]:
    """Draft (or refresh) an unconfirmed world-bible.json from the campaign's source text.

    Idempotent: re-running merges `name` / `voice` / `fields` into the existing
    draft, preserving anything already authored, and scaffolds an empty `index`
    (npcs/locations/items/monsters) for the named-thing roster. Refuses to touch
    a bible a human has confirmed (ConfirmedBibleError).
    """
    cdir = Path(campaign_dir)
    path = _bible_path(cdir)
    existing = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    # Absent flag == confirmed (the WorldBible rule): hand-authored and legacy
    # bibles are never overwritten by a draft pass.
    if existing and existing.get("confirmed", True):
        raise ConfirmedBibleError(
            f"world-bible.json in {campaign_dir} is confirmed — refusing to redraft it")

    src_path = cdir / "source" / "current-document.txt"
    if not src_path.exists():
        legacy = cdir / "current-document.txt"  # pre-source/ campaigns
        if legacy.exists():
            src_path = legacy
        else:
            raise FileNotFoundError(
                f"no source/current-document.txt in {campaign_dir} — run `gm-extract.sh prepare` first")
    source = src_path.read_text(encoding="utf-8", errors="replace")
    log_token_estimate(source, label="draft-bible")

    bible = dict(existing)
    bible["name"] = name or bible.get("name") or cdir.name
    for key, default in _SKELETON:
        bible.setdefault(key, copy.deepcopy(default))
    if fields:
        bible.update(fields)
    if voice is not None:
        bible["voice"] = draft_voice(
            style=voice.get("style", ""),
            sample_passages=voice.get("sample_passages", []),
            source_text=source,
            vocab=voice.get("vocab", []),
        )
    else:
        bible.setdefault("voice", draft_voice("", [], source))
    bible["confirmed"] = False

    path.write_text(json.dumps(bible, indent=2, ensure_ascii=False), encoding="utf-8")
    return bible


def write_campaign_rules(campaign_dir) -> Dict[str, Any]:
    """Map the bible's signature systems into campaign-overview.json's campaign_rules."""
    rules = bible_to_campaign_rules(load_bible(campaign_dir))
    seed_overview(campaign_dir, campaign_rules=rules)
    return rules


INDEX_BUCKETS = ("npcs", "locations", "items", "monsters")


def write_index(campaign_dir, index: Dict[str, Any]) -> Dict[str, Any]:
    """Persist a WORLD INDEX into the bible (the light import pass, not the census).

    Merges `index` into the bible's existing `index`, keyed by four buckets
    (npcs/locations/items/monsters). Each entry is reduced to `{name, note}`;
    nameless entries are DROPPED and names are deduped case-insensitively (first
    note wins, a later note fills a blank one). Writes back to world-bible.json
    without touching any other field or the confirm flag.
    """
    bible = load_bible(campaign_dir)
    existing = bible.get("index") or {}
    out: Dict[str, Any] = {}
    for bucket in INDEX_BUCKETS:
        seen: Dict[str, Dict[str, str]] = {}
        for entry in list(existing.get(bucket, []) or []) + list((index or {}).get(bucket, []) or []):
            if not isinstance(entry, dict):
                continue
            name = (entry.get("name") or "").strip()
            if not name:
                continue  # drop nameless typed extras
            note = (entry.get("note") or "").strip()
            key = name.lower()
            if key not in seen:
                seen[key] = {"name": name, "note": note}
            elif note and not seen[key]["note"]:
                seen[key]["note"] = note
        out[bucket] = list(seen.values())
    bible["index"] = out
    _bible_path(campaign_dir).write_text(
        json.dumps(bible, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


_COIN_RE = re.compile(r'^\s*[\d,]+\s+(gold|silver|copper|platinum|electrum)\s+pieces?\s*$', re.I)


def derive_index_from_module(campaign_dir) -> Dict[str, Any]:
    """Build a WORLD INDEX from a converted module's OWN data — no agent authoring.

    /import-module writes adventure.json + npcs.json but never drafted a bible, so
    the WORLD INDEX block in scene context silently did not render. That block is
    the rail that stops a name being invented, or a real name being placed in the
    wrong scene. Deriving it mechanically from what the import already persisted
    keeps the index true to the book by construction.
    """
    cdir = Path(campaign_dir)

    def _load(name, default):
        p = cdir / name
        if not p.exists():
            return default
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return default

    npcs = _load("npcs.json", {})
    locations = _load("locations.json", {})
    adventure = _load("adventure.json", {})
    scenes = adventure.get("scenes") or []

    # A module import has no source/current-document.txt, so draft_bible cannot run.
    # Seed the minimum a bible needs to hold an index, left unconfirmed so a later
    # draft-bible pass can still enrich it.
    bible_path = _bible_path(cdir)
    if not bible_path.exists():
        meta = adventure.get("meta") or {}
        bible_path.write_text(json.dumps({
            "name": meta.get("title") or cdir.name,
            "confirmed": False,
            "source": "derived from converted module (adventure.json)",
            "index": {b: [] for b in INDEX_BUCKETS},
        }, indent=2, ensure_ascii=False), encoding="utf-8")

    index: Dict[str, List[Dict[str, str]]] = {b: [] for b in INDEX_BUCKETS}

    for name, body in (npcs.items() if isinstance(npcs, dict) else []):
        note = (body or {}).get("description", "") if isinstance(body, dict) else ""
        index["npcs"].append({"name": name, "note": str(note).strip()})

    for name, body in (locations.items() if isinstance(locations, dict) else []):
        note = (body or {}).get("description", "") if isinstance(body, dict) else ""
        index["locations"].append({"name": name, "note": str(note).strip()})

    for scene in scenes:
        if not isinstance(scene, dict):
            continue
        key = str(scene.get("key") or "").strip()
        where = f"scene {key}" if key else "the module"

        loc = str(scene.get("location") or "").strip()
        if loc:
            index["locations"].append({"name": loc, "note": f"{where}: {scene.get('title', '')}".strip(": ")})

        for enc in scene.get("encounters") or []:
            for mon in (enc or {}).get("monsters") or []:
                mname = str((mon or {}).get("name") or "").strip()
                if mname:
                    index["monsters"].append({"name": mname, "note": where})

        for item in scene.get("treasure") or []:
            iname = str(item or "").strip()
            if iname and not _COIN_RE.match(iname):
                index["items"].append({"name": iname, "note": where})

    return write_index(cdir, index)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Book Bible import chain")
    sub = parser.add_subparsers(dest="action", required=True)

    p_bible = sub.add_parser("draft-bible", help="draft/refresh an unconfirmed world-bible.json")
    p_bible.add_argument("campaign_dir")
    p_bible.add_argument("--name", help="the world's name (defaults to the campaign folder)")
    p_bible.add_argument("--voice-json", help='{"style":...,"sample_passages":[...],"vocab":[...]}')
    p_bible.add_argument("--fields-json", help="JSON object of creative fields (tone/themes/factions/...)")

    p_rules = sub.add_parser("campaign-rules", help="write campaign_rules into campaign-overview.json")
    p_rules.add_argument("campaign_dir")

    p_index = sub.add_parser("write-index",
                             help="persist a WORLD INDEX into the bible (the light import pass)")
    p_index.add_argument("campaign_dir")
    p_index.add_argument("--index-json", required=True,
                         help='{"npcs":[{"name":..,"note":..}],"locations":[...],"items":[...],"monsters":[...]}')

    p_derive = sub.add_parser("index-from-module",
                              help="derive the WORLD INDEX from adventure.json + npcs.json")
    p_derive.add_argument("campaign_dir")

    args = parser.parse_args()

    try:
        if args.action == "index-from-module":
            idx = derive_index_from_module(args.campaign_dir)
            print("WORLD INDEX derived from the module: " + ", ".join(
                f"{len(idx.get(b, []))} {b}" for b in INDEX_BUCKETS))
        elif args.action == "draft-bible":
            bible = draft_bible(
                args.campaign_dir,
                name=args.name,
                voice=json.loads(args.voice_json) if args.voice_json else None,
                fields=json.loads(args.fields_json) if args.fields_json else None,
            )
            idx = bible.get("index", {})
            idx_counts = ", ".join(f"{len(idx.get(b, []))} {b}"
                                   for b in ("npcs", "locations", "items", "monsters"))
            print(f"world-bible.json drafted: {bible['name']} "
                  f"(index: {idx_counts}; "
                  f"{len(bible['voice']['sample_passages'])} verbatim passages, confirmed=False)")
        elif args.action == "write-index":
            idx = write_index(args.campaign_dir, json.loads(args.index_json))
            counts = ", ".join(f"{len(idx.get(b, []))} {b}" for b in INDEX_BUCKETS)
            print(f"world index written: {counts}")
        else:
            rules = write_campaign_rules(args.campaign_dir)
            print(f"campaign_rules written: {len(rules['signature_systems'])} signature systems")
    except (ConfirmedBibleError, FileNotFoundError) as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
