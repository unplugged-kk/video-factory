"""Tests for scripts/measure_job.py (process-tree memory sampler).

Unit tests use synthetic `ps` text; one integration test runs a tiny real
Python child tree.  Nothing here touches the workspace, ledger or HyperFrames.
"""
import importlib.util
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "measure_job.py"
_spec = importlib.util.spec_from_file_location("measure_job", SCRIPT)
mj = importlib.util.module_from_spec(_spec)
sys.modules["measure_job"] = mj
_spec.loader.exec_module(mj)

PS = textwrap.dedent("""\
      1     0     1   1000 /sbin/launchd
    100     1   100   5000 /usr/bin/python3 job.py --workers 4
    101   100   100   2000 sleep 60
    102   101   100   3000 /x/Google Chrome for Testing --headless --workers=6
    103   100   100   4000 /x/chrome-headless-shell --type=renderer
    200     1   100   7000 orphan-in-group
    201   200   200   1500 child-of-orphan
    300     1   300  90000 /unrelated/other
    301   300   300  10000 /unrelated/child
""")


def test_parse_ps_skips_garbage():
    procs = mj.parse_ps("garbage\n 5 1 5 100 cmd with args\n x y z w v\n 6 1 6\n")
    assert list(procs) == [5]
    assert procs[5].command == "cmd with args" and procs[5].rss_kb == 100


def test_descendants_only():
    procs = mj.parse_ps(PS)
    m = mj.tree_members(procs, 100, None)
    assert m == {100, 101, 102, 103}


def test_process_group_inclusion_and_descendants_of_orphans():
    procs = mj.parse_ps(PS)
    m = mj.tree_members(procs, 100, 100)
    assert {200, 201} <= m           # re-parented group member and its child
    assert 300 not in m and 301 not in m and 1 not in m


def test_root_gone_uses_group_only():
    procs = mj.parse_ps(PS)
    m = mj.tree_members(procs, 100, 100, root_alive=False)
    assert 200 in m  # still found via group


def test_exclude_self():
    procs = mj.parse_ps(PS)
    assert 101 not in mj.tree_members(procs, 100, 100, exclude={101})


def test_summary_peak_math_worker_count_and_workers_args():
    procs = mj.parse_ps(PS)
    s = mj.summarize(procs, mj.tree_members(procs, 100, 100))
    assert s["rss_kb"] == 5000 + 2000 + 3000 + 4000 + 7000 + 1500
    assert s["procs"] == 6
    assert s["workers"] == 2
    assert s["workers_args"] == {4, 6}


def test_worker_heuristic_ignores_args_mentions():
    assert mj.is_worker("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome --type=gpu")
    assert not mj.is_worker("python run.py --browser chrome")
    assert mj.parse_workers_args("hf render --workers 3 --x") == [3]
    assert mj.parse_workers_args("hf --workers=auto") == []


def test_recorder_peak_and_gib():
    r = mj.Recorder(1.0)
    for t, kb, n, w in [(0, 1024, 1, 0), (1, 2 * 1024 * 1024, 5, 3), (2, 500, 2, 1)]:
        r.add(t, {"rss_kb": kb, "procs": n, "workers": w, "workers_args": {2} if w else set()})
    res = r.result()
    assert res["samples_count"] == 3
    assert res["peak_rss_kb"] == 2 * 1024 * 1024
    assert res["peak_rss_gib"] == 2.0
    assert res["peak_process_count"] == 5 and res["peak_worker_count"] == 3
    assert res["workers_arg_values"] == [2]


class FakeProc:
    def __init__(self, pid, polls):
        self.pid, self._polls, self.returncode = pid, list(polls), None

    def poll(self):
        if self._polls:
            v = self._polls.pop(0)
            if v is not None:
                self.returncode = v
            return v
        return self.returncode

    def wait(self, timeout=None):
        if self.returncode is None:
            self.returncode = 0
        return self.returncode


def test_measure_with_injected_ps_and_fake_popen(tmp_path, monkeypatch):
    monkeypatch.setenv("HF_CAPTURE_PARALLEL_STREAM", "true")
    monkeypatch.delenv("HYPERFRAMES_BIN", raising=False)
    snaps = iter([PS.replace("5000", "9000"), PS, PS])
    fake = FakeProc(100, [None, None, 3, 3, 3, 3])
    out = tmp_path / "s.json"
    rc = mj.measure(["fake"], str(out), 0.01,
                    ps_runner=lambda: next(snaps, PS), popen=lambda *a, **k: fake)
    assert rc == 3
    d = json.loads(out.read_text())
    assert d["exit_code"] == 3 and d["samples_count"] >= 2
    assert d["peak_rss_kb"] == 26500  # first snapshot had root RSS 9000 instead of 5000
    assert d["peak_worker_count"] == 2 and d["workers_arg_values"] == [4, 6]
    assert d["env"] == {"HF_CAPTURE_PARALLEL_STREAM": "true", "HYPERFRAMES_BIN": None}
    assert d["limits"] and any("double counts" in x for x in d["limits"])
    assert any("shorter than" in x or "spike" in x for x in d["limits"])
    assert d["platform"]["system"]


def test_ps_failure_is_counted_not_fatal(tmp_path):
    def boom():
        raise RuntimeError("ps broke")
    out = tmp_path / "s.json"
    rc = mj.measure([sys.executable, "-c", "pass"], str(out), 0.05, ps_runner=boom)
    d = json.loads(out.read_text())
    assert rc == 0 and d["sample_errors"] >= 1 and d["samples_count"] == 0


def test_command_not_found_writes_sidecar(tmp_path):
    out = tmp_path / "nested" / "s.json"
    rc = mj.main(["--out", str(out), "--", "/no/such/command-xyz"])
    d = json.loads(out.read_text())
    assert rc == 127 and d["exit_code"] == 127 and "not found" in d["error"]
    assert d["samples_count"] == 0 and d["limits"]


def test_interrupt_writes_sidecar_and_does_not_signal(tmp_path):
    class Boom(FakeProc):
        def wait(self, timeout=None):
            raise KeyboardInterrupt
    fake = Boom(100, [None, None, None, None])
    out = tmp_path / "s.json"
    rc = mj.measure(["fake"], str(out), 0.01, ps_runner=lambda: PS, popen=lambda *a, **k: fake)
    d = json.loads(out.read_text())
    assert rc == 130 and d["interrupted"] and d["child_still_running"]
    assert fake.returncode is None  # we never touched it


def test_cli_requires_command(tmp_path):
    with pytest.raises(SystemExit):
        mj.main(["--out", str(tmp_path / "x.json")])


@pytest.mark.skipif(sys.platform == "win32", reason="needs POSIX ps")
def test_integration_real_tree(tmp_path):
    child = tmp_path / "child.py"
    child.write_text(textwrap.dedent("""\
        import subprocess, sys, time
        kids = [subprocess.Popen([sys.executable, "-c", "import time; time.sleep(3)", "--workers", "2"])
                for _ in range(2)]
        buf = bytearray(40 * 1024 * 1024)
        for i in range(0, len(buf), 4096):
            buf[i] = 1
        time.sleep(2)
        for k in kids:
            k.terminate()
        sys.exit(7)
    """))
    out = tmp_path / "side.json"
    r = subprocess.run([sys.executable, str(SCRIPT), "--out", str(out), "--interval", "0.2",
                        "--", sys.executable, str(child)], capture_output=True, text=True, timeout=60)
    assert r.returncode == 7, r.stderr
    d = json.loads(out.read_text())
    assert d["exit_code"] == 7 and d["schema"] == "measure_job/1"
    assert d["samples_count"] >= 3 and len(d["samples"]) == d["samples_count"]
    assert d["peak_process_count"] >= 3
    assert d["peak_rss_kb"] >= 40 * 1024
    assert 2 in d["workers_arg_values"]
    assert d["wall_seconds"] > 1
    assert set(d["samples"][0]) == {"t", "rss_kb", "procs", "workers"}
