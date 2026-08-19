#!/usr/bin/env python3
"""
D&D 5e Rules API Core - Simple request wrapper
Just makes requests and returns JSON. Nothing fancy.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "dnd-api"))

from dnd_api_core import BASE_URL, fetch, output, error_output