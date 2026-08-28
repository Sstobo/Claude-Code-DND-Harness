#!/usr/bin/env python3
"""One-shot visual_appearance migration + the unauthored-looks report.

The d28fb34 field-set change (clothing/species/age/demeanor out; color/shirt/
pants/short_description in) shipped a read-time shim with no data pass, so
legacy blocks lost `age`/`demeanor` content on every read and most NPCs carried
blank legacy templates that fail image generation closed.

  migrate [--dry-run]   Normalize every PC and NPC block in every campaign,
                        folding legacy vocabulary forward, and write back only
                        what changed. Idempotent.
  report [<campaign>]   List every character whose block is blank (unauthored)
                        — the author-a-look worklist. Exposed as
                        `gm-npc.sh appearance-report`.

A future field-set change must ship with a `migrate` run in the same commit;
this file is the precedent.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import visual_appearance as va_mod

BASE = Path(__file__).resolve().parent.parent / "world-state" / "campaigns"


def _load(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _save(p: Path, data) -> None:
    p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def migrate(dry_run: bool = False) -> int:
    changed = 0
    for camp in sorted(BASE.glob("*/")):
        char_p = camp / "character.json"
        char = _load(char_p)
        if isinstance(char, dict) and isinstance(char.get("visual_appearance"), dict):
            new = va_mod.normalize(char["visual_appearance"])
            if new != char["visual_appearance"]:
                changed += 1
                print(f"[MIGRATE] {camp.name}/PC {char.get('name', '?')}")
                if not dry_run:
                    char["visual_appearance"] = new
                    _save(char_p, char)

        npcs_p = camp / "npcs.json"
        npcs = _load(npcs_p)
        if isinstance(npcs, dict):
            dirty = False
            for name, npc in npcs.items():
                if not isinstance(npc, dict):
                    continue
                old = npc.get("visual_appearance")
                if not isinstance(old, dict):
                    continue
                new = va_mod.normalize(old)
                if new != old:
                    changed += 1
                    dirty = True
                    print(f"[MIGRATE] {camp.name}/NPC {name}")
                    npc["visual_appearance"] = new
            if dirty and not dry_run:
                _save(npcs_p, npcs)
    print(f"{'Would migrate' if dry_run else 'Migrated'} {changed} block(s).")
    return 0


def report(campaign: str = None) -> int:
    """List unauthored (blank) looks — everyone image generation refuses."""
    total_blank = total = 0
    for camp in sorted(BASE.glob("*/")):
        if campaign and camp.name != campaign:
            continue
        blanks = []
        char = _load(camp / "character.json")
        if isinstance(char, dict):
            total += 1
            if va_mod.is_blank(char.get("visual_appearance")):
                total_blank += 1
                blanks.append(f"PC  {char.get('name', '?')}")
        npcs = _load(camp / "npcs.json")
        if isinstance(npcs, dict):
            for name, npc in npcs.items():
                if not isinstance(npc, dict):
                    continue
                total += 1
                if va_mod.is_blank(npc.get("visual_appearance")):
                    total_blank += 1
                    blanks.append(f"NPC {name}")
        if blanks:
            print(f"\n{camp.name} — {len(blanks)} unauthored look(s):")
            for b in blanks:
                print(f"  {b}")
    print(f"\n{total_blank}/{total} characters have no authored look; "
          f"gm-image.sh will refuse to render them until one is set "
          f"(gm-npc.sh set-appearance / gm-player.sh set-appearance).")
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["migrate"]:
        sys.exit(migrate(dry_run="--dry-run" in args))
    if args[:1] == ["report"]:
        sys.exit(report(args[1] if len(args) > 1 else None))
    print(__doc__)
    sys.exit(1)
