"""visual_appearance.py — the canonical look-of-a-character block.

Every character in the world (the PC and every NPC) carries a structured
``visual_appearance`` dict so images render them CONSISTENTLY. The image model
has no memory between calls; this block is the single source of truth the
scene-illustrator injects into every prompt that contains that character.

The field set is FIXED and ORDERED. Authored at creation (world-gen / NPC-gen /
character-creation) and updated whenever a character's look changes in play
(new gear, wounds, a haircut, aging). One module so the PC and NPC paths can
never drift apart.
"""

from __future__ import annotations

# The exact, ordered field set. Do NOT add/remove keys without updating the
# scene-illustrator agent, the creation docs, and the extraction schema.
VISUAL_FIELDS = (
    "sex",        # male / female / nonbinary / n/a (construct, swarm, etc.)
    "age",        # "late 20s", "ancient", "adolescent"
    "race",       # cultural/fantasy race or ethnicity ("Human", "Half-Orc")
    "species",    # biological kind ("human", "rat-changeling", "ooze", "AI drone")
    "hair",       # color, length, style, condition ("" if none — bald, slime, metal)
    "face",       # shape, skin tone, marks, default expression
    "eyes",       # color + what they do ("brown, darting"; "no eyes — sensor cluster")
    "clothing",   # every visible garment: color, fit, wear, branding
    "gear",       # visible weapons/items, how carried; note barefoot here if so
    "demeanor",   # posture, body language, vibe (scrappy / regal / broken)
    "size",       # build + scale ("small, slight"; "towering, 9ft"; "tiny, cat-sized")
)


def empty_template() -> dict:
    """A fresh block with every field present and blank (authored later)."""
    return {k: "" for k in VISUAL_FIELDS}


def normalize(va) -> dict:
    """Coerce arbitrary input to the canonical key set, in order.

    Unknown keys are dropped; missing keys are filled blank; values are
    stringified and trimmed. Always returns all VISUAL_FIELDS.
    """
    src = va if isinstance(va, dict) else {}
    out = {}
    for k in VISUAL_FIELDS:
        v = src.get(k, "")
        out[k] = ("" if v is None else str(v)).strip()
    return out


def is_blank(va) -> bool:
    """True if no field carries any content (nothing authored yet)."""
    n = normalize(va)
    return not any(n.values())


def merge(existing, updates: dict) -> dict:
    """Return existing block updated with only the non-empty provided fields."""
    out = normalize(existing)
    for k, v in (updates or {}).items():
        if k in VISUAL_FIELDS and v is not None and str(v).strip() != "":
            out[k] = str(v).strip()
    return out


def format_line(name: str, va) -> str:
    """Render a one-line 'character bible' string for an image prompt.

    Skips blank fields so a partially-authored block still reads naturally.
    Returns "" if the block is entirely blank.
    """
    n = normalize(va)
    if not any(n.values()):
        return ""

    # race + species fold together when both present / when redundant.
    race, species = n["race"], n["species"]
    if race and species and race.lower() != species.lower():
        kind = f"{race} ({species})"
    else:
        kind = race or species

    parts = []
    ident = ", ".join(p for p in (n["sex"], n["age"], kind) if p)
    if ident:
        parts.append(ident)
    if n["hair"]:
        parts.append(f"{n['hair']} hair")
    if n["face"]:
        parts.append(n["face"])
    if n["eyes"]:
        parts.append(f"{n['eyes']} eyes")
    if n["clothing"]:
        parts.append(f"wearing {n['clothing']}")
    if n["gear"]:
        parts.append(n["gear"])
    if n["demeanor"]:
        parts.append(f"{n['demeanor']} demeanor")
    if n["size"]:
        parts.append(f"{n['size']} build")

    return f"{name} — " + "; ".join(parts) + "."
