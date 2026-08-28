"""Tests for advisory-hooks: PostToolUse state-write logging + Stop autosave.

Hooks are advisory and non-blocking. These assert the config is valid (statusLine
preserved), the scripts parse, and the PostToolUse script exits 0 (never wedges).
"""

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_settings_keeps_statusline_and_adds_hooks():
    s = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert "statusLine" in s, "must not clobber the existing statusLine"
    assert "PostToolUse" in s["hooks"]
    assert "Stop" in s["hooks"]


def test_hook_scripts_exist_and_parse():
    for name in ("post-tool-state-log.sh", "session-autosave.sh"):
        p = ROOT / ".claude" / "hooks" / name
        assert p.exists(), f"missing hook {name}"
        assert subprocess.run(["bash", "-n", str(p)]).returncode == 0


def test_post_tool_hook_never_blocks(tmp_path):
    inp = '{"tool_input": {"command": "bash tools/gm-player.sh hp Tandy -5"}}'
    r = subprocess.run(
        ["bash", str(ROOT / ".claude" / "hooks" / "post-tool-state-log.sh")],
        input=inp, capture_output=True, text=True,
        env={"CLAUDE_PROJECT_DIR": str(tmp_path), "PATH": __import__("os").environ.get("PATH", "")},
    )
    assert r.returncode == 0
    # It should have logged the state write under the project dir.
    log = tmp_path / ".ship-it" / "state-writes.log"
    assert log.exists() and "gm-player.sh hp" in log.read_text(encoding="utf-8")


def test_dc_rolls_are_logged_for_audit(tmp_path):
    """A --dc roll is a promise to paste the staged block into narration. No hook
    can inspect the model's outgoing text to enforce that, so every rolled DC is
    logged instead — a skipped block shows up as a roll with no matching narration."""
    inp = '{"tool_input": {"command": "uv run python lib/dice.py \\"1d20+7\\" --dc 15"}}'
    r = subprocess.run(
        ["bash", str(ROOT / ".claude" / "hooks" / "post-tool-state-log.sh")],
        input=inp, capture_output=True, text=True,
        env={"CLAUDE_PROJECT_DIR": str(tmp_path), "PATH": __import__("os").environ.get("PATH", "")},
    )
    assert r.returncode == 0
    log = tmp_path / ".ship-it" / "dice-rolls.log"
    assert log.exists() and "--dc 15" in log.read_text(encoding="utf-8")


def test_a_dc_less_roll_is_not_logged_as_a_dc_roll(tmp_path):
    """A plain damage/initiative roll (no --dc) makes no narration promise."""
    inp = '{"tool_input": {"command": "uv run python lib/dice.py \\"2d6+4\\""}}'
    subprocess.run(
        ["bash", str(ROOT / ".claude" / "hooks" / "post-tool-state-log.sh")],
        input=inp, capture_output=True, text=True,
        env={"CLAUDE_PROJECT_DIR": str(tmp_path), "PATH": __import__("os").environ.get("PATH", "")},
    )
    assert not (tmp_path / ".ship-it" / "dice-rolls.log").exists()


def test_post_tool_hook_ignores_non_state_commands(tmp_path):
    inp = '{"tool_input": {"command": "ls -la"}}'
    r = subprocess.run(
        ["bash", str(ROOT / ".claude" / "hooks" / "post-tool-state-log.sh")],
        input=inp, capture_output=True, text=True,
        env={"CLAUDE_PROJECT_DIR": str(tmp_path), "PATH": __import__("os").environ.get("PATH", "")},
    )
    assert r.returncode == 0
    assert not (tmp_path / ".ship-it" / "state-writes.log").exists()
