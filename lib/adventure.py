#!/usr/bin/env python3
"""
Adventure module for GM tools
Holds the per-campaign adventure.json: the book's scene spine, the converted
scene bodies, and where the table currently is in it.

The spine is authored once (`init`), scene bodies arrive in batches from the
converter agents (`merge`, order-independent — spine order always wins), and
play moves the pointer (`advance` / `jump`).
"""

import json
import re
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

# Add lib directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from entity_manager import EntityManager
from entity_aliases import (normalize_entity_name, resolve_entity_name,
                            resolve_or_merge_key)
from character_schema import to_flat

# Fields every scene carries, with the empty value a stub starts at.
SCENE_FIELDS = {
    'location': '',
    'read_aloud': '',
    'gm_notes': '',
    'encounters': list,
    'npcs': list,
    'treasure': list,
    'checks': list,
    'transitions': list,
    'pages': list,
    'requires': list,
}

# What a scene assumes is already true when the party walks in, as typed clauses:
# {kind, <the kind's own field>, note}. The kind set is CLOSED because the reader
# on the other end is code — a clause it cannot type is an assumption the book
# made that nobody checks. `narrative` is the escape hatch for an assumption no
# machine can test (they have been changed by what they saw), and is by design
# permanently unsatisfied: it exists to be adapted around, not met.
REQUIRES_KINDS = {
    'party_size': 'min',        # a group of at least this many
    'npc_with_party': 'name',   # this NPC is travelling with them
    'npc_known': 'name',        # they have met this NPC before
    'item_held': 'name',        # they are carrying this
    'prior_event': 'id',        # this happened earlier (a scene key, or another module)
    'pc_level': 'min',          # the scene is pitched at this level
    'narrative': 'note',        # unmeetable by design — the quote IS the clause
}

# A `prior_event` id shaped like another module's code: a scene in a book this
# table is not playing. It can never be completed here, so it is a standing
# adaptation — rule what happened instead — and never a conversion error. The
# shapes real product lines print: "AT-04", "DDAL05-01" (season folded into the
# letters), "WBW-3a", and any of them with the book's title running on after the
# code ("AT-04 The Cogs of Lost Time"), which is how a module cites another module.
_MODULE_CODE_RE = re.compile(
    r"""^[a-z]{1,8}           # the product line: AT, DDAL, WBW
        \d{0,3}               # a season folded into it: DDAL05
        [-_ ]?\d{1,3}[a-z]?   # the adventure's own number: -04, -01, 3a
        (?:\s+\S.*)?$         # and the title the citation may carry after it
    """, re.IGNORECASE | re.VERBOSE)

_DIGIT_RUN_RE = re.compile(r'\d+')


def _key_shape(key: Any) -> str:
    """A scene key with its numbers blanked — the family it belongs to.

    'part-3' -> 'part-#', '2.17' -> '#.#'. A book keys its scenes in one or two
    shapes, and an id wearing one of them is this book's own key family: absent
    from the spine it is a converter typo ('part-5'), never another module.
    """
    return _DIGIT_RUN_RE.sub('#', str(key).strip().lower())


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class AdventureError(Exception):
    """A bad request against the adventure (unknown key, no file, invalid input)."""


def _srd_monster_index() -> Dict[str, str]:
    """Return {lowercased SRD monster name: index} from the dnd5eapi monster list."""
    api_dir = str(Path(__file__).parent.parent / "features" / "dnd-api")
    if api_dir not in sys.path:
        sys.path.append(api_dir)
    from dnd_api_core import fetch

    data = fetch("/monsters")
    if not isinstance(data, dict) or data.get('error'):
        detail = (data or {}).get('message', data) if isinstance(data, dict) else data
        raise AdventureError(f"could not read the SRD monster index: {detail}")

    index = {}
    for row in data.get('results', []):
        if isinstance(row, dict) and row.get('name') and row.get('index'):
            index[row['name'].strip().lower()] = row['index']
    if not index:
        raise AdventureError("the SRD monster index came back empty")
    return index


def _singulars(name: str) -> List[str]:
    """Candidate singular forms of a plural the book used ("Harpies" -> "Harpy")."""
    forms = [name]
    if name.endswith('ies') and len(name) > 4:
        forms.append(name[:-3] + 'y')
    if name.endswith('ves') and len(name) > 4:
        forms.append(name[:-3] + 'f')
    if name.endswith('es') and len(name) > 3:
        forms.append(name[:-2])
    if name.endswith('s') and not name.endswith('ss') and len(name) > 2:
        forms.append(name[:-1])
    return forms


def match_srd_monster(name: str, index: Dict[str, str]) -> Optional[str]:
    """The SRD index for a monster name, matched case-insensitively and through
    a simple de-pluralization. None means the book's creature is not in the SRD."""
    if not isinstance(name, str) or not name.strip():
        return None
    for form in _singulars(name.strip().lower()):
        if form in index:
            return index[form]
    return None


def _stub_scene(key: str, title: str, pages: Optional[List[int]] = None) -> Dict[str, Any]:
    scene = {'key': key, 'title': title}
    for field, empty in SCENE_FIELDS.items():
        scene[field] = empty() if callable(empty) else empty
    scene['pages'] = list(pages or [])
    return scene


def _requires_errors(key: str, requires: Any) -> List[str]:
    """Problems with one scene's `requires` list, every message naming the scene.

    Three rules, and each one exists because of what happens without it. The kind
    must be in the closed set, or the clause is a note nothing reads. The kind's
    own field must be there and usable, or the clause names an assumption without
    saying what it is ("party_size" with no number cannot be compared to a party).
    And every clause carries a `note` quoting the module text it was read from,
    because otherwise a converted assumption and an invented one look identical
    on disk — the quote is what makes a clause checkable against the book.
    """
    if not isinstance(requires, list):
        return [f"scene '{key}': 'requires' must be a list"]

    errors = []
    for n, clause in enumerate(requires, 1):
        if not isinstance(clause, dict):
            errors.append(f"scene '{key}': requires #{n} must be an object")
            continue

        kind = clause.get('kind')
        # A kind straight out of LLM JSON can be a list or a dict, and looking an
        # unhashable value up in the kind set raises out of a function whose whole
        # contract is to return the problems it found.
        if not isinstance(kind, str):
            errors.append(f"scene '{key}': requires #{n} needs a string 'kind' "
                          f"(got {kind!r})")
            continue
        if kind not in REQUIRES_KINDS:
            errors.append(
                f"scene '{key}': requires #{n} has unknown kind {kind!r} "
                f"(known kinds: {', '.join(sorted(REQUIRES_KINDS))})")
            continue

        field = REQUIRES_KINDS[kind]
        errors.extend(_clause_value_errors(f"scene '{key}': requires #{n}", kind,
                                           clause.get(field)))

        note = clause.get('note')
        if field != 'note' and (not isinstance(note, str) or not note.strip()):
            errors.append(f"scene '{key}': requires #{n} ({kind}) needs a 'note' quoting "
                          f"the module text that evidences it (got {note!r})")

    return errors


def _clause_value_errors(label: str, kind: str, value: Any) -> List[str]:
    """Problems with the value carried under a clause kind's own field."""
    field = REQUIRES_KINDS[kind]
    if field == 'min':
        # bool is an int in Python, and a party of `True` is nonsense.
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            return [f"{label} ({kind}) needs a positive integer '{field}' (got {value!r})"]
    elif not isinstance(value, str) or not value.strip():
        return [f"{label} ({kind}) needs a non-empty string '{field}' (got {value!r})"]
    return []


def _adaptation_errors(adaptation: Any) -> List[str]:
    """Problems with `meta.adaptation` — the rulings this table made about the book.

    A ruling is the answer the player gave to an assumption the book made and this
    table could not meet, so it is law for the rest of the campaign. A malformed one
    is worse than a missing one: it reads as a decision nobody can act on. The kind
    is checked against the same closed set the clauses use, because a ruling about
    `party_mood` answers no clause that will ever be reported.
    """
    if adaptation is None:
        return []
    if not isinstance(adaptation, dict):
        return ["meta.adaptation must be an object"]

    rulings = adaptation.get('rulings', [])
    if not isinstance(rulings, list):
        return ["meta.adaptation.rulings must be a list"]

    errors = []
    for n, ruling in enumerate(rulings, 1):
        label = f"meta.adaptation: ruling #{n}"
        if not isinstance(ruling, dict):
            errors.append(f"{label} must be an object")
            continue

        kind = ruling.get('kind')
        # An unhashable kind (a list straight out of LLM JSON) must not raise out of
        # a function whose contract is to RETURN what is wrong.
        if not isinstance(kind, str):
            errors.append(f"{label} needs a string 'kind' (got {kind!r})")
            continue
        if kind not in REQUIRES_KINDS:
            errors.append(f"{label} has unknown kind {kind!r} "
                          f"(known kinds: {', '.join(sorted(REQUIRES_KINDS))})")
            continue

        text = ruling.get('ruling')
        if not isinstance(text, str) or not text.strip():
            errors.append(f"{label} ({kind}) needs a non-empty string 'ruling' (got {text!r})")

        # The scope value is optional — a ruling can answer a whole kind — but a
        # scope that is there and unusable narrows the ruling to nothing.
        value = ruling.get(REQUIRES_KINDS[kind])
        if value is not None:
            errors.extend(_clause_value_errors(label, kind, value))

    return errors


def _scope_pool(kind: str, state: Dict[str, Any]) -> Any:
    """The live records a name clause is folded against — the set `_judge` asks.

    NPC kinds fold against every NPC on file, not just the party: an NPC the
    party left behind is still ONE person, so the two spellings of them are still
    one question. Items fold against what the PC carries.
    """
    if kind in ('npc_with_party', 'npc_known'):
        return state.get('npcs')
    if kind == 'item_held':
        return state.get('equipment')
    return None


def _clause_scope(kind: str, value: Any, pool: Any = None) -> Any:
    """Identity for dedup: two scenes assuming "Puck is along" are ONE question.

    A name is folded against the campaign's own records FIRST, through the same
    `entity_aliases` resolution the runtime uses everywhere else (exact -> case ->
    the record's aliases -> normalized -> a short name against a longer key). Two
    spellings this campaign resolves to one NPC are one class, because that is
    the single identity `_judge` will answer about.

    Normalized equality is only the fallback, and it is weaker than it looks: it
    strips a fixed list of honorifics, so a title the list has never heard of
    ("Sheriff") keeps two spellings of one person apart. That is the honest
    answer for a name the campaign has no record of — two strangers, two
    questions — and the reason the live records get asked first.

    Ids and quotes fold on case only: a scene key is not a person's name.
    """
    if not isinstance(value, str):
        return value
    if REQUIRES_KINDS.get(kind) == 'name':
        if pool:
            key = resolve_or_merge_key(value, pool)
            if key:
                return normalize_entity_name(key) or key.strip().lower()
        return normalize_entity_name(value) or value.strip().lower()
    return value.strip().lower()


def _coerce_scope_value(kind: str, value: Any) -> Any:
    """The CLI hands every `--value` in as a string; `min` kinds mean a number."""
    if REQUIRES_KINDS[kind] != 'min':
        return str(value).strip()
    try:
        n = int(str(value).strip())
    except ValueError:
        raise AdventureError(f"{kind} takes a number for --value (got {value!r})")
    if n < 1:
        raise AdventureError(f"{kind} takes a positive number for --value (got {value!r})")
    return n


def validate_adventure(adv: Dict[str, Any]) -> List[str]:
    """Return a list of human-readable problems with an adventure dict (empty = valid)."""
    errors = []

    if not isinstance(adv, dict):
        return ["adventure must be a JSON object"]

    scenes = adv.get('scenes')
    if not isinstance(scenes, list):
        return ["'scenes' must be a list"]

    seen = set()
    for i, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            errors.append(f"scene #{i + 1}: must be an object")
            continue
        key = scene.get('key')
        if not key:
            errors.append(f"scene #{i + 1}: missing 'key'")
        if not scene.get('title'):
            label = key or f"#{i + 1}"
            errors.append(f"scene '{label}': missing 'title'")
        if key:
            if key in seen:
                errors.append(f"duplicate scene key '{key}'")
            seen.add(key)

    for scene in scenes:
        if not isinstance(scene, dict):
            continue
        key = scene.get('key', '?')
        # A scene converted before `requires` existed simply has none.
        errors.extend(_requires_errors(key, scene.get('requires', [])))
        transitions = scene.get('transitions', [])
        if not isinstance(transitions, list):
            errors.append(f"scene '{key}': 'transitions' must be a list")
            continue
        for n, t in enumerate(transitions, 1):
            if not isinstance(t, dict):
                errors.append(f"scene '{key}': each transition must be an object")
                continue
            # A transition with no usable to_key is a dead end that silently reads
            # as "fall through to spine order" — reject it rather than lose the link.
            to_key = t.get('to_key')
            if not isinstance(to_key, str) or not to_key.strip():
                errors.append(
                    f"scene '{key}': transition #{n} needs a non-empty string 'to_key' "
                    f"(got {to_key!r})")
            elif to_key not in seen:
                errors.append(f"scene '{key}': transition points at unknown scene '{to_key}'")

    progress = adv.get('progress', {})
    if not isinstance(progress, dict):
        errors.append("'progress' must be an object")
    else:
        current = progress.get('current_scene')
        if current and current not in seen:
            errors.append(f"progress.current_scene '{current}' is not a scene in this adventure")
        completed = progress.get('completed', [])
        if not isinstance(completed, list):
            errors.append("progress.completed must be a list")
        else:
            for key in completed:
                if key not in seen:
                    errors.append(f"progress.completed lists unknown scene '{key}'")

    meta = adv.get('meta', {})
    if not isinstance(meta, dict):
        errors.append("'meta' must be an object")
    else:
        errors.extend(_adaptation_errors(meta.get('adaptation')))

    return errors


class AdventureManager(EntityManager):
    """Manage the campaign's adventure.json. Inherits campaign resolution from EntityManager."""

    def __init__(self, world_state_dir: str = None):
        super().__init__(world_state_dir)
        self.adventure_file = "adventure.json"

    # --- storage ---------------------------------------------------------

    @property
    def adventure_path(self) -> Path:
        return Path(self.campaign_dir) / self.adventure_file

    def exists(self) -> bool:
        return self.adventure_path.exists()

    def load(self) -> Dict[str, Any]:
        """Load adventure.json. Raises AdventureError if the campaign has none."""
        if not self.exists():
            raise AdventureError(
                "No adventure.json in this campaign — run `adventure init <spine.json>` first")
        return self.json_ops.load_json(self.adventure_file) or {}

    def save(self, adv: Dict[str, Any]) -> bool:
        return self.json_ops.save_json(self.adventure_file, adv)

    # --- ops -------------------------------------------------------------

    def validate(self) -> List[str]:
        return validate_adventure(self.load())

    def init(self, spine: List[Dict[str, Any]], meta: Optional[Dict[str, Any]] = None,
             force: bool = False) -> Dict[str, Any]:
        """Create adventure.json from an ordered spine of {key, title, pages}.

        Refuses to overwrite an existing adventure — a re-init would throw away the
        table's progress (current scene + everything completed). `force` says do it
        anyway.
        """
        if self.exists() and not force:
            raise AdventureError(
                "This campaign already has an adventure.json — re-running init would "
                "wipe its progress. Pass --force to replace it.")
        if not isinstance(spine, list) or not spine:
            raise AdventureError("spine must be a non-empty list of {key, title, pages}")

        scenes = []
        for i, row in enumerate(spine):
            if not isinstance(row, dict):
                raise AdventureError(f"spine entry #{i + 1}: must be an object")
            key = row.get('key')
            if not key:
                raise AdventureError(f"spine entry #{i + 1}: missing 'key'")
            scenes.append(_stub_scene(key, row.get('title', ''), row.get('pages')))

        adv = {
            'meta': dict(meta or {}),
            'scenes': scenes,
            'progress': {'current_scene': scenes[0]['key'], 'completed': []},
        }

        errors = validate_adventure(adv)
        if errors:
            raise AdventureError("; ".join(errors))

        self.save(adv)
        return adv

    def merge(self, batch: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Upsert a batch of scenes by key. Spine order is preserved: an existing
        scene is updated in place, and only genuinely new keys append at the end."""
        if not isinstance(batch, list):
            raise AdventureError("merge input must be a list of scenes")

        adv = self.load()
        scenes = adv.setdefault('scenes', [])
        by_key = {s.get('key'): s for s in scenes if isinstance(s, dict)}

        for i, incoming in enumerate(batch):
            if not isinstance(incoming, dict):
                raise AdventureError(f"scene #{i + 1}: must be an object")
            key = incoming.get('key')
            if not key:
                raise AdventureError(f"scene #{i + 1}: missing 'key'")

            target = by_key.get(key)
            if target is None:
                target = _stub_scene(key, incoming.get('title', ''))
                scenes.append(target)
                by_key[key] = target

            for field, value in incoming.items():
                if field == 'key':
                    continue
                target[field] = value

        errors = validate_adventure(adv)
        if errors:
            raise AdventureError("; ".join(errors))

        self.save(adv)
        return adv

    def _monsters(self, adv: Dict[str, Any]):
        for scene in adv.get('scenes', []):
            if not isinstance(scene, dict):
                continue
            for encounter in scene.get('encounters', []):
                if not isinstance(encounter, dict):
                    continue
                for monster in encounter.get('monsters', []):
                    if isinstance(monster, dict):
                        yield monster

    def resolve_monsters(self) -> Dict[str, Any]:
        """Point every monster the SRD already knows at its `srd_index`.

        A monster the module statted itself is left alone even when its name
        matches the SRD — the converter copied that block because this book's
        "Goblin" is not the SRD's. No monster carries both an `srd_index` and a
        `stat_block`; the stale index from an earlier run is cleared first, so
        re-running gives the same answer.
        """
        adv = self.load()
        index = None  # fetched on first need, so a statted book stays offline

        resolved, embedded, unstatted, gaps = 0, 0, 0, []
        changed = False
        for monster in self._monsters(adv):
            name = monster.get('name')
            had = monster.pop('srd_index', None)

            if monster.get('stat_block'):
                embedded += 1
                changed = changed or had is not None
                continue

            if index is None:
                index = _srd_monster_index()
            srd_index = match_srd_monster(name, index)
            if srd_index:
                monster['srd_index'] = srd_index
                resolved += 1
                changed = changed or had != srd_index
            else:
                unstatted += 1
                changed = changed or had is not None
                if isinstance(name, str) and name.strip():
                    gaps.append(name)

        if changed:
            self.save(adv)
        return {'resolved': resolved, 'embedded': embedded, 'unstatted': unstatted,
                'unstatted_names': sorted(set(gaps))}

    def _scene_keys(self, adv: Dict[str, Any]) -> List[str]:
        return [s.get('key') for s in adv.get('scenes', []) if isinstance(s, dict) and s.get('key')]

    def _scene(self, adv: Dict[str, Any], key: str) -> Optional[Dict[str, Any]]:
        for s in adv.get('scenes', []):
            if isinstance(s, dict) and s.get('key') == key:
                return s
        return None

    def _next_key(self, adv: Dict[str, Any], key: str) -> Optional[str]:
        """The scene after `key`: its first transition if it has one, else spine order."""
        scene = self._scene(adv, key)
        if scene:
            for t in scene.get('transitions', []):
                if isinstance(t, dict) and t.get('to_key'):
                    return t['to_key']
        keys = self._scene_keys(adv)
        if key in keys:
            i = keys.index(key)
            if i + 1 < len(keys):
                return keys[i + 1]
        return None

    def status(self) -> Dict[str, Any]:
        adv = self.load()
        progress = adv.get('progress', {})
        current = progress.get('current_scene')
        scene = self._scene(adv, current) if current else None
        next_key = self._next_key(adv, current) if current else None
        next_scene = self._scene(adv, next_key) if next_key else None

        return {
            'title': adv.get('meta', {}).get('title', ''),
            'current_scene': current,
            'current_title': scene.get('title') if scene else None,
            'next_scene': next_key,
            'next_title': next_scene.get('title') if next_scene else None,
            'completed': list(progress.get('completed', [])),
            'total_scenes': len(self._scene_keys(adv)),
            'at_end': next_key is None,
        }

    def advance(self) -> Dict[str, Any]:
        """Mark the current scene completed and move the pointer to the next one."""
        adv = self.load()
        progress = adv.setdefault('progress', {'current_scene': None, 'completed': []})
        current = progress.get('current_scene')
        if not current:
            raise AdventureError("no current scene to advance from — use `jump <key>`")

        completed = progress.setdefault('completed', [])
        if current not in completed:
            completed.append(current)

        next_key = self._next_key(adv, current)
        if next_key:
            progress['current_scene'] = next_key
        self.save(adv)

        result = self.status()
        result['advanced_from'] = current
        result['at_end'] = next_key is None
        return result

    def jump(self, key: str) -> Dict[str, Any]:
        adv = self.load()
        if key not in self._scene_keys(adv):
            raise AdventureError(f"unknown scene '{key}'")
        adv.setdefault('progress', {'completed': []})['current_scene'] = key
        self.save(adv)
        return self.status()

    # --- adaptation: the book's assumptions vs this table --------------------

    def _meta(self, adv: Dict[str, Any]) -> Dict[str, Any]:
        meta = adv.get('meta', {})
        if not isinstance(meta, dict):
            raise AdventureError("'meta' is not an object — run `validate`")
        return meta

    def _live_state(self, adv: Dict[str, Any]) -> Dict[str, Any]:
        """The table as it actually is, read from the campaign's own files.

        One field per clause kind, so the whole diff is pure Python over files that
        already exist — no RAG, no model call, nothing to get creative about. A
        campaign with no PC reads as an empty table (party 0, level 0), which is
        exactly the provisional answer a report before binding should give.

        The sheet goes through `character_schema.to_flat` on the way in, the same
        normalizer `player_manager` and the session context apply on load. A
        legacy open-schema sheet keeps its name under `identity` and its level
        under `progression`; read raw, that PC does not exist and the book waits
        for a character who is already sitting at the table.
        """
        char = to_flat(self.json_ops.load_json('character.json') or {})
        if not isinstance(char, dict):
            char = {}
        npcs = self.json_ops.load_json('npcs.json') or {}
        if not isinstance(npcs, dict):
            npcs = {}

        name = char.get('name')
        pc = name.strip() if isinstance(name, str) and name.strip() else None
        level = char.get('level', 1)
        if not isinstance(level, int) or isinstance(level, bool) or level < 1:
            level = 1

        party = {n: d for n, d in npcs.items()
                 if isinstance(d, dict) and d.get('is_party_member')}
        # "Known" is having a shared past on the record, which is what an NPC's
        # events list IS — the beats gm-npc.sh persisted between them and the PC.
        known = {n: d for n, d in npcs.items()
                 if isinstance(d, dict) and isinstance(d.get('events'), list) and d['events']}
        equipment = char.get('equipment') or []
        if not isinstance(equipment, list):
            equipment = []

        progress = adv.get('progress', {})
        completed = progress.get('completed', []) if isinstance(progress, dict) else []
        scene_keys = self._scene_keys(adv)

        return {
            'pc': pc,
            'pc_level': level if pc else 0,
            'party': party,
            'party_names': sorted(party),
            'party_size': (1 if pc else 0) + len(party),
            'known': known,
            'npcs': npcs,
            'equipment': [i for i in equipment if isinstance(i, str)],
            'completed': [str(k) for k in completed if isinstance(k, (str, int))],
            'scene_keys': scene_keys,
            'key_shapes': {_key_shape(k) for k in scene_keys},
        }

    def _judge_prior_event(self, value: str, state: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
        """Whether an earlier beat happened — and, when it did not, WHY not.

        Three unmet cases that look identical on disk and are nothing alike at the
        table: a scene of this book they have not reached yet (it can still come
        true), another module's scene (it never can — that is a standing
        adaptation), and an id matching nothing at all (a mis-converted key). The
        third is reported with its flag rather than crashing or quietly passing,
        because a typo'd scene key is a conversion bug the GM should see.

        The book's own key shapes are asked before any module-code pattern, and
        they have to be: 'part-5' in a book keyed part-1..part-4 reads exactly
        like a product code, and calling it another module's scene turns a typo
        into a standing adaptation nobody will ever revisit.
        """
        wanted = value.strip().lower()
        if wanted in {k.lower() for k in state['completed']}:
            return True, "already played", None
        if wanted in {k.lower() for k in state['scene_keys']}:
            return False, "a scene in this book the table has not reached yet", 'not_yet_played'
        shape = _key_shape(value)
        if shape in state.get('key_shapes', set()):
            return (False, f"keyed like this book's own scenes ({shape}) but names none of "
                           f"them — a mis-converted key", 'unresolved')
        if _MODULE_CODE_RE.match(value.strip()):
            return False, "another module's scene — this table can never play it here", 'other_module'
        return False, "matches no scene in this book and no module code", 'unresolved'

    def _judge(self, kind: str, value: Any,
               state: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
        """Is this one assumption true at this table? -> (met, detail, flag)."""
        if kind == 'party_size':
            return state['party_size'] >= value, f"the party numbers {state['party_size']}", None
        if kind == 'pc_level':
            if not state['pc']:
                return False, "there is no PC yet", None
            return state['pc_level'] >= value, f"the PC is level {state['pc_level']}", None
        if kind == 'npc_with_party':
            key = resolve_entity_name(value, state['party'])
            return bool(key), (f"{key} is travelling with them" if key
                               else "not travelling with the party"), None
        if kind == 'npc_known':
            key = resolve_entity_name(value, state['known'])
            return bool(key), (f"met before ({len(state['known'][key]['events'])} beat(s) on record)"
                               if key else "the table has never met them"), None
        if kind == 'item_held':
            key = resolve_entity_name(value, state['equipment'])
            return bool(key), (f"carried as '{key}'" if key else "not in the PC's kit"), None
        if kind == 'prior_event':
            return self._judge_prior_event(value, state)
        # narrative — the quote IS the clause, and no file can answer it.
        return False, "nothing on disk can answer this", 'unmeetable'

    def _requires_groups(self, adv: Dict[str, Any],
                         state: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        """Union every scene's `requires` into one class per kind+value.

        Deduped, because the GM turns each class into ONE question for the player:
        three scenes that each assume Puck is along is one thing to decide, not
        three. The strongest quote wins the group — the longest note, since that is
        the one carrying the most of the book's own wording into the question.
        Clauses the reader cannot type are counted, not skipped in silence; naming
        them is `validate`'s job, and the count is the pointer to it.
        """
        groups: Dict[Any, Dict[str, Any]] = {}
        order: List[Any] = []
        stats = {'clauses': 0, 'malformed': 0}

        for scene in adv.get('scenes', []):
            if not isinstance(scene, dict):
                continue
            key = scene.get('key', '?')
            # A scene converted before `requires` existed simply has none.
            requires = scene.get('requires', [])
            if not isinstance(requires, list):
                stats['malformed'] += 1
                continue

            for clause in requires:
                if not isinstance(clause, dict):
                    stats['malformed'] += 1
                    continue
                kind = clause.get('kind')
                if not isinstance(kind, str) or kind not in REQUIRES_KINDS:
                    stats['malformed'] += 1
                    continue
                field = REQUIRES_KINDS[kind]
                value = clause.get(field)
                if _clause_value_errors('', kind, value):
                    stats['malformed'] += 1
                    continue
                if isinstance(value, str):
                    value = value.strip()
                stats['clauses'] += 1

                note = clause.get('note')
                note = note.strip() if isinstance(note, str) else ''
                scope = (kind, _clause_scope(kind, value, _scope_pool(kind, state)))
                group = groups.get(scope)
                if group is None:
                    group = {'kind': kind, 'field': field, 'value': value,
                             'scenes': [], 'quote': note}
                    groups[scope] = group
                    order.append(scope)
                elif len(note) > len(group['quote']):
                    group['quote'] = note
                if key not in group['scenes']:
                    group['scenes'].append(key)

        return [groups[s] for s in order], stats

    def requires_report(self) -> Dict[str, Any]:
        """Diff every scene's assumptions against this table, binding once a PC exists.

        At import the union is provisional: the book assumes four 5th-level heroes
        and there is nobody at the table yet, so every clause reads unmet and the
        answer means nothing. It becomes real the moment a PC exists — and that is
        the moment it is stamped, `meta.adaptation.matched_to_pc`, the same
        one-time gate `opening_seed` uses for the opening beat. After the stamp this
        reports and never re-decides: the rulings the GM made WITH the player are
        the campaign's law, and a book that re-matched itself to every later PC
        would overwrite them behind the table's back.
        """
        adv = self.load()
        meta = self._meta(adv)
        adaptation = meta.get('adaptation') or {}
        if not isinstance(adaptation, dict):
            raise AdventureError("'meta.adaptation' is not an object — run `validate`")

        state = self._live_state(adv)
        raw, stats = self._requires_groups(adv, state)
        groups = []
        for group in raw:
            met, detail, flag = self._judge(group['kind'], group['value'], state)
            groups.append({**group, 'met': met, 'detail': detail, 'flag': flag})

        if not state['pc']:
            binding = 'awaiting-pc'
        elif adaptation.get('matched_to_pc'):
            binding = 'already-bound'
        else:
            adaptation = dict(adaptation)
            adaptation['matched_to_pc'] = True
            adaptation['pc'] = state['pc']
            adaptation['decided_at'] = _now()
            # Rulings made before a PC existed are answers too — the stamp joins
            # them, it does not replace them.
            adaptation.setdefault('rulings', [])
            meta['adaptation'] = adaptation
            adv['meta'] = meta
            # The stamp goes down whatever shape the rulings are in. A ruling
            # nobody can act on is exactly the thing the GM is running this report
            # to find, and this report is the only place they would ever see it —
            # raising here would hide it behind a crash and block the binding too.
            self.save(adv)
            binding = 'bound'

        rulings = list(adaptation.get('rulings') or [])
        return {
            'title': meta.get('title', ''),
            'binding': binding,
            'pc': state['pc'],
            'bound_to': adaptation.get('pc'),
            'decided_at': adaptation.get('decided_at'),
            'table': {'party_size': state['party_size'],
                      'party_members': state['party_names'],
                      'pc_level': state['pc_level'],
                      'completed': len(state['completed'])},
            'scenes': len(state['scene_keys']),
            'clauses': stats['clauses'],
            'malformed_clauses': stats['malformed'],
            # One list of classes, each carrying its own `met`. `unmet` used to be
            # a second list of the SAME dicts, which doubled every class in --json.
            'groups': groups,
            'unmet_count': sum(1 for g in groups if not g['met']),
            'rulings': rulings,
            'ruling_problems': _adaptation_errors(adaptation),
        }

    def adapt(self, kind: str, ruling: str, value: Any = None) -> Dict[str, Any]:
        """Record what this table does about one of the book's assumptions.

        Scoped to a kind, optionally narrowed to the single value it answers
        (`--value Puck`). Re-ruling the same scope REPLACES the earlier answer:
        two contradictory rulings on one assumption is a table that cannot be read
        back. Available before binding and after it — the stamp is about matching
        the book once, not about closing the door on later rulings.

        Only the ruling being written is judged. A malformed ruling already on
        disk is reported back (and named by `requires-report`), never a reason to
        refuse the answer the player just gave; `unadapt` is how it goes away.
        """
        if not isinstance(kind, str) or kind not in REQUIRES_KINDS:
            raise AdventureError(f"unknown adaptation kind {kind!r} — valid kinds: "
                                 f"{', '.join(sorted(REQUIRES_KINDS))}")
        if not isinstance(ruling, str) or not ruling.strip():
            raise AdventureError("a ruling needs text — what does this table do instead?")

        field = REQUIRES_KINDS[kind]
        entry: Dict[str, Any] = {'kind': kind}
        if value is not None and str(value).strip():
            entry[field] = _coerce_scope_value(kind, value)
        entry['ruling'] = ruling.strip()

        adv = self.load()
        meta = self._meta(adv)
        adaptation = meta.get('adaptation') or {}
        if not isinstance(adaptation, dict):
            raise AdventureError("'meta.adaptation' is not an object — run `validate`")
        rulings = adaptation.get('rulings')
        if rulings is None:
            rulings = []
        if not isinstance(rulings, list):
            raise AdventureError("'meta.adaptation.rulings' is not a list — run `validate`")

        pool = _scope_pool(kind, self._live_state(adv))
        scope = _clause_scope(kind, entry.get(field), pool) if field in entry else None
        replaced = False
        for i, existing in enumerate(rulings):
            if not isinstance(existing, dict) or existing.get('kind') != kind:
                continue
            existing_value = existing.get(field)
            existing_scope = (_clause_scope(kind, existing_value, pool)
                              if existing_value is not None else None)
            if existing_scope == scope:
                rulings[i] = entry
                replaced = True
                break
        if not replaced:
            rulings.append(entry)

        adaptation['rulings'] = rulings
        meta['adaptation'] = adaptation
        adv['meta'] = meta
        # Judge the ruling being written, never the ones already there.
        errors = _adaptation_errors({'rulings': [entry]})
        if errors:
            raise AdventureError("; ".join(errors))
        self.save(adv)
        return {'ruling': entry, 'replaced': replaced, 'rulings': len(rulings),
                'bound': bool(adaptation.get('matched_to_pc')),
                'unreadable': _adaptation_errors(adaptation)}

    def unadapt(self, kind: str, value: Any = None) -> Dict[str, Any]:
        """Drop the standing ruling at one scope — the way back.

        Deliberately NOT kind-checked, unlike `adapt`: the ruling most likely to
        need removing is one carrying a kind `adapt` refuses to write, and without
        this the only cure for that is hand-editing adventure.json. Scope matching
        is `adapt`'s: `--value Puck` drops the Puck ruling, no value drops the
        whole-kind one.
        """
        if not isinstance(kind, str) or not kind.strip():
            raise AdventureError("which kind of ruling should go? (--kind)")

        adv = self.load()
        meta = self._meta(adv)
        adaptation = meta.get('adaptation') or {}
        if not isinstance(adaptation, dict):
            raise AdventureError("'meta.adaptation' is not an object — run `validate`")
        rulings = adaptation.get('rulings') or []
        if not isinstance(rulings, list):
            raise AdventureError("'meta.adaptation.rulings' is not a list — run `validate`")

        field = REQUIRES_KINDS.get(kind)
        pool = _scope_pool(kind, self._live_state(adv))
        scope = None
        if value is not None and str(value).strip():
            scope = _clause_scope(
                kind, _coerce_scope_value(kind, value) if field else str(value).strip(), pool)

        kept, dropped = [], []
        for existing in rulings:
            matches = isinstance(existing, dict) and existing.get('kind') == kind
            if matches:
                existing_value = existing.get(field) if field else None
                existing_scope = (_clause_scope(kind, existing_value, pool)
                                  if existing_value is not None else None)
                matches = existing_scope == scope
            (dropped if matches else kept).append(existing)

        if not dropped:
            raise AdventureError(
                f"no standing {kind} ruling"
                + (f" scoped to {str(value).strip()!r}" if scope is not None else "")
                + " to remove")

        adaptation['rulings'] = kept
        meta['adaptation'] = adaptation
        adv['meta'] = meta
        self.save(adv)
        return {'removed': dropped, 'rulings': len(kept),
                'bound': bool(adaptation.get('matched_to_pc')),
                'unreadable': _adaptation_errors(adaptation)}


def format_status(status: Dict[str, Any]) -> str:
    lines = []
    if status.get('title'):
        lines.append(f"=== {status['title']} ===")
    current = status.get('current_scene')
    if current:
        lines.append(f"Current: {current} — {status.get('current_title') or ''}".rstrip(" —"))
    else:
        lines.append("Current: (nowhere — no scene selected)")
    if status.get('next_scene'):
        lines.append(f"Next:    {status['next_scene']} — {status.get('next_title') or ''}".rstrip(" —"))
    else:
        lines.append("Next:    (end of the adventure)")
    lines.append(f"Progress: {len(status.get('completed', []))}/{status.get('total_scenes', 0)} scenes completed")
    return "\n".join(lines)


def _group_line(group: Dict[str, Any]) -> str:
    if group['kind'] == 'narrative':
        label = "a state of mind the book assumes"
    elif group['field'] == 'min':
        label = f"at least {group['value']}"
    else:
        label = str(group['value'])
    line = f"  {'✓' if group['met'] else '✗'} {group['kind']} — {label} · {group['detail']}"
    if group.get('flag'):
        line += f" [{group['flag']}]"
    return line


def _ruling_line(ruling: Any) -> str:
    """One standing ruling, marked when it is one nothing can act on."""
    if not isinstance(ruling, dict):
        return f"  ✗ [UNREADABLE] {ruling!r}"
    kind = ruling.get('kind')
    field = REQUIRES_KINDS.get(kind) if isinstance(kind, str) else None
    scope = ruling.get(field) if field else None
    head = f"{kind}" + (f" ({scope})" if scope is not None else "")
    broken = _adaptation_errors({'rulings': [ruling]})
    mark = "✗" if broken else "•"
    return f"  {mark} {head}: {ruling.get('ruling')}" + ("   [UNREADABLE]" if broken else "")


def format_requires_report(report: Dict[str, Any]) -> str:
    """The report the GM reads before asking the player anything."""
    title = report.get('title')
    lines = ["=== ADAPTATION" + (f" — {title}" if title else "") + " ==="]

    binding = report.get('binding')
    if binding == 'bound':
        lines.append(f"BOUND to {report['pc']} ({report['decided_at']}) — the one time this "
                     f"book gets matched to this table.")
    elif binding == 'already-bound':
        lines.append(f"Bound to {report.get('bound_to')} ({report.get('decided_at')}) — standing "
                     f"report, nothing re-decided.")
    else:
        lines.append("PROVISIONAL — no PC yet, so this diff runs against an empty table. "
                     "Binding waits for a character.")

    table = report.get('table', {})
    members = table.get('party_members') or []
    lines.append(f"This table: party of {table.get('party_size', 0)}"
                 + (f" ({', '.join(members)} alongside)" if members else "")
                 + f" · PC level {table.get('pc_level', 0)}"
                 + f" · {table.get('completed', 0)} scene(s) played")

    groups = report.get('groups', [])
    unmet = [g for g in groups if not g.get('met')]
    lines.append(f"{report.get('scenes', 0)} scenes · {report.get('clauses', 0)} assumption "
                 f"clause(s) · {len(groups)} class(es) · {len(unmet)} unmet")
    if report.get('malformed_clauses'):
        lines.append(f"[WARNING] {report['malformed_clauses']} clause(s) are unreadable and were "
                     f"skipped — run `validate` to see them")

    if not groups:
        lines.append("")
        lines.append("No scene in this book declares what it assumes, so there is nothing to "
                     "adapt. (A book converted before `requires` existed carries none.)")

    if unmet:
        lines.append("")
        lines.append("UNMET — what the book assumes and this table does not have:")
        for group in unmet:
            lines.append(_group_line(group))
            lines.append(f"      scenes: {', '.join(group['scenes'])}")
            if group.get('quote'):
                lines.append(f"      {group['quote']}")

    met = [g for g in groups if g['met']]
    if met:
        lines.append("")
        lines.append("MET — no ruling needed:")
        lines.extend(_group_line(g) for g in met)

    rulings = report.get('rulings') or []
    if rulings:
        lines.append("")
        lines.append("Standing rulings:")
        lines.extend(_ruling_line(r) for r in rulings)

    problems = report.get('ruling_problems') or []
    if problems:
        lines.append("")
        lines.append(f"[WARNING] {len(problems)} standing ruling(s) nothing can act on. They are "
                     f"left exactly as they are — `adapt` still records new ones:")
        lines.extend(f"  • {p}" for p in problems)
        lines.append("  Re-rule the same scope to overwrite one, or drop it: "
                     "bash tools/gm-adventure.sh adapt --kind <kind> [--value <v>] --remove")

    if unmet:
        # The hint gets copy-pasted verbatim, so a class that is ABOUT one value —
        # this NPC, this item, that other module's scene — has to carry its
        # --value. Without it the paste rules on the whole kind, and one answer
        # about Puck becomes the answer about everyone. Only the `min` kinds
        # (party of N, level N) are whole-kind rulings by nature.
        first = unmet[0]
        hint = f"  bash tools/gm-adventure.sh adapt --kind {first['kind']}"
        if first.get('field') in ('name', 'id'):
            hint += f" --value \"{first['value']}\""
        lines.append("")
        lines.append("Next: turn each unmet class into ONE numbered question for the player, "
                     "then persist their answer:")
        lines.append(hint + " --ruling \"<what this table does instead>\"")
    return "\n".join(lines)


def _read_json_arg(path: str) -> List[Dict[str, Any]]:
    """Read a spine/scenes file: either a bare list or {"scenes": [...]}."""
    try:
        data = json.loads(Path(path).read_text(encoding='utf-8'))
    except FileNotFoundError:
        raise AdventureError(f"file not found: {path}")
    except json.JSONDecodeError as e:
        raise AdventureError(f"invalid JSON in {path}: {e}")
    if isinstance(data, dict):
        return data.get('scenes', data.get('spine', []))
    return data


def main():
    """CLI interface for the adventure store"""
    import argparse
    from cli_output import wants_json, strip_json_flag, emit, emit_error

    parser = argparse.ArgumentParser(description='Adventure store')
    sub = parser.add_subparsers(dest='action', help='Action to perform')

    sub.add_parser('validate', help='Check adventure.json for schema problems')

    init_parser = sub.add_parser('init', help='Create adventure.json from a spine file')
    init_parser.add_argument('spine', help='Path to spine.json — ordered [{key, title, pages}]')
    init_parser.add_argument('--title', default='', help='Adventure title (meta)')
    init_parser.add_argument('--source-file', dest='source_file', default='', help='Source book path (meta)')
    init_parser.add_argument('--levels', default='', help='Level range, e.g. "1-3" (meta)')
    init_parser.add_argument('--force', action='store_true',
                             help='Replace an existing adventure.json (discards progress)')

    merge_parser = sub.add_parser('merge', help='Upsert a batch of converted scenes')
    merge_parser.add_argument('scenes', help='Path to scenes.json — [scene, ...]')

    sub.add_parser('resolve-monsters',
                   help='Point every SRD-known monster at its srd_index')

    sub.add_parser('requires-report',
                   help="Diff the book's assumptions against this table (binds once a PC exists)")

    adapt_parser = sub.add_parser('adapt', help='Record what this table does about an assumption')
    adapt_parser.add_argument('--kind', required=True,
                              help=f"Which assumption: {', '.join(sorted(REQUIRES_KINDS))}")
    adapt_parser.add_argument('--ruling', default=None,
                              help='What this table does instead')
    adapt_parser.add_argument('--value', default=None,
                              help='Narrow the ruling to one value (e.g. --value Puck)')
    adapt_parser.add_argument('--remove', action='store_true',
                              help='Drop the standing ruling at this scope instead of writing one')

    sub.add_parser('status', help='Current scene and what comes next')
    sub.add_parser('advance', help='Complete the current scene and move to the next')

    jump_parser = sub.add_parser('jump', help='Move the pointer to any scene')
    jump_parser.add_argument('key', help='Scene key')

    json_mode = wants_json()
    args = parser.parse_args(strip_json_flag(sys.argv[1:]))

    if not args.action:
        parser.print_help()
        sys.exit(1)

    try:
        manager = AdventureManager()

        if args.action == 'validate':
            errors = manager.validate()
            if errors:
                if json_mode:
                    emit({'valid': False, 'errors': errors}, json_mode=True)
                else:
                    print("[ERROR] adventure.json is invalid:", file=sys.stderr)
                    for e in errors:
                        print(f"  • {e}", file=sys.stderr)
                sys.exit(1)
            emit({'valid': True, 'errors': []}, message="[SUCCESS] adventure.json is valid",
                 json_mode=json_mode)

        elif args.action == 'init':
            meta = {'title': args.title, 'source_file': args.source_file}
            if args.levels:
                meta['levels'] = args.levels
            adv = manager.init(_read_json_arg(args.spine), meta=meta, force=args.force)
            emit({'scenes': len(adv['scenes']), 'current_scene': adv['progress']['current_scene']},
                 message=f"[SUCCESS] Created adventure.json with {len(adv['scenes'])} scenes "
                         f"(starting at '{adv['progress']['current_scene']}')",
                 json_mode=json_mode)

        elif args.action == 'merge':
            batch = _read_json_arg(args.scenes)
            adv = manager.merge(batch)
            emit({'merged': len(batch), 'scenes': len(adv['scenes'])},
                 message=f"[SUCCESS] Merged {len(batch)} scene(s); adventure has "
                         f"{len(adv['scenes'])} scenes",
                 json_mode=json_mode)

        elif args.action == 'resolve-monsters':
            result = manager.resolve_monsters()
            message = (f"[SUCCESS] {result['resolved']} monster(s) resolved to the SRD, "
                       f"{result['embedded']} kept the module's own stat block")
            if result['unstatted']:
                message += (f"\n[WARNING] {result['unstatted']} monster(s) have NO stats at "
                            f"all — not in the SRD and no stat block was converted. "
                            f"These are conversion gaps; stat them before they reach the "
                            f"table:\n  " + ", ".join(result['unstatted_names']))
            emit(result, message=message, json_mode=json_mode)

        elif args.action == 'requires-report':
            report = manager.requires_report()
            emit(report, message=format_requires_report(report), json_mode=json_mode)

        elif args.action == 'adapt':
            if args.remove:
                result = manager.unadapt(args.kind, args.value)
                message = (f"[SUCCESS] Removed {len(result['removed'])} {args.kind} ruling(s) "
                           f"({result['rulings']} standing)")
            elif not args.ruling or not args.ruling.strip():
                raise AdventureError(
                    'adapt needs --ruling "<what this table does instead>" '
                    '(or --remove to drop a standing ruling)')
            else:
                result = manager.adapt(args.kind, args.ruling, args.value)
                verb = "Updated" if result['replaced'] else "Recorded"
                message = (f"[SUCCESS] {verb} the {args.kind} ruling "
                           f"({result['rulings']} standing)")
            if result.get('unreadable'):
                message += (f"\n[WARNING] {len(result['unreadable'])} other standing ruling(s) are "
                            f"unreadable and were left alone — `requires-report` names them:\n  • "
                            + "\n  • ".join(result['unreadable']))
            emit(result, message=message, json_mode=json_mode)

        elif args.action == 'status':
            status = manager.status()
            emit(status, message=format_status(status), json_mode=json_mode)

        elif args.action == 'advance':
            status = manager.advance()
            message = format_status(status)
            if status['at_end']:
                message += "\n(That was the last scene — the adventure is finished.)"
            emit(status, message=message, json_mode=json_mode)

        elif args.action == 'jump':
            status = manager.jump(args.key)
            emit(status, message=format_status(status), json_mode=json_mode)

    except (AdventureError, RuntimeError) as e:
        sys.exit(emit_error(e, json_mode=json_mode))


if __name__ == "__main__":
    main()
