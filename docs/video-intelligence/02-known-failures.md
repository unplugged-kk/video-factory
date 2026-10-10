# Known failures (with evidence)

## KF-001 `npx --no-install hyperframes` fails from a job folder outside the repo
- **When:** after jobs moved to `$VIDEO_FACTORY_WORKSPACE` (external storage). `compose` and `render` run with the job's `project/` as working directory; `npx` there cannot see the repo's `node_modules` and tries to fetch another version (0.8.145) from the network; PATH-prepending did not help.
- **Evidence:** `node_modules/.bin/hyperframes --version` prints 0.8.114 from any folder; bare `npx` does not resolve it.
- **Fix (commit 045b570):** `contentos/hf.py` calls `node_modules/.bin/hyperframes` by absolute path (`HYPERFRAMES_BIN` overrides, `npx` is only a fallback when nothing is installed). Pipeline, preview and `motion_compare.py` use it. Test: `tests/test_hf.py`.

## KF-002 Videos share one backdrop
- **Within a video:** Pilot 001 portrait master, 7 scenes: `visual scenes` measures 1 distinct backdrop (needs 4). Ep3 is one continuous `#root` canvas by construction.
- **Across videos:** Ep3 vs Pilot 001: identical on structure (radial), temperature (cool), texture (grid), base (hue 7, dark) and accent families (amber + teal/cyan), so 0 of 5 fields differ (needs 2). Ep2 differs on all five.
- **Status:** detected by Rule A / Rule B; not yet fixed in Ep3 (it is the evidence case). Fixing means changing its backdrop treatment and re-running the critic.
- **Reproduce:** `python -m contentos.intelligence.visual check <ep3 project dir> --as ep3-what-is-generative-ai` (exit 1); `... visual scenes <mp4> --timing <scene-plan.resolved.json>`.

## KF-003 Migration skips the ledger when a new one already exists
- **When:** `contentos storage migrate --apply` reported `workspace/ledger.db: destination already exists; nothing overwritten`, because a `contentos` command had already created an empty ledger in the new workspace.
- **Effect:** old run history and approvals were not copied.
- **Mitigation:** check both ledgers' row counts; if the new one is empty, move it aside and re-run the migration (see docs/STORAGE.md section 10). The migration deliberately never overwrites.
