#!/usr/bin/env python3
"""
Character Creation Core - Simple request wrapper for D&D 5e API
Just makes requests and returns JSON. Nothing fancy.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "dnd-api"))

from dnd_api_core import BASE_URL, fetch, output, error_output