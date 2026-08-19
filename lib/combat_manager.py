#!/usr/bin/env python3
"""
Persisted combat state.

Combat is the one subsystem that used to persist NOTHING — initiative, enemy HP,
conditions, and the round lived only in the model's working memory and drifted
across turns/compaction/resume. This manager keeps it in `combat_state.json` so
combat is resumable and truthful. Combat is OPTIONAL: a narrated skirmish that
never calls `start` still works; this is for fights worth tracking.

Harm/conditions go through the generic game_core (no 5e assumptions).
"""

import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent))

from entity_manager import EntityManager
from game_core import apply_harm, heal, add_condition, remove_condition


def _ac_value(raw: Any) -> Optional[int]:
    """SRD armour_class is a list of {type, value}; the --combat view uses `ac`."""
    if isinstance(raw, list):
        raw = raw[0] if raw else None
    if isinstance(raw, dict):
        raw = raw.get('value')
    return int(raw) if isinstance(raw, (int, float)) else None


def _pick(block: Dict[str, Any], *keys: str) -> Any:
    """First key holding a non-null value.

    Homebrew-adapted blocks carry explicit nulls (`"hit_points": null`) where the
    SRD would omit the key, so a plain `.get(a, .get(b))` would take the null and
    drop the sibling that actually has the number.
    """
    for k in keys:
        v = block.get(k)
        if v is not None:
            return v
    return None


def _pick_populated(block: Dict[str, Any], *keys: str) -> Any:
    """Like `_pick`, but an empty/zero primary also yields to a populated sibling.

    An adapted block that zeroes `hit_points` or empties `actions` while carrying
    the real value under the sibling key would otherwise arrive dead on arrival
    (0 HP) or unarmed. Only for fields where empty is never meaningful — `xp` 0
    and `cr` 0 ARE meaningful, so those keep plain `_pick`.
    """
    for k in keys:
        if block.get(k):
            return block[k]
    return _pick(block, *keys)


def _coerce_xp(raw: Any) -> Optional[int]:
    """XP is summed at `end()`; anything unsummable is rejected on the way in.

    A homebrew `"xp": "1,100"` used to persist fine and then crash the end-of-fight
    summary, losing it after the fight was already over. `json.loads` also accepts
    bare `Infinity`/`NaN`, which `int()` refuses with OverflowError/ValueError.
    """
    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float):
        if not math.isfinite(raw):
            raise ValueError(f"stat block xp must be a finite number ({raw!r})")
        return int(raw)
    if isinstance(raw, str):
        try:
            return int(raw.replace(',', '').strip())
        except ValueError:
            pass
    raise ValueError(f"stat block xp must be a number ({raw!r})")


def _from_stat_block(block: Dict[str, Any]) -> Dict[str, Any]:
    """Map a fetched SRD monster block onto enemy-record fields.

    Accepts both shapes `features/dnd-api/monsters/dnd_monster.py` prints: the
    full block (`armor_class`, `hit_points`, `challenge_rating`, `actions`) and
    the `--combat` view (`ac`, `hp`, `cr`, `attacks`).
    """
    if not isinstance(block, dict):
        raise ValueError("stat block must be a JSON object")
    out = {
        'name': block.get('name'),
        'hp': _pick_populated(block, 'hit_points', 'hp'),
        # Per candidate, not per key: `armor_class` can be present yet unreadable
        # (`[]`, `"17 (natural armor)"`), and the `ac` sibling must still be tried.
        'ac': next((v for v in (_ac_value(block.get('armor_class')),
                                _ac_value(block.get('ac'))) if v is not None), None),
        'xp': _coerce_xp(block.get('xp')),
        'cr': _pick(block, 'challenge_rating', 'cr'),
        'attacks': _pick_populated(block, 'actions', 'attacks'),
        'source': 'srd',
    }
    return {k: v for k, v in out.items() if v is not None}


class CombatManager(EntityManager):
    def __init__(self, world_state_dir: str = None):
        super().__init__(world_state_dir)
        self.combat_file = "combat_state.json"

    def _load(self) -> Dict[str, Any]:
        return self.json_ops.load_json(self.combat_file) or {}

    def _save(self, data: Dict[str, Any]) -> bool:
        return self.json_ops.save_json(self.combat_file, data)

    def is_active(self) -> bool:
        return bool(self._load().get('combatants'))

    def start(self) -> Dict[str, Any]:
        data = {'active': True, 'round': 1, 'turn_index': 0, 'combatants': []}
        self._save(data)
        return data

    def add_combatant(self, name: str = None, hp: int = None, ac: int = None,
                      initiative: int = 0, side: str = 'enemy',
                      stat_block: Dict[str, Any] = None) -> Dict[str, Any]:
        """Add a combatant, either from manual numbers or a fetched SRD stat block.

        A `stat_block` (the JSON `dnd_monster.py` prints, full or `--combat`) is
        authoritative: its AC/HP/XP/CR/actions land on the record as fetched so
        nobody retypes them. Explicit args still win where passed (a scaled
        elite, a named boss).
        """
        fetched = _from_stat_block(stat_block) if stat_block else {}
        name = name or fetched.get('name')
        hp = hp if hp is not None else fetched.get('hp')
        if not name or hp is None:
            raise ValueError("combatant needs a name and HP (pass them, or a stat block carrying them)")
        data = self._load()
        if not data.get('active'):
            data = self.start()
        name = self._unique_name(data, name)
        combatant = {
            'name': name, 'hp_current': int(hp), 'hp_max': int(hp),
            'ac': int(ac if ac is not None else fetched.get('ac', 10)),
            'conditions': [], 'initiative': int(initiative), 'side': side,
        }
        if fetched:
            combatant.update({k: fetched[k] for k in ('xp', 'cr', 'attacks', 'source')
                              if fetched.get(k) is not None})
        data.setdefault('combatants', []).append(combatant)
        data['combatants'].sort(key=lambda c: c.get('initiative', 0), reverse=True)
        self._save(data)
        return combatant

    def _unique_name(self, data, name: str) -> str:
        """Four goblins are four combatants: "Goblin", "Goblin 2", "Goblin 3"...

        `_find` matches by name, so a duplicate would shadow its twins and leave
        them undamageable. Suffix on the way in instead.
        """
        if self._find(data, name) is None:
            return name
        n = 2
        while self._find(data, f"{name} {n}") is not None:
            n += 1
        return f"{name} {n}"

    def _find(self, data, name):
        for c in data.get('combatants', []):
            if c['name'].lower() == name.lower():
                return c
        return None

    def modify_hp(self, name: str, delta: int) -> Optional[Dict[str, Any]]:
        data = self._load()
        c = self._find(data, name)
        if c is None:
            return None
        if delta < 0:
            c['hp_current'] = apply_harm(c['hp_current'], -delta)
        else:
            c['hp_current'] = heal(c['hp_current'], c['hp_max'], delta)
        self._save(data)
        return c

    def set_condition(self, name: str, action: str, condition: str) -> Optional[Dict[str, Any]]:
        data = self._load()
        c = self._find(data, name)
        if c is None:
            return None
        c['conditions'] = (add_condition(c['conditions'], condition) if action == 'add'
                           else remove_condition(c['conditions'], condition))
        self._save(data)
        return c

    def next_turn(self) -> Dict[str, Any]:
        data = self._load()
        n = len(data.get('combatants', []))
        if n == 0:
            return data
        data['turn_index'] = (data.get('turn_index', 0) + 1) % n
        if data['turn_index'] == 0:
            data['round'] = data.get('round', 1) + 1
        self._save(data)
        return data

    def end(self) -> Dict[str, Any]:
        data = self._load()
        defeated = [c for c in data.get('combatants', []) if c.get('hp_current', 1) <= 0]
        # Kill XP comes from the fetched block when the enemy carried one, so the
        # award matches the SRD rather than a retyped CR-table lookup. Saves written
        # before xp was validated may hold junk; those are reported by name rather
        # than crashing the summary of a fight that is already over — silently
        # dropping them would short-change the player, and `_save({})` below
        # destroys the evidence.
        awarded, unreadable = {}, []
        for c in defeated:
            try:
                xp = _coerce_xp(c.get('xp'))
            except (ValueError, OverflowError, TypeError):
                unreadable.append(c['name'])
                continue
            if xp is not None:
                awarded[c['name']] = xp
        summary = {
            'rounds': data.get('round', 1),
            'combatants': [c['name'] for c in data.get('combatants', [])],
            'defeated': [c['name'] for c in defeated],
            # Kill XP comes from the fetched block when the enemy carried one, so
            # the award matches the SRD rather than a retyped CR-table lookup.
            'xp_awarded': sum(awarded.values()),
            'xp_by_enemy': awarded,
        }
        if unreadable:
            summary['xp_unreadable'] = unreadable
        self._save({})  # clear — combat is over
        return summary

    def header(self) -> str:
        data = self._load()
        if not data.get('combatants'):
            return "(no active combat)"
        lines = [f"⚔ COMBAT — Round {data.get('round', 1)}"]
        for i, c in enumerate(data['combatants']):
            marker = '>' if i == data.get('turn_index', 0) else ' '
            dead = ' 💀' if c.get('hp_current', 1) <= 0 else ''
            cond = f" [{', '.join(c['conditions'])}]" if c.get('conditions') else ""
            lines.append(f"{marker} {c['name']}: {c['hp_current']}/{c['hp_max']} HP, AC {c['ac']}{cond}{dead}")
        return "\n".join(lines)


def main():
    import argparse
    import json
    from cli_output import wants_json, strip_json_flag, emit, emit_error

    parser = argparse.ArgumentParser(description="Persisted combat state")
    sub = parser.add_subparsers(dest='action')
    sub.add_parser('start')
    p = sub.add_parser('add-enemy'); p.add_argument('name', nargs='?'); p.add_argument('hp', nargs='?', type=int)
    p.add_argument('--ac', type=int); p.add_argument('--init', type=int, default=0)
    p.add_argument('--stat-block', help="fetched SRD monster JSON (dnd_monster.py output)")
    p.add_argument('--stat-block-file', help="path to a file holding that JSON ('-' for stdin)")
    p = sub.add_parser('hp'); p.add_argument('name'); p.add_argument('delta', type=int)
    p = sub.add_parser('condition'); p.add_argument('name'); p.add_argument('op', choices=['add', 'remove']); p.add_argument('condition')
    sub.add_parser('next-turn')
    sub.add_parser('header')
    sub.add_parser('status')
    sub.add_parser('end')

    json_mode = wants_json()
    args = parser.parse_args(strip_json_flag(sys.argv[1:]))
    if not args.action:
        parser.print_help(); sys.exit(1)

    m = CombatManager()
    out = None
    if args.action == 'start':
        out = m.start()
    elif args.action == 'add-enemy':
        try:
            block = None
            raw = None
            if args.stat_block_file:
                raw = (sys.stdin.read() if args.stat_block_file == '-'
                       else Path(args.stat_block_file).read_text())
            elif args.stat_block:
                raw = args.stat_block
            if raw is not None:
                try:
                    block = json.loads(raw)
                except json.JSONDecodeError as e:
                    raise ValueError(f"stat block is not valid JSON ({e})")
            out = m.add_combatant(args.name, args.hp, ac=args.ac,
                                  initiative=args.init, stat_block=block)
        except (ValueError, OverflowError, TypeError, OSError) as e:
            if json_mode:
                sys.exit(emit_error(str(e), json_mode=True))
            print(f"[ERROR] {e}", file=sys.stderr); sys.exit(1)
    elif args.action == 'hp':
        out = m.modify_hp(args.name, args.delta)
    elif args.action == 'condition':
        out = m.set_condition(args.name, args.op, args.condition)
    elif args.action == 'next-turn':
        out = m.next_turn()
    elif args.action == 'end':
        out = m.end()
    elif args.action in ('header', 'status'):
        print(m.header()); return

    if out is None:
        if json_mode:
            sys.exit(emit_error("combatant not found", json_mode=True))
        print("[ERROR] combatant not found", file=sys.stderr); sys.exit(1)
    if json_mode:
        emit(out, json_mode=True)
    else:
        print(json.dumps(out, indent=2))
        print(m.header())


if __name__ == "__main__":
    main()
