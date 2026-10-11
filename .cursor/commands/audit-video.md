Audit a finished video. Read-only: no re-render, no export, no edits to sidecars.

Read `AGENTS.md` first. The target is what I typed after the command: a `video.mp4`, a job folder under
`$VIDEO_FACTORY_WORKSPACE/jobs/YYYY/MM/<job-id>/`, or an entry in the publishing library. If I typed
nothing, find the most recent job under the workspace and tell me which one you picked.

Run, in order, and keep the raw output:

1. `./contentos.sh qa <video>` — report every check with its status, including the ones that WARN
   (`frozen_frames` on text slides is expected, `loudness` near the edge is worth a sentence).
2. `./contentos.sh preview <video> --at 2,10,30 --out <workspace dir> --sheet`, then actually look at the
   frames at phone size and describe what you see, not just what the log said.
3. If a `timeline/1` file exists for the job:
   `python -m contentos.production.sheet <video> <timeline.json> -o <dir>` for timeline-labelled tiles
   (new and in shadow mode; it fails closed when it cannot draw labels). On this Mac expect that failure:
   the homebrew ffmpeg has no `drawtext`, so report it once and fall back to `preview --sheet` above — do
   not reach for `--allow-unlabelled` to get past it, and do not treat the fallback sheet as equivalent
   when the labels are the point of the audit.
4. Rendered-frame gate for what lint cannot see:
   `python -m contentos.production.visual_gate layers <target>`,
   `... captions <video>`,
   `... transitions <video> --at <seconds>` (repeat `--at` per cut), `... log <render log>`.
5. Apply the `explainer-visual-qa` skill and score the video as an **independent** critic — you did not
   build it, so you write the report. Validate it with
   `python -m contentos.production.critic report.json`; a `reject` or `revise` verdict means it goes back to
   the builder, and the report is never edited by the person being graded.

Report: the verdict and what drove it, the QA table, the visual findings with the frame time for each, the
single fix you would make first, and anything you could not check with the tools available. If the video is
an exported final, also state whether its `.publish.json` sidecar is present and consistent — but do not
touch it.
