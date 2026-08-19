#!/usr/bin/env python3
"""
Quick D&D encounter helper using API CR filtering

Two modes:
  pick-at-CR   uv run python dnd_encounter_v2.py --cr <CR> [--count <number>]
  XP budget    uv run python dnd_encounter_v2.py --party-level 3 --difficulty hard
"""

import sys
import argparse
import random
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from dnd_api_core import fetch, output, error_output

DIFFICULTIES = ("easy", "medium", "hard", "deadly")

# DMG p.82 — XP thresholds per character, by level: easy / medium / hard / deadly.
XP_THRESHOLDS = {
    1:  (25, 50, 75, 100),
    2:  (50, 100, 150, 200),
    3:  (75, 150, 225, 400),
    4:  (125, 250, 375, 500),
    5:  (250, 500, 750, 1100),
    6:  (300, 600, 900, 1400),
    7:  (350, 750, 1100, 1700),
    8:  (450, 900, 1400, 2100),
    9:  (550, 1100, 1600, 2400),
    10: (600, 1200, 1900, 2800),
    11: (800, 1600, 2400, 3600),
    12: (1000, 2000, 3000, 4500),
    13: (1100, 2200, 3400, 5100),
    14: (1250, 2500, 3800, 5700),
    15: (1400, 2800, 4300, 6400),
    16: (1600, 3200, 4800, 7200),
    17: (2000, 3900, 5900, 8800),
    18: (2100, 4200, 6300, 9500),
    19: (2400, 4900, 7300, 10900),
    20: (2800, 5700, 8500, 12700),
}

# DMG p.82 — XP by challenge rating.
CR_XP = {
    0: 10, 0.125: 25, 0.25: 50, 0.5: 100,
    1: 200, 2: 450, 3: 700, 4: 1100, 5: 1800, 6: 2300, 7: 2900, 8: 3900,
    9: 5000, 10: 5900, 11: 7200, 12: 8400, 13: 10000, 14: 11500, 15: 13000,
    16: 15000, 17: 18000, 18: 20000, 19: 22000, 20: 25000, 21: 33000,
    22: 41000, 23: 50000, 24: 62000, 25: 75000, 26: 90000, 27: 105000,
    28: 120000, 29: 135000, 30: 155000,
}

# DMG p.82 — the multiplier ladder. A small party shifts one step up, a large
# party one step down; that is why 0.5 sits below the single-monster default.
MULTIPLIER_LADDER = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0)


def party_thresholds(party_level, party_size):
    """The four DMG XP budgets for this party, as a dict keyed by difficulty."""
    if party_level not in XP_THRESHOLDS:
        raise ValueError(f"party level must be 1-20, got {party_level}")
    if party_size < 1:
        raise ValueError(f"party size must be at least 1, got {party_size}")
    per_pc = XP_THRESHOLDS[party_level]
    return {name: per_pc[i] * party_size for i, name in enumerate(DIFFICULTIES)}


def xp_budget(party_level, party_size, difficulty):
    """XP budget for one encounter at the given difficulty."""
    if difficulty not in DIFFICULTIES:
        raise ValueError(f"difficulty must be one of {DIFFICULTIES}, got {difficulty!r}")
    return party_thresholds(party_level, party_size)[difficulty]


def encounter_multiplier(monster_count, party_size=4):
    """DMG encounter multiplier for a number of monsters against a party size."""
    if monster_count < 1:
        raise ValueError(f"monster count must be at least 1, got {monster_count}")
    if monster_count == 1:
        step = 1
    elif monster_count == 2:
        step = 2
    elif monster_count <= 6:
        step = 3
    elif monster_count <= 10:
        step = 4
    elif monster_count <= 14:
        step = 5
    else:
        step = 6
    if party_size < 3:
        step += 1
    elif party_size >= 6:
        step -= 1
    step = max(0, min(step, len(MULTIPLIER_LADDER) - 1))
    return MULTIPLIER_LADDER[step]


def classify_difficulty(adjusted_xp, party_level, party_size):
    """Which band an adjusted-XP total falls in: trivial/easy/medium/hard/deadly."""
    budgets = party_thresholds(party_level, party_size)
    for name in reversed(DIFFICULTIES):
        if adjusted_xp >= budgets[name]:
            return name
    return "trivial"


def normalize_cr(cr):
    """The CR_XP key for a CR the user typed, or None if the SRD has no such CR."""
    if cr is None:
        return None
    for key in CR_XP:
        if key == cr:
            return key
    return None


def cr_choices():
    """Every valid CR, formatted for an error message."""
    return ", ".join("1/8" if c == 0.125 else "1/4" if c == 0.25 else
                     "1/2" if c == 0.5 else str(c) for c in sorted(CR_XP))


def band_window(party_level, party_size, difficulty):
    """(floor, ceiling) of one band's adjusted XP. The ceiling is exclusive.

    A "hard" encounter has to stop below the deadly line, and by the same logic a
    "medium" one has to stop below the hard line — asking for medium and getting
    something classify_difficulty calls hard is the same failure one band down.
    Deadly is open-ended, so it takes a little headroom instead of a next floor.
    """
    budgets = party_thresholds(party_level, party_size)
    floor = budgets[difficulty]
    if difficulty == "deadly":
        return floor, budgets["deadly"] * 1.25
    return floor, budgets[DIFFICULTIES[DIFFICULTIES.index(difficulty) + 1]]


def rank_plans(party_level, party_size, difficulty, cr_hint=None, max_monsters=8):
    """Every count/CR combination, best first.

    Pure math — no network. Three tiers: combinations that land squarely in the
    requested band, then ones that overshoot it but stay under deadly, then the
    rest by distance from the budget. Anything outside the requested band carries
    a `note` naming the band it actually lands in, so nothing overshoots silently.
    """
    floor, ceiling = band_window(party_level, party_size, difficulty)
    deadly = party_thresholds(party_level, party_size)["deadly"]

    hint = normalize_cr(cr_hint)
    crs = [hint] if hint is not None else sorted(CR_XP)
    exact, over, under = [], [], []
    for count in range(1, max_monsters + 1):
        mult = encounter_multiplier(count, party_size)
        for cr in crs:
            raw = CR_XP[cr] * count
            adjusted = raw * mult
            plan = {"count": count, "cr": cr, "raw_xp": raw,
                    "multiplier": mult, "adjusted_xp": adjusted,
                    "band": classify_difficulty(adjusted, party_level, party_size)}
            in_band = floor <= adjusted <= ceiling if difficulty == "deadly" \
                else floor <= adjusted < ceiling
            if in_band:
                exact.append(plan)
            elif adjusted >= floor and (difficulty == "deadly" or adjusted < deadly):
                over.append(plan)
            else:
                under.append(plan)

    exact.sort(key=lambda p: (p["adjusted_xp"], p["count"]))
    over.sort(key=lambda p: (p["adjusted_xp"], p["count"]))
    under.sort(key=lambda p: (abs(p["adjusted_xp"] - floor), p["count"]))

    ranked = exact + over + under
    for plan in ranked[len(exact):]:
        plan["note"] = (f"Lands in {plan['band']}, not the requested {difficulty}: "
                        f"{plan['adjusted_xp']:g} adjusted XP against a {floor:g} budget"
                        + ("" if exact else "; no combination lands in {} for this party"
                           .format(difficulty)) + ".")
    return ranked


def plan_encounter(party_level, party_size, difficulty, cr_hint=None, max_monsters=8):
    """The best count/CR combination for the requested band. Pure math."""
    return rank_plans(party_level, party_size, difficulty, cr_hint, max_monsters)[0]


def select_plan(candidates, pool_for_cr):
    """First candidate whose CR has monsters, plus any warning that pick earned.

    `pool_for_cr` maps a CR to the list of monsters at it. The SRD has CRs with
    no monsters at all (CR 18 is empty), and the planner chose the CR itself, so
    an empty pool falls through to the next-best plan rather than failing.
    """
    first = candidates[0]
    for plan in candidates:
        if pool_for_cr(plan["cr"]):
            if plan["cr"] == first["cr"]:
                return plan, []
            return plan, [f"No SRD monsters at CR {first['cr']}; built at CR {plan['cr']} instead."]
    return None, [f"No SRD monsters at any CR this budget can use (tried CR {first['cr']} and below)."]


def summarize_encounter(monsters, plan, party_level, party_size, difficulty):
    """Rate the monsters actually in hand — never the ones we hoped to fetch."""
    raw_xp = sum(m.get("xp") or 0 for m in monsters)
    multiplier = encounter_multiplier(len(monsters), party_size)
    adjusted_xp = round(raw_xp * multiplier)

    counts = {}
    for m in monsters:
        counts[m["name"]] = counts.get(m["name"], 0) + 1

    summary = {
        "mode": "budget",
        "party_level": party_level,
        "party_size": party_size,
        "difficulty": difficulty,
        "budget": party_thresholds(party_level, party_size)[difficulty],
        "thresholds": party_thresholds(party_level, party_size),
        "planned_cr": plan["cr"],
        "count": len(monsters),
        "raw_xp": raw_xp,
        "multiplier": multiplier,
        "adjusted_xp": adjusted_xp,
        "resulting_difficulty": classify_difficulty(adjusted_xp, party_level, party_size),
        "monsters": monsters,
    }
    repeats = {name: n for name, n in counts.items() if n > 1}
    if repeats:
        # combat_manager suffixes these on add-enemy ("Goblin", "Goblin 2"); say
        # so here too, so the GM sees the shape of the fight at build time.
        summary["duplicates"] = repeats
    return summary


def get_monsters_by_cr(target_cr):
    """Get all monsters of a specific CR using API filtering"""
    data = fetch(f"/monsters?challenge_rating={target_cr}")

    if "error" in data:
        if data["error"] == "HTTP 429":
            error_output("Rate limited. Please wait a moment and try again.")
        elif data["error"].startswith("HTTP "):
            error_output(f"{data['error']}: {data['message']}")
        else:
            error_output(data["message"])

    if "results" in data:
        # Extract monster indices from URLs
        return [m["url"].split("/")[-1] for m in data["results"]]
    return []


def pick(available, count):
    """Choose `count` monsters, allowing duplicates only when the pool is small."""
    if count > len(available):
        return [random.choice(available) for _ in range(count)]
    return random.sample(available, count)


def combat_fields(monster_index):
    """The add-enemy-composable view of one SRD monster."""
    data = fetch(f"/monsters/{monster_index}")
    if "error" in data:
        return None
    return {
        "index": monster_index,
        "name": data.get("name"),
        "hp": data.get("hit_points"),
        "ac": (data.get("armor_class") or [{}])[0].get("value", 10),
        "cr": data.get("challenge_rating"),
        "xp": data.get("xp"),
    }


def run_budget_mode(args):
    pools = {}

    def pool_for_cr(cr):
        if cr not in pools:
            pools[cr] = get_monsters_by_cr(cr)
        return pools[cr]

    candidates = rank_plans(args.party_level, args.party_size, args.difficulty, args.cr)
    plan, warnings = select_plan(candidates, pool_for_cr)
    if plan is None:
        error_output(warnings[0])
    if plan.get("note"):
        warnings.append(plan["note"])

    selected = pick(pools[plan["cr"]], plan["count"])
    monsters = [m for m in (combat_fields(i) for i in selected) if m]

    dropped = plan["count"] - len(monsters)
    if dropped * 2 > plan["count"]:
        error_output(f"Could not fetch stats for {dropped} of {plan['count']} CR {plan['cr']} monsters")
    if dropped:
        warnings.append(f"{dropped} of {plan['count']} stat blocks failed to fetch; "
                        f"rated on the {len(monsters)} that returned.")

    # Rate what came back, and say plainly when that is short of the plan.
    summary = summarize_encounter(monsters, plan, args.party_level, args.party_size, args.difficulty)
    if warnings:
        summary["warnings"] = warnings
    output(summary)


def run_cr_mode(args):
    available = get_monsters_by_cr(args.cr)

    if not available:
        error_output(f"No monsters found for CR {args.cr}")

    selected = pick(available, args.count)

    if args.quick:
        # Just output the names
        output({
            "cr": args.cr,
            "count": args.count,
            "monsters": selected
        })
    else:
        # Fetch full details
        monsters = []
        for monster_index in selected:
            data = fetch(f"/monsters/{monster_index}")
            if "error" not in data:
                # Extract combat info
                monsters.append({
                    "name": data.get("name"),
                    "hp": data.get("hit_points"),
                    "ac": data.get("armor_class", [{}])[0].get("value", 10),
                    "cr": data.get("challenge_rating"),
                    "xp": data.get("xp")
                })

        output({
            "cr": args.cr,
            "count": args.count,
            "encounter_xp": sum(m.get("xp", 0) for m in monsters),
            "monsters": monsters
        })


def main():
    parser = argparse.ArgumentParser(description='Quick D&D encounter helper')
    parser.add_argument('--cr', type=float, help='Challenge rating (a hint in budget mode)')
    parser.add_argument('--count', type=int,
                        help='Number of monsters (flat-CR mode only, default 1; '
                             'in budget mode the plan chooses the count)')
    parser.add_argument('--quick', action='store_true', help='Just return monster names')
    parser.add_argument('--party-level', type=int, help='Party level 1-20 (enables XP-budget mode)')
    parser.add_argument('--party-size', type=int, default=4, help='Number of characters (default 4)')
    parser.add_argument('--difficulty', choices=DIFFICULTIES, default='medium',
                        help='Target difficulty in budget mode')

    args = parser.parse_args()

    if args.party_level is not None:
        if args.party_level not in XP_THRESHOLDS:
            error_output(f"--party-level must be 1-20, got {args.party_level}")
        if args.party_size < 1:
            error_output(f"--party-size must be at least 1, got {args.party_size}")
        if args.count is not None or args.quick:
            error_output("--count and --quick belong to flat-CR mode; budget mode sizes "
                         "the encounter itself. Drop them, or drop --party-level.")
        if args.cr is not None and normalize_cr(args.cr) is None:
            error_output(f"--cr {args.cr} is not a D&D challenge rating. Valid: {cr_choices()}")
        run_budget_mode(args)
    elif args.cr is not None:
        args.count = 1 if args.count is None else args.count
        run_cr_mode(args)
    else:
        error_output("Give --cr for a pick-at-CR encounter, or --party-level for XP-budget mode")

if __name__ == "__main__":
    main()
