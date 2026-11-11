"""The shell surface the universal skills tell an agent to run must exist in the CLI parser.

The skills document `./contentos.sh looks ...` and `./contentos.sh videojob select ...`; if the parser does not know
those words, an agent following a skill hits a command that does not exist.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from contentos import cli  # noqa: E402


def run(monkeypatch, capsys, argv):
    monkeypatch.setattr(sys, "argv", ["contentos", *argv])
    with pytest.raises(SystemExit) as e:
        cli.main()
    return e.value.code, capsys.readouterr().out


def test_looks_is_reachable_from_the_contentos_cli(monkeypatch, capsys):
    code, out = run(monkeypatch, capsys, ["looks", "validate"])
    assert code == 0 and '"ok": true' in out


def test_videojob_select_is_reachable_and_a_blocker_exits_1(monkeypatch, capsys):
    code, out = run(monkeypatch, capsys, ["videojob", "select", "--intent", "edit"])
    assert code == 1 and "talking-head-editor" in out and '"state": "planned"' in out
