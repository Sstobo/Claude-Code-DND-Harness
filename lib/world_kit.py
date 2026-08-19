#!/usr/bin/env python3
"""
World Kit: the D&D 5e ruleset that sits on top of the generic game core.

The mechanics are HARDCODED — every campaign plays 5e (str/dex/con/int/wis/cha,
hp, d20-vs-dc, XP levels, death saves). There is no per-campaign `ruleset.json`
any more; if one is left on disk from an older campaign the kit ignores it.
Play still runs through `game_core`, so resolution, progression, and harm stay
in one place and the engine stays system-agnostic underneath.

A book's own flavor does NOT come from the kit — `signature_systems()` is empty
by design, so scene context falls through to `campaign_rules()`
(campaign-overview.json → `campaign_rules`), which is where an imported world's
loot boxes, viewer counts, and house systems live.
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent))

from json_ops import JsonOperations
from campaign_manager import CampaignManager
from game_core import make_progression, opposed_check, resolve_check


# XP required to reach level 2..20 (standard 5e table). Index i = level i+2.
XP_THRESHOLDS = [300, 900, 2700, 6500, 14000, 23000, 34000, 48000, 64000,
                 85000, 100000, 120000, 140000, 165000, 195000, 225000,
                 265000, 305000, 355000]

ATTRIBUTES = ["str", "dex", "con", "int", "wis", "cha"]
VITALS = ["hp"]

# Specialist agents the 5e kit legitimizes (dnd5eapi-backed).
ACTIVE_AGENTS = ["monster-manual", "rules-master", "spell-caster",
                 "gear-master", "loot-dropper"]


class WorldKit:
    """The D&D 5e kit, driving play through the generic core."""

    def __init__(self, world_state_dir: str = None):
        base = world_state_dir or "world-state"
        cm = CampaignManager(base)
        self.campaign_dir = cm.get_active_campaign_dir()
        self.json_ops = JsonOperations(str(self.campaign_dir))
        self.progression = make_progression("xp-levels", thresholds=XP_THRESHOLDS)

    # --- declared configuration ---
    def name(self) -> str:
        return "D&D 5e"

    def kit(self) -> str:
        """Kit identity. Always 'dnd5e' — it unlocks the D&D mechanics Skills
        (gm-combat, gm-levelup, gm-spellcasting) and the dnd5eapi agents."""
        return "dnd5e"

    def stat_schema(self) -> Dict[str, Any]:
        return {"attributes": list(ATTRIBUTES), "vitals": list(VITALS)}

    def vitals(self) -> List[str]:
        """Vital tracks this world runs on. 5e has one: hp."""
        return list(VITALS)

    def resolution(self) -> Dict[str, Any]:
        """{'model': name, 'params': {...}} for game_core.resolve_check."""
        return {"model": "d20-vs-dc", "params": {}}

    def resolution_model(self) -> str:
        return self.resolution()["model"]

    def progression_model(self) -> str:
        return "xp-levels"

    def active_agents(self) -> List[str]:
        return list(ACTIVE_AGENTS)

    def rules_doc_path(self) -> Optional[Path]:
        """The campaign's long-form rules prose (loaded on demand), if present.

        By convention `rules.md` in the campaign dir — the `ruleset.rules_doc`
        pointer went away with ruleset.json.
        """
        if self.campaign_dir is None:
            return None
        p = Path(self.campaign_dir) / "rules.md"
        return p if p.exists() else None

    def campaign_rules(self) -> Dict[str, Any]:
        """World-flavor systems (loot boxes, viewers, ...) from campaign-overview.

        This is where an imported book's own systems live: the kit declares no
        signature systems, so scene context always renders these.
        """
        overview = self.json_ops.load_json("campaign-overview.json") or {}
        return overview.get("campaign_rules", {})

    def skills(self) -> List[str]:
        """Skill names the kit declares. Empty: 5e's skill list lives in the
        gm-skills Skill, not in the kit block."""
        return []

    def signature_systems(self) -> List[Dict[str, str]]:
        """Prose rule flavor declared by the kit. Always empty — book flavor
        flows through `campaign_rules()` instead."""
        return []

    def lethality(self) -> Dict[str, Any]:
        """The kit's lethality model for `game_core.classify_harm`.

        5e-faithful death saves: 0 HP opens the dying gate, and only overkill of
        at least max HP kills outright (classify_harm defaults the massive-damage
        bar to max HP when it is not named).
        """
        return {"model": "death-saves"}

    def systems(self) -> List[Dict[str, Any]]:
        """Executable signature-system primitives. Always empty — the 5e kit
        instantiates none of game_core's named_track / price_roll / etc."""
        return []

    # --- play, driven through the generic core ---
    def resolve(self, modifier: int = 0, dc: int = 10, advantage: str = None) -> Dict[str, Any]:
        """Roll a d20 check through the generic core."""
        return resolve_check(modifier, dc, advantage, model=self.resolution())

    def oppose(self, modifier_a: int = 0, modifier_b: int = 0,
               advantage_a: str = None, advantage_b: str = None) -> Dict[str, Any]:
        """Contest two sides through the generic core."""
        return opposed_check(modifier_a, modifier_b, advantage_a, advantage_b,
                             model=self.resolution())

    def advance_progression(self, state: Dict[str, Any], **kw) -> Dict[str, Any]:
        return self.progression.advance(state, **kw)

    def level(self, state: Dict[str, Any]) -> int:
        return self.progression.level(state)


def main():
    import argparse
    import json
    from cli_output import wants_json, strip_json_flag, emit

    parser = argparse.ArgumentParser(description="World Kit info")
    parser.add_argument("action", nargs="?", default="info", choices=["info"])
    json_mode = wants_json()
    parser.parse_args(strip_json_flag(sys.argv[1:]))

    kit = WorldKit()
    info = {
        "name": kit.name(),
        "kit": kit.kit(),
        "stat_schema": kit.stat_schema(),
        "resolution_model": kit.resolution_model(),
        "progression_model": kit.progression_model(),
        "active_agents": kit.active_agents(),
        "rules_doc": str(kit.rules_doc_path()) if kit.rules_doc_path() else None,
    }
    if json_mode:
        emit(info, json_mode=True)
    else:
        print(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()
