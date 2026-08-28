"""Legacy visual_appearance content folds forward instead of dropping.

Regression for d28fb34: the field-set change (clothing/species/age/demeanor →
color/shirt/pants/short_description) shipped a read-time shim that DROPPED
`age` and `demeanor` — Conan lost "young, late teens" and his movement
description on every single image render, silently.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

import visual_appearance as va


def test_age_appends_onto_face():
    out = va.normalize({"face": "hard, grim", "age": "young, late teens"})
    assert out["face"] == "hard, grim, young, late teens"


def test_demeanor_appends_onto_short_description():
    out = va.normalize({"demeanor": "coiled, watchful"})
    assert out["short_description"] == "coiled, watchful"


def test_append_is_idempotent():
    once = va.normalize({"face": "grim", "age": "young"})
    assert va.normalize(once) == once
    # And feeding the legacy key again does not double the content.
    assert va.normalize({**once, "age": "young"}) == once


def test_rename_folds_still_work():
    out = va.normalize({"clothing": "a cheap tunic", "species": "human"})
    assert out["shirt"] == "a cheap tunic"
    assert out["race"] == "human"


def test_rename_never_overwrites_authored_content():
    out = va.normalize({"race": "Cimmerian", "species": "human"})
    assert out["race"] == "Cimmerian"


def test_migrate_tool_is_idempotent_against_live_data():
    """After the 2026-08-28 in-place migration, a second run changes nothing."""
    import appearance_migrate
    if not appearance_migrate.BASE.exists():
        import pytest
        pytest.skip("no live campaigns")
    import contextlib, io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        appearance_migrate.migrate(dry_run=True)
    assert "Would migrate 0 block(s)." in buf.getvalue()
