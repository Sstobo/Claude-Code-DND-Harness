#!/usr/bin/env python3
"""
Simple dice rolling library for D&D
Supports standard notation: 1d20, 3d6+2, 2d20kh1 (advantage), etc.
"""

import random
import sys
import re
from typing import List, Tuple, Dict

# Import colors for formatted output
try:
    from lib.colors import Colors, format_roll_result
except ImportError:
    # Fallback if running directly
    try:
        from colors import Colors, format_roll_result
    except ImportError:
        # No colors available - use plain text
        class Colors:
            RESET = ""
            RED = ""
            GREEN = ""
            YELLOW = ""
            CYAN = ""
            BOLD = ""
            BOLD_RED = ""
            BOLD_GREEN = ""
            BOLD_YELLOW = ""
            BOLD_CYAN = ""
            DIM = ""

        def format_roll_result(notation, rolls, total, is_crit=False, is_fumble=False):
            rolls_str = '+'.join(str(r) for r in rolls)
            base = f"🎲 {notation}: [{rolls_str}] = {total}"
            if is_crit:
                base += " ⚔️ CRITICAL HIT!"
            elif is_fumble:
                base += " 💀 CRITICAL MISS!"
            return base

class DiceRoller:
    def __init__(self):
        # Regex patterns for different dice notations
        self.simple_pattern = re.compile(r'(\d+)d(\d+)([+-]\d+)?')
        self.advantage_pattern = re.compile(r'(\d+)d(\d+)kh(\d+)([+-]\d+)?')  # keep highest
        self.disadvantage_pattern = re.compile(r'(\d+)d(\d+)kl(\d+)([+-]\d+)?')  # keep lowest
        
    def roll(self, notation: str) -> Dict:
        """
        Roll dice based on notation and return detailed results
        
        Returns dict with:
        - notation: original notation
        - rolls: individual die results
        - total: final total
        - natural_20: True if d20 rolled natural 20
        - natural_1: True if d20 rolled natural 1
        """
        notation = notation.strip()
        
        # Check for advantage (keep highest)
        match = self.advantage_pattern.match(notation)
        if match:
            count, sides, keep = int(match.group(1)), int(match.group(2)), int(match.group(3))
            if sides < 1:
                raise ValueError(f"Invalid die size: d{sides} (must be at least 1)")
            modifier = int(match.group(4)) if match.group(4) else 0
            rolls = sorted([random.randint(1, sides) for _ in range(count)], reverse=True)
            kept = rolls[:keep]
            return self._mark_natural({
                'notation': notation,
                'rolls': rolls,
                'kept': kept,
                'discarded': rolls[keep:],
                'modifier': modifier,
                'total': sum(kept) + modifier,
                'type': 'advantage'
            }, sides, keep)
        
        # Check for disadvantage (keep lowest)
        match = self.disadvantage_pattern.match(notation)
        if match:
            count, sides, keep = int(match.group(1)), int(match.group(2)), int(match.group(3))
            if sides < 1:
                raise ValueError(f"Invalid die size: d{sides} (must be at least 1)")
            modifier = int(match.group(4)) if match.group(4) else 0
            rolls = sorted([random.randint(1, sides) for _ in range(count)])
            kept = rolls[:keep]
            return self._mark_natural({
                'notation': notation,
                'rolls': rolls,
                'kept': kept,
                'discarded': rolls[keep:],
                'modifier': modifier,
                'total': sum(kept) + modifier,
                'type': 'disadvantage'
            }, sides, keep)
        
        # Standard roll
        match = self.simple_pattern.match(notation)
        if match:
            count, sides = int(match.group(1)), int(match.group(2))
            if sides < 1:
                raise ValueError(f"Invalid die size: d{sides} (must be at least 1)")
            modifier = int(match.group(3)) if match.group(3) else 0

            rolls = [random.randint(1, sides) for _ in range(count)]
            total = sum(rolls) + modifier
            
            result = {
                'notation': notation,
                'rolls': rolls,
                'modifier': modifier,
                'total': total,
                'type': 'standard'
            }
            
            # Check for natural 20/1 on d20
            if sides == 20 and count == 1:
                if rolls[0] == 20:
                    result['natural_20'] = True
                elif rolls[0] == 1:
                    result['natural_1'] = True
                    
            return result
        
        raise ValueError(f"Invalid dice notation: {notation}")
    
    @staticmethod
    def _mark_natural(result: Dict, sides: int, keep: int) -> Dict:
        """Flag nat 20 / nat 1 on the kept d20 of an advantage or disadvantage roll.

        Only the plain `1d20` path used to set these, so a crit rolled with
        advantage (Reckless Attack, flanking, a prone target) came back as an
        ordinary hit and never doubled its dice.
        """
        if sides == 20 and keep == 1 and result.get('kept'):
            die = result['kept'][0]
            if die == 20:
                result['natural_20'] = True
            elif die == 1:
                result['natural_1'] = True
        return result

    def format_result(self, result: Dict) -> str:
        """Format a roll result for display with colors"""
        if result['type'] == 'advantage':
            kept_str = '+'.join(str(r) for r in result['kept'])
            discarded_str = '+'.join(str(r) for r in result['discarded'])
            mod_str = f" {result.get('modifier', 0):+d}" if result.get('modifier', 0) != 0 else ""
            return f"🎲 {result['notation']}: {Colors.CYAN}[{kept_str}]{Colors.RESET} {Colors.DIM}(discarded: {discarded_str}){Colors.RESET}{mod_str} = {Colors.CYAN}{result['total']}{Colors.RESET}"

        elif result['type'] == 'disadvantage':
            kept_str = '+'.join(str(r) for r in result['kept'])
            discarded_str = '+'.join(str(r) for r in result['discarded'])
            mod_str = f" {result.get('modifier', 0):+d}" if result.get('modifier', 0) != 0 else ""
            return f"🎲 {result['notation']}: {Colors.CYAN}[{kept_str}]{Colors.RESET} {Colors.DIM}(discarded: {discarded_str}){Colors.RESET}{mod_str} = {Colors.CYAN}{result['total']}{Colors.RESET}"

        else:  # standard
            is_crit = result.get('natural_20', False)
            is_fumble = result.get('natural_1', False)

            rolls_str = '+'.join(str(r) for r in result['rolls'])
            base = f"🎲 {result['notation']}: {Colors.CYAN}[{rolls_str}]{Colors.RESET}"

            if result['modifier'] != 0:
                mod_str = f"{result['modifier']:+d}"
                base += f" {mod_str}"

            base += f" = {Colors.CYAN}{result['total']}{Colors.RESET}"

            if is_crit:
                base += f" ⚔️ {Colors.BOLD_GREEN}CRITICAL HIT!{Colors.RESET}"
            elif is_fumble:
                base += f" 💀 {Colors.BOLD_RED}CRITICAL MISS!{Colors.RESET}"

            return base


    # ---------------------------------------------------------------- check
    # A check roll renders as a staged block rather than a one-liner: the target
    # lands first, then dead air, then the result. The pause is real because the
    # GM's message streams — tool output does not reliably reach the player at
    # all, so nothing dramatic can live in a spinner or a \r animation.

    WORDS = "zero one two three four five six seven eight nine ten".split()

    def _plain(self, n: int) -> str:
        return self.WORDS[n] if 0 <= n < len(self.WORDS) else str(n)

    @staticmethod
    def roll_parts(result: Dict, sources=None) -> list:
        """The " · "-joined breakdown line: the dice, then where each bonus came from."""
        modifier = result.get('modifier', 0)
        kept = result.get('kept') or result.get('rolls') or []
        discarded = result.get('discarded') or []

        if discarded:
            # From the notation, not by comparing dice: two equal dice would
            # otherwise mislabel an advantage roll as disadvantage.
            keep_word = "advantage" if "kh" in result.get('notation', '') else "disadvantage"
            dice_line = (f"{' and '.join(str(r) for r in kept + discarded)} — "
                         f"{keep_word}, keep the {kept[0]}")
        else:
            dice_line = f"{'+'.join(str(r) for r in kept)} on the die"

        parts = [dice_line]
        if sources:
            parts += [f"**{b:+d}** coming from {label}" for label, b in sources]
        elif modifier:
            parts.append(f"**{modifier:+d}**")
        return parts

    @staticmethod
    def format_staged(target: int, total: int, parts, verdict: str,
                      need_label: str = "You need to beat", tail: str = None) -> str:
        """The staged block: the target FIRST, dead air, then the roll and the verdict.

        The pause is real because the message streams, so nothing may collapse it or
        put the outcome above the target. Combat attacks render through here too, so
        a swing and a skill check read identically at the table.
        """
        lines = [
            need_label, "", f"## [ {target} ]", "",
            ".", "", ".", "", ".", "",
            "You rolled", "", f"## [ {total} ]", "",
            " · ".join(parts), "",
            verdict,
        ]
        if tail:
            lines += ["", tail]
        return "\n".join(lines)

    def format_check(self, result: Dict, dc: int, sources=None) -> str:
        """Render a d20 check against a DC, attributing every point of the bonus."""
        total = result['total']
        parts = self.roll_parts(result, sources)

        if result.get('natural_20'):
            verdict = "**⚔ NATURAL 20 — fantastic success. More than you hoped for.**"
        elif result.get('natural_1'):
            verdict = "**💀 NATURAL 1 — it goes wrong, and it costs you.**"
        elif total >= dc:
            margin = total - dc
            by = "on the nose" if margin == 0 else f"by {self._plain(margin)}"
            verdict = f"**✓ SUCCESS — {by}.**"
        else:
            verdict = f"**✗ FAILURE — short by {self._plain(dc - total)}.**"

        return self.format_staged(dc, total, parts, verdict)


# Module-level convenience functions
_roller = DiceRoller()

def roll(notation: str) -> int:
    """Quick roll that returns just the total. Use for simple checks."""
    return _roller.roll(notation)['total']

def roll_detailed(notation: str) -> Dict:
    """Roll with full details (rolls, modifiers, crits, etc.)"""
    return _roller.roll(notation)

def roll_formatted(notation: str) -> str:
    """Roll and return formatted string for display."""
    result = _roller.roll(notation)
    return _roller.format_result(result)


def main():
    """CLI interface for dice rolling"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Roll dice. With --dc, renders a staged check block for the GM to drop into narration.",
        epilog='Examples: dice.py 1d20+5  |  dice.py "1d20+7" --dc 15 '
               '--from "strength:4" --from "your training in athletics:3"')
    parser.add_argument("notation", help="1d20, 3d6+2, 2d20kh1 (advantage), 2d20kl1 (disadvantage)")
    parser.add_argument("--dc", type=int, help="target number — switches output to the staged check block")
    parser.add_argument("--from", dest="sources", action="append", default=[], metavar='"label:N"',
                        help="attribute part of the bonus, e.g. --from \'strength:4\' (repeatable)")
    args = parser.parse_args()

    sources = []
    for raw in args.sources:
        label, _, bonus = raw.rpartition(":")
        if not label or not bonus.lstrip("+-").isdigit():
            print(f"Error: --from expects \"label:N\", got {raw!r}")
            sys.exit(1)
        sources.append((label, int(bonus)))

    roller = DiceRoller()
    try:
        result = roller.roll(args.notation)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    if args.dc is None:
        print(roller.format_result(result))
        return

    # An attribution that does not add up to the modifier is worse than none —
    # it names a source for points that came from somewhere else.
    if sources and sum(b for _, b in sources) != result.get("modifier", 0):
        print(f"[WARN] --from adds to {sum(b for _, b in sources):+d} but the notation "
              f"carries {result.get('modifier', 0):+d}", file=sys.stderr)
    print(roller.format_check(result, args.dc, sources))


if __name__ == "__main__":
    main()