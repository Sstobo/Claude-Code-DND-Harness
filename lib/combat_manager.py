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

import re

from entity_manager import EntityManager
from dice import DiceRoller
from game_core import classify_harm, heal, add_condition, remove_condition


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
        'dex': _pick(block, 'dexterity') or (block.get('abilities') or {}).get('DEX'),
        'source': 'srd',
    }
    return {k: v for k, v in out.items() if v is not None}


_DICE = DiceRoller()

_DAMAGE_NOTATION = re.compile(r'^(\d*)d(\d+)(.*)$', re.I)


def _mod(score: Any) -> int:
    """5e ability modifier. Anything unreadable contributes nothing."""
    try:
        return (int(score) - 10) // 2
    except (TypeError, ValueError):
        return 0


def _crit_dice(notation: str) -> str:
    """Double the DICE of a damage roll, never the flat modifier (5e crit rule)."""
    m = _DAMAGE_NOTATION.match(notation.strip())
    if not m:
        return notation
    count = int(m.group(1) or 1)
    return f"{count * 2}d{m.group(2)}{m.group(3)}"


def _damage_from_action(action: Dict[str, Any]) -> List[Dict[str, str]]:
    """[{dice, type}] for every damage entry on a fetched SRD action."""
    out = []
    for d in action.get('damage') or []:
        dice = d.get('damage_dice')
        if not dice:
            continue
        dtype = (d.get('damage_type') or {})
        out.append({'dice': dice, 'type': (dtype.get('name') or '').lower()})
    return out


def _find_action(attacks: Any, wanted: Optional[str]) -> Optional[Dict[str, Any]]:
    """The named action from a stored block, or the first one that can attack."""
    actions = [a for a in (attacks or []) if isinstance(a, dict)]
    if wanted:
        for a in actions:
            if str(a.get('name', '')).lower() == wanted.lower():
                return a
        for a in actions:
            if wanted.lower() in str(a.get('name', '')).lower():
                return a
        return None
    return next((a for a in actions if a.get('attack_bonus') is not None), None)


def _damage_leg(r: Dict[str, Any]) -> str:
    """One damage roll shown as dice, faces, and type: `1d6+2 [4] +2 slashing`."""
    faces = "+".join(str(x) for x in r.get("rolls", []))
    mod = f" {r['modifier']:+d}" if r.get("modifier") else ""
    dtype = f" {r['type']}" if r.get("type") else ""
    return f"{r['dice']} [{faces}]{mod}{dtype}"


def _warn_sheet(err: Exception) -> None:
    """stderr only — stdout carries --json."""
    print(f"[WARNING] PC hit points not mirrored to character.json: {err}", file=sys.stderr)


def _hp_bar(current: int, maximum: int, width: int = 12) -> str:
    if maximum <= 0:
        return ""
    filled = max(0, min(width, round(width * current / maximum)))
    ratio = current / maximum
    mark = "✓" if ratio > 0.6 else "⚠" if ratio > 0.25 else "⚠⚠"
    return f"{'█' * filled}{'░' * (width - filled)} {current}/{maximum} {mark}"


class CombatManager(EntityManager):
    def __init__(self, world_state_dir: str = None):
        super().__init__(world_state_dir)
        self._base = world_state_dir  # so the PC write-through lands in the same world
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
                      initiative: int = None, side: str = 'enemy',
                      stat_block: Dict[str, Any] = None, hp_max: int = None,
                      dex: int = None) -> Dict[str, Any]:
        """Add a combatant, either from manual numbers or a fetched SRD stat block.

        A `stat_block` (the JSON `dnd_monster.py` prints, full or `--combat`) is
        authoritative: its AC/HP/XP/CR/actions land on the record as fetched so
        nobody retypes them. Explicit args still win where passed (a scaled
        elite, a named boss).

        Initiative is ROLLED (1d20 + DEX mod) when not passed — 5e's own order,
        not the arrival order. Pass `--init` only to honour a fixed value.
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
        dex = dex if dex is not None else fetched.get('dex')
        rolled = None
        if initiative is None:
            rolled = _DICE.roll(f"1d20{_mod(dex):+d}")
            initiative = rolled['total']
        combatant = {
            'name': name, 'hp_current': int(hp),
            'hp_max': int(hp_max if hp_max is not None else hp),
            'ac': int(ac if ac is not None else fetched.get('ac', 10)),
            'conditions': [], 'initiative': int(initiative), 'side': side,
        }
        if dex is not None:
            combatant['dex'] = int(dex)
        if fetched:
            combatant.update({k: fetched[k] for k in ('xp', 'cr', 'attacks', 'source')
                              if fetched.get(k) is not None})
        data.setdefault('combatants', []).append(combatant)
        data['combatants'].sort(key=lambda c: c.get('initiative', 0), reverse=True)
        self._save(data)
        out = dict(combatant)
        if rolled is not None:
            out['initiative_roll'] = rolled['rolls'][0]
        # The `--combat` view strips attack_bonus/damage, so a block fetched that
        # way stores attacks nobody can roll. Say so on the way in rather than at
        # the moment of the swing.
        if combatant.get('attacks') and _find_action(combatant['attacks'], None) is None:
            out['warning'] = (f"{name}'s stored actions carry no attack_bonus — fetch the FULL "
                              f"block (dnd_monster.py without --combat) or pass --bonus/--damage")
        return out

    def join_pc(self, initiative: int = None) -> Dict[str, Any]:
        """Put the active PC into the initiative order, read from character.json.

        Combat used to track only enemies, so the turn order the GM narrated had
        no record behind it. The PC's own HP stays on the character sheet (that is
        the source of truth for damage between fights); this record mirrors it so
        the order, AC and death saves are real.
        """
        from player_manager import PlayerManager
        char = PlayerManager(self._base)._load_character()
        if not char:
            raise ValueError("no active PC — character.json not found")
        hp = char.get('hp') or {}
        stats = char.get('stats') or {}
        return self.add_combatant(
            name=char.get('name'), hp=hp.get('current', hp.get('max')),
            hp_max=hp.get('max'), ac=char.get('ac'), side='pc',
            initiative=initiative, dex=stats.get('dex', stats.get('dexterity')))

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

    def _apply_delta(self, c: Dict[str, Any], delta: int) -> str:
        """Move a combatant's HP and return the 5e outcome: ok / dying / dead.

        0 HP is the DYING gate, not auto-death (CLAUDE.md, Stakes & Death), and
        only overkill past max HP kills outright — `game_core.classify_harm` owns
        that judgment so combat and the Death Protocol agree. Mutates `c`; the
        caller saves.
        """
        if c.get('side') == 'pc':
            self._mirror_to_sheet(c['name'], delta)
        if delta >= 0:
            c['hp_current'] = heal(c['hp_current'], c['hp_max'], delta)
            if c['hp_current'] > 0:
                for gone in ('unconscious', 'stable', 'dead'):
                    c['conditions'] = remove_condition(c.get('conditions', []), gone)
                c.pop('death_saves', None)
            return 'ok'
        result = classify_harm(c['hp_current'], c['hp_max'], -delta)
        c['hp_current'] = result['new_hp']
        outcome = result['outcome']
        # 5e's default: a monster at 0 HP is dead; only heroes get the dying gate
        # and the death saves that go with it.
        if outcome == 'dying' and c.get('side') not in ('pc', 'ally'):
            outcome = 'dead'
        if outcome == 'dead':
            c['conditions'] = add_condition(c.get('conditions', []), 'dead')
            c.pop('death_saves', None)
        elif outcome == 'dying':
            c['conditions'] = add_condition(c.get('conditions', []), 'unconscious')
            c.setdefault('death_saves', {'successes': 0, 'failures': 0})
        return outcome

    def _mirror_to_sheet(self, name: str, delta: int) -> None:
        """Push the active PC's HP change onto character.json, its real home.

        `end()` deletes combat_state.json, so damage recorded only here would be
        healed by the fight ending. Only the ACTIVE PC is mirrored — a combatant
        marked `pc` who is not the one on the sheet (a second hero at the table)
        would otherwise write their damage onto someone else's hit points.
        Best-effort: a fight run without a loadable sheet still resolves.
        """
        import contextlib
        import io
        try:
            from player_manager import PlayerManager
            pm = PlayerManager(self._base)
            char = pm._load_character()
            if char and str(char.get('name', '')).lower() == name.lower():
                with contextlib.redirect_stdout(io.StringIO()):
                    pm.modify_hp(char.get('name'), delta)
        except Exception as e:  # never let bookkeeping kill a swing mid-fight
            _warn_sheet(e)

    def modify_hp(self, name: str, delta: int) -> Optional[Dict[str, Any]]:
        data = self._load()
        c = self._find(data, name)
        if c is None:
            return None
        outcome = self._apply_delta(c, delta)
        self._save(data)
        return dict(c, outcome=outcome)

    def attack(self, attacker: str, target: str, with_action: str = None,
               bonus: int = None, damage: str = None, advantage: str = None,
               sources: List = None) -> Dict[str, Any]:
        """Resolve one attack: to-hit vs the target's STORED AC, then damage.

        This is the only place a swing is adjudicated, so the numbers cannot drift
        between the block that was fetched and the narration that follows. An
        attacker already in the order supplies its own bonus and damage dice from
        its stored SRD actions; `--bonus`/`--damage` override (a PC's weapon, a
        scaled elite, a trap) and are REQUIRED for an attacker with no block.
        Nat 20 hits and doubles the damage dice; nat 1 misses whatever the total.
        """
        data = self._load()
        tgt = self._find(data, target)
        if tgt is None:
            raise ValueError(f"'{target}' is not in this combat — add them first")
        atk = self._find(data, attacker)

        action = _find_action((atk or {}).get('attacks'), with_action)
        if with_action and action is None and bonus is None:
            raise ValueError(f"'{attacker}' has no action called '{with_action}' "
                             f"(pass --bonus/--damage to run it anyway)")
        if bonus is None:
            bonus = (action or {}).get('attack_bonus')
        if bonus is None:
            # An action found by name but carrying no bonus is usually not an attack
            # at all (Fey Charm, Web, a breath weapon) — it forces a SAVE, which the
            # defender rolls with lib/dice.py. Sending the GM to refetch the block
            # would be the wrong fix, so say which case this is.
            if action is not None:
                raise ValueError(
                    f"'{action.get('name')}' is not an attack roll — it has no attack bonus. "
                    f"If it forces a save, roll it as a check: "
                    f"uv run python lib/dice.py \"1d20+<mod>\" --dc <save DC>")
            raise ValueError(f"no attack bonus for '{attacker}' — fetch the full stat block "
                             f"or pass --bonus (never invent one)")
        dmg_parts = ([{'dice': damage, 'type': ''}] if damage
                     else _damage_from_action(action or {}))
        if not dmg_parts:
            raise ValueError(f"no damage dice for '{attacker}' — fetch the full stat block "
                             f"or pass --damage (never invent one)")

        notation = {'advantage': '2d20kh1', 'disadvantage': '2d20kl1'}.get(advantage, '1d20')
        roll = _DICE.roll(f"{notation}{int(bonus):+d}")
        crit, fumble = bool(roll.get('natural_20')), bool(roll.get('natural_1'))
        hit = crit or (not fumble and roll['total'] >= tgt['ac'])

        # An attribution that does not add up names a source for points that came
        # from somewhere else — worse than no attribution at all.
        if sources and sum(b for _, b in sources) != int(bonus):
            print(f"[WARNING] --from adds to {sum(b for _, b in sources):+d} but the attack "
                  f"carries {int(bonus):+d}", file=sys.stderr)

        out = {
            'attacker': (atk or {}).get('name', attacker),
            'target': tgt['name'], 'action': (action or {}).get('name'),
            'to_hit': roll['total'], 'target_ac': tgt['ac'], 'hit': hit,
            'critical': crit, 'fumble': fumble, 'damage': 0, 'outcome': None,
        }
        rolled = []
        if hit:
            for part in dmg_parts:
                dice = _crit_dice(part['dice']) if crit else part['dice']
                r = _DICE.roll(dice)
                rolled.append({'dice': dice, 'type': part['type'], 'total': r['total'],
                               'rolls': r['rolls'], 'modifier': r.get('modifier', 0)})
            out['damage'] = sum(r['total'] for r in rolled)
            out['damage_rolls'] = rolled
            out['outcome'] = self._apply_delta(tgt, -out['damage'])
            self._save(data)
        out['target_hp'] = tgt['hp_current']
        out['target_hp_max'] = tgt['hp_max']
        out['render'] = self._render_attack(out, roll, sources)
        return out

    @staticmethod
    def _render_attack(out: Dict[str, Any], roll: Dict[str, Any], sources: List = None) -> str:
        """The staged block — the AC first, the pause, then the swing and its cost."""
        if out['critical']:
            verdict = "**⚔ CRITICAL HIT — the dice double.**"
        elif out['fumble']:
            verdict = "**💀 NATURAL 1 — the swing goes wide, and it costs you.**"
        elif out['hit']:
            over = out['to_hit'] - out['target_ac']
            verdict = f"**✓ HIT — {'on the nose' if over == 0 else f'past the guard by {over}'}.**"
        else:
            verdict = f"**✗ MISS — short by {out['target_ac'] - out['to_hit']}.**"

        tail = None
        if out['hit']:
            legs = " + ".join(_damage_leg(r) for r in out.get("damage_rolls", []))
            tail = (f"🎲 Damage: {legs} = **{out['damage']}** ▼ "
                    f"{out['target']} {_hp_bar(out['target_hp'], out['target_hp_max'])}")
            if out['outcome'] == 'dead':
                tail += "  💀 DEAD"
            elif out['outcome'] == 'dying':
                tail += "  💀 DOWN — 0 HP, dying"
        return _DICE.format_staged(out['target_ac'], out['to_hit'],
                                   _DICE.roll_parts(roll, sources), verdict,
                                   need_label=f"To hit {out['target']}, you need to beat",
                                   tail=tail)

    def death_save(self, name: str) -> Dict[str, Any]:
        """One 5e death save: DC 10 flat, three up or three down, nat 20 stands up.

        Persisted on the record so the tally survives a compaction or a resume —
        three failures across two sessions still kills. On a third failure the
        caller runs the Death Protocol (CLAUDE.md); this only records the truth.
        """
        data = self._load()
        c = self._find(data, name)
        if c is None:
            raise ValueError(f"'{name}' is not in this combat")
        if c['hp_current'] > 0:
            raise ValueError(f"{c['name']} is not dying ({c['hp_current']} HP)")
        for done in ('dead', 'stable'):
            if done in (c.get('conditions') or []):
                raise ValueError(f"{c['name']} is {done} — no more death saves")
        saves = c.setdefault('death_saves', {'successes': 0, 'failures': 0})
        roll = _DICE.roll("1d20")
        die = roll['rolls'][0]

        if die == 20:
            c['hp_current'] = 1
            c.pop('death_saves', None)
            c['conditions'] = remove_condition(c.get('conditions', []), 'unconscious')
            status, verdict = 'revived', "**⚔ NATURAL 20 — eyes open, 1 HP, back in the fight.**"
        else:
            if die == 1:
                saves['failures'] += 2
                verdict = "**💀 NATURAL 1 — that is two failures.**"
            elif die >= 10:
                saves['successes'] += 1
                verdict = "**✓ SUCCESS — one step back from the edge.**"
            else:
                saves['failures'] += 1
                verdict = "**✗ FAILURE — one step closer.**"
            if saves['failures'] >= 3:
                status = 'dead'
                c['conditions'] = add_condition(c.get('conditions', []), 'dead')
                verdict += "\n\n**💀 THREE FAILURES — dead.**"
            elif saves['successes'] >= 3:
                status = 'stable'
                c['conditions'] = add_condition(c.get('conditions', []), 'stable')
                verdict += "\n\n**Three successes — stable, still at 0 HP.**"
            else:
                status = 'dying'
                verdict += (f"\n\nDeath saves: {saves['successes']} success / "
                            f"{saves['failures']} failure.")
        self._save(data)
        return {
            'name': c['name'], 'die': die, 'status': status,
            'death_saves': c.get('death_saves', {'successes': 0, 'failures': 0}),
            'render': _DICE.format_staged(10, roll['total'], _DICE.roll_parts(roll), verdict,
                                          need_label=f"{c['name']} is dying. The save beats"),
        }

    def set_condition(self, name: str, action: str, condition: str) -> Optional[Dict[str, Any]]:
        data = self._load()
        c = self._find(data, name)
        if c is None:
            return None
        c['conditions'] = (add_condition(c['conditions'], condition) if action == 'add'
                           else remove_condition(c['conditions'], condition))
        self._save(data)
        return c

    @staticmethod
    def _has_a_turn(c: Dict[str, Any]) -> bool:
        """A corpse gets no turn; a dying hero does — that turn IS their death save."""
        if c.get('hp_current', 1) > 0:
            return True
        conditions = c.get('conditions') or []
        if 'dead' in conditions or 'stable' in conditions:
            return False
        return c.get('side') in ('pc', 'ally')

    def next_turn(self) -> Dict[str, Any]:
        """Advance to the next combatant who still has a turn, rolling the round over.

        The pointer used to land on the fallen, so every fight asked the GM to
        notice and step over its own corpses. If nobody is left standing the
        pointer simply stops where the scan ended — the fight is over.
        """
        combatants = self._load().get('combatants', [])
        data = self._load()
        n = len(combatants)
        if n == 0:
            return data
        idx, rnd = data.get('turn_index', 0), data.get('round', 1)
        for _ in range(n):
            idx += 1
            if idx >= n:
                idx, rnd = 0, rnd + 1
            if self._has_a_turn(combatants[idx]):
                break
        data['turn_index'], data['round'] = idx, rnd
        self._save(data)
        return data

    def end(self) -> Dict[str, Any]:
        data = self._load()
        down = [c for c in data.get('combatants', []) if c.get('hp_current', 1) <= 0]
        # A hero at 0 is down, not defeated — only enemies count as kills (and
        # only enemies carry XP), so the summary must not read the party as loot.
        defeated = [c for c in down if c.get('side') not in ('pc', 'ally')]
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
            'down': [c['name'] for c in down if c.get('side') in ('pc', 'ally')],
            # Allies live in npcs.json, which this manager does not write; report
            # what they finished on so the GM can persist it before the state is
            # cleared. The PC's own HP was mirrored to the sheet as it happened.
            'ally_hp': {c['name']: c['hp_current'] for c in data.get('combatants', [])
                        if c.get('side') == 'ally'},
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
            side = {'pc': '★', 'ally': '+'}.get(c.get('side'), '·')
            dead = ' 💀' if c.get('hp_current', 1) <= 0 else ''
            cond = f" [{', '.join(c['conditions'])}]" if c.get('conditions') else ""
            saves = c.get('death_saves')
            saves = (f" (death saves {saves['successes']}✓/{saves['failures']}✗)"
                     if saves else "")
            lines.append(f"{marker} {c.get('initiative', 0):>2} {side} {c['name']}: "
                         f"{c['hp_current']}/{c['hp_max']} HP, AC {c['ac']}{cond}{dead}{saves}")
        return "\n".join(lines)


def main():
    import argparse
    import json
    from cli_output import wants_json, strip_json_flag, emit, emit_error

    parser = argparse.ArgumentParser(description="Persisted combat state")
    sub = parser.add_subparsers(dest='action')
    p = sub.add_parser('start'); p.add_argument('--pc', action='store_true',
                                                help="also roll the active PC into the order")
    p = sub.add_parser('add-enemy'); p.add_argument('name', nargs='?'); p.add_argument('hp', nargs='?', type=int)
    p.add_argument('--ac', type=int)
    p.add_argument('--init', type=int, help="fixed initiative; omitted = rolled 1d20+DEX")
    p.add_argument('--stat-block', help="fetched SRD monster JSON (dnd_monster.py output)")
    p.add_argument('--stat-block-file', help="path to a file holding that JSON ('-' for stdin)")
    p = sub.add_parser('join', help="put the PC or an ally into the initiative order")
    p.add_argument('name', nargs='?'); p.add_argument('hp', nargs='?', type=int)
    p.add_argument('--pc', action='store_true', help="the active PC, read from character.json")
    p.add_argument('--ac', type=int); p.add_argument('--init', type=int)
    p.add_argument('--dex', type=int, help="DEX score, for the initiative roll")
    p.add_argument('--side', choices=['pc', 'ally'], default='ally')
    p = sub.add_parser('attack', help="resolve one attack against a combatant's stored AC")
    p.add_argument('attacker'); p.add_argument('--at', required=True, dest='target')
    p.add_argument('--with', dest='with_action', help="action name from the stored stat block")
    p.add_argument('--bonus', type=int, help="to-hit bonus (required if no stored block)")
    p.add_argument('--damage', help="damage notation, e.g. 2d6+4 (required if no stored block)")
    p.add_argument('--adv', action='store_true'); p.add_argument('--dis', action='store_true')
    p.add_argument('--from', dest='sources', action='append', default=[], metavar='"label:N"',
                   help="attribute part of the bonus, e.g. --from 'strength:4' (repeatable)")
    p = sub.add_parser('death-save'); p.add_argument('name')
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
        if args.pc:
            try:
                out = {'combat': out, 'pc': m.join_pc()}
            except ValueError as e:
                sys.exit(emit_error(str(e), json_mode=json_mode))
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
    elif args.action == 'join':
        try:
            out = (m.join_pc(initiative=args.init) if args.pc else
                   m.add_combatant(args.name, args.hp, ac=args.ac, initiative=args.init,
                                   side=args.side, dex=args.dex))
        except ValueError as e:
            sys.exit(emit_error(str(e), json_mode=json_mode))
    elif args.action == 'attack':
        sources = []
        for raw in args.sources:
            label, _, b = raw.rpartition(':')
            if not label or not b.lstrip('+-').isdigit():
                sys.exit(emit_error(f'--from expects "label:N", got {raw!r}', json_mode=json_mode))
            sources.append((label, int(b)))
        try:
            out = m.attack(args.attacker, args.target, with_action=args.with_action,
                           bonus=args.bonus, damage=args.damage, sources=sources,
                           advantage='advantage' if args.adv else
                                     'disadvantage' if args.dis else None)
        except ValueError as e:
            sys.exit(emit_error(str(e), json_mode=json_mode))
        if not json_mode:
            print(out['render']); print(); print(m.header()); return
    elif args.action == 'death-save':
        try:
            out = m.death_save(args.name)
        except ValueError as e:
            sys.exit(emit_error(str(e), json_mode=json_mode))
        if not json_mode:
            print(out['render']); print(); print(m.header()); return
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
