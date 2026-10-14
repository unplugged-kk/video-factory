# T1 — Review official skills inside the existing HyperFrames pin (research note; no repo change)

**Why:** the pinned tag `v0.8.114` (commit `01c6f6004a00ecfa6e77ab4025b47a46a5e925fc`) contains official skills (e.g. `hyperframes-audio`) that our lock file does not list. Adding them is low-risk **only after** we know their licence, files, scripts and any service dependency.
**Prereq:** T0 CLEARED (or owner explicitly allows this read-only task).
**You create:** `docs/research/motion-design-integration/T1-pinned-skill-review.md` (the note) and scratch files under `$HOME/audit-scratch/t1/`.
**You modify:** nothing in the repo. **You do not change** `config/upstream-skills.lock.json`, `.claude/skills/`.
**Network:** allowed **once**, to `https://github.com/heygen-com/hyperframes`, into `$HOME/audit-scratch/t1/` only.

## Steps

1. Snapshot: `bash $HOME/audit-scratch/snapshot.sh $HOME/audit-scratch/before-T1.txt`.
2. Read `contentos/upstream_skills.py` and `scripts/upstream_skills.py`. Write down (in your note): how `sync` finds skill folders inside the clone (the sub-path), how the tree hash is computed, and which flags (`--lock`, `--skills-dir`) let you redirect to scratch.
3. Clone into scratch (never into the repo):
   ```bash
   mkdir -p $HOME/audit-scratch/t1 && cd $HOME/audit-scratch/t1
   git clone --depth 1 --branch v0.8.114 --no-tags https://github.com/heygen-com/hyperframes hf-src
   git -C hf-src rev-parse HEAD     # must equal 01c6f6004a00ecfa6e77ab4025b47a46a5e925fc, else STOP
   ```
4. List every skill folder at that tag (use the sub-path from step 2): `ls <skills-subpath>`. Put the full list in the note, marking which three are already pinned.
5. For **each** non-pinned skill, collect (read-only; **do not run any script or install anything**):
   - name, one-line purpose from its `SKILL.md` frontmatter `description`;
   - file count and total size (`find … | wc -l`, `du -sk`);
   - any executable/script files (`.sh .py .js .mjs .ts` or exec bit) — list them, do not run them;
   - any mention of: `http`, `sign in`, `login`, `api key`, `token`, `heygen.com`, `npx`, `npm install`, `pip install`, `curl`, `download` — list file:line (use `grep -rnE`), summarise: does it need an account, network or a paid service?
   - licence: repo `LICENSE` (Apache-2.0 expected) plus any per-skill licence file;
   - overlap with factory skills (`explainer-motion-craft` R1–R6, `video-director`): does it contradict any R-rule? Quote the line if so.
6. Pay special attention to: `hyperframes-audio` (does it document `data-fx-chain` and voiceover ducking? does it bundle audio files — then list names and file licences), `faceless-explainer` (flag: pulls in `media-use`, HeyGen sign-in; **recommend EXCLUDE**), anything named `*media*`, `*tts*`, `*transcribe*`.
7. Dry-run the sync into scratch with a **copied** lock (never the real one):
   ```bash
   cp ~/…/video-factory/config/upstream-skills.lock.json $HOME/audit-scratch/t1/lock.test.json
   # edit ONLY the copy: add the candidate skill name(s) to sources[0].skills and delete its tree_sha256 map entry for new names
   cd <repo> && ~/.contentos/venv/bin/python scripts/upstream_skills.py sync --lock $HOME/audit-scratch/t1/lock.test.json --skills-dir $HOME/audit-scratch/t1/skills-out
   ```
   Record the printed tree hashes. (This clones the pinned tag again via the script — allowed — into its own temp area. If the script writes anywhere inside the repo, STOP and report.)
8. Write the note with a decision table: skill | purpose | scripts | service/network | licence | recommend (ADD / EXCLUDE / OWNER-DECIDE) | reason.
9. Also state the exact command sequence the owner would run to adopt a skill (do **not** run it):
   ```
   # edit config/upstream-skills.lock.json → add skill name to sources[0].skills
   python scripts/upstream_skills.py sync --record
   python scripts/upstream_skills.py verify
   ~/.contentos/venv/bin/python -m pytest tests/test_upstream_skills.py -q
   # then (owner decision) add a capabilities.json entry so director plans can name it
   ```
   and the rollback: `python scripts/upstream_skills.py remove` is **not** a rollback for one skill (it removes all listed); say so, and give the safe rollback (restore the lock file from git, delete that one skill folder).
10. Verify: snapshot after; diff against before → identical. `git status --porcelain` shows only the new note (untracked).
11. Append the report to `90-run-log.md`.

## Acceptance
- Note exists with every non-pinned skill assessed; each row has evidence (file:line), not opinion.
- Commit hash in scratch clone equals the lock's commit.
- Snapshot diff identical; no repo file modified.

## Do not
Run any upstream script; run `npm`/`npx`/`pip`; touch `.claude/skills`; edit the real lock; recommend `faceless-explainer` without a clear statement of the HeyGen dependency.

## Rollback
`rm` the note; `rm -rf $HOME/audit-scratch/t1`.
