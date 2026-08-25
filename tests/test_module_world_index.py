"""The WORLD INDEX derived from a converted module.

/import-module writes adventure.json + npcs.json but has no source text, so
draft_bible cannot run and the index block silently never rendered — leaving the
GM with no rail against placing a real name in the wrong scene. These cover the
derivation that closes that hole.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from book_bible import derive_index_from_module


def _campaign(tmp_path):
    (tmp_path / "npcs.json").write_text(json.dumps({
        "Borin Grimhammer": {"description": "Gruff dwarf shopkeeper — first seen in 2.2"},
    }))
    (tmp_path / "adventure.json").write_text(json.dumps({
        "meta": {"title": "The Whispering Wood"},
        "scenes": [
            {"key": "2.1", "title": "Dockside Hustle", "location": "Eldoria Docks",
             "encounters": [{"monsters": [{"name": "Scout"}]}],
             "treasure": ["24 Gold pieces", "Cloak of Elvenkind"]},
        ],
    }))
    return tmp_path


def test_index_is_derived_from_the_modules_own_files(tmp_path):
    index = derive_index_from_module(_campaign(tmp_path))
    assert {e["name"] for e in index["npcs"]} == {"Borin Grimhammer"}
    assert "Eldoria Docks" in {e["name"] for e in index["locations"]}
    assert "Scout" in {e["name"] for e in index["monsters"]}


def test_a_module_import_gets_a_bible_even_with_no_source_text(tmp_path):
    """draft_bible needs current-document.txt; a module import never has one."""
    derive_index_from_module(_campaign(tmp_path))
    bible = json.loads((tmp_path / "world-bible.json").read_text())
    assert bible["name"] == "The Whispering Wood"
    assert bible["confirmed"] is False, "must stay redraftable"


def test_loose_coin_is_not_a_named_item(tmp_path):
    names = {e["name"] for e in derive_index_from_module(_campaign(tmp_path))["items"]}
    assert "Cloak of Elvenkind" in names
    assert "24 Gold pieces" not in names


def test_rerunning_does_not_duplicate_entries(tmp_path):
    cdir = _campaign(tmp_path)
    derive_index_from_module(cdir)
    twice = derive_index_from_module(cdir)
    assert len(twice["npcs"]) == 1
    assert len(twice["locations"]) == 1
