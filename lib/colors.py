#!/usr/bin/env python3
"""
Color utilities for GM display output.
Strategic ANSI colors for dice, damage, and key moments.

Import-only helper module:
    from lib.colors import Colors, format_roll_result
"""

# ANSI Color Codes
class Colors:
    # Reset
    RESET = "\033[0m"

    # Standard colors
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    CYAN = "\033[36m"

    # Bold variants
    BOLD = "\033[1m"
    BOLD_RED = "\033[1;31m"
    BOLD_GREEN = "\033[1;32m"
    BOLD_YELLOW = "\033[1;33m"
    BOLD_CYAN = "\033[1;36m"

    # Dim for secondary info
    DIM = "\033[2m"


def damage(amount: int) -> str:
    """Format damage in red bold."""
    return f"{Colors.BOLD_RED}-{amount} HP{Colors.RESET}"


def heal(amount: int) -> str:
    """Format healing in green bold."""
    return f"{Colors.BOLD_GREEN}+{amount} HP{Colors.RESET}"


def format_roll_result(notation: str, rolls: list, total: int,
                       is_crit: bool = False, is_fumble: bool = False) -> str:
    """
    Format a full dice roll result with colors (for use by dice.py).

    Args:
        notation: The dice notation (e.g., "1d20+5")
        rolls: List of individual die results
        total: Final total after modifiers
        is_crit: True if natural 20
        is_fumble: True if natural 1
    """
    rolls_str = '+'.join(str(r) for r in rolls)

    # Base roll in cyan
    base = f"🎲 {notation}: {Colors.CYAN}[{rolls_str}]{Colors.RESET}"

    # Add total
    base += f" = {Colors.CYAN}{total}{Colors.RESET}"

    # Add crit/fumble indicators
    if is_crit:
        base += f" ⚔️ {Colors.BOLD_GREEN}CRITICAL HIT!{Colors.RESET}"
    elif is_fumble:
        base += f" 💀 {Colors.BOLD_RED}CRITICAL MISS!{Colors.RESET}"

    return base


def success(text: str = "SUCCESS") -> str:
    """Format success text in green bold."""
    return f"{Colors.BOLD_GREEN}{text}{Colors.RESET}"


def failure(text: str = "FAILURE") -> str:
    """Format failure text in red bold."""
    return f"{Colors.BOLD_RED}{text}{Colors.RESET}"
