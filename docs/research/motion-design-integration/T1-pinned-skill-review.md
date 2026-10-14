# T1 - Pinned-skill review (HyperFrames v0.8.114)

Research note only. Nothing in the repo was changed. `config/upstream-skills.lock.json` and `.claude/skills/` are untouched.

Date: 2026-10-12. Pin: `https://github.com/heygen-com/hyperframes`, tag `v0.8.114`.

## 1. Provenance check

- `git -C $HOME/audit-scratch/t1/hf-src rev-parse HEAD` = `01c6f6004a00ecfa6e77ab4025b47a46a5e925fc`. Equals the lock commit. OK.
- Clone: one shallow clone, `--depth 1 --branch v0.8.114 --no-tags`, into scratch only. Git LFS warnings appeared for test fixtures under `packages/producer/tests/`. No skill folder contains an LFS pointer (`grep -rl git-lfs.github.com/spec skills` = 0).
- Licence at repo root: `LICENSE` is Apache License 2.0 (matches lock `license: Apache-2.0`).

## 2. How the installer works (read, not run)

Source: `contentos/upstream_skills.py` and `scripts/upstream_skills.py`.

- Skill folders: `sync` reads `<clone>/skills/<name>/` and requires `SKILL.md` there (`upstream_skills.py` `sync()`).
- Tree hash: `tree_hash()` = SHA-256 over sorted relative paths plus each file's SHA-256 bytes. Files matching `EXCLUDE` (`*.test.mjs`, `*.test.js`, `__pycache__`, `.DS_Store`) are skipped.
- Redirect flags: `--lock <path>` and `--skills-dir <path>` (`scripts/upstream_skills.py` `main()`). Both point at scratch without touching the real files.
- `sync` clones into `tempfile.TemporaryDirectory`, not the repo. It refuses if the tag's commit differs from the lock.
- Pinned hashes re-checked locally with the repo's own `tree_hash` against the scratch clone: all three match the lock (`hyperframes-core` 24231d50…, `hyperframes-animation` 39bfce44…, `hyperframes-keyframes` faebacc6…). The hashing method is therefore reproducible for this tag.

## 3. Full skill list at the tag

Folders under `skills/` (21 entries; `python-encoding.test.mjs` is a loose file, not a skill):

| Folder | Status |
|---|---|
| hyperframes-core | PINNED |
| hyperframes-animation | PINNED |
| hyperframes-keyframes | PINNED |
| embedded-captions | candidate |
| faceless-explainer | candidate |
| figma | candidate |
| general-video | candidate |
| hyperframes | candidate |
| hyperframes-audio | candidate |
| hyperframes-cli | candidate |
| hyperframes-creative | candidate |
| hyperframes-registry | candidate |
| hyperframes-studio | candidate |
| media-use | candidate |
| motion-graphics | candidate |
| music-to-video | candidate |
| pr-to-video | candidate |
| product-launch-video | candidate |
| remotion-to-hyperframes | candidate |
| slideshow | candidate |
| talking-head-recut | candidate |

18 candidates. Every folder has a `SKILL.md`.

## 4. Cross-cutting finding: most candidates phone home on use

Quoted from the skill files at the tag.

- 10 of the 18 candidates open with: "First, keep this skill fresh - confirm with the user before running: `npx hyperframes skills update <name>`." Examples: `embedded-captions/SKILL.md:14`, `faceless-explainer/SKILL.md:8`, `figma/SKILL.md:8`, `music-to-video/SKILL.md:8`, `pr-to-video/SKILL.md:8`, `product-launch-video/SKILL.md:8`, `slideshow/SKILL.md:14`, `talking-head-recut/SKILL.md:8`. `general-video/SKILL.md:18` has the same command without the header. `motion-graphics` uses the catalog and feedback commands (section 4 below), not the header.
- Scaffolding calls: `npx hyperframes init ... --skill=<name>` "checks the installed skills against the latest on GitHub" (`faceless-explainer/SKILL.md:32`, `pr-to-video/SKILL.md:47`, `product-launch-video/SKILL.md:34`).
- `hyperframes/SKILL.md:49`: `npx hyperframes@latest upgrade --project . --check` (unpinned `@latest`).
- `figma/SKILL.md:91`: usage beacon, `npx hyperframes events --sk...` ("anonymous, consent-gated").
- `motion-graphics/catalog-map.md:13`: `npx hyperframes feedback --search-miss ...` (sends feedback).

Consequence: adopting any of these skills as-is would let the agent run network commands that conflict with our no-network, no-unpinned-upgrade rules (AGENTS.md section 1). Any adoption needs those lines removed or the commands blocked, and that is an owner decision.

## 5. Per-skill assessment

Evidence is file:line from the tag. "Scripts" lists executable or script files; none were run. "Overlap" compares with `explainer-motion-craft` R1-R6 and `video-director`.

| Skill | Purpose (SKILL.md) | Files / KB | Scripts | Service / network | Licence | Overlap / R-rules | Recommend | Reason |
|---|---|---|---|---|---|---|---|---|
| hyperframes-audio | Mix audio already placed in a composition: fades, ducking, voiceover carve, `data-fx-chain` effects, `<hf-audio-group>` | 7 / 108 | `scripts/carve.mjs` (+ test) | none in SKILL.md; no bundled audio files; `npx hyperframes normalize-audio` at `references/diagnosis.md:157` (CLI, not a service) | Apache-2.0 | No R-rule conflict found. Sourcing is delegated to `/media-use` (SKILL.md:12), which we exclude | OWNER-DECIDE, leaning ADD | Covers exactly the gap the audit named: `data-fx-chain` (SKILL.md:25, :50), voiceover ducking (SKILL.md:225-233), carve config (:254-258). No keys, no `keep fresh` header. Unverified: whether `normalize-audio` exists in CLI 0.8.114 (not run) |
| hyperframes-creative | Non-animation creative direction: palettes, typography, beat planning, `frame.md`/`design.md` | 79 / 1376 | `contrast-report.mjs`, `extract-audio-data.py`, `package-loader.mjs` | `package-loader.mjs:4` runs `npm install --ignore-scripts` at runtime; `references/design-picker.md:120` starts `python3 -m http.server`; `beat-direction.md:102` `npx hyperframes add` | Apache-2.0 | Overlaps style cards (T2) and palettes; not reviewed line by line | OWNER-DECIDE | Useful content, but runtime `npm install` and overlap with T2 need a decision first |
| hyperframes-registry | Search and install blocks from the HF registry | 12 / 108 | none | `SKILL.md:94-108` `npx hyperframes catalog` / `add` (network to registry) | Apache-2.0 | Named-look lookup conflicts with our "compose from our registries" rule | EXCLUDE (default) | Network at use; our look selection is from `config/*.json` registries |
| motion-graphics | Motion-graphics categories; "compose existing catalog blocks" | 23 / 156 | `categories/maps/bake-basemap.mjs`, `grounding/locate.mjs` | `catalog-map.md:7,13,16` (catalog, feedback sends) | Apache-2.0 | Default "compose catalog blocks, not hand-author" conflicts with factory Track B (hand-authored composition) | EXCLUDE | Network feedback plus conflicting workflow |
| hyperframes | Intent-layer workflow for HF projects | 29 / 208 | `plugin-cli.mjs`, `lib/frame-packets-core.mjs` | `SKILL.md:49` `npx hyperframes@latest upgrade` (unpinned); `:91` `skills update` | Apache-2.0 | Second workflow owner over our orchestrator | EXCLUDE | Unpinned upgrade and workflow overlap |
| hyperframes-cli | CLI command reference | 11 / 144 | none | `SKILL.md:16-22` all `npx hyperframes ...` | Apache-2.0 | none | EXCLUDE (default) | Reference only; we run `./contentos.sh`. Use the pinned CLI directly if needed |
| hyperframes-studio | Desktop Studio app notes | 1 / 12 | none | none | Apache-2.0 | none | EXCLUDE | Not needed for headless pipeline |
| media-use | "Agent Media OS": BGM, SFX, image, voice, LUT resolution | 104 / 1952 | ~45 scripts incl. `heygen-tts.mjs`, `gemini-tts.mjs`, `lyria-recipe.py`, `transcribe.mjs` | HeyGen account required for free path (`SKILL.md:12`); HeyGen catalog for bgm/image (`:24`, `:26`); voice HeyGen (`:29`); Gemini key read from env (`audio/scripts/lib/gemini-auth.mjs:7-8`); `pip install` at `references/operations.md:42-43, :112` | Apache-2.0 | Sources paid/account media; conflicts with "no paid API" (AGENTS.md section 1) | EXCLUDE | HeyGen sign-in dependency; plan §2 excludes it |
| faceless-explainer | Text to faceless explainer; invents visuals per scene | 27 / 332 | 12 `.mjs` incl. `audio.mjs`, `build-frame.mjs` | HeyGen sign-in: `SKILL.md:38` "Show sign-in status ... run `npx hyperframes auth status`"; requires `/media-use` (`:10`, `:36`); `skills update` header `:8` | Apache-2.0 | Duplicates our `video-director` planning; sources via media-use | **EXCLUDE (recommended)** | HeyGen dependency is pulled in through `media-use`. Recommend exclude without a clear owner decision to accept HeyGen sign-in |
| general-video | General explainer workflow | 5 / 44 | `frame-packets.mjs` | `SKILL.md:18`, `:25` (`/media-use`), `:44` init | Apache-2.0 | Overlaps orchestrator | EXCLUDE | Workflow overlap; depends on media-use |
| embedded-captions | Caption overlay workflow | 144 / 3708 | 4 scripts (`gen-stroke-path.py`, `prepare.sh`, `render-and-composite.sh`, `render-theme.sh`) | `SKILL.md:14` skills update; `:30` `npm install` (sharp, puppeteer); `modes/standard/_anatomy.md:33` `npx hyperframes transcribe` | Apache-2.0 | Captions are already ours (Track A) | EXCLUDE | Network use, heavy install, overlaps our captions |
| figma | Import Figma into composition | 2 / 28 | `verify-motion.mjs` | `SKILL.md:8`; `:91` usage beacon; Figma connector | Apache-2.0 | none | EXCLUDE | Needs Figma connector and beacon |
| music-to-video | Beat-synced video from a track | 169 / 6428 | 6 scripts; `references/motion-primitives/assets/gsap.min.js` | `SKILL.md:8`; `:67` `python3 -m pip install librosa numpy soundfile` | Apache-2.0; **GSAP file under GreenSock standard licence** | none | EXCLUDE (not in scope) | Out of scope for explainers; pip install; vendored GSAP has its own licence |
| pr-to-video | Code-change explainer from a GitHub PR | 33 / 420 | 14 scripts incl. `fetch-pr.mjs`, `fetch-people-avatars.mjs` | `SKILL.md:53` sign-in; `:47` init checks GitHub; fetches PRs and avatars | Apache-2.0 | none | EXCLUDE | Network fetch of third-party data; out of scope |
| product-launch-video | Product URL to launch video | 34 / 396 | 13 scripts incl. `stage-assets.mjs` | `SKILL.md:40` sign-in; `:34` init checks GitHub; scrapes product URL | Apache-2.0 | none | EXCLUDE | Network scraping; out of scope |
| remotion-to-hyperframes | Port Remotion source to HF | 77 / 380 | 5 scripts; test corpus with `remotion-src` | `SKILL.md:90-91` `npx remotion render` (Remotion, excluded by plan); `:8` skills update | Apache-2.0 | Remotion excluded (plan §2) | EXCLUDE | Remotion is out of scope |
| slideshow | Slide deck composition | 2 / 80 | none | `SKILL.md:14`; `:491` `npx hyperframes present` | Apache-2.0 | Overlaps our slides | EXCLUDE | Network header; not needed |
| talking-head-recut | Overlay cards on talking-head video | 28 / 564 | none | `SKILL.md:8`; `:43-55` npx; `:102` `npx hyperframes transcribe` (local Whisper) | Apache-2.0 repo; **`NOTICE.md`: adapted from vtake-skills, MIT (leeoxiang 2026)**; `assets/vendor/gsap.min.js` under GreenSock standard licence | Talking-head is out of scope (plan §2) | EXCLUDE | Out of scope; licence notice must be kept if ever adopted |

Summary of candidates: ADD - none. OWNER-DECIDE - hyperframes-audio (leaning add), hyperframes-creative. EXCLUDE - the other 16.

## 6. Hash check of candidates (for a later adoption)

Computed locally with the repo's `tree_hash` on the scratch clone (no upstream script run):

- hyperframes-audio `d7562939efe0f36d…`
- hyperframes-creative `3b9b835cc9029a81…`
- faceless-explainer `bb83fce928103189…` (for reference, recommend EXCLUDE)

Full list of candidate hashes is in the run log entry for T1.

## 7. Not run, and why

Step 7 of the task asked for a `sync` dry run into scratch. Not done. Two reasons:

1. The task says "Do not: run any upstream script", and step 7 says the sync script clones again. The task also says network is allowed once. A second clone would break that rule.
2. The same hashes were obtained without the script, using the repo's own `tree_hash` on the clone that was already fetched. That is the same function `sync` uses.

Owner can run the dry run later if wanted: `scripts/upstream_skills.py sync --lock <copy> --skills-dir <scratch>`.

## 8. Adoption commands (for the owner; NOT run)

```
# 1. edit config/upstream-skills.lock.json -> add the skill name to sources[0].skills
# 2. record hashes for the new set (writes lock; review the diff first)
python scripts/upstream_skills.py sync --record
# 3. check
python scripts/upstream_skills.py verify
~/.contentos/venv/bin/python -m pytest tests/test_upstream_skills.py -q
# 4. owner decision: add a config/capabilities.json entry so director plans can name it
```

Rollback, important: `python scripts/upstream_skills.py remove` is NOT a rollback for one skill. It deletes every skill the lock lists, including the three pinned ones. The safe rollback for one skill is:

1. `git checkout -- config/upstream-skills.lock.json` (restore the lock from git).
2. `rm -rf .claude/skills/<skill-name>` (delete that one folder only).
3. Run `python scripts/upstream_skills.py verify` and confirm the other skills still pass.

## 9. Acceptance

- Note exists, every non-pinned skill assessed with file:line evidence: yes (section 5).
- Commit in scratch clone equals lock commit: yes (`01c6f600…`).
- Snapshot diff identical and no repo file modified: see run log.

## 10. Open questions for owner

1. hyperframes-audio: ADD for the ducking and `data-fx-chain` gap? If yes, approve the adoption steps in section 8.
2. hyperframes-creative: do you want its palettes and typography guidance, given the T2 style cards and its runtime `npm install`?
3. faceless-explainer: confirm EXCLUDE (HeyGen sign-in via media-use).
