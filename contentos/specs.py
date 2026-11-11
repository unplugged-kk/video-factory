"""Validation and workspace-only persistence for Creator Studio Track A specs."""
from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

import yaml

from . import storage
from .production import platforms

VOICE_IDS_FILE = Path(__file__).with_name("kokoro_voice_ids.json")
KOKORO_VOICE_IDS = frozenset(json.loads(VOICE_IDS_FILE.read_text(encoding="utf-8")))
TOP_LEVEL_FIELDS = frozenset({
    "content_id", "title", "format", "voice", "script", "render", "kind", "platform_targets", "language",
})
SCRIPT_LINE_FIELDS = frozenset({"say", "headline", "tag", "lang", "voice"})
FORMATS = frozenset({"9:16", "16:9"})
WORDS_PER_SECOND = 2.5
_WORD = re.compile(r"\b[\w]+(?:['’\-][\w]+)*\b", re.UNICODE)


class SpecError(RuntimeError):
    """Base class for safe spec operations."""


class SpecValidationError(SpecError):
    def __init__(self, errors: list[dict[str, str]]):
        self.errors = errors
        super().__init__("spec is invalid")


class SpecCollisionError(SpecError):
    """The content id already names a different saved spec."""


def _error(errors: list[dict[str, str]], path: str, message: str) -> None:
    errors.append({"path": path, "message": message})


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_spec(spec: Any) -> dict[str, Any]:
    """Return a machine-friendly validation report without changing the input."""
    errors: list[dict[str, str]] = []
    word_count = 0

    if not isinstance(spec, dict):
        _error(errors, "$", "spec must be a mapping")
        return _report(errors, word_count)

    for field in sorted((field for field in spec if field not in TOP_LEVEL_FIELDS), key=str):
        _error(errors, str(field), "field is not supported by the Track A creator")

    content_id = spec.get("content_id")
    if not _non_empty_string(content_id):
        _error(errors, "content_id", "content_id is required")
    elif not storage.valid_job_id(content_id):
        _error(
            errors,
            "content_id",
            "must match [A-Za-z0-9][A-Za-z0-9._-]{0,127} and must not contain '..'",
        )

    if not _non_empty_string(spec.get("title")):
        _error(errors, "title", "title is required")

    if spec.get("format") not in FORMATS:
        _error(errors, "format", "must be 9:16 or 16:9")

    voice = spec.get("voice")
    language = spec.get("language", "en")
    if language not in ("en", "hi", "hi-en", "or", "auto"):
        _error(errors, "language", "must be en, hi, hi-en, or or auto")
    elif language == "en" and all(ln.get("lang", "en") == "en" for ln in spec.get("script", []) if isinstance(ln, dict)):
        if not _non_empty_string(voice):
            _error(errors, "voice", "voice is required")
        elif voice not in KOKORO_VOICE_IDS:
            _error(errors, "voice", f"Kokoro voice id {voice!r} is not in the factory allowlist")
    else:                                              # other languages: the voice is a profile of the routed backend (or omitted)
        from .lang import router as _lr
        from .lang.errors import LangError
        try:
            for ln in [{}] + [l for l in spec.get("script", []) if isinstance(l, dict)]:
                _lr.resolve(spec, ln)
            from .lang import script as _ls
            for i, ln in enumerate(l for l in spec.get("script", []) if isinstance(l, dict)):
                if _lr.resolve(spec, ln).language != "en" or spec.get("language") == "auto":
                    for p in _ls.validate(_lr.resolve(spec, ln).language, [str(ln.get("say", ""))]):
                        _error(errors, f"script[{i}].say", p)
        except LangError as exc:
            _error(errors, "language", str(exc))

    render = spec.get("render", "hyperframes")
    if render != "hyperframes":
        _error(errors, "render", "MVP render must be hyperframes")

    kind = spec.get("kind", "short")
    if kind not in platforms.KINDS:
        _error(errors, "kind", f"must be one of {', '.join(sorted(platforms.KINDS))}")

    targets = spec.get("platform_targets")
    if targets is not None and (not isinstance(targets, list) or not targets):
        _error(errors, "platform_targets", "select at least one platform")
    elif targets is not None and not all(_non_empty_string(target) for target in targets):
        _error(errors, "platform_targets", "platform targets must be non-empty strings")
    elif targets is not None:
        try:
            known = platforms.load()
        except platforms.PlatformError as exc:
            _error(errors, "platform_targets", f"platform registry is unavailable: {exc}")
        else:
            unknown = sorted(set(targets) - set(known))
            if unknown:
                _error(errors, "platform_targets", f"unknown platform target(s): {', '.join(unknown)}")
            if len(targets) != len(set(targets)):
                _error(errors, "platform_targets", "platform targets must not contain duplicates")

    script = spec.get("script")
    if not isinstance(script, list) or not script:
        _error(errors, "script", "script must contain at least one line")
    else:
        for index, line in enumerate(script):
            path = f"script[{index}]"
            if not isinstance(line, dict):
                _error(errors, path, "script line must be a mapping")
                continue
            for field in sorted((field for field in line if field not in SCRIPT_LINE_FIELDS), key=str):
                _error(errors, f"{path}.{field}", "field is not supported by the Track A creator")
            say = line.get("say")
            if not _non_empty_string(say):
                _error(errors, f"{path}.say", "say is required")
            else:
                word_count += len(_WORD.findall(say))
            for field in ("headline", "tag"):
                if field in line and not _non_empty_string(line[field]):
                    _error(errors, f"{path}.{field}", f"{field} must be a non-empty string")

    return _report(errors, word_count)


def _report(errors: list[dict[str, str]], word_count: int) -> dict[str, Any]:
    return {
        "ok": not errors,
        "errors": errors,
        "narration": {
            "word_count": word_count,
            "estimated_seconds": round(word_count / WORDS_PER_SECOND, 1),
            "words_per_second": WORDS_PER_SECOND,
        },
    }


def load_spec(path: str | os.PathLike[str]) -> Any:
    """Load YAML for validation; this function never writes beside the input."""
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def save_spec(spec: Any) -> Path:
    """Atomically save a valid spec beneath the configured workspace.

    The destination is always derived from ``content_id``. Existing identical
    content is an idempotent success; different content is a collision.
    """
    report = validate_spec(spec)
    if not report["ok"]:
        raise SpecValidationError(report["errors"])

    root = storage.workspace_root()
    specs_dir = root / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)
    if specs_dir.is_symlink():
        raise SpecError("workspace specs directory must not be a symlink")
    destination = specs_dir / f"{spec['content_id']}.yaml"

    if destination.is_symlink():
        raise SpecCollisionError(f"saved spec for {spec['content_id']!r} must not be a symlink")
    if destination.exists():
        return _resolve_existing(destination, spec)

    text = yaml.safe_dump(spec, sort_keys=False, allow_unicode=True)
    fd, temporary_name = tempfile.mkstemp(prefix=".spec-", suffix=".yaml", dir=specs_dir)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, destination)
        except FileExistsError:
            return _resolve_existing(destination, spec)
        return destination
    finally:
        temporary.unlink(missing_ok=True)


def _resolve_existing(destination: Path, spec: dict[str, Any]) -> Path:
    if destination.is_symlink():
        raise SpecCollisionError(f"saved spec for {spec['content_id']!r} must not be a symlink")
    try:
        existing = yaml.safe_load(destination.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise SpecCollisionError(f"cannot compare existing spec for {spec['content_id']!r}") from exc
    if existing == spec:
        return destination
    raise SpecCollisionError(f"content_id {spec['content_id']!r} already has a different saved spec")
