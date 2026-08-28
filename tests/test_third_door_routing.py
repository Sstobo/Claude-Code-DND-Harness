"""The third door must stay reachable.

Regression for the audit finding: /import-module was advertised in the README
but appeared in zero lines of gm.md or help.md — gm.md's menu even said
"or module" and then routed everything to /import, silently giving the player
the RAG book pipeline the module command exists to avoid.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _gm():
    return (ROOT / ".claude" / "commands" / "gm.md").read_text(encoding="utf-8")


def _help():
    return (ROOT / ".claude" / "commands" / "help.md").read_text(encoding="utf-8")


def test_gm_menu_routes_modules_to_import_module():
    text = _gm()
    assert "/import-module" in text
    # The old mis-wire: an unconditional "If IMPORT DOCUMENT → Run /import".
    assert "If IMPORT DOCUMENT → Run `/import`" not in text


def test_help_lists_import_module_and_does_not_misroute():
    text = _help()
    assert "/import-module" in text
    assert "Import module:    /import\n" not in text


def test_readme_does_not_deny_the_embeddings_step():
    # import-module.md Step 9 embeds the sliced module; whispering-wood's 2.2MB
    # vectors/ dir proves it. The README must not claim otherwise.
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "No embeddings, no world-bible drafting" not in text


def test_import_module_header_matches_its_own_step_9():
    text = (ROOT / ".claude" / "commands" / "import-module.md").read_text(encoding="utf-8")
    assert "never builds embeddings" not in text
    assert "gm-extract.sh add" in text
