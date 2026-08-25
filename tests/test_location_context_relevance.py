"""A location only keeps source passages that are actually about it.

Semantic search always returns its best N however bad they are. Taking the top 5
unconditionally wrote five passages about a different city into a location's
permanent record, labelled "(from source)" — which reads as canon for that place.
"""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.entity_enhancer import EntityEnhancer, MAX_CONTEXT_DISTANCE


def _enhancer(tmp_path):
    (tmp_path / "campaigns" / "c").mkdir(parents=True)
    (tmp_path / "active-campaign.txt").write_text("c")
    (tmp_path / "campaigns" / "c" / "vectors").mkdir()
    (tmp_path / "campaigns" / "c" / "vectors" / "chroma.sqlite3").write_text("x")
    (tmp_path / "campaigns" / "c" / "locations.json").write_text("{}")
    return EntityEnhancer(str(tmp_path))


def _passages(*distances):
    return [{"text": f"passage at {d}", "distance": d, "metadata": {}} for d in distances]


def test_noise_only_results_yield_no_context(tmp_path):
    """The failure that shipped: every hit is noise, all five get stored anyway."""
    e = _enhancer(tmp_path)
    noise = _passages(0.772, 0.774, 0.777, 0.782, 0.809)
    with patch.object(EntityEnhancer, "search_raw", return_value=noise):
        assert e.get_scene_context("The Saltbreeze Stockade") is None


def test_relevant_results_survive(tmp_path):
    e = _enhancer(tmp_path)
    with patch.object(EntityEnhancer, "search_raw", return_value=_passages(0.442, 0.554)):
        result = e.get_scene_context("The Whispering Wood")
    assert result and len(result["passages"]) == 2


def test_the_floor_splits_a_mixed_result(tmp_path):
    e = _enhancer(tmp_path)
    mixed = _passages(0.44, 0.59, 0.61, 0.78)
    with patch.object(EntityEnhancer, "search_raw", return_value=mixed):
        kept = e.get_scene_context("Eldoria")["passages"]
    assert [p["distance"] for p in kept] == [0.44, 0.59]
    assert all(p["distance"] <= MAX_CONTEXT_DISTANCE for p in kept)


def test_a_passage_with_no_distance_is_not_trusted(tmp_path):
    e = _enhancer(tmp_path)
    with patch.object(EntityEnhancer, "search_raw",
                      return_value=[{"text": "t", "metadata": {}}]):
        assert e.get_scene_context("Nowhere") is None
