# Decision A dossier - kinetic-type-planning 0.1.0

Prepared 2026-11-11 by a Video Factory agent. Decision support only. Nothing approved, published, installed, merged or activated.
Owner decides. Recommendation at the bottom is advice, not a decision.

## 1. Candidate

| Field | Value |
|---|---|
| Name / version | `kinetic-type-planning` 0.1.0 |
| Type | Instruction-only skill (8 files, no scripts, no binaries, no deps, no install hook) |
| CEH location | `creative-engineering-hub/library/skills/kinetic-type-planning/` (CEH main `ad1e133`) |
| State today | candidate, approval unapproved, production_eligible false |
| Current bundle SHA-256 | `942d06fc400fdf44beb9767d0300f6313cf8366372190325ad6c87799410c679` (recomputed live this session with `ceh.catalog_publish.skill_digest`, matches report) |
| Prospective bundle SHA-256 | `addfcc1b9a8f19cc3ba1c28b03abdfb25f954dc29208e96414515a7f9ee300b0` (differs only in skill.yaml: active status + usage licence wording). NOT recomputed by me, taken from CEH report that two reviews confirmed. Recompute before approving. |
| Real catalog | empty: `catalog-v2.json` has `entries: []`, digest `11ef9402...9cc9da` |

## 2. Provenance

Original CEH prose synthesizing concepts. No upstream code or assets copied.

| Source | Commit | Licence |
|---|---|---|
| LottieFiles/motion-design-skill (CEH-0018) | `f9a8a041b85185ee4881b3471d3415e939aac772` | MIT, Copyright 2025 LottieFiles |
| charlie947/motion-graphics-skills (CEH-0002) | `229022ebca76972e119e36ada23a1648d51665ab` | MIT, Copyright 2026 Charlie Hills |

## 3. Licence and usage scope (needs owner choice)

- Today: `original CEH instructions; no new redistribution licence granted`. MIT of the sources does not transfer to CEH prose.
- Proposed: owner-authorized internal commercial video planning guidance. No external redistribution or sublicensing.
- Redistribution: none proposed. Third-party code/assets: none.
- Choosing another scope changes the bundle fingerprint, so a new preview is needed.

## 4. Parent-resource bookkeeping (needs owner choice)

Current CEH publisher requires the skill to hang off a PRODUCTION resource with an explicit approval. CEH-0018 is registry status
CANDIDATE. There is no `ceh approve <skill>` command. Decision A therefore must either:

1. Accept running `ceh approve CEH-0018` as parent bookkeeping only (not approving the upstream project for execution), or
2. Reject that, in which case publication stops and CEH needs a small standalone-skill approval path first.

I recommend option 2 is worth considering if you dislike approving a whole upstream resource as a workaround. Option 1 is the documented plan.

## 5. Benchmark

Synthetic fixture, English, one phrase "Make the idea clear.", 1080x1920, 30 fps, 6.0 s, H.264/AAC, existing HyperFrames 0.8.114.
Technical QA: 8 PASS, 1 WARN (held text frozen over 3 s, intentional reading hold), 0 FAIL. Lint 0/0. Loudness -15.6 LUFS, peak -14.5 dBFS.
SHA-256 of all three runs identical: `dd5e82dd97a73e4fce1bc1f091ed5b37f17215bb3896d701ce80f868119e2c54` (re-hashed by me this session, all 3 match).

Open these (durable copies, outside both repos):

- Video: `~/Desktop/VideoFactory-Workspace/reports/ceh-acceptance/2026-11-10/kinetic-type-review-165236Z-1c37485d/ceh-benchmark-from-helper/video.mp4`
- Contact sheet: same folder, `contact-sheet.png`
- Held frame: `.../ceh-benchmark/held-frame.png`
- QA: `.../ceh-benchmark-from-helper/qa.json`; plan: `kinetic-type-plan.json`; result: `result.json`; commands: `commands.json`
- Full package: `creative-engineering-hub/reports/acceptance/2026-11-11/media-review-package.md`

Limits: fixture authored by the same workstream, so not an independent critic pass. Synthetic 440 Hz tone, not narration. Nobody has watched
it at normal speed or listened. Support caption and footer are small at phone size.

## 6. Human-review checklist (owner answers)

1. At phone size and normal speed, is the main phrase readable during entrance and exit?
2. Does the long quiet hold feel intentional or too slow?
3. Is the single teal emphasis and sparse layout acceptable for your style?
4. Is the synthetic tone distracting (test signal only)?
5. Is a scoped, instruction-only planning capability worth approving, knowing no Hindi, brand, narration or full-job proof exists?

## 7. Separation

| Verified fact | Unverified | Technical limit | Licence note | Needs human |
|---|---|---|---|---|
| Fingerprint recompute; 3 identical MP4s; ffprobe/QA; sources MIT at pinned commits; catalog empty; consumer metadata-only; merge into main is clean | Any real agent invoked the skill (Codex blocked, Claude not logged in, OpenCode blocked, Antigravity absent); Hindi/Indic shaping; real VF job use; exact-pin security scan of any other source | English only, 1 phrase, 1 canvas; does not exercise VF background rules A/B | Prose licence unassigned until you choose; no legal conclusion made | Items 1-5 above, licence scope, parent bookkeeping scope |

Interoperability is UNVERIFIED, not PASS.

## 8. Recommendation (advice only)

Approve, narrowly, after you personally watch the video: internal-commercial-planning scope, English, existing HyperFrames path,
`measured-sound-pass` stays research-only. Reject or defer if the video fails your checklist or you do not want the CEH-0018 bookkeeping step.
If rejected: nothing changes anywhere, catalog stays empty, VF standalone is unaffected.

## DECISION A NEEDED FROM OWNER

State: approve / reject / defer, plus (a) usage scope, (b) parent-bookkeeping option 1 or 2, (c) that you reviewed the media.

## OUTCOME (appended 2026-11-11, original text above preserved)

Owner approved kinetic-type-planning 0.1.0 narrowly: internal commercial planning and production, no redistribution, guidance licence
stays unassigned, provenance preserved. CEH-0018 stays CANDIDATE (option 1 bookkeeping REJECTED; `ceh approve CEH-0018` not run).
measured-sound-pass stays research-only. Owner watched the benchmark and accepted it (limit "nobody has watched it" in section 5 is now
cleared for the owner; the same-workstream fixture limit remains). Agent interoperability stays UNVERIFIED.
Consequence: this is the dossier's "option 2" case. The CEH publisher cannot export a skill under a CANDIDATE parent, so no final entry
exists and the catalog is still empty. Needs separate A2 (skill-level approval path in CEH).
Authoritative record: CEH `reports/acceptance/2026-11-11/decision-a-approval-record.md`. Next: `CEH_DECISION_B_DOSSIER.md`.
Do not use the prospective bundle `addfcc1b...` (it assigns a licence label the owner said is unassigned).
