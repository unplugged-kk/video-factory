"""Recovery of artifacts left by an interrupted pipeline attempt."""
import shutil
from pathlib import Path

from .. import ledger, storage


def scrub_interrupted(content_id, spec, project_dir=None):
    """Remove artifacts that have no completed ledger stage.

    The caller must hold the job's ``.run.lock``. Keeping lock ownership at the
    pipeline boundary prevents recovery from racing an active stage.
    """
    from .. import pipeline

    d = Path(project_dir) if project_dir else storage.find_job_dir(content_id)
    if d is None:
        return []
    with ledger.db() as c:
        done = {r[0] for r in c.execute(
            "SELECT DISTINCT stage FROM runs WHERE content_id=? AND status='OK'", (content_id,)
        )}
    removed, dirty = [], False
    for scratch in d.glob("work-*"):
        if scratch.is_dir():
            shutil.rmtree(scratch, ignore_errors=True)
            removed.append(f"render:{scratch.name}")
    for st in pipeline.STAGES:
        dirty = dirty or st not in done
        if not dirty:
            continue
        target = d / ("audio" if st == "voice" else pipeline.artifact(st, spec).replace("%02d", "01"))
        if target.is_dir():
            had_files = any(target.iterdir())
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()
            had_files = True
        else:
            continue
        if had_files:
            removed.append(f"{st}:{target.relative_to(d)}")
    return removed
