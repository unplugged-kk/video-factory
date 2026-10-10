# Experiments

Status: the registry/runner (`experiment.py`) is planned (slice 2). The discipline applies now; record results in `<workspace>/intelligence/experiments/` as JSON (`templates/experiment.example.json`).

Categories: A script/hook, B voice/audio, C motion graphics, D visual identity, E pipeline/tooling.
Discipline: one major variable; same script, audio, plan, assets, resolution, fps and renderer for both arms; cheap checks before expensive renders; repeat noisy measurements; judges are independent and told neither arm; **stopping rule written before running** (for example "one pair; repeat once only if the timing difference reverses").
Use existing instruments: `scripts/motion_compare.py` (prepare/build/render/measure/frames/report), `motion_audit`, the critic, `visual scenes`.
What an outcome may claim: counted measurements (seconds, bytes, pops) and reviewer findings. It may not claim audience impact. Honest limits to state: frame differences between arms are visible to reviewers, so "blind" is partial; n=1 is a smoke test, not proof.
Decision values: `adopt` (changes the default), `reject`, `investigate` (needs more evidence). A single run supports at most `experimental` confidence. A failed experiment never replaces a proven workflow.
