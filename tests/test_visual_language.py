"""Background rules A (variety inside a video) and B (variety across videos), measured, not asserted in prose."""
import json
import subprocess
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from contentos.intelligence import visual  # noqa: E402

EP3_CSS = """:root{--bg:#06080c;--cyan:#22d3ee;--amber:#fbbf24}
html,body{background:var(--bg)}
#root{background:radial-gradient(circle at 50% 16%,#141c30 0%,#0a0e18 40%,#05070b 100%)}
#grid{opacity:.055;background-image:linear-gradient(rgba(255,255,255,.9) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.9) 1px,transparent 1px);background-size:60px 60px}
.a{color:var(--cyan)}.b{border-color:var(--amber)}.c{color:var(--cyan)}"""
PILOT_HTML = """<html><head><style>:root{--bg:#0a0f1d;--amber:#fbbf24;--teal:#5eead4}
#root{background:radial-gradient(ellipse at 50% 18%,#16213d,#0a0f1d)}
#grid{background-image:linear-gradient(rgba(255,255,255,.9) 1px,transparent 1px);background-size:60px 60px}
.x{color:var(--amber)}.y{color:var(--teal)}</style></head><body></body></html>"""
PAPER_CSS = """:root{--paper:#f4efe4;--ink:#222;--red:#c0392b;--ochre:#d68910}
body{background:#f4efe4}.p{color:var(--red)}.q{color:var(--ochre)} /* paper texture */"""
NEON_CSS = """:root{--bg:#2a0b3a;--pink:#ff2bd6;--lime:#b6ff3b}
#root{background:linear-gradient(180deg,#2a0b3a,#12051c)}.a{color:var(--pink)}.b{color:var(--lime)}"""


def project(tmp_path, css, name="p"):
    d = tmp_path / name
    d.mkdir()
    (d / "styles.css").write_text(css)
    (d / "index.html").write_text('<html><head><link rel="stylesheet" href="./styles.css"></head><body></body></html>')
    return d


def sig(css):
    return visual.signature_from_css(css)


# ---- signature extraction -----------------------------------------------------------------------------------------

def test_signature_of_ep3_like_css():
    s = sig(EP3_CSS)
    assert (s["structure"], s["temperature"], s["texture"]) == ("radial", "cool", "grid")
    assert s["base"]["tier"] == "dark" and s["base"]["hue"] == 7 and set(s["accents"]) == {6, 1}


def test_signature_follows_linked_stylesheet_and_job_dirs(tmp_path):
    d = project(tmp_path, EP3_CSS)
    assert visual.signature_of(d) == sig(EP3_CSS)


def test_paper_look_is_detected():
    s = sig(PAPER_CSS)
    assert s["structure"] == "paper" and s["texture"] == "paper" and s["base"]["tier"] == "light" and s["temperature"] == "warm"


def test_missing_composition_is_a_clear_error(tmp_path):
    with pytest.raises(visual.VisualError):
        visual.signature_of(tmp_path)


# ---- Rule B ---------------------------------------------------------------------------------------------------------

def entry(cid, css):
    return {"content_id": cid, "signature": sig(css)}


def test_teal_and_cyan_are_one_family_so_ep3_duplicates_pilot():
    pilot = {"content_id": "pilot", "signature": visual.signature_from_css(PILOT_HTML)}
    r = visual.rule_b(sig(EP3_CSS), [pilot], content_id="ep3")
    assert not r["ok"] and r["duplicates"] == ["pilot"] and r["compared"][0]["different_on"] == []


def test_a_slightly_different_blue_is_not_a_new_look():
    bluer = EP3_CSS.replace("#06080c", "#070a12").replace("#141c30", "#16203a")
    assert visual.differing(sig(EP3_CSS), sig(bluer)) == []


def test_genuinely_different_looks_pass():
    r = visual.rule_b(sig(NEON_CSS), [entry("ep3", EP3_CSS), entry("ep2", PAPER_CSS)], content_id="new")
    assert r["ok"] and all(len(c["different_on"]) >= 2 for c in r["compared"])


def test_one_changed_field_is_not_enough():
    near = EP3_CSS.replace("#fbbf24", "#ef4444").replace("--cyan:#22d3ee", "--cyan:#ec4899")      # only the accents change
    r = visual.rule_b(sig(near), [entry("ep3", EP3_CSS)], content_id="x")
    assert not r["ok"] and r["compared"][0]["different_on"] == ["accents"]


def test_series_may_share_accents_but_not_the_whole_look():
    r = visual.rule_b(sig(EP3_CSS), [entry("a", EP3_CSS)], content_id="x", shared=["accents"])
    assert not r["ok"]                                                    # same backdrop: sharing accents cannot rescue it
    flat = EP3_CSS.replace("radial-gradient(circle at 50% 16%,#141c30 0%,#0a0e18 40%,#05070b 100%)", "#0b3d2e").replace("#grid{", "#nogrid{").replace("linear-gradient(rgba(255,255,255,.9) 1px,transparent 1px)", "none")
    r2 = visual.rule_b(sig(flat), [entry("a", EP3_CSS)], content_id="x", shared=["accents"])
    assert r2["ok"] and "accents" not in r2["compared"][0]["different_on"]


def test_only_brand_tokens_can_be_shared():
    with pytest.raises(visual.VisualError):
        visual.rule_b(sig(EP3_CSS), [], shared=["base"])


def test_window_limits_the_comparison():
    old = entry("old", EP3_CSS)
    others = [entry(f"o{i}", NEON_CSS if i % 2 else PAPER_CSS) for i in range(5)]
    assert visual.rule_b(sig(EP3_CSS), [old] + others, content_id="x", window=5)["ok"]
    assert not visual.rule_b(sig(EP3_CSS), [old] + others, content_id="x", window=6)["ok"]


def test_a_video_never_conflicts_with_itself():
    assert visual.rule_b(sig(EP3_CSS), [entry("ep3", EP3_CSS)], content_id="ep3")["ok"]


def test_claim_records_blocks_and_is_idempotent(tmp_path, monkeypatch):
    seed, led = tmp_path / "seed.json", tmp_path / "ws" / "led.json"
    seed.write_text(json.dumps({"entries": [entry("pilot", EP3_CSS)]}))
    dup = visual.claim("ep3", sig(EP3_CSS), seed=seed, path=led)
    assert not dup["ok"] and not led.exists()                              # a duplicate is never recorded
    ok = visual.claim("neon", sig(NEON_CSS), seed=seed, path=led)
    assert ok["ok"] and ok.get("recorded") and len(json.loads(led.read_text())["entries"]) == 1
    again = visual.claim("neon", sig(NEON_CSS), seed=seed, path=led)       # same id: replaces itself, no second row
    assert again["ok"] and len(json.loads(led.read_text())["entries"]) == 1
    nxt = visual.claim("neon-copy", sig(NEON_CSS), seed=seed, path=led)    # a different video with that look is a duplicate
    assert not nxt["ok"] and nxt["duplicates"] == ["neon"]
    dry = visual.claim("paper", sig(PAPER_CSS), seed=seed, path=led, dry_run=True)
    assert dry["ok"] and "recorded" not in dry and len(json.loads(led.read_text())["entries"]) == 1


def test_concurrent_claims_do_not_lose_entries(tmp_path):
    seed, led = tmp_path / "seed.json", tmp_path / "led.json"
    seed.write_text(json.dumps({"entries": []}))
    looks = [PAPER_CSS, NEON_CSS, EP3_CSS]
    ts = [threading.Thread(target=visual.claim, args=(f"c{i}", sig(css)), kwargs={"seed": seed, "path": led}) for i, css in enumerate(looks)]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert len(json.loads(led.read_text())["entries"]) == 3


def test_shipped_seed_ledger_flags_the_ep3_look():
    seed = json.loads(visual.SEED.read_text())
    ids = {e["content_id"] for e in seed["entries"]}
    assert {"pilot-001-agent-tool-use", "ep2-tool-call-failure"} <= ids and "ep3-what-is-generative-ai" not in ids
    ep3 = sig(EP3_CSS)
    r = visual.rule_b(ep3, seed["entries"], content_id="ep3-what-is-generative-ai")
    assert not r["ok"] and "pilot-001-agent-tool-use" in r["duplicates"]


# ---- Rule A ---------------------------------------------------------------------------------------------------------

def make_scenes_video(path, colors, seconds=1.0):
    inputs, parts = [], []
    for i, c in enumerate(colors):
        inputs += ["-f", "lavfi", "-i", f"color=c={c}:size=270x480:rate=10:duration={seconds}"]
        parts.append(f"[{i}:v]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", "".join(parts) + f"concat=n={len(colors)}:v=1:a=0[v]",
                    "-map", "[v]", "-pix_fmt", "yuv420p", str(path)], check=True)
    return [i * seconds for i in range(len(colors))], seconds * len(colors)


def test_rule_a_fails_when_every_scene_has_the_same_backdrop(tmp_path):
    starts, total = make_scenes_video(tmp_path / "same.mp4", ["0x0a0f1d"] * 6)
    r = visual.rule_a_from_video(tmp_path / "same.mp4", starts, total)
    assert r["status"] == "fail" and r["distinct_backdrops"] == 1 and r["required"] == 3


def test_rule_a_passes_with_enough_distinct_backdrops(tmp_path):
    starts, total = make_scenes_video(tmp_path / "var.mp4", ["0x0a0f1d", "0x0a0f1d", "0x3b0a1d", "0x1d3b0a", "0xe8e0c8", "0x0a0f1d"])
    r = visual.rule_a_from_video(tmp_path / "var.mp4", starts, total)
    assert r["status"] == "pass" and r["distinct_backdrops"] >= 3


def test_rule_a_motif_downgrades_to_a_recorded_warning(tmp_path):
    starts, total = make_scenes_video(tmp_path / "same.mp4", ["0x0a0f1d"] * 4)
    r = visual.rule_a_from_video(tmp_path / "same.mp4", starts, total, motif="one continuous canvas by design")
    assert r["status"] == "warn" and r["ok"] and r["motif"]


def test_rule_a_single_scene_video_is_fine():
    assert visual.rule_a_result(1, 1)["status"] == "pass"


def test_rule_a_from_declared_plan():
    plan = {"scenes": [{"id": "a", "backdrop": "navy"}, {"id": "b", "backdrop": "navy"}, {"id": "c", "backdrop": "paper"}, {"id": "d", "backdrop": "navy"}]}
    assert visual.rule_a_from_plan(plan)["status"] == "pass"             # 2 distinct of 4 scenes meets ceil(4/2)
    plan["scenes"][2]["backdrop"] = "navy"
    assert visual.rule_a_from_plan(plan)["status"] == "fail"
    with pytest.raises(visual.VisualError):
        visual.rule_a_from_plan({"scenes": [{"id": "a"}]})


def test_timing_files_in_both_shapes(tmp_path):
    v = tmp_path / "v.mp4"
    make_scenes_video(v, ["0x101010"] * 2)
    assert visual.starts_from_timing({"scenes": [{"start": 0}, {"start": 1.0}], "total_s": 2.0}, v) == ([0.0, 1.0], 2.0)
    assert visual.starts_from_timing({"scenes": [{"t0": 0}, {"t0": 1.0}], "total": 2.0}, v) == ([0.0, 1.0], 2.0)
    with pytest.raises(visual.VisualError):
        visual.starts_from_timing({"scenes": []}, v)


def test_cli_exit_codes(tmp_path, capsys):
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"scenes": [{"backdrop": "a"}, {"backdrop": "a"}]}))
    assert visual._main(["plan", str(plan)]) == 1
    assert visual._main(["plan", str(tmp_path / "missing.json")]) == 2
