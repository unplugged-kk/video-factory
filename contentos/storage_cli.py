"""`contentos storage ...`: inspect and manage the external workspace and the publishing library."""
from __future__ import annotations

import json

from . import export, handoff, storage, storage_admin


def _mb(b):
    return f"{b / 1e6:.1f} MB"


def cmd_paths(a):
    cfg = storage.config()
    print(f"workspace   {storage.workspace_root(cfg)}   (env {storage.ENV_WORKSPACE})")
    print(f"jobs        {storage.jobs_root(cfg)}")
    print(f"ledger      {storage.ledger_path(cfg)}")
    print(f"publishing  {storage.publish_root(cfg)}   (env {storage.ENV_PUBLISH})")
    print(f"staging     {storage.staging_root(cfg)}")
    print(f"cache       {storage.cache_root(cfg)}")
    print(f"export mode {storage.export_mode(cfg)}")
    if a.check:
        paths = storage.preflight(publish=True, cfg=cfg)
        print("OK: both roots exist and are writable" if paths["publish"] else "OK")
    return 0


def cmd_inventory(a):
    items = storage_admin.inventory()
    print(json.dumps(items, indent=2) if a.json else storage_admin.format_inventory(items))
    return 0


def cmd_migrate(a):
    log = storage_admin.migrate(apply=a.apply, include_active=a.include_active)
    for r in log["results"]:
        print(f"{r['status']:22} {r['path']} -> {r['destination']}" + (f"   ({r['note']})" if r["note"] else ""))
    if a.apply:
        print(f"log: {log.get('log_file')}")
    else:
        print("dry run: nothing was copied. Re-run with --apply to copy (originals are never moved or deleted).")
    return 1 if any(r["status"] == "FAILED" for r in log["results"]) else 0


def cmd_adopt(a):
    d = storage.find_job_dir(a.job_id)
    if d is None:
        print(f"no job directory for {a.job_id!r}")
        return 2
    m = storage.adopt(d)
    print("already a job manifest" if m is None else f"adopted: legacy manifest kept in metadata/legacy-manifest.json; set title/project in {d.name}/manifest.json before exporting")
    return 0


def cmd_export(a):
    try:
        r = export.export_job(a.job_id, force=a.force, mode=a.mode)
    except storage.StorageError as exc:
        print(f"not exported: {exc}")
        return 1
    print(f"{r['status']}: {r['video']}\n  sidecar: {r['sidecar']}")
    return 0


def cmd_ready(a):
    entries, problems = handoff.discover(storage.publish_root(), project=a.project, status=a.status)
    for e in entries:
        print(f"{e['effective_status']:10} {e.get('project_id')}  {e['job_id']}  {e['video_path']}")
    for p in problems:
        print(f"PROBLEM {p['sidecar']}: {p['problem']}")
    print(f"{len(entries)} video(s), {len(problems)} problem(s)")
    superseded = []
    if a.check:                                          # read-only: compares each workspace video with its sidecar sha
        rep = export.divergence()
        for r in rep["superseded"]:
            superseded.append(r["job_id"])
            print(f"SUPERSEDED  {r['job_id']}  workspace {str(r['workspace_sha256'])[:12]} != exported "
                  f"{str(r['exported_sha256'])[:12]}  ({r['exported_video']})")
        for r in rep["sidecar_missing"]:
            print(f"NO-SIDECAR  {r['job_id']}  ({r['exported_video']})")
        for r in rep["workspace_video_missing"]:
            print(f"NO-VIDEO    {r['job_id']}  ({r['exported_video']})")
        for name in rep["unreadable_manifest"]:
            print(f"UNREADABLE  {name}")
        print(f"integrity: {rep['checked']} exported, {len(rep['ok'])} matching, {len(superseded)} superseded, "
              f"{len(rep['archived'])} archived, {len(rep['workspace_video_missing'])} without a workspace video")
        if superseded:
            print("a superseded job's workspace video differs from what was exported; "
                  "re-export it with `contentos storage export <job> --force` if the new render is the one to ship")
    return 1 if (problems or superseded) else 0


def cmd_cleanup(a):
    r = storage_admin.cleanup(apply=a.apply)
    for c in r["candidates"]:
        print(f"{'removed' if a.apply else 'would remove':13} {c['job']}/{c['path']}  {_mb(c['bytes'])}")
    for s in r["skipped"]:
        print(f"skipped       {s['job']}: {s['reason']}")
    print(f"{_mb(r['bytes'])} {'freed' if a.apply else 'reclaimable (dry run; pass --apply to delete)'}")
    return 0


def cmd_recover(a):
    r = export.recover(apply=a.apply)
    for n in r["stale_staging"]:
        print(f"{'removed' if a.apply else 'stale staging':14} {n}")
    for n in r["orphan_videos"]:
        print(f"{'quarantined' if a.apply else 'orphan video':14} {n}")
    if not r["stale_staging"] and not r["orphan_videos"]:
        print("nothing to recover")
    elif not a.apply:
        print("dry run; pass --apply to clean up")
    return 0


def register(sp):
    s = sp.add_parser("storage", help="external workspace and publishing library: paths, inventory, migrate, export, ready, cleanup, recover")
    sub = s.add_subparsers(dest="scmd", required=True)
    p = sub.add_parser("paths"); p.add_argument("--check", action="store_true", help="also create and test-write both roots"); p.set_defaults(f=cmd_paths)
    p = sub.add_parser("inventory"); p.add_argument("--json", action="store_true"); p.set_defaults(f=cmd_inventory)
    p = sub.add_parser("migrate", help="copy old in-repo artifacts to the workspace (dry run unless --apply; never deletes)")
    p.add_argument("--apply", action="store_true"); p.add_argument("--include-active", action="store_true"); p.set_defaults(f=cmd_migrate)
    p = sub.add_parser("adopt"); p.add_argument("job_id"); p.set_defaults(f=cmd_adopt)
    p = sub.add_parser("export", help="validate a job's final video and export it to ready/")
    p.add_argument("job_id"); p.add_argument("--force", action="store_true"); p.add_argument("--mode", choices=storage.EXPORT_MODES); p.set_defaults(f=cmd_export)
    p = sub.add_parser("ready", help="list exported videos"); p.add_argument("--project"); p.add_argument("--status")
    p.add_argument("--check", action="store_true", help="also report jobs whose workspace video no longer matches what was exported (read-only)")
    p.set_defaults(f=cmd_ready)
    p = sub.add_parser("cleanup", help="remove expired scratch paths (dry run unless --apply)"); p.add_argument("--apply", action="store_true"); p.set_defaults(f=cmd_cleanup)
    p = sub.add_parser("recover", help="find leftovers of an interrupted export (dry run unless --apply)"); p.add_argument("--apply", action="store_true"); p.set_defaults(f=cmd_recover)
