"""Multilingual routing, TTS adapter contract, ASR routing, alignment safety. Hermetic: no model is loaded and nothing is downloaded.
Real-model tests are skipped with a stated reason when the artifacts are absent."""
import copy
import json
import os
import re
import subprocess
import wave
from pathlib import Path

import pytest
import yaml

from contentos import pipeline, specs
from contentos.lang import asr, config as C, lexicon, metrics, router as R, tts as T
from contentos.lang.errors import LangError
from contentos.production import align

ROOT = Path(__file__).resolve().parent.parent
CFG = C.load()
FIX = json.loads((ROOT / "tests/fixtures/multilingual/benchmark.json").read_text(encoding="utf-8"))


def mk_cfg(tmp_path, **paths):
    c = copy.deepcopy(CFG)
    for k, v in paths.items():
        c["paths"][k] = str(v)
    return c


def sp(lang=None, n=2, **kw):
    s = {"title": "t", "voice": "af_heart", "script": [{"say": f"line {i}"} for i in range(n)], **kw}
    if lang:
        s["language"] = lang
    return s


# ---- config and routing --------------------------------------------------------------------------------------------

def test_config_is_valid_and_default_is_english():
    assert C.validate(CFG) == [] and CFG["default_language"] == "en"


@pytest.mark.parametrize("lang,backend,asr_model,policy", [("en", "kokoro", "whisper_small_en", "as_is"), ("hi", "chatterbox_v3", "whisper_turbo_q5", "as_is"),
                                                           ("hi-en", "chatterbox_v3", "whisper_turbo_q5", "translit_known")])
def test_each_language_routes_to_its_configured_backend_and_asr(lang, backend, asr_model, policy):
    r = R.resolve(sp(lang, voice=None) if lang != "en" else sp(lang))
    assert (r.language, r.tts_backend, r.asr_model, r.text_policy) == (lang, backend, asr_model, policy)


def test_missing_language_means_english_kokoro_and_legacy():
    assert R.resolve(sp()).tts_backend == "kokoro" and R.is_legacy(sp()) and R.is_legacy(sp("en"))


def test_hindi_or_a_per_line_override_leaves_the_legacy_path():
    assert not R.is_legacy(sp("hi")) and not R.is_legacy({**sp(), "script": [{"say": "a"}, {"say": "b", "lang": "hi"}]})


def test_per_line_language_overrides_the_video_language():
    s = {**sp("en"), "script": [{"say": "a"}, {"say": "b", "lang": "hi"}]}
    assert R.resolve(s, s["script"][0]).tts_backend == "kokoro" and R.resolve(s, s["script"][1]).tts_backend == "chatterbox_v3"


def test_auto_without_metadata_is_refused():
    with pytest.raises(LangError) as e:
        R.resolve(sp("auto"))
    assert e.value.code == "auto_needs_metadata"
    with pytest.raises(LangError):
        R.resolve({**sp("auto"), "language_metadata": {"language": "hi", "source": "detected", "confidence": 0.5}})


def test_auto_accepts_declared_or_confident_detected_metadata():
    assert R.resolve({**sp("auto", voice=None), "language_metadata": {"language": "hi", "source": "declared"}}).language == "hi"
    assert R.resolve({**sp("auto", voice=None), "language_metadata": {"language": "hi", "source": "detected", "confidence": 0.97}}).language == "hi"


def test_script_hint_is_a_suggestion_never_reliable():
    h = R.script_hint("कुबेरनेट्स में pod")
    assert h["suggestion"] == "hi-en" and h["reliable"] is False


def test_unsupported_language_is_an_explicit_error_naming_the_options():
    with pytest.raises(LangError) as e:
        R.resolve(sp("ta"))
    assert e.value.code == "unsupported_language" and "en, hi, hi-en, or" in str(e.value) and "matrix" in str(e.value)


def test_invalid_hindi_voice_is_an_error_not_a_kokoro_voice():
    with pytest.raises(LangError) as e:
        R.resolve(sp("hi", voice="af_heart"))
    assert e.value.code == "invalid_voice"
    assert R.resolve(sp("hi", voice="hindi-default")).voice == "hindi-default"


# ---- spec validation and approval digest ------------------------------------------------------------------------------

def _errs(spec):
    spec.setdefault("content_id", "x"); spec.setdefault("format", "9:16")
    return {e["path"] for e in specs.validate_spec(spec)["errors"]}


def test_spec_language_validation():
    assert "language" in _errs(sp("xx"))
    assert "voice" not in _errs(sp("hi", voice=None))
    assert "language" in _errs(sp("hi", voice="af_heart"))
    assert "voice" in _errs({**sp(), "voice": "hf_alpha"})                 # English still requires a factory Kokoro voice


def test_english_script_digest_is_unchanged_but_language_changes_it():
    s = sp()
    old = pipeline._digest([json.dumps({"title": "t", "script": [{"say": ln["say"], "tts": None} for ln in s["script"]]}, sort_keys=True, ensure_ascii=False)])
    assert pipeline.script_digest(s) == old                                  # existing approvals stay valid
    assert pipeline.script_digest(sp("hi")) != pipeline.script_digest({**sp("hi"), "language": "hi-en"})


# ---- text policy and lexicon ------------------------------------------------------------------------------------------

def test_translit_known_replaces_lexicon_terms_and_reports_unknowns():
    out, warn = T.prepare_text("Kubernetes में pod fail, zorgblat", "translit_known")
    assert "कुबेरनेट्स" in out and "पॉड" in out and "फेल" in out and "zorgblat" in out
    assert warn and "zorgblat" in warn[0]
    assert T.prepare_text("Kubernetes pod", "as_is") == ("Kubernetes pod", [])


def test_lexicon_folds_both_scripts_to_the_same_form():
    assert lexicon.fold("pod") == lexicon.fold("पॉड") == "पॉड"


def test_benchmark_fixture_texts_contain_their_declared_terms():
    for k, v in FIX["samples"].items():
        assert all(t in v["text"] for t in v["technical_terms"]), k


# ---- readiness errors ------------------------------------------------------------------------------------------------

def test_missing_runtime_reference_and_weights_are_actionable(tmp_path):
    route = R.resolve(sp("hi", voice=None))
    with pytest.raises(LangError) as e:
        T.check_ready(route, mk_cfg(tmp_path, mlx_python=tmp_path / "no/python"))
    assert e.value.code == "runtime_missing" and "uv pip install" in str(e.value)
    py = tmp_path / "python"; py.write_text("")
    cfg = mk_cfg(tmp_path, mlx_python=py, hf_home=tmp_path / "hf")
    cfg["tts_backends"]["chatterbox_v3"]["voice_profiles"]["hindi-default"]["reference"] = str(tmp_path / "ref.wav")
    with pytest.raises(LangError) as e:
        T.check_ready(route, cfg)
    assert e.value.code == "reference_missing" and "no default voice" in str(e.value)
    (tmp_path / "ref.wav").write_bytes(b"x")
    with pytest.raises(LangError) as e:
        T.check_ready(route, cfg)
    assert e.value.code == "weights_missing" and "download-tts" in str(e.value)


def test_invalid_asr_model_path_fails_clearly(tmp_path):
    with pytest.raises(LangError) as e:
        asr.transcribe(tmp_path / "a.wav", tmp_path / "missing.bin", "hi")
    assert e.value.code == "asr_model_missing"
    small = tmp_path / "tiny.bin"; small.write_bytes(b"x" * 100)
    with pytest.raises(LangError) as e:
        asr.transcribe(tmp_path / "a.wav", small, "hi")
    assert e.value.code == "asr_model_missing"                               # a truncated download is also refused


# ---- adapter contract (worker faked; real ffmpeg normalisation) ---------------------------------------------------------

def _fake_worker(calls):
    def run(jobs, route, cfg):
        calls.append([j["text"] for j in jobs])
        items = []
        for j in jobs:                                                        # 16 kHz stereo on purpose: the adapter must normalise it
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=f=220:d=1.2:r=16000", "-ac", "2", j["out"]], check=True)
            items.append({"out": j["out"], "gen_seconds": 0.1, "chunks": [{"index": 0, "text": j["text"], "start": 0, "end": 1.2}]})
        return {"ok": True, "items": items, "model": "fake/model", "load_seconds": 0.0, "peak_memory_gb": 1.0}
    return run


@pytest.fixture
def ready(monkeypatch):
    monkeypatch.setattr(T, "check_ready", lambda *a, **k: None)


@pytest.mark.skipif(not subprocess.run(["which", "ffmpeg"], capture_output=True, env={**os.environ, "PATH": "/opt/homebrew/bin:" + os.environ["PATH"]}).returncode == 0, reason="needs ffmpeg")
def test_hindi_lines_share_one_model_load_and_come_back_in_the_pipeline_format(tmp_path, monkeypatch, ready):
    calls = []
    monkeypatch.setattr(T, "_run_worker", _fake_worker(calls))
    monkeypatch.setenv("PATH", "/opt/homebrew/bin:" + os.environ["PATH"])
    s = sp("hi", voice=None, n=3)
    res = T.synthesize_lines(s, tmp_path / "audio", CFG)
    assert len(calls) == 1 and len(calls[0]) == 3                              # lazy + reused: one worker launch for the whole script
    for r in res:
        assert (r.sample_rate, r.channels, r.codec) == (24000, 1, "pcm_s16le")
        assert r.backend == "chatterbox_v3" and r.word_timestamps == "none" and r.fallback_from is None
        meta = json.loads(Path(r.path).with_suffix(".tts.json").read_text(encoding="utf-8"))
        assert meta["model"] == "fake/model" and meta["duration"] > 1


def test_english_only_scripts_never_touch_the_mlx_worker(tmp_path, monkeypatch, ready):
    monkeypatch.setattr(T, "_run_worker", lambda *a, **k: pytest.fail("MLX worker must not start for English"))
    monkeypatch.setattr(T, "_kokoro", lambda text, route, out, cfg, t0: (out.write_bytes(b"x"), T.TTSResult(text, "en", "kokoro", "k", route.voice, str(out), 24000, 1, "pcm_s16le", 1.0, 0.0))[1])
    res = T.synthesize_lines(sp("en"), tmp_path, CFG)
    assert [r.backend for r in res] == ["kokoro", "kokoro"]


def test_generation_failure_does_not_silently_use_another_backend(tmp_path, monkeypatch, ready):
    monkeypatch.setattr(T, "_run_worker", lambda *a, **k: (_ for _ in ()).throw(LangError("boom", code="generation_failed")))
    monkeypatch.setattr(T, "_kokoro", lambda *a, **k: pytest.fail("silent fallback to Kokoro"))
    with pytest.raises(LangError) as e:
        T.synthesize_lines(sp("hi", voice=None), tmp_path, CFG)
    assert e.value.code == "generation_failed"


def test_a_configured_fallback_is_used_and_visible_in_the_metadata(tmp_path, monkeypatch, ready):
    cfg = copy.deepcopy(CFG)
    cfg["languages"]["hi"]["fallback_tts"] = "kokoro_hindi"
    monkeypatch.setattr(T, "_run_worker", lambda *a, **k: (_ for _ in ()).throw(LangError("boom", code="generation_failed")))
    seen = []
    def fake(text, route, out, cfg_, t0):
        seen.append(route.tts_backend); out.write_bytes(b"x")
        return T.TTSResult(text, "hi", route.tts_backend, "kokoro", route.voice, str(out), 24000, 1, "pcm_s16le", 1.0, 0.0)
    monkeypatch.setattr(T, "_kokoro", fake)
    res = T.synthesize_lines(sp("hi", voice=None, n=1), tmp_path, cfg)
    assert seen == ["kokoro_hindi"] and res[0].fallback_from == "chatterbox_v3" and any("FALLBACK" in w for w in res[0].warnings)
    assert json.loads((tmp_path / "01.tts.json").read_text(encoding="utf-8"))["fallback_from"] == "chatterbox_v3"


def test_a_voice_or_language_error_is_never_masked_by_the_fallback(tmp_path, ready):
    cfg = copy.deepcopy(CFG); cfg["languages"]["hi"]["fallback_tts"] = "kokoro_hindi"
    with pytest.raises(LangError) as e:
        T.synthesize_lines(sp("hi", voice="af_heart"), tmp_path, cfg)
    assert e.value.code == "invalid_voice"


# ---- ASR routing and timestamps ---------------------------------------------------------------------------------------

def test_asr_routes_english_to_the_existing_model_and_indic_to_multilingual():
    assert C.asr_model_path(CFG, "whisper_small_en").name == "ggml-small.en.bin"
    assert C.asr_model_path(CFG, "whisper_turbo_q5").name == "ggml-large-v3-turbo-q5_0.bin"
    assert not CFG["asr_models"]["whisper_small_en"]["multilingual"] and CFG["asr_models"]["whisper_turbo_q5"]["multilingual"]


def test_english_words_for_keeps_the_legacy_hyperframes_path_and_hindi_uses_the_router(tmp_path, monkeypatch):
    called = []
    monkeypatch.setattr(pipeline, "sh", lambda cmd, **k: called.append(("sh", [str(c) for c in cmd][:2])))
    assert pipeline.words_for(tmp_path / "a.wav", tmp_path / "w") is None        # no transcript produced -> legacy even-spacing fallback
    assert called and called[0][0] == "sh" and "transcribe" in called[0][1][1]
    monkeypatch.setattr(asr, "route_transcribe", lambda wav, route, cfg: {"words": [{"text": "नमस्ते", "start": 0.0, "end": 0.5}], "model": "m", "asr_model_id": route.asr_model, "language": "hi", "seconds": 1, "route_language": "hi"})
    out = pipeline.words_for(tmp_path / "a.wav", tmp_path / "w2", language="hi")
    assert out == [("नमस्ते", 0.0, 0.5)] and len(called) == 1                    # hyperframes not called again


def test_valid_timestamps_detects_the_three_failure_kinds():
    ok = [{"text": "a", "start": 0, "end": 1}, {"text": "b", "start": 1, "end": 2}]
    assert asr.valid_timestamps(ok, 2.0) == []
    assert asr.valid_timestamps([{"text": "a", "start": 2, "end": 1}], 5)
    assert asr.valid_timestamps([{"text": "a", "start": 0, "end": 3}, {"text": "b", "start": 0.5, "end": 1}], 5)
    assert asr.valid_timestamps([{"text": "a", "start": 0, "end": 9}], 2)


# ---- alignment safety for non-Latin scripts -----------------------------------------------------------------------------

@pytest.mark.parametrize("w", ["Hello", "it's", "AI-ML", "x86", "don't!", "ABC123", ""])
def test_english_normalisation_is_exactly_the_original(w):
    assert align.norm(w) == re.sub(r"[^a-z0-9']+", "", w.lower())


def test_devanagari_words_no_longer_normalise_to_nothing():
    assert align.norm("पॉड") and align.norm("पॉड") != align.norm("कंटेनर")
    assert align.norm("ज़्यादा") == align.norm("ज्यादा")                         # nukta folded


def test_hindi_alignment_is_anchored_not_degenerate():
    words = "कुबेरनेट्स में पॉड सबसे छोटी इकाई".split()
    a = [{"text": t, "start": i * 0.5, "end": i * 0.5 + 0.4} for i, t in enumerate(["Kubernetes", "में", "pod", "सबसे", "छोड़ी", "इकाई"])]
    wl, st = align.align_words(words, a, fold=lexicon.fold)
    assert [round(s, 1) for _, s, _ in wl] == [0.0, 0.5, 1.0, 1.5, 2.0, 2.5] and st["match_ratio"] >= 0.8
    _, st0 = align.align_words(words, a)
    assert st["match_ratio"] > st0["match_ratio"]                                 # folding Latin terms is what makes it match


def test_metrics_known_values():
    assert metrics.wer("a b c d", "a b x d") == 0.25 and metrics.cer("abcd", "abxd") == 0.25
    assert metrics.wer("नमस्ते दुनिया।", "नमस्ते  दुनिया") == 0.0


# ---- real artifacts (skipped when absent) ---------------------------------------------------------------------------------

MODEL = C.asr_model_path(CFG, "whisper_turbo_q5")
SAMPLE = Path(os.path.expanduser("~/Desktop/VideoFactory-Workspace/experiments/multilingual/audio/hi__chatterbox.wav"))


@pytest.mark.skipif(not (MODEL.exists() and SAMPLE.exists()),
                    reason="needs the multilingual whisper model and the Hindi sample generated by scripts/lang_benchmark.py")
def test_real_hindi_audio_transcribes_with_valid_timestamps_and_mostly_right_text():
    r = asr.transcribe(SAMPLE, MODEL, "hi")
    ref = lexicon.fold(FIX["samples"]["hi"]["text"])
    assert metrics.wer(ref, lexicon.fold(r["text"])) < 0.15
    assert asr.valid_timestamps(r["words"], 18.6) == []


# ---- script-aware typography ---------------------------------------------------------------------------------------------

def _compose(tmp_path, spec_):
    from contentos.scenekit import compose as skc
    (tmp_path / "audio").mkdir()
    for i in range(1, len(spec_["script"]) + 1):
        (tmp_path / "audio" / f"{i:02d}.wav").write_bytes(b"RIFF")
    skc.compose({"id": "x", "dir": tmp_path, "spec": spec_, "res": (1080, 1920)}, dur=lambda p: 4.0, words_for=lambda *a, **k: None,
                caption_words=lambda toks, asr, d, **k: [(w, i * 0.3, i * 0.3 + 0.25) for i, w in enumerate(toks)], stage=lambda *a, **k: None, lint_cmd=["lint"])
    return (tmp_path / "project/index.html").read_text()


def test_devanagari_text_disables_letter_spacing_and_uppercase_via_a_script_marker(tmp_path):
    hi = {"content_id": "x", "title": "t", "language": "hi", "visual_style": "blueprint-architecture",
          "script": [{"say": "कुबेरनेट्स में पॉड", "headline": "पॉड क्या है", "tag": "परिचय"}]}
    en = {**hi, "language": "en", "script": [{"say": "a pod", "headline": "What is a pod", "tag": "Intro"}]}
    a, b = tmp_path / "a", tmp_path / "b"; a.mkdir(); b.mkdir()
    h_hi, h_en = _compose(a, hi), _compose(b, en)
    assert 'data-script="deva"' in h_hi and 'data-script="latin"' in h_en
    assert "Kohinoor Devanagari" in h_hi and "letter-spacing:0!important" in h_hi
    assert 'src:local("Kohinoor Devanagari Regular")' in h_hi and "@font-face" not in h_en        # lint needs a declaration per family


# ======================= round 3: Odia, script validation, capability matrix, cloud-facing behaviour ======================

from contentos.lang import capabilities as K, script as SC, setup as SU, typography as TY  # noqa: E402

ODIA = "ଓଡ଼ିଶା ଭାରତର ପୂର୍ବ ଉପକୂଳରେ ଥିବା ଏକ ରାଜ୍ୟ।"
HINDI = "कुबेरनेट्स में पॉड सबसे छोटी इकाई है।"


def test_odia_is_a_registered_language_with_its_own_script_and_fonts():
    prof = CFG["language_profiles"]["or"]
    assert prof["script"] == "odia" and prof["unicode_ranges"] == ["0B00-0B7F"] and "Oriya Sangam MN" in prof["fonts"]
    assert R.resolve(sp("or", voice=None)).tts_backend == "indic_parler_odia"


def test_odia_tts_is_blocked_with_the_exact_reason_and_never_falls_back_to_another_voice():
    route = R.resolve(sp("or", voice=None))
    with pytest.raises(LangError) as e:
        T.check_ready(route, CFG)
    assert e.value.code == "backend_blocked"
    assert "Hugging Face token" in str(e.value) and "PyTorch" in str(e.value)
    assert CFG["languages"]["or"]["fallback_tts"] is None


@pytest.mark.parametrize("lang,text,ok", [("hi", HINDI, True), ("hi", "plain English text", False), ("or", ODIA, True), ("or", HINDI, False),
                                          ("hi-en", "Kubernetes में pod सबसे छोटी unit है", True), ("hi-en", "kya haal hai doston", False),
                                          ("en", "A plain English line.", True), ("en", HINDI, False)])
def test_script_validation_by_language(lang, text, ok):
    assert (SC.validate(lang, [text], CFG) == []) is ok


def test_script_validation_catches_encoding_problems():
    import unicodedata
    decomposed = ODIA + " \u0b47\u0b56"                                  # U+0B47 + U+0B56 composes to U+0B48 under NFC
    assert unicodedata.normalize("NFC", decomposed) != decomposed
    assert any("NFC" in p for p in SC.validate("or", [decomposed], CFG))
    assert SC.validate("or", [SC.normalise(decomposed)], CFG) == []
    assert any("zero-width" in p for p in SC.validate("hi", [HINDI + "\u200b"], CFG))
    assert any("U+FFFD" in p for p in SC.validate("hi", [HINDI + "\ufffd"], CFG))
    assert any("empty" in p for p in SC.validate("hi", ["  "], CFG))
    assert SC.validate("hi", [HINDI + " \u200c"], CFG) == []                # ZWNJ is legitimate in Indic text and must not be flagged


def test_spec_validation_flags_a_script_that_is_not_in_the_language():
    s = {"content_id": "x", "format": "9:16", **sp("hi", voice=None, n=1)}
    s["script"] = [{"say": "This is English for a Hindi job."}]
    errs = specs.validate_spec(s)["errors"]
    assert any(e["path"] == "script[0].say" and "devanagari" in e["message"] for e in errs)
    s["script"] = [{"say": HINDI}]
    assert not any(e["path"] == "script[0].say" for e in specs.validate_spec(s)["errors"])


def test_pipeline_voice_stage_refuses_a_blocked_language_and_a_mismatched_script(tmp_path):
    ctx = {"dir": tmp_path, "allow_paid": False, "spec": {"title": "t", "language": "or", "script": [{"say": ODIA}]}}
    with pytest.raises(pipeline.Blocked) as e:
        pipeline.s_voice(ctx)
    assert "language_blocked" in str(e.value) and "Odia" in str(e.value)
    ctx = {"dir": tmp_path, "allow_paid": False, "spec": {"title": "t", "language": "hi", "script": [{"say": "English only here"}]}}
    with pytest.raises(pipeline.Blocked) as e:
        pipeline.s_voice(ctx)
    assert "script_language_mismatch" in str(e.value)


# ---- capability matrix rules ---------------------------------------------------------------------------------------

READY = {"status": "ready", "detail": "x"}
ev_pass = {"end_to_end_render": {"status": "pass"}, "automated_tests": {"status": "pass"}}


def test_matrix_status_rules():
    assert K._status({"status": "blocked", "detail": "gated"}, READY, ev_pass)[0] == "blocked"
    assert K._status(READY, {"status": "not-ready", "detail": "no model"}, ev_pass)[0] == "blocked"
    assert K._status(READY, READY, {})[0] == "experimental"                                   # installed but nothing validated
    assert K._status(READY, READY, {"end_to_end_render": {"status": "pass"}})[0] == "experimental"
    assert K._status(READY, READY, ev_pass)[0] == "tested"                                    # no human review yet
    assert K._status(READY, READY, {**ev_pass, "human_audio_review": {"status": "pass"}})[0] == "production-ready"
    assert K._status(READY, READY, {**ev_pass, "production_history": "shipped"})[0] == "production-ready"
    assert K._status(READY, READY, {**ev_pass, "human_audio_review": {"status": "pass"}, "max_status": {"status": "experimental", "reason": "r"}})[0] == "experimental"
    assert K._status(READY, {"status": "timing-fallback", "detail": "x"}, ev_pass)[0] == "tested"   # Odia-style timing fallback is allowed


def test_an_installed_but_unreviewed_language_never_reads_as_production_ready():
    m = K.build(CFG)["languages"]
    assert m["en"]["status"] == "production-ready"
    assert m["hi"]["status"] == "experimental" and "fluent listener" in m["hi"]["status_reason"]
    assert m["hi-en"]["status"] != "production-ready" and m["or"]["status"] == "blocked"
    assert all(l["evidence"]["human_audio_review"]["status"] != "pass" for c, l in m.items() if c != "en")


@pytest.mark.skipif(not C.path(CFG, "mlx_python").exists(), reason="the snapshot reflects this Mac's installed models")
def test_the_checked_in_capability_snapshot_is_current():
    assert K.current() == K.build(CFG), "run: python -m contentos.lang matrix --write"


def test_snapshot_carries_what_the_cloud_adapter_reads():
    snap = K.current()
    for code, l in snap["languages"].items():
        assert {"status", "status_reason", "voices", "default_voice"} <= set(l)
        assert {"unicode_ranges", "min_script_share", "script", "fonts"} <= set(l["subtitle"]), code
        assert l["default_voice"] in l["voices"], code


# ---- ASR timing fallback is explicit and only where configured -------------------------------------------------------------

def test_odia_timing_fallback_is_recorded_as_unverified_and_hindi_stays_strict(tmp_path, monkeypatch):
    err = lambda *a, **k: (_ for _ in ()).throw(LangError("model missing", code="asr_model_missing"))
    monkeypatch.setattr(asr, "route_transcribe", err)
    assert pipeline.words_for(tmp_path / "a.wav", tmp_path / "w", language="or") is None       # caption_words then spaces words evenly
    note = json.loads((tmp_path / "w" / "asr-route.json").read_text(encoding="utf-8"))
    assert "UNVERIFIED" in note["timing"]
    with pytest.raises(LangError):
        pipeline.words_for(tmp_path / "a.wav", tmp_path / "w2", language="hi")                 # Hindi has no timing fallback


# ---- typography ----------------------------------------------------------------------------------------------------------

def test_script_kind_and_typography_blocks():
    assert TY.script_kind("hello") == "latin" and TY.script_kind(HINDI) == "deva" and TY.script_kind(ODIA) == "odia"
    assert TY.script_kind(HINDI + ODIA) == "odia"
    assert TY.block("latin", ["h1"]) == ""
    deva = TY.block("deva", ["h1", ".cap"])
    assert 'local("Kohinoor Devanagari Regular")' in deva and "letter-spacing:0!important" in deva and "Oriya" not in deva
    odia = TY.block("odia", ["h1"], "[data-script=odia]")
    assert 'local("Oriya Sangam MN")' in odia and "[data-script=odia] h1" in odia and "Kohinoor" not in odia


def test_legacy_english_template_gets_no_indic_css():
    assert TY.block(TY.script_kind("What is a pod headline"), ["h1", ".tag", ".cap"]) == ""     # so English HTML is byte-identical


def test_setup_requires_hindi_only_on_apple_silicon(tmp_path):
    assert SU.required_languages("darwin", "arm64") == ("en", "hi", "hi-en")
    assert SU.required_languages("linux", "x86_64") == ("en",)
    assert SU.required_languages("darwin", "x86_64") == ("en",)
    good = tmp_path / "m.bin"
    good.write_bytes(b"abc")
    assert SU.artifact_ok(good, 3) is True
    assert SU.artifact_ok(good, 4) is False
    assert SU.artifact_ok(good, 3, "not-a-hash") is False
