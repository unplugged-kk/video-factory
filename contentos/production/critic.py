"""Structured, independent visual-critic report for a rendered explainer.

A critic is a SEPARATE agent (or person) that did not build the video. It sees contact sheets / frames and the brief and
returns one JSON report. This module only checks that the report is well-formed and computes the verdict from the scores
so a builder cannot grade its own work by editing a number or the verdict text. It never looks at pixels.

The rubric shape (scored dimensions + named hard failures + pass thresholds) is adapted from the scored critic in
Liamrjohnston/remotion-motion-graphics-skill (MIT), re-written for narrated explainers. The thresholds are PROVISIONAL:
they are not calibrated against human judgement yet; tune them after a few reviewed videos."""
from __future__ import annotations

DIMENSIONS = (
    "hook_clarity",          # the first seconds state the value in the viewer's language
    "concept_specificity",   # visuals could only belong to this subject; traceable to the script/source
    "readability",           # essential text and the focal action are legible at phone size
    "composition",           # hierarchy, framing, safe zones, no clipping or dead space
    "motion_causality",      # motion explains cause -> effect; nothing moves only to be 'alive'
    "continuity",            # one persistent world; no snaps/pops at cuts; transitions carry meaning
    "av_sync",               # reveals and captions land on the spoken words
    "restraint",             # no decorative effects competing with the subject
)
HARD_FAILURES = (
    "fabricated_data_unlabeled",    # invented UI/metrics/results presented as real
    "text_clipped_or_unreadable",
    "caption_out_of_sync",
    "brand_mark_misuse",            # logos/likenesses used without rights or redrawn
    "claim_unverified",             # factual claim not backed by the research notes
    "dead_or_black_frames",
    "generic_template_look",        # could be any topic's video with the words swapped
)
VERDICTS = ("pass", "revise", "reject")
MIN_EACH, MIN_AVG = 7, 8.0       # provisional


def validate(report: dict) -> list[str]:
    """Problems with the report's shape (empty list = well-formed)."""
    p = []
    if report.get("critic") != "independent":
        p.append("critic must be 'independent' (a reviewer that did not build the video)")
    scores = report.get("scores")
    if not isinstance(scores, dict):
        p.append("scores must be an object")
        scores = {}
    for d in DIMENSIONS:
        v = scores.get(d)
        if isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= 10:
            p.append(f"score {d!r} must be an integer 0-10")
    for extra in set(scores) - set(DIMENSIONS):
        p.append(f"unknown score dimension {extra!r}")
    hf = report.get("hard_failures", [])
    if not isinstance(hf, list):
        p.append("hard_failures must be a list")
    else:
        p.extend(f"unknown hard failure {h!r}" for h in hf if h not in HARD_FAILURES)
    if report.get("verdict") not in VERDICTS:
        p.append(f"verdict must be one of {VERDICTS}")
    notes = report.get("notes", [])
    if not isinstance(notes, list) or any(not isinstance(n, dict) or "issue" not in n for n in notes):
        p.append("notes must be a list of objects with an 'issue' field (optional 'time_s')")
    return p


def verdict(report: dict, min_each: int = MIN_EACH, min_avg: float = MIN_AVG) -> str:
    """Verdict computed from the scores: any hard failure -> reject; any low score or low average -> revise; else pass."""
    if report.get("hard_failures"):
        return "reject"
    s = [report["scores"][d] for d in DIMENSIONS]
    if min(s) < min_each or sum(s) / len(s) < min_avg:
        return "revise"
    return "pass"


def check(report: dict, **kw) -> dict:
    """Validate, compute the verdict, and flag a claimed verdict that disagrees with the scores."""
    problems = validate(report)
    if problems:
        return {"ok": False, "problems": problems}
    computed = verdict(report, **kw)
    mismatch = computed != report["verdict"]
    return {"ok": not mismatch, "computed_verdict": computed, "claimed_verdict": report["verdict"],
            "problems": [f"claimed verdict {report['verdict']!r} but scores imply {computed!r}"] if mismatch else []}


if __name__ == "__main__":      # python -m contentos.production.critic report.json   (exit 0 only when well-formed and consistent)
    import json
    import sys

    out = check(json.loads(open(sys.argv[1]).read()))
    print(json.dumps(out, indent=1))
    sys.exit(0 if out["ok"] else 1)
