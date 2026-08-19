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
import sys
from typing import Any, Dict, List, Optional
from pathlib import Path

# Add lib directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from entity_manager import EntityManager

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
}


class AdventureError(Exception):
    """A bad request against the adventure (unknown key, no file, invalid input)."""


def _stub_scene(key: str, title: str, pages: Optional[List[int]] = None) -> Dict[str, Any]:
    scene = {'key': key, 'title': title}
    for field, empty in SCENE_FIELDS.items():
        scene[field] = empty() if callable(empty) else empty
    scene['pages'] = list(pages or [])
    return scene


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
