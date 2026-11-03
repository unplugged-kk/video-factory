"""Chatterbox Multilingual v3 (MLX) worker. Runs under the isolated mlx-audio venv, NOT the main venv.

  <mlx-venv>/bin/python chatterbox_worker.py --text-file T.txt --lang hi --ref REF.wav --out OUT.wav [--model REPO] [--exaggeration 0.5]

Prints exactly one JSON object on stdout (ok, duration, sample_rate, gen_seconds, peak_memory_gb, chunks, model, ...) and exits
0 on success, 2 on any failure (ok=false, error=...). Splits text at sentence ends, synthesises each chunk, joins with 0.25 s
of silence and records every chunk's offset, so captions and scene boundaries can be checked against real positions.
This checkpoint ships no default voice (no conds.safetensors), so --ref is REQUIRED; the worker refuses to run without one.
"""
import argparse
import json
import re
import sys
import time

DEFAULT_MODEL = "mlx-community/chatterbox-multilingual-v3"
GAP_S = 0.25


def split_chunks(text, limit=220):
    parts = [p.strip() for p in re.split(r"(?<=[।.!?])\s+", text.strip()) if p.strip()]
    out = []
    for p in parts:                      # a very long sentence is split at commas, never mid-word
        while len(p) > limit and "," in p[:limit]:
            cut = p[:limit].rfind(",") + 1
            out.append(p[:cut].strip()); p = p[cut:].strip()
        out.append(p)
    return out


def fail(msg, **kw):
    print(json.dumps({"ok": False, "error": msg, **kw}, ensure_ascii=False))
    sys.exit(2)


def synth(model, text, ref, lang, exaggeration, out, sr):
    """Generate one text to `out` (int16 WAV). Returns the item record. Raises RuntimeError with a clear message on failure."""
    import numpy as np
    from scipy.io import wavfile
    audio, chunks, pos = [], [], 0.0
    t1 = time.time()
    for i, ch in enumerate(split_chunks(text)):
        segs = [np.array(r.audio, dtype=np.float32).reshape(-1) for r in model.generate(text=ch, ref_audio=ref, lang_code=lang, exaggeration=exaggeration)]
        wav = np.concatenate(segs) if segs else np.zeros(0, np.float32)
        if not len(wav):
            raise RuntimeError(f"chunk {i} produced no audio: {ch[:40]!r}")
        d = len(wav) / sr
        chunks.append({"index": i, "text": ch, "start": round(pos, 3), "end": round(pos + d, 3)})
        audio.append(wav); pos += d
        audio.append(np.zeros(int(GAP_S * sr), np.float32)); pos += GAP_S
    full = np.concatenate(audio[:-1])
    peak = float(np.abs(full).max()) or 1.0
    wavfile.write(out, sr, (np.clip(full / max(peak, 1.0), -1, 1) * 32767).astype(np.int16))
    return {"out": out, "duration": round(len(full) / sr, 3), "gen_seconds": round(time.time() - t1, 2), "chunks": chunks, "text": text}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text-file"); ap.add_argument("--batch", help="JSON list of {text, out}; the model loads once for all")
    ap.add_argument("--lang", required=True); ap.add_argument("--ref"); ap.add_argument("--out")
    ap.add_argument("--model", default=DEFAULT_MODEL); ap.add_argument("--exaggeration", type=float, default=0.5)
    a = ap.parse_args()
    if not a.ref:
        fail("this checkpoint has no default voice: a reference recording (--ref) is required")
    if not a.batch and not (a.text_file and a.out):
        fail("give --batch JOBS.json, or --text-file and --out")
    try:
        import mlx.core as mx
        from mlx_audio.tts.utils import load_model
    except Exception as e:
        fail(f"mlx-audio runtime not importable: {type(e).__name__}: {e}")
    if a.batch:
        jobs = json.load(open(a.batch, encoding="utf-8"))
    else:
        jobs = [{"text": open(a.text_file, encoding="utf-8").read().strip(), "out": a.out}]
    if not jobs or any(not j["text"].strip() for j in jobs):
        fail("empty text")
    t0 = time.time()
    try:
        model = load_model(a.model)
    except Exception as e:
        fail(f"model load failed ({a.model}): {type(e).__name__}: {e}")
    load_s = time.time() - t0
    sr = getattr(model, "sample_rate", 24000)
    items = []
    for j in jobs:
        try:
            items.append(synth(model, j["text"].strip(), a.ref, a.lang, a.exaggeration, j["out"], sr))
        except Exception as e:
            fail(f"generation failed: {type(e).__name__}: {e}", out=j["out"])
    try:
        mem = mx.get_peak_memory() / 1e9
    except Exception:
        mem = None
    res = {"ok": True, "items": items, "sample_rate": sr, "channels": 1, "load_seconds": round(load_s, 2), "peak_memory_gb": mem,
           "model": a.model, "lang": a.lang, "ref": a.ref, "exaggeration": a.exaggeration}
    if not a.batch:                                   # single-job output keeps the flat shape the benchmark reads
        res.update(items[0])
    print(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    main()
