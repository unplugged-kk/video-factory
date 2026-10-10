# Storage: external workspace and the publishing library

Generated work no longer lives in the Git repository. There are two folders **outside** the repo:

| Folder | Default | Env var | Holds |
|---|---|---|---|
| Workspace | `~/Desktop/VideoFactory-Workspace` | `VIDEO_FACTORY_WORKSPACE` | everything the factory generates: audio, scenes, renders, logs, the ledger |
| Publishing library | `~/Desktop/Video-Publishing` | `VIDEO_FACTORY_PUBLISH_DIR` | only validated final videos plus a small JSON sidecar each. The hand-off point for schedulers. |

Git holds code, config, docs and tests only. `*.mp4 *.wav *.mp3 …` and both folder names are in `.gitignore` as a second line of defence.

## 1. Architecture

```
 ContentOS pipeline                              Scheduler / uploader (external, not part of this repo)
 brief script voice compose render qa package            │
        │  (all intermediates)                           │ reads ready/, claims, schedules, archives
        ▼                                                ▼
 VideoFactory-Workspace  ── export stage ──►  Video-Publishing/ready/<project>/YYYY/MM/<content>__<job>.mp4
 jobs/YYYY/MM/<job-id>/      validate +                                                  <content>__<job>.publish.json
                             stage + atomic promote
```

Four identities are kept apart: **project** (channel/series, `project_id`), **content** (the piece, `content_id` slug), **job** (one production run, `job_id` = the existing `content_id` the ledger already uses), **destination** (platform targets, listed in the sidecar, never in file names). All names are safe slugs; job ids must match `[A-Za-z0-9][A-Za-z0-9._-]{0,127}` and cannot contain `..` or separators.

## 2. Layout

```
VideoFactory-Workspace/
  ledger.db                       SQLite ledger (was workspace/ledger.db)
  jobs/2026/10/<job-id>/          one isolated folder per job
    manifest.json                 job record (schema jobmanifest/1)
    audio/ project/ video.mp4 qa.json metadata.yaml content.json export-result.json …
    temporary/                    scratch; the only thing cleanup may remove
  shared-cache/                   optional reusable downloads/models (VIDEO_FACTORY_CACHE_DIR)
  recovery/                       migration logs, copied legacy folders
  research/ experiments/ reports/ created on first use (no empty speculative folders)

Video-Publishing/
  ready/<project>/2026/10/<content>__<job>.mp4
  ready/<project>/2026/10/<content>__<job>.publish.json     ← written LAST; it is the "ready" marker
  archive/<project>/2026/10/…     after a scheduler records "published" and archives
  .staging/                       in-flight copies (same filesystem as ready/ so promotion is atomic)
  .state/exports/ locks/ claims/ orphans/
```

Flat mode (`VIDEO_FACTORY_EXPORT_MODE=flat`, or `export.mode: flat`) puts files directly in `ready/` for schedulers that want one folder.

## 3. Configuration

Precedence: environment variable > `config/storage.yaml` > default. Paths must be absolute (`~` and `$VARS` are expanded).

| Setting | Env | Notes |
|---|---|---|
| workspace | `VIDEO_FACTORY_WORKSPACE` | must be outside the repo |
| publish_dir | `VIDEO_FACTORY_PUBLISH_DIR` | outside the repo; must not contain or sit inside the workspace |
| cache_dir | `VIDEO_FACTORY_CACHE_DIR` | default `<workspace>/shared-cache` |
| staging_dir | – | default `<publish>/.staging`; must be on the same filesystem as `ready/` |
| export.mode | `VIDEO_FACTORY_EXPORT_MODE` | `nested` (default) or `flat` |
| validation.require_audio | – | per job: `require_audio: false` in the spec |
| retention.* | – | see §9 |

**No silent fallback.** If a folder is missing, not writable, relative, or inside the repo, the run stops with a clear `StorageError` before any work starts. Nothing is ever created inside the repository instead.

Check your setup: `./contentos.sh storage paths --check`.

## 4. Job lifecycle

`created → running → ready → exported`, or `failed` at any point. Stage state transitions and retry rules of the pipeline are unchanged; the manifest is a record, never a gate. A job spec may add (all optional, nothing is invented when absent): `project`, `project_name`, `content`, `topic`, `description`, `tags`, `platform_targets`, `language`, `kind` (`short`/`long`), `require_audio`.

The pipeline gained one stage, `export`, between `package` and `publish`. It is idempotent: re-running it for the same video returns `already_exported` and changes nothing.

## 5. Export procedure and guarantees

Under a per-job lock (safe across threads and processes):

1. Already exported with the same checksum → return `already_exported`.
2. A different video for the same job → refused unless `--force`; refused outright if a scheduler already claimed it, or if the job was archived.
3. Validate the final video (§6). Failure → manifest `failed`, nothing leaves the workspace.
4. Copy into `.staging/`, fsync, verify size and SHA-256.
5. Write the sidecar into staging, then `os.replace` the **video first, sidecar last**.
6. Verify the promoted file, record the export in the manifest and `.state/exports/`, remove staging.

Any failure removes staging and anything this call promoted. A video without a sidecar is by contract not ready and is invisible to `discover()`. `contentos storage recover` lists (dry-run) or quarantines orphans and stale staging; it never deletes a video.

## 6. Final-video validation

`contentos/finalcheck.py` reuses `qa.run_qa` (resolution for the declared format, fps, max duration, audio track, loudness, clipping, black and frozen frames) and adds file-exists / non-empty / readable / duration > 0. Any `FAIL` → not exported. `WARN` (for example loudness off-target, frozen text slide) is recorded but allowed. Missing ffprobe/ffmpeg counts as failed: an unvalidated video is never exported. The result is stored in the manifest and summarised in the sidecar.

## 7. Sidecar schema (`*.publish.json`, `schema_version: 1`)

Required: `schema_version, project_id, content_id, job_id, video_filename, video_sha256, video_bytes, created_at, exported_at, validation_status, publishing_status`.
Optional (null/empty when unknown, never guessed): `project_name, title, description, platform_targets[], tags[], language, format (short|long), aspect_ratio, duration_seconds, validation{status,checked_at,checks[{check,status}]}, scheduled_at, published_at`.
The sidecar contains only a bare `video_filename` (it sits next to the video), no absolute paths, no credentials. It is written once and never rewritten.

## 8. Scheduler contract (`contentos/handoff.py`)

The factory owns `ready/` and the sidecar. A scheduler owns `.state/claims/<job>.json`. Scheduling state never flows back into factory job state.

```python
from contentos import handoff
entries, problems = handoff.discover(pub_dir, project="…", platform="…", fmt="short", language="en")
handoff.claim(pub_dir, job_id, "my-scheduler")             # exclusive; second claimant gets AlreadyClaimed
handoff.transition(pub_dir, job_id, "scheduled", "my-scheduler")   # ready→claimed→scheduled→published | failed→ready
handoff.archive(pub_dir, job_id)                            # moves to archive/ (only after published, or force)
```

CLI: `python -m contentos.handoff list|claim|transition|archive|status`. Any language can instead read `ready/**/*.publish.json` directly: a video is ready iff its sidecar exists and `video_bytes` matches the file (`video_sha256` for a full check). `discover` reports incomplete or tampered entries in `problems` instead of returning them. Archiving is not publishing: `published_at` is set only by a `published` transition.

## 9. Retention and cleanup

Nothing is deleted automatically. `./contentos.sh storage cleanup` is a **dry run**; `--apply` deletes. Only `retention.intermediate_paths` (default `temporary`, `project/work-*`) of jobs whose status is `exported` and older than `intermediate_days` (30) are candidates. Skipped: the final video, failed jobs (unless you set `failed_days`), jobs with a `.keep` file, jobs queued/running/blocked in the ledger, jobs whose lock is held, legacy manifests, and anything resolving outside the job folder (symlinks).

## 10. Migration from the old in-repo layout

```
./contentos.sh storage inventory          # read-only: what exists, size, git-tracked?, ledger references, risks
./contentos.sh storage migrate            # DRY RUN
./contentos.sh storage migrate --apply    # copy + verify
./contentos.sh storage adopt <job-id>     # for jobs with their own manifest.json (e.g. Pilot 001)
```

Stop workers first. `--apply` **copies** (never moves or deletes), verifies each tree by file count, size and digest, copies `ledger.db` with the SQLite backup API, skips jobs that are active in the ledger (`--include-active` overrides), never overwrites an existing destination, and writes a log to `<workspace>/recovery/migrations/`. Old folders stay where they are until you delete them yourself after checking. Legacy repo-root folders (`output/ state/ done/ …`) are copied to `recovery/legacy-root/`; `reference/stale-july-2025-artifacts` is left alone. Foreign manifests are kept: `adopt` stores the original as `metadata/legacy-manifest.json` and starts a job manifest. Dashboard, learn and research read both locations, so nothing breaks mid-migration.

**If `ledger.db` is reported as skipped** ("destination already exists"), a command already created an empty ledger in the workspace. Compare row counts in both (`select count(*) from runs`), and if the new one is empty move it aside (`mv ledger.db ledger.db.empty-bak`) and run `migrate --apply` again. See docs/video-intelligence/02-known-failures.md (KF-003).

**Recovery / undo:** originals are untouched, so undo = delete the copies under the workspace (listed in the migration log) and unset the env vars.

## 11. Recovery and troubleshooting

| Symptom | Action |
|---|---|
| `storage … is not writable` / `must be an absolute path` | fix the env var or folder; re-run `storage paths --check` |
| Export interrupted | re-run `storage export <job>` (idempotent); `storage recover` for leftovers |
| Video in `ready/` with no sidecar | `storage recover --apply` quarantines it to `.state/orphans/` |
| Export refused: failed validation | open `manifest.json` → `validation.checks`, fix the render, re-run |
| Wrong video already exported | `storage export <job> --force` (unless claimed/archived) |
| mpt container cannot see clips | recreate it: the compose override now mounts `$VIDEO_FACTORY_WORKSPACE/jobs` |

## 12. Example trees

```
Video-Publishing/
  ready/ai-explained/2026/10/
    what-happens-when-an-ai-agent-uses-a-tool__ep1-agent-tool-use.mp4
    what-happens-when-an-ai-agent-uses-a-tool__ep1-agent-tool-use.publish.json
  archive/ai-explained/2026/09/…
  .state/{exports,claims,locks,orphans}/   .staging/
```

## 13. Commands

```
./contentos.sh storage paths --check | inventory | migrate [--apply] | adopt <id> | export <id> [--force] [--mode flat]
./contentos.sh storage ready [--project P] [--status S] | cleanup [--apply] | recover [--apply]
./contentos.sh pipeline run examples/youtube-short.yaml        # now ends with the export stage
```
