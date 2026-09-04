"""The golden fixture must pass its own schema.

lib/schemas.py is what /world-check runs. Until 2026-09-04 it rejected data the
game itself writes — `move` creates locations with an empty description, and
extraction writes free-text item types — so a healthy campaign reported ~80
errors and the fixture failed its own check.
"""
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def test_the_golden_fixture_validates_clean(dcc_world):
    r = subprocess.run(
        [sys.executable, "lib/schemas.py"],
        cwd=PROJECT_ROOT, capture_output=True, text=True,
        env={"GM_WORLD_STATE_BASE": dcc_world, "PATH": "/usr/bin:/bin"},
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert "errors" not in r.stdout, r.stdout
