"""Controlled TTS + ASR benchmark. Original scripts with known reference text (tests/fixtures/multilingual/benchmark.json).

  ~/.contentos/venv/bin/python scripts/lang_benchmark.py [--out DIR] [--skip-generate]

Generates each sample with each applicable TTS backend, normalises it exactly as the pipeline does (loudnorm -14 LUFS, 24 kHz mono),
transcribes with the applicable ASR models plus negative controls, and writes results.json + results.md under --out.
It measures; it does not judge naturalness (a listener must). Needs: hyperframes tts, the mlx-audio venv, whisper-cli, ffmpeg.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from contentos.lang import asr, lexicon, metrics  # noqa: E402

PY = os.path.expanduser("~/.contentos/venv/bin/python")
MLX_PY = os.path.expanduser("~/.contentos/venv-mlx-audio/bin/python")
MODELS = Path(os.path.expanduser("~/.cache/hyperframes/whisper/models"))
EN, TURBO = MODELS / "ggml-small.en.bin", MODELS / "ggml-large-v3-turbo-q5_0.bin"
ENV = {**os.environ, "PATH": "/opt/homebrew/bin:" + os.environ["PATH"], "HYPERFRAMES_PYTHON": PY,
       "HF_HOME": os.path.expanduser("~/.cache/contentos/huggingface")}


def run_timed(cmd):
    """Run with /usr/bin/time -l so max resident set size is measured, not guessed."""
    t = time.time()
    r = subprocess.run(["/usr/bin/time", "-l", *cmd], capture_output=True, text=True, env=ENV, cwd=ROOT)
    m = re.search(r"(\d+)\s+maximum resident set size", r.stderr)
    return r, round(time.time() - t, 2), round(int(m.group(1)) / 1e9, 2) if m else None


def norm(raw, out):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", raw, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "24000", "-ac", "1", out], check=True, env=ENV)


def audio_stats(p):
    j = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=sample_rate,channels,codec_name", "-of", "json", p],
                                  capture_output=True, text=True, env=ENV).stdout)
    s = j["streams"][0]
    e = subprocess.run(["ffmpeg", "-hide_banner", "-i", p, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True, env=ENV).stderr
    tail = e[e.rfind("Summary"):]
    return {"duration": round(float(j["format"]["duration"]), 2), "sample_rate": int(s["sample_rate"]), "channels": s["channels"], "codec": s["codec_name"],
            "lufs": float(re.search(r"I:\s+(-?[\d.]+) LUFS", tail).group(1)), "true_peak_dbfs": float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", tail).group(1))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.expanduser("~/Desktop/VideoFactory-Workspace/experiments/multilingual"))
    ap.add_argument("--skip-generate", action="store_true")
    a = ap.parse_args()
    out = Path(a.out); (out / "audio").mkdir(parents=True, exist_ok=True); (out / "ref").mkdir(exist_ok=True)
    bm = json.load(open(ROOT / "tests/fixtures/multilingual/benchmark.json"))
    S = bm["samples"]
    ref_wav = out / "ref/kokoro_hf_alpha_ref.wav"
    texts = {"en": S["en"]["text"], "hi": S["hi"]["text"], "hi-en": S["hi-en"]["text"], "hi-en_translit": lexicon.to_devanagari(S["hi-en"]["text"])[0]}
    # (sample key, backend id, kokoro voice/lang or chatterbox lang)
    jobs = [("en", "kokoro", ("af_heart", None)), ("hi", "kokoro", ("hf_alpha", "hi")), ("hi-en", "kokoro", ("hf_alpha", "hi")),
            ("hi", "chatterbox", "hi"), ("hi-en", "chatterbox", "hi"), ("hi-en_translit", "chatterbox", "hi")]
    rows = []
    for key, be, cfg in jobs:
        raw, fin = out / f"audio/{key}__{be}.raw.wav", out / f"audio/{key}__{be}.wav"
        gen = {}
        if not a.skip_generate or not fin.exists():
            if be == "kokoro":
                v, l = cfg
                r, secs, rss = run_timed(["node_modules/.bin/hyperframes", "tts", texts[key], "-v", v, "-o", str(raw), "--json", *(["--lang", l] if l else [])])
                gen = {"seconds": secs, "max_rss_gb": rss, "model": "kokoro-v1.0.onnx", "voice": v, "lang_arg": l}
            else:
                tf = out / f"audio/{key}.txt"; tf.write_text(texts[key], encoding="utf-8")
                r, secs, rss = run_timed([MLX_PY, "contentos/lang/chatterbox_worker.py", "--text-file", str(tf), "--lang", cfg, "--ref", str(ref_wav), "--out", str(raw)])
                j = json.loads(r.stdout.strip().splitlines()[-1])
                gen = {"seconds": secs, "max_rss_gb": rss, "mlx_peak_gb": j.get("peak_memory_gb"), "model": j.get("model"), "lang_arg": cfg,
                       "load_seconds": j.get("load_seconds"), "gen_seconds": j.get("gen_seconds"), "chunks": j.get("chunks"), "ref": "kokoro hf_alpha synthetic clip"}
            norm(str(raw), str(fin)); raw.unlink()
        st = audio_stats(str(fin))
        ref_key = "hi-en" if key.startswith("hi-en") else key
        ref = texts[key] if key == "hi-en_translit" else S[ref_key]["text"]
        asr_runs = []
        plans = {"en": [(EN, "en"), (TURBO, "en")], "hi": [(TURBO, "hi"), (TURBO, "auto"), (EN, "en")], "hi-en": [(TURBO, "hi"), (TURBO, "auto"), (TURBO, "en")]}[ref_key]
        for model, lang in plans:
            try:
                r = asr.transcribe(fin, model, lang)
            except Exception as e:
                asr_runs.append({"model": model.name, "lang": lang, "error": str(e)}); continue
            f_ref, f_hyp = lexicon.fold(ref), lexicon.fold(r["text"])
            terms = S[ref_key]["technical_terms"]
            hits = lexicon.term_hits(r["text"], terms)
            asr_runs.append({"model": model.name, "lang": lang, "seconds": r["seconds"], "text": r["text"],
                             "wer_raw": round(metrics.wer(ref, r["text"]), 3), "cer_raw": round(metrics.cer(ref, r["text"]), 3),
                             "wer_folded": round(metrics.wer(f_ref, f_hyp), 3), "cer_folded": round(metrics.cer(f_ref, f_hyp), 3),
                             "terms_preserved": f"{sum(hits.values())}/{len(hits)}", "terms_missing": [t for t, h in hits.items() if not h],
                             "timestamps_problems": asr.valid_timestamps(r["words"], st["duration"]), "word_count": len(r["words"]),
                             "first_words": r["words"][:3]})
        rows.append({"sample": key, "tts": be, "audio": str(fin), "reference": ref, "audio_stats": st, "generation": gen, "asr": asr_runs})
    (out / "results.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False))
    md = ["| sample | TTS | dur s | LUFS | peak dBFS | gen s | RSS GB | ASR model / -l | WER raw | WER folded | CER folded | terms | asr s |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        g, s = r["generation"], r["audio_stats"]
        for x in r["asr"]:
            md.append(f"| {r['sample']} | {r['tts']} | {s['duration']} | {s['lufs']} | {s['true_peak_dbfs']} | {g.get('seconds', '-')} | {g.get('max_rss_gb', '-')} | {x['model'].replace('ggml-', '').replace('.bin', '')} / {x['lang']} | "
                      f"{x.get('wer_raw', 'ERR')} | {x.get('wer_folded', '-')} | {x.get('cer_folded', '-')} | {x.get('terms_preserved', '-')} | {x.get('seconds', '-')} |")
    (out / "results.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
