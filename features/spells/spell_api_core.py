#!/usr/bin/env python3
"""
D&D 5e Spell API Core - Simple request wrapper
Just makes requests and returns JSON. Nothing fancy.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "dnd-api"))

# Cached core. Callers here pass full /api/2014/... paths, which fetch() handles.
from dnd_api_core import API_HOST as BASE_URL, fetch, output, error_output

def format_spell_index(spell_name):
    """Convert spell name to API index format"""
    # Convert to lowercase and replace spaces with hyphens
    # Handle special cases like apostrophes
    return spell_name.lower().replace(" ", "-").replace("'", "")