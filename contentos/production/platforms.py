"""Platform delivery limits for short-form and long-form video (read-only, pure, no network).

`config/platforms.json` (schema platforms/1) records, per platform and per format kind ("short" or "long"), the longest
upload, aspect range and file limits we know of, with a confidence label and the sources. This module answers:

  * budget()  what is the longest video that fits every chosen platform for a kind?
  * check()   does a video of N seconds and aspect A fit platform P?
  * plan()    check() for every chosen platform, with a verdict per platform.

Statuses: ok | ok-unverified | over-owner-ceiling | too-long | aspect-mismatch | unsupported | disabled | needs-opt-in
  ok-unverified: the video fits, but the stored limit is third-party or conflicting; re-check before publishing.
  over-owner-ceiling: longer than the owner's own cap for that kind (short-form: 300 s hard, 180 s default).
  disabled:      the platform is not enabled by default (for example TikTok, which is blocked in India).
  needs-opt-in:  the format needs a paid or verified account the owner has not declared (for example X Premium).

Limits are a snapshot (see `checked` in the file) and platforms change them; the file is data, not policy. Nothing
here uploads, posts or calls a service.

CLI (exit 0 = every chosen platform fits, 1 = at least one problem, 2 = unreadable registry):
  python -m contentos.production.platforms budget --kind short [--platforms a,b] [--tier x=premium] [--opt-in x]
  python -m contentos.production.platforms check  --kind short --seconds 56 [--aspect 9:16] [--platforms a,b]
  python -m contentos.production.platforms list
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

KINDS = ("short", "long")
CONFIDENCE = ("official", "official-partial", "third-party", "conflicting")
UNVERIFIED = ("third-party", "conflicting")
DEFAULT_PATH = Path(__file__).resolve().parents[2] / "config" / "platforms.json"


class PlatformError(ValueError):
    pass


def parse_aspect(text):
    """'9:16' -> 0.5625 (width / height). Accepts a number too."""
    if isinstance(text, (int, float)):
        return float(text)
    try:
        w, h = str(text).split(":")
        w, h = float(w), float(h)
        if w <= 0 or h <= 0:
            raise ValueError
        return w / h
    except ValueError:
        raise PlatformError(f"aspect {text!r} must look like '9:16'") from None


def _validate(data):
    if not isinstance(data, dict) or data.get("schema") != "platforms/1":
        raise PlatformError("platforms.json: schema must be 'platforms/1'")
    out, seen = {}, set()
    for p in data.get("platforms", []):
        pid = p.get("id")
        if not isinstance(pid, str) or not pid or pid in seen:
            raise PlatformError(f"platform id missing or duplicated: {pid!r}")
        seen.add(pid)
        for key in ("name", "default_enabled", "available_in_india", "formats"):
            if key not in p:
                raise PlatformError(f"{pid}: missing {key!r}")
        if not p["formats"]:
            raise PlatformError(f"{pid}: needs at least one format")
        for kind, f in p["formats"].items():
            where = f"{pid}.{kind}"
            if kind not in KINDS:
                raise PlatformError(f"{where}: kind must be one of {KINDS}")
            if not isinstance(f.get("max_seconds"), (int, float)) or f["max_seconds"] <= 0:
                raise PlatformError(f"{where}: max_seconds must be a positive number")
            if f.get("confidence") not in CONFIDENCE:
                raise PlatformError(f"{where}: confidence must be one of {CONFIDENCE}")
            if not f.get("sources"):
                raise PlatformError(f"{where}: at least one source is required")
            ar = f.get("aspect_range")
            if ar is not None and not (isinstance(ar, list) and len(ar) == 2 and 0 < ar[0] <= ar[1]):
                raise PlatformError(f"{where}: aspect_range must be null or [min, max] with 0 < min <= max")
            for tier, t in f.get("tiers", {}).items():
                if not isinstance(t.get("max_seconds"), (int, float)) or t["max_seconds"] <= 0:
                    raise PlatformError(f"{where}: tier {tier!r} needs a positive max_seconds")
        out[pid] = p
    if not out:
        raise PlatformError("no platforms")
    return out


def _read(path):
    path = Path(path) if path else DEFAULT_PATH
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PlatformError(f"cannot read {path}: {exc}") from exc


def load(path=None):
    return _validate(_read(path))


def owner_limits(path=None):
    """Owner ceilings in seconds: {'short': n or None, 'long': n or None, 'short_default': n or None}."""
    o = _read(path).get("owner", {})
    out = {"short": o.get("short_max_seconds"), "long": o.get("long_max_seconds"), "short_default": o.get("short_default_max_seconds")}
    for k, v in out.items():
        if v is not None and (not isinstance(v, (int, float)) or v <= 0):
            raise PlatformError(f"owner.{k} must be null or a positive number")
    if out["short"] and out["short_default"] and out["short_default"] > out["short"]:
        raise PlatformError("owner short default is above the short ceiling")
    return out


def default_platforms(reg):
    return [pid for pid, p in reg.items() if p["default_enabled"]]


def _resolve(reg, platforms):
    ids = list(platforms) if platforms else default_platforms(reg)
    unknown = [i for i in ids if i not in reg]
    if unknown:
        raise PlatformError(f"unknown platform(s): {unknown}; known: {sorted(reg)}")
    return ids


def _limits(f, tier):
    lim = {"max_seconds": f["max_seconds"], "max_mb": f.get("max_mb")}
    if tier:
        t = f.get("tiers", {}).get(tier)
        if t is None:
            raise PlatformError(f"no tier {tier!r}; available: {sorted(f.get('tiers', {}))}")
        lim.update({k: v for k, v in t.items() if k in lim})
    return lim


def check(reg, pid, kind, seconds, aspect=None, tier=None, opt_in=(), allow_disabled=False, owner_max=None):
    """Verdict for one platform. Never raises for a normal miss; returns {'platform','kind','status','reasons',...}."""
    if kind not in KINDS:
        raise PlatformError(f"kind must be one of {KINDS}")
    if pid not in reg:
        raise PlatformError(f"unknown platform {pid!r}; known: {sorted(reg)}")
    p = reg[pid]
    res = {"platform": pid, "kind": kind, "status": "ok", "reasons": [], "max_seconds": None, "confidence": None}
    f = p["formats"].get(kind)
    if f is None:
        res.update(status="unsupported", reasons=[f"no {kind}-form format recorded for {p['name']}"])
        return res
    lim = _limits(f, tier)
    res.update(max_seconds=lim["max_seconds"], confidence=f["confidence"], label=f.get("label"))
    if not p["default_enabled"] and not allow_disabled:
        res.update(status="disabled", reasons=[p.get("india_note") or "disabled by default"])
        return res
    if f.get("requires") and pid not in opt_in:
        res.update(status="needs-opt-in", reasons=[f"needs {f['requires']}; opt in only if the account has it"])
        return res
    if owner_max is not None and seconds > owner_max:
        res.update(status="over-owner-ceiling", reasons=[f"{seconds:g} s exceeds the owner's {kind}-form ceiling of {owner_max:g} s"])
        return res
    if seconds > lim["max_seconds"]:
        res.update(status="too-long", reasons=[f"{seconds:g} s exceeds {lim['max_seconds']:g} s"])
        return res
    ar = f.get("aspect_range")
    if aspect is not None and ar is not None:
        a = parse_aspect(aspect)
        if not ar[0] - 1e-6 <= a <= ar[1] + 1e-6:
            res.update(status="aspect-mismatch", reasons=[f"aspect {aspect} is outside {ar[0]:.3f}-{ar[1]:.3f} (width/height)"])
            return res
    if f["confidence"] in UNVERIFIED:
        res.update(status="ok-unverified", reasons=[f"limit is {f['confidence']}; verify before publishing"])
    return res


def plan(reg, kind, seconds, aspect=None, platforms=None, tiers=None, opt_in=(), allow_disabled=False, owner_max=None):
    tiers = tiers or {}
    return [check(reg, pid, kind, seconds, aspect, tiers.get(pid), opt_in, allow_disabled, owner_max) for pid in _resolve(reg, platforms)]


def budget(reg, kind, platforms=None, tiers=None, opt_in=(), allow_disabled=False, owner_max=None):
    """Longest video (seconds) that fits every chosen platform that has a usable `kind` format.
    Skipped platforms (unsupported, disabled, needs opt-in) are listed, never silently ignored."""
    tiers = tiers or {}
    per, skipped = {}, {}
    for pid in _resolve(reg, platforms):
        v = check(reg, pid, kind, 0, None, tiers.get(pid), opt_in, allow_disabled)
        if v["status"] in ("unsupported", "disabled", "needs-opt-in"):
            skipped[pid] = v["status"]
        else:
            per[pid] = {"max_seconds": v["max_seconds"], "confidence": v["confidence"]}
    if not per:
        return {"kind": kind, "max_seconds": None, "limiting": None, "owner_ceiling": owner_max, "per_platform": per, "skipped": skipped}
    limiting = min(per, key=lambda k: (per[k]["max_seconds"], k))
    platform_max = per[limiting]["max_seconds"]
    # the owner ceiling is a hard cap; when it is the tighter one it is the limiting factor
    if owner_max is not None and owner_max < platform_max:
        return {"kind": kind, "max_seconds": owner_max, "limiting": "owner", "owner_ceiling": owner_max, "platform_max_seconds": platform_max, "per_platform": per, "skipped": skipped}
    return {"kind": kind, "max_seconds": platform_max, "limiting": limiting, "owner_ceiling": owner_max, "platform_max_seconds": platform_max, "per_platform": per, "skipped": skipped}


def _parse_tiers(items):
    out = {}
    for it in items or []:
        if "=" not in it:
            raise PlatformError(f"--tier expects platform=tier, got {it!r}")
        k, v = it.split("=", 1)
        out[k] = v
    return out


def _csv(s):
    return [x for x in (s or "").split(",") if x] or None


def _main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m contentos.production.platforms", description=__doc__.split("\n")[0])
    ap.add_argument("--registry", default=None)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    for name in ("budget", "check"):
        p = sub.add_parser(name)
        p.add_argument("--kind", required=True, choices=KINDS)
        p.add_argument("--platforms", default=None, help="comma-separated ids; default = enabled platforms")
        p.add_argument("--tier", action="append", help="platform=tier, e.g. youtube=verified")
        p.add_argument("--opt-in", default=None, help="comma-separated ids whose paid/verified requirement is met")
        p.add_argument("--include-disabled", action="store_true")
        p.add_argument("--ceiling", type=float, default=None, help="override the owner ceiling in seconds (default: from platforms.json)")
        if name == "check":
            p.add_argument("--seconds", type=float, required=True)
            p.add_argument("--aspect", default=None)
    a = ap.parse_args(argv)
    try:
        reg = load(a.registry)
        if a.cmd == "list":
            for pid, p in reg.items():
                fm = ", ".join(f"{k}:{v['max_seconds']:g}s({v['confidence']})" for k, v in p["formats"].items())
                print(f"{pid:10} {'on ' if p['default_enabled'] else 'off'} india={'yes' if p['available_in_india'] else 'NO '} {fm}")
            return 0
        owner_max = a.ceiling if a.ceiling is not None else owner_limits(a.registry)[a.kind]
        kw = dict(platforms=_csv(a.platforms), tiers=_parse_tiers(a.tier), opt_in=_csv(a.opt_in) or (), allow_disabled=a.include_disabled, owner_max=owner_max)
        if a.cmd == "budget":
            b = budget(reg, a.kind, **kw)
            if b["max_seconds"] is None:
                print(f"no platform has a usable {a.kind}-form format; skipped: {b['skipped']}")
                return 1
            print(f"{a.kind}-form budget: {b['max_seconds']:g} s, limited by {b['limiting']}"
                  + (f" (owner ceiling {b['owner_ceiling']:g} s)" if b.get("owner_ceiling") else ""))
            for pid, v in sorted(b["per_platform"].items()):
                print(f"  {pid:10} {v['max_seconds']:g} s ({v['confidence']})")
            for pid, why in sorted(b["skipped"].items()):
                print(f"  {pid:10} skipped: {why}")
            return 0
        res = plan(reg, a.kind, a.seconds, a.aspect, **kw)
        bad = False
        for v in res:
            print(f"  {v['platform']:10} {v['status']:15} {'; '.join(v['reasons'])}")
            bad |= v["status"] in ("too-long", "aspect-mismatch", "unsupported", "over-owner-ceiling")
        return 1 if bad else 0
    except PlatformError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(_main())
