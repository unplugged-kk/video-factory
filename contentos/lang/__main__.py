"""python -m contentos.lang <command>     (use the production venv python; the MLX venv is only spawned for you)

  routes                           the language -> backend/voice/ASR table from config/language.yaml, with each language's status
  matrix [--write|--check]         capability matrix (status, evidence, limits); --write refreshes config/language-capabilities.json
  validate-script LANG FILE        check a script's Unicode and script share for a language (one line per row)
  doctor                           what is installed/ready for each language, with the exact fix when it is not
  verify-models                    size + sha256 of every configured ASR model against the config
  reference --make [--from FILE]   create ~/.contentos/voices/hi_reference.wav (synthetic Kokoro clip, or a recording you supply with consent)
  setup                            install English, Hindi, and Hinglish runtimes and models. Odia stays blocked.
  download-tts                     pre-fetch the Chatterbox checkpoint into the HF cache (~3 GB, network)
  speak --lang hi --text "..." --out OUT.wav [--voice V]     one segment through the router
  transcribe WAV --lang hi         word timings through the routed ASR model
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import asr as A
from . import config as C
from . import router as R
from . import tts as T
from .errors import LangError

ROOT = Path(__file__).resolve().parent.parent.parent
FIX = ROOT / "tests/fixtures/multilingual/benchmark.json"


def _sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="contentos.lang", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for n in ("routes", "doctor", "verify-models", "download-tts", "setup"):
        sub.add_parser(n)
    p = sub.add_parser("matrix"); p.add_argument("--write", action="store_true"); p.add_argument("--check", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("validate-script"); p.add_argument("lang"); p.add_argument("file")
    p = sub.add_parser("reference"); p.add_argument("--make", action="store_true"); p.add_argument("--from", dest="src")
    p = sub.add_parser("speak"); p.add_argument("--lang", required=True); p.add_argument("--text", required=True); p.add_argument("--out", required=True); p.add_argument("--voice")
    p = sub.add_parser("transcribe"); p.add_argument("wav"); p.add_argument("--lang", required=True)
    a = ap.parse_args(argv)
    try:
        cfg = C.load()
        if a.cmd == "matrix":
            from . import capabilities as K
            m = K.build(cfg)
            if a.write:
                K.SNAPSHOT.write_text(json.dumps(m, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"); print(f"wrote {K.SNAPSHOT}")
            if a.check:
                cur = K.current()
                if cur != m:
                    print("config/language-capabilities.json is stale: run `python -m contentos.lang matrix --write`"); return 1
                print("ok: capability snapshot is current")
            print(json.dumps(m, indent=1, ensure_ascii=False) if a.json else K.render_table(m)); return 0
        if a.cmd == "validate-script":
            from . import script as SC
            lines = [l for l in Path(a.file).read_text(encoding="utf-8").splitlines() if l.strip()]
            problems = SC.validate(a.lang, lines, cfg)
            print("\n".join(problems) or f"ok: {len(lines)} lines valid for {a.lang}"); return 1 if problems else 0
        if a.cmd == "routes":
            from . import capabilities as K
            snap = K.build(cfg)["languages"]
            for l in cfg["languages"]:
                r = R.resolve({"language": l}, None, cfg)
                print(f"{l:6} [{snap[l]['status']}] tts={r.tts_backend:14} voice={r.voice:14} asr={r.asr_model:18} -l {r.asr_language}  text_policy={r.text_policy}  fallback={r.fallback_tts}")
            print("auto   accepted only with spec.language_metadata (declared, or detected with confidence >= %s)" % cfg["auto"]["min_detected_confidence"])
            return 0
        if a.cmd == "verify-models":
            bad = 0
            for k, m in cfg["asr_models"].items():
                p = C.asr_model_path(cfg, k)
                if not p.exists():
                    print(f"MISSING {k}: {p}"); bad += 1; continue
                size_ok = p.stat().st_size == m["size_bytes"]
                sha = _sha(p); sha_ok = (sha == m["sha256"]) if m.get("sha256") else None
                print(f"{'OK ' if size_ok and sha_ok is not False else 'BAD'} {k}: {p.stat().st_size} bytes (expected {m['size_bytes']}), sha256 {sha[:16]}... "
                      + ("matches official" if sha_ok else "no official checksum configured (recorded only)" if sha_ok is None else "MISMATCH"))
                bad += not (size_ok and sha_ok is not False)
            return 1 if bad else 0
        if a.cmd == "doctor":
            rc = 0
            for l in cfg["languages"]:
                r = R.resolve({"language": l}, None, cfg)
                issues = []
                try:
                    T.check_ready(r, cfg)
                except LangError as e:
                    issues.append(str(e))
                if not C.asr_model_path(cfg, r.asr_model).exists():
                    issues.append(f"[asr_model_missing] {C.asr_model_path(cfg, r.asr_model)}")
                print(f"{l:6} {'READY' if not issues else 'NOT READY'}  tts={r.tts_backend} asr={r.asr_model}")
                for i in issues:
                    print("       " + i); rc = 1
            return rc
        if a.cmd == "reference":
            dest = Path(os.path.expanduser(cfg["tts_backends"]["chatterbox_v3"]["voice_profiles"]["hindi-default"]["reference"]))
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                print(f"refusing to overwrite existing {dest}"); return 1
            if a.src:
                shutil.copy(a.src, dest)
                print(f"copied {a.src} -> {dest}. You are responsible for consent to use that voice (see docs/MULTILINGUAL.md).")
                return 0
            if not a.make:
                print("use --make or --from FILE"); return 2
            text = json.loads(FIX.read_text(encoding="utf-8"))["reference_voice_text_hi"]
            res = T._kokoro(text, R.Route("hi", "hi", "kokoro_hindi", "hf_alpha", "whisper_turbo_q5", "hi", "as_is", None), dest, cfg, __import__("time").time())
            print(f"wrote {dest} ({res.duration} s, synthetic Kokoro hf_alpha; no real person's voice)"); return 0
        if a.cmd == "setup":
            from .setup import setup
            return setup(cfg)
        if a.cmd == "download-tts":
            be = cfg["tts_backends"]["chatterbox_v3"]
            py = C.path(cfg, "mlx_python")
            code = ("from huggingface_hub import snapshot_download as s;import sys;"
                    f"print(s({be['model']!r}));print(s('mlx-community/S3TokenizerV2'))")
            r = subprocess.run([str(py), "-c", code], env=T._env(cfg), capture_output=True, text=True)
            print(r.stdout.strip() or r.stderr[-400:]); return r.returncode
        if a.cmd == "speak":
            rt = R.resolve({"language": a.lang, "voice": a.voice}, None, cfg)
            res = T.synthesize(a.text, rt, Path(a.out), cfg)
            print(json.dumps(res.to_dict(), indent=1, ensure_ascii=False)); return 0
        if a.cmd == "transcribe":
            rt = R.resolve({"language": a.lang}, None, cfg)
            r = A.route_transcribe(a.wav, rt, cfg)
            print(json.dumps({k: r[k] for k in ("model", "language", "seconds", "text")}, ensure_ascii=False, indent=1)); return 0
    except LangError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    sys.exit(main())
