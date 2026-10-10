"""Where the video factory keeps its files (stdlib + PyYAML only; no network, no media tools).

Two roots, both OUTSIDE the repository and both configurable:

  workspace   generated work: jobs/YYYY/MM/<job-id>/, the SQLite ledger, research, shared-cache, recovery, reports
              VIDEO_FACTORY_WORKSPACE            default ~/Desktop/VideoFactory-Workspace
  publish     the hand-off library for external schedulers: ready/, archive/, .staging/, .state/
              VIDEO_FACTORY_PUBLISH_DIR          default ~/Desktop/Video-Publishing

Resolution order for every setting: environment variable, then config/storage.yaml, then the macOS default. Paths must be
absolute after ~ and $VARS are expanded, must not be inside the repository (or contain it), and the two roots must not
contain each other. A root that cannot be created or written to is an error; the code never falls back to the repository.

The job id is the factory's existing `content_id`. Job manifests are `manifest.json` (schema jobmanifest/1) at the job
root; paths in them are relative to the job directory and they never hold secrets or environment values.
"""
from __future__ import annotations

import contextlib
import datetime as dt
import json
import os
import re
import tempfile
import uuid
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
ENV_WORKSPACE = "VIDEO_FACTORY_WORKSPACE"
ENV_PUBLISH = "VIDEO_FACTORY_PUBLISH_DIR"
ENV_CACHE = "VIDEO_FACTORY_CACHE_DIR"
ENV_EXPORT_MODE = "VIDEO_FACTORY_EXPORT_MODE"
DEFAULT_WORKSPACE = "~/Desktop/VideoFactory-Workspace"
DEFAULT_PUBLISH = "~/Desktop/Video-Publishing"
CONFIG_FILE = REPO / "config" / "storage.yaml"
MANIFEST = "manifest.json"
MANIFEST_SCHEMA = "jobmanifest/1"
JOB_STATUSES = ("created", "running", "failed", "ready", "exported")
EXPORT_MODES = ("nested", "flat")

DEFAULT_CONFIG = {
    "workspace": None, "publish_dir": None, "cache_dir": None, "staging_dir": None,
    "export": {"mode": "nested"},
    "validation": {"require_audio": True},
    "retention": {"intermediate_days": 30, "intermediate_paths": ["temporary", "project/work-*"],
                  "failed_days": None, "staging_stale_minutes": 60},
}

_JOB_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class StorageError(RuntimeError):
    """A configured location is missing, unusable or unsafe, or an id/path is not allowed."""


# ---- configuration ------------------------------------------------------------------------------------------------

def _merge(base, over):
    out = dict(base)
    for k, v in (over or {}).items():
        out[k] = _merge(out[k], v) if isinstance(out.get(k), dict) and isinstance(v, dict) else v
    return out


def config(path=None):
    """config/storage.yaml merged over the defaults. A missing file means defaults; a malformed one is an error."""
    p = Path(path) if path else CONFIG_FILE
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else {}
    except (OSError, yaml.YAMLError) as exc:
        raise StorageError(f"cannot read {p}: {exc}") from exc
    if data is not None and not isinstance(data, dict):
        raise StorageError(f"{p} must contain a mapping")
    cfg = _merge(DEFAULT_CONFIG, data or {})
    if cfg["export"]["mode"] not in EXPORT_MODES:
        raise StorageError(f"export.mode must be one of {EXPORT_MODES}, got {cfg['export']['mode']!r}")
    return cfg


def _expand(raw, label):
    text = os.path.expandvars(os.path.expanduser(str(raw)))
    p = Path(text)
    if not p.is_absolute() or "$" in text:
        raise StorageError(f"{label} must be an absolute path (got {raw!r}); set it explicitly")
    return Path(os.path.normpath(p))


def _inside(child, parent):
    c, p = Path(os.path.realpath(child)), Path(os.path.realpath(parent))
    return c == p or p in c.parents


def _check_outside_repo(p, label):
    if _inside(p, REPO):
        raise StorageError(f"{label} {p} is inside the repository {REPO}; generated files must live outside it")
    if _inside(REPO, p):
        raise StorageError(f"{label} {p} contains the repository {REPO}; choose a dedicated folder")


def _root(env, key, default, label, cfg):
    raw = os.environ.get(env, "").strip() or cfg.get(key) or default
    p = _expand(raw, label)
    _check_outside_repo(p, label)
    return p


def workspace_root(cfg=None):
    cfg = cfg or config()
    return _root(ENV_WORKSPACE, "workspace", DEFAULT_WORKSPACE, "workspace", cfg)


def publish_root(cfg=None):
    cfg = cfg or config()
    p = _root(ENV_PUBLISH, "publish_dir", DEFAULT_PUBLISH, "publishing directory", cfg)
    w = workspace_root(cfg)
    if _inside(p, w) or _inside(w, p):
        raise StorageError(f"the publishing directory {p} and the workspace {w} must not contain each other")
    return p


def cache_root(cfg=None):
    cfg = cfg or config()
    raw = os.environ.get(ENV_CACHE, "").strip() or cfg.get("cache_dir")
    if not raw:
        return workspace_root(cfg) / "shared-cache"
    p = _expand(raw, "cache directory")
    _check_outside_repo(p, "cache directory")
    return p


def export_mode(cfg=None):
    cfg = cfg or config()
    mode = os.environ.get(ENV_EXPORT_MODE, "").strip() or cfg["export"]["mode"]
    if mode not in EXPORT_MODES:
        raise StorageError(f"export mode must be one of {EXPORT_MODES}, got {mode!r}")
    return mode


def staging_root(cfg=None):
    """Staging must be on the same filesystem as ready/ so promotion is an atomic rename, so it defaults to a hidden
    folder inside the publishing directory."""
    cfg = cfg or config()
    raw = cfg.get("staging_dir")
    if raw:
        p = _expand(raw, "staging directory")
        _check_outside_repo(p, "staging directory")
        return p
    return publish_root(cfg) / ".staging"


def jobs_root(cfg=None):
    return workspace_root(cfg) / "jobs"


def ledger_path(cfg=None):
    return workspace_root(cfg) / "ledger.db"


def ensure_dir(p, label):
    """Create `p` (one level, parent must exist) and prove it is writable. Raises StorageError with a clear message."""
    p = Path(p)
    try:
        if not p.exists():
            if not p.parent.is_dir():
                raise StorageError(f"{label} {p}: parent folder {p.parent} does not exist (is the drive mounted?)")
            p.mkdir()
        if not p.is_dir():
            raise StorageError(f"{label} {p} exists but is not a directory")
        with tempfile.NamedTemporaryFile(dir=p, prefix=".write-test-"):
            pass
    except StorageError:
        raise
    except OSError as exc:
        raise StorageError(f"{label} {p} is not writable: {exc}") from exc
    return p


def preflight(publish=True, cfg=None):
    """Validate and prepare the roots before a job runs. Returns the resolved paths. Never touches the repository."""
    cfg = cfg or config()
    out = {"workspace": ensure_dir(workspace_root(cfg), "workspace"), "jobs": None, "publish": None}
    out["jobs"] = ensure_dir(out["workspace"] / "jobs", "jobs folder")
    if publish:
        pub = ensure_dir(publish_root(cfg), "publishing directory")
        for sub in ("ready", ".staging", ".state"):
            ensure_dir(pub / sub, f"publishing {sub}")
        out["publish"] = pub
        st = staging_root(cfg)
        if st != pub / ".staging":
            ensure_dir(st, "staging directory")
        if os.stat(st).st_dev != os.stat(pub / "ready").st_dev:
            raise StorageError(f"staging {st} and {pub / 'ready'} are on different filesystems; atomic promotion needs one")
    return out


# ---- names --------------------------------------------------------------------------------------------------------

def valid_job_id(job_id):
    return isinstance(job_id, str) and bool(_JOB_ID.match(job_id)) and ".." not in job_id


def check_job_id(job_id):
    if not valid_job_id(job_id):
        raise StorageError(f"job id {job_id!r} is not allowed: use letters, digits, '.', '_' or '-' (max 128), no '..', no path separators")
    return job_id


def slugify(text, fallback="untitled", limit=80):
    """Filesystem-safe lowercase ASCII slug. Never empty, never starts or ends with '-', never contains a separator."""
    s = re.sub(r"[^a-z0-9]+", "-", str(text or "").lower()).strip("-")[:limit].strip("-")
    return s or fallback


# ---- atomic files -------------------------------------------------------------------------------------------------

def write_json_atomic(path, obj):
    """Write JSON so a reader sees the old file or the whole new one, never a partial file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2, ensure_ascii=False, sort_keys=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        with contextlib.suppress(FileNotFoundError):
            tmp.unlink()


def fsync_dir(path):
    with contextlib.suppress(OSError):
        fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


@contextlib.contextmanager
def file_lock(path):
    """Exclusive advisory lock held for the with-block (blocking). POSIX only; on other systems it is a no-op."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import fcntl
    except ImportError:                                      # pragma: no cover
        yield
        return
    with open(path, "a+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def lock_is_held(path):
    """True if another process holds the lock right now (used by cleanup so it never touches a job in use)."""
    path = Path(path)
    if not path.exists():
        return False
    try:
        import fcntl
    except ImportError:                                      # pragma: no cover
        return False
    with open(path, "a+") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            return True
        fcntl.flock(f, fcntl.LOCK_UN)
        return False


# ---- job directories ----------------------------------------------------------------------------------------------

def now_iso(now=None):
    return (now or dt.datetime.now(dt.timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")


def find_job_dir(job_id, jobs=None):
    """The existing job directory for `job_id` (the earliest if somehow two months hold it), or None."""
    check_job_id(job_id)
    root = Path(jobs) if jobs else jobs_root()
    if not root.is_dir():
        return None
    hits = sorted(p for p in root.glob(f"[0-9][0-9][0-9][0-9]/[0-1][0-9]/{job_id}") if p.is_dir())
    return hits[0] if hits else None


def job_dir(job_id, create=True, now=None, jobs=None):
    """The isolated directory for one job: jobs/YYYY/MM/<job-id>. Creates it (atomically) the first time."""
    check_job_id(job_id)
    root = Path(jobs) if jobs else jobs_root()
    found = find_job_dir(job_id, root)
    if found:
        return found
    if not create:
        raise StorageError(f"no job directory for {job_id!r}")
    when = now or dt.datetime.now(dt.timezone.utc)
    d = root / f"{when.year:04d}" / f"{when.month:02d}" / job_id
    d.parent.mkdir(parents=True, exist_ok=True)
    with contextlib.suppress(FileExistsError):               # another process may have won the race; that is fine
        d.mkdir()
    return d


def legacy_job_dir(job_id):
    """Read-only lookup of a project still in the old in-repo location. Nothing writes there any more."""
    check_job_id(job_id)
    p = REPO / "workspace" / "projects" / job_id
    return p if p.is_dir() else None


def rel(path, base):
    return Path(os.path.relpath(path, base)).as_posix()


_SECRET = re.compile(r"(?i)(\b(?:api[_-]?key|token|secret|password|passwd|authorization)\b\s*[=:]\s*(?:bearer\s+)?|bearer\s+)[A-Za-z0-9._~+/=-]{8,}|\b()(?:sk|pk|ghp|gho|xox[abp]|AKIA)[-_A-Za-z0-9]{12,}")
_SECRET_ENV = re.compile(r"(?i)(key|token|secret|password|passwd|credential)")


def scrub(text, limit=500):
    """Remove local absolute paths and anything that looks like a credential from text that goes into a manifest or sidecar."""
    s = str(text)
    s = _SECRET.sub(lambda m: (m.group(1) or "") + "[redacted]", s)
    for k, v in os.environ.items():
        if v and len(v) >= 12 and _SECRET_ENV.search(k):
            s = s.replace(v, "[redacted]")
    for p in {str(Path.home()), str(REPO)}:
        if p and p != "/":
            s = s.replace(p, "~" if p == str(Path.home()) else "<repo>")
    for fn in (workspace_root, publish_root):
        with contextlib.suppress(StorageError):
            s = s.replace(str(fn()), "<workspace>" if fn is workspace_root else "<publish>")
    return s[:limit]


# ---- job manifest -------------------------------------------------------------------------------------------------

def manifest_path(d):
    return Path(d) / MANIFEST


def read_manifest(d):
    """The job manifest, or None when absent. A manifest.json from another tool (legacy projects have one) raises
    StorageError instead of being overwritten; use `adopt` to keep it as metadata/legacy-manifest.json."""
    p = manifest_path(d)
    if not p.exists():
        return None
    try:
        m = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StorageError(f"unreadable manifest {p}: {exc}") from exc
    if not isinstance(m, dict) or m.get("schema") != MANIFEST_SCHEMA:
        raise StorageError(f"{p} is not a {MANIFEST_SCHEMA} manifest (legacy project?); run `contentos storage adopt` first")
    return m


def new_manifest(job_id, *, project_id=None, project_name=None, content_id=None, title=None, topic=None,
                 renderer=None, aspect_ratio=None, description="", tags=None, platform_targets=None, language=None,
                 kind=None, require_audio=True, now=None):
    return {
        "schema": MANIFEST_SCHEMA, "schema_version": 1, "job_id": job_id,
        "project_id": project_id, "project_name": project_name, "content_id": content_id,
        "title": title, "topic": topic, "description": description or "", "tags": list(tags or []),
        "platform_targets": list(platform_targets or []), "language": language, "kind": kind,
        "aspect_ratio": aspect_ratio, "require_audio": bool(require_audio), "renderer": renderer,
        "created_at": now_iso(now), "updated_at": now_iso(now), "status": "created",
        "artifacts": {}, "final_output": None, "validation": None, "export": None, "failure": None,
    }


def write_manifest(d, m):
    m["updated_at"] = now_iso()
    write_json_atomic(manifest_path(d), m)
    return m


def update_manifest(d, **changes):
    """Read-modify-write under a per-job lock. `artifacts` entries are merged by stage; other keys replace."""
    d = Path(d)
    with file_lock(d / ".manifest.lock"):
        m = read_manifest(d)
        if m is None:
            raise StorageError(f"no manifest in {d}")
        arts = changes.pop("artifacts", None)
        if arts:
            m["artifacts"].update(arts)
        if changes.get("status") is not None and changes["status"] not in JOB_STATUSES:
            raise StorageError(f"unknown job status {changes['status']!r}")
        m.update(changes)
        return write_manifest(d, m)


def open_job(job_id, spec, *, now=None):
    """Create the job directory and manifest on first use, or return the existing ones (resume keeps the same job).
    Metadata comes from the spec; unknown values stay None/empty rather than being invented."""
    d = job_dir(job_id, now=now)
    with file_lock(d / ".manifest.lock"):
        m = read_manifest(d)
        if m is None:
            title = spec.get("title")
            m = new_manifest(
                job_id, project_id=slugify(spec["project"], "unassigned") if spec.get("project") else "unassigned",
                project_name=spec.get("project_name"),
                content_id=slugify(spec.get("content") or title or job_id, slugify(job_id)),
                title=title, topic=spec.get("topic"), renderer=spec.get("render", "hyperframes"),
                aspect_ratio=spec.get("format", "9:16"), description=spec.get("description", ""), tags=spec.get("tags"),
                platform_targets=spec.get("platform_targets"), language=spec.get("language"), kind=spec.get("kind"),
                require_audio=spec.get("require_audio", config()["validation"]["require_audio"]), now=now)
            write_manifest(d, m)
    return d, m


def adopt(d):
    """Keep a legacy manifest.json as metadata/legacy-manifest.json and start a job manifest from it where possible."""
    d = Path(d)
    p = manifest_path(d)
    if not p.exists():
        raise StorageError(f"{d} has no manifest.json to adopt")
    try:
        read_manifest(d)
        return None                                          # already ours
    except StorageError:
        pass
    (d / "metadata").mkdir(exist_ok=True)
    keep = d / "metadata" / "legacy-manifest.json"
    if not keep.exists():
        keep.write_bytes(p.read_bytes())
    old = {}
    with contextlib.suppress(Exception):
        old = json.loads(p.read_text(encoding="utf-8"))
    job_id = d.name
    m = new_manifest(job_id, title=old.get("title") if isinstance(old.get("title"), str) else None, project_id="unassigned")
    m["content_id"] = slugify(m["title"] or job_id, slugify(job_id))
    m["status"] = "created"
    m["note"] = "adopted from a legacy project; legacy manifest kept in metadata/legacy-manifest.json"
    write_manifest(d, m)
    return m
