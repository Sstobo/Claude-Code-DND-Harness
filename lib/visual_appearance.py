"""visual_appearance.py — the canonical look-of-a-character block.

Every character in the world (the PC and every NPC) carries a structured
``visual_appearance`` dict so images render them CONSISTENTLY. The image model
has no memory between calls; this block is the single source of truth the
scene-illustrator injects into every prompt that contains that character.

The field set is FIXED and ORDERED, and it is authored BEFORE a character's
first image — never derived from one afterwards. Once authored it is frozen:
it changes only on an explicit in-world event (new armor, a scar, a haircut),
never by re-deriving it from a fresh scene prompt. Re-derivation is how looks
drift.

Write values as fixed vocabulary tokens, not prose: "olive-green", not
"a sort of mottled greenish tone". The model re-reads identical words as an
identical instruction; paraphrase reads as a new character.

One module so the PC and NPC paths can never drift apart. The CLI flags on
`gm-npc.sh set-appearance` / `gm-player.sh set-appearance` are generated from
VISUAL_FIELDS, so adding a field here adds it everywhere.
"""

from __future__ import annotations

# The exact, ordered field set. Do NOT add/remove keys without updating the
# scene-illustrator agent, the creation docs, and the extraction schema.
VISUAL_FIELDS = (
    "race",              # cultural/fantasy race or kind ("Half-Orc", "ooze", "AI drone")
    "sex",               # male / female / nonbinary / n/a (construct, swarm)
    "size",              # build + scale ("small, slight"; "towering, 7ft, heavy")
    "color",             # skin/hide/chassis colour ("olive-green", "ash-grey")
    "hair",              # colour, length, style ("" if none — bald, slime, metal)
    "eyes",              # colour + what they do ("dark brown, deep-set")
    "face",              # shape, marks, default expression
    "shirt",             # upper body: garment, colour, condition
    "pants",             # lower body: garment, colour, footwear (note barefoot here)
    "gear",              # visible weapons/items and how they're carried
    "short_description",  # the silhouette at thumbnail size: one shape, one colour, one prop
)

# Fields the old 11-field schema carried that this one folds elsewhere.
# Kept so existing campaigns keep their authored looks instead of blanking.
_LEGACY_MAP = {
    "clothing": "shirt",   # old single garment field → upper body
    "species": "race",     # old biological kind → race, when race is empty
}


def empty_template() -> dict:
    """A fresh block with every field present and blank (authored later)."""
    return {k: "" for k in VISUAL_FIELDS}


def normalize(va) -> dict:
    """Coerce arbitrary input to the canonical key set, in order.

    Legacy keys (``clothing``, ``species``) migrate into their replacement when
    that replacement is empty; other unknown keys are dropped. Missing keys are
    filled blank; values are stringified and trimmed.
    """
    src = va if isinstance(va, dict) else {}
    out = {}
    for k in VISUAL_FIELDS:
        v = src.get(k, "")
        out[k] = ("" if v is None else str(v)).strip()
    for old, new in _LEGACY_MAP.items():
        if not out[new] and src.get(old):
            out[new] = str(src[old]).strip()
    return out


def is_blank(va) -> bool:
    """True if no field carries any content (nothing authored yet)."""
    return not any(normalize(va).values())


def merge(existing, updates: dict) -> dict:
    """Return existing block updated with only the non-empty provided fields."""
    out = normalize(existing)
    for k, v in (updates or {}).items():
        if k in VISUAL_FIELDS and v is not None and str(v).strip() != "":
            out[k] = str(v).strip()
    return out


def format_line(name: str, va) -> str:
    """Render the block as one prompt-ready spec line.

    Emitted as ``key: value`` pairs in fixed order — a spec sheet, not prose —
    so the same character reaches the model as the same string every time.
    Blank fields are skipped; a wholly blank block returns "".
    """
    n = normalize(va)
    parts = [f"{k}: {n[k]}" for k in VISUAL_FIELDS if n[k]]
    return f"{name} — " + "; ".join(parts) + "." if parts else ""


def demo() -> None:
    """Self-check: field order, legacy migration, merge, blank handling."""
    assert empty_template() == {k: "" for k in VISUAL_FIELDS}
    assert is_blank({}) and is_blank({"race": "  "}) and format_line("X", {}) == ""

    legacy = {"species": "half-orc", "clothing": "fur harness", "age": "30s",
              "sex": "male", "hair": "black"}
    n = normalize(legacy)
    assert n["race"] == "half-orc", n           # species folded in
    assert n["shirt"] == "fur harness", n       # clothing folded in
    assert "age" not in n and "demeanor" not in n
    assert list(n) == list(VISUAL_FIELDS)       # order is stable

    # An explicit race wins over the legacy species value.
    assert normalize({"race": "Half-Orc", "species": "orc"})["race"] == "Half-Orc"

    merged = merge(n, {"eyes": "dark brown", "hair": "", "bogus": "x"})
    assert merged["eyes"] == "dark brown" and merged["hair"] == "black"
    assert "bogus" not in merged

    line = format_line("Kordan", merged)
    assert line.startswith("Kordan — race: half-orc; sex: male; "), line
    assert line.index("hair:") < line.index("eyes:") < line.index("shirt:"), line
    print("visual_appearance demo OK")


if __name__ == "__main__":
    demo()
