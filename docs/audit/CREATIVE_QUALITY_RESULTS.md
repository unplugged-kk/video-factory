# Creative quality results - existing fixture baseline only

Three real HyperFrames fixture renders at `cce972d`, 2026-11-24. They exercised the existing approved-test path in isolated scratch libraries; the publish stage was a dry run. No look was wired into the builder, no new creative capability was implemented, and all three fixtures are technology explainers. This is not three-niche coverage.

Evidence root: `/Users/kishore/.contentos/checkpoints/video-factory-phase2-20261124/fixture-renders/`. Each fixture directory below contains `video.mp4`, `qa.json` and `review-six/contact-sheet.png`. Six frames sampled at 1, 5, 9, 13, 17 and 21 seconds.

| Fixture directory under evidence root | Duration | Technical QA | Initial frame inspection |
|---|---:|---|---|
| `test_fixture_runs_end_to_end_m0/ws/jobs/2026/11/24/m3-sample-01-hf-sketch` | 32.5 s | 12 pass, 0 warn/fail | Hook and captions legible; mostly same card geometry and large empty areas; no visual demonstration of the event-log concept in sampled frames. |
| `test_fixture_runs_end_to_end_m1/ws/jobs/2026/11/24/m3-sample-02-hf-product` | 29.5 s | 12 pass, 0 warn/fail | Stronger panel separation, readable word highlight. Sample at 9 s is dimmer; check transition frames and reduced contrast there before accepting. Product concept still presented primarily as text. |
| `test_fixture_runs_end_to_end_m2/ws/jobs/2026/11/24/m3-sample-03-hf-spatial` | 27.6 s | 11 pass, 1 `frozen_frames` warn, 0 fail | Highly abstract text-only scenes; nearest-neighbor concept needs a picture. Strong dark/light contrast on sampled text but little composition variation. |

**Technical run:** `CONTENTOS_E2E=1 ~/.contentos/venv/bin/python -m pytest tests/test_e2e_features.py -q -rs -k 'hf-' --basetemp <evidence-root>`: exit 0, 3 passed / 3 Remotion cases deselected (184.25 s). `fixture-renders.log` and `fixture-review.log` are adjacent to the evidence root. Media stays outside Git.

**Initial creative verdict: revise, not acceptance.** Used legibility, hierarchy, visual variety and conceptual clarity on sampled frames. Captions and headlines are comfortably inside the sampled frame edges, but gradients changing behind similarly composed cards do not deliver a visually distinct treatment. These stills cannot validate cut timing, motion, music, sound effects, clip-by-clip alignment or narration quality. No independent critic or listener approved the fixtures; no formal creative score. Finance and history/documentary cases and A/B look evidence remain untested.
