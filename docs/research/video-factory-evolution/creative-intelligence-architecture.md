# C — Creative intelligence architecture

**Proposal. The creative layer is now partly built, so this document extends the real code rather than replacing it.**
Two untracked modules already exist on this branch and both are in **shadow mode** — nothing in the pipeline reads them:

- `contentos/intelligence/styles.py` — `style/1` cards: six structural axes, five dials, forbidden motion, sound strategy,
  a frame checklist, a named reviewer. Two cards must differ on ≥3 of the 6 axes, so **a recolour cannot pass as a style**.
- `contentos/intelligence/creative.py` — `creative-decision/1`: `propose` / `record` / `report`. Scores are
  `2*fit + novelty_vs_most_recent + repeat_penalty(-3 if the 6-axis combo appeared in the last window)`.
  **Palette is deliberately not an input** (asserted by `tests/test_creative.py::test_palette_is_not_an_input`).

Everything below is designed to sit on those two modules. It is deterministic and local: **no LLM call belongs in the
selection path** — that is the existing design and it should hold.

---

## 1. Principle: three separated decisions

The failure mode this architecture exists to prevent is doing all three of these at once, at the end, by taste.

| Decision | Question | Where it lives |
|---|---|---|
| **Correctness** | Is the video accurate, legible, and within gates? | Existing: `qa.py`, `visual_gate.py`, `finalcheck.py`, gates. **Never overridable by a creative score.** |
| **Content fit** | What does this *material* need? | New: the creative brief → dials → candidate styles |
| **Novelty** | Is this *materially different from recent videos*? | Existing: `variety_report`, Rule A/B, `check_distinct` |

A creative score may **never** override a hard failure. A style that is novel but illegible is rejected at the
correctness filter, not scored down.

---

## 2. Input contract

### 2.1 What the creative director must be given

Today `creative.validate_brief` accepts `job, topic, content_type, length_kind, factual_density, register`. That is a good
deterministic core but it is missing the inputs the brief asks the director to consider. Proposed **additive** extension —
every new field optional, so existing briefs and tests keep working:

```jsonc
{
  "schema": "creative-brief/2",
  "job": "ep4-…",                       // existing; must match the content_id regex
  "topic": "…",                          // existing
  "content_type": "ai-workflow",         // existing; drives style-card fit
  "length_kind": "short",                // existing
  "factual_density": "high",             // existing
  "register": "curious",                 // existing

  // --- proposed additions ---
  "audience": {                          // who, and what they already know
    "who": "backend engineers",
    "prior_knowledge": "high",           // none | low | medium | high
    "language": "en"
  },
  "learning_objective": "explain why a tool call fails and how to recover",  // one sentence, required if factual_density>=medium
  "entertainment_goal": null,            // or the objective; exactly one of the two must be set
  "promise": "you will see the failure, then the fix",   // the central promise = the hook's payoff
  "hook_options": ["…", "…"],            // 2-5 candidate openings, chosen from the table in §3
  "platforms": ["youtube-shorts"],       // feeds production/platforms.py budgets, not the style
  "aspect": "9:16",
  "assets": {                            // what actually exists
    "narration": "script-timed",         // script-timed | supplied-audio | none
    "source_footage": false,
    "screenshots": true,
    "music": false
  },
  "energy": "medium",                    // calm | medium | high
  "visual_referents": "available",       // available | abstract-only  → constrains illustration_mode
  "evidence": ["https://…"],             // per-claim sources; required when factual_density is high
  "rights": {"audio": "owned"},          // unknown must block publication (already enforced by supplied_audio)
  "priority": "normal"                   // feeds scheduling, not creativity
}
```

**Why each addition earns its place.** `audience.prior_knowledge` and `visual_referents` are the two inputs that most
change the right treatment, and neither is currently expressible. `learning_objective` gives the "explain why this
technique" requirement something to point at. `hook_options` makes the hook a *decision with rejected alternatives*
rather than an emergent first line. `rights` connects the creative layer to the already-wired G3 gate.

**Validation rules** (deterministic, same style as today's `validate_brief`): exactly one of `learning_objective` /
`entertainment_goal`; ≥2 `hook_options` when `length_kind == "short"`; `aspect` must exist in
`config/quality.yaml`'s formats; a `visual_style` card whose `illustration_mode` is `photographic` is invalid when
`visual_referents == "abstract-only"`.

### 2.2 Inputs the director must **not** take

- Platform monetisation state — that is a publishing policy question (doc E), not a style input.
- Any per-video "make it go viral" knob. There is no evidence any style choice guarantees retention.
- Renderer internals. A style may declare a capability *requirement*; the renderer either satisfies it or the style is
  ineligible.

---

## 3. Hook selection — a decision framework, not a checklist

The hook is the highest-leverage creative decision and the one with the worst evidence base. **No hook in this table is
claimed to improve retention.** Retention claims would need a controlled comparison, and the only honest thing a design
document can do is state the mechanism, the conditions, the failure mode, and the observation that would count as
evidence.

The framework's job is narrow and useful: **make the hook a deliberate choice from the material, recorded with rejected
alternatives** — which `creative.record`'s mandatory ≥8-character rejection reasons already force.

| Hook | Mechanism it exploits | Suitable when | Harms comprehension when | What would count as evidence it helped |
|---|---|---|---|---|
| **Start with the result** | Answers "is this worth my time" before spending attention | The outcome is visually showable and the *means* are the interesting part | The result is meaningless without its setup, or is a spoiler that removes the reason to watch | Viewer keeps watching past the first 15 %; comment/drop-off data within the first 3 s at launch |
| **Visual contradiction** | An image that cannot be true forces a question | The material contains a genuine paradox or a counter-intuitive number | The contradiction is manufactured, or resolving it is trivial | A measurable pause/replay on that segment; unprompted comments asking about it |
| **Reveal a hidden mechanism** | Curiosity about an opaque box | The subject is a system whose behaviour is visible but whose cause is not | The mechanism needs more than ~20 s of prerequisite | Retention at the reveal beat vs the channel baseline |
| **Animate the problem first** | Makes an abstract failure concrete and felt | The topic is a failure mode, a bug, or a risk | The problem is obvious and the animation is therefore padding | Comment sentiment; a drop in skip rate over the problem segment |
| **Transform one metaphor into another** | Continuity of a single idea through the piece | The piece has one spine and a visual vocabulary that can carry it | The metaphor is decorative rather than load-bearing — then it is noise | Recall/recognition of the metaphor in comments or a quiz |
| **Concrete before/after** | Visible delta, fast comprehension | The change is real, visible, and attributable to one cause | The before/after are not controlled, so the delta is misleading — **this is a correctness risk, not just a style one** | The viewer can state the delta unprompted |
| **Ask a question, resolve visually** | Open loop | The question is genuinely open and answered in the piece | The answer arrives too late, or the loop is never closed (violates the closing-callback discipline) | Comment rate on the question; drop-off before the answer |
| **Progressive reveal of an architecture** | Withholding structure rewards attention | The architecture is genuinely non-obvious and decomposable | The system is simple; the reveal becomes an artificial delay | Retention curve flat across the reveal |
| **One word triggers an event** | Ties narration to picture at the exact syllable | Word-level timing is trustworthy (see §6) | Timing is ASR-derived-and-unverified, so the event lands off the word | Measured cue error in frames (doc D/§6 of the roadmap) |
| **Silence, contrast, or a held frame before a payoff** | Contrast makes the payoff land | The piece has a genuine climax | Used early or often — contrast only works once | Measured: is the loudest/strongest frame actually after the quiet one |
| **Closing callback to the opening** | Shape; makes the piece feel whole | The opening image can be meaningfully transformed | The callback is a literal repeat with no change | Comment references to the ending |

**Pairing rules** (deterministic, and where a real gate could live later):

- Exactly **one** primary hook; secondary hooks may support but not compete.
- A hook requiring word-accurate timing is **ineligible** while timing is `asr-derived-unverified`.
- "Concrete before/after" requires the same measurement method and scale on both sides, or it must be labelled
  illustrative — this is a **correctness** precondition, enforced before scoring.
- The hook must be expressible in the `arc`'s first scene purpose (`hook`), which `director.coherence_issues` already
  requires.

---

## 4. Style and visual grammar selection

### 4.1 The pipeline (all deterministic)

```
brief ──▶ FILTER ──▶ needs ──▶ CANDIDATES ──▶ SCORE ──▶ 3 DIRECTIONS ──▶ PICK ──▶ STYLE FRAMES ──▶ human gate
           ▲                     ▲              ▲                              ▲
     hard constraints      required axes   content fit + novelty      must be ≥3-axes distinct
     (rights, aspect,      from the brief  (existing score_card)       (existing check_distinct)
      referents, capability
      availability)
```

1. **Filter — non-negotiable.** Remove any card whose `requires[]` is not `installed` in `config/capabilities.json`
   (already enforced by `styles.validate_card`), whose `illustration_mode` is `photographic` when
   `visual_referents == "abstract-only"`, or that needs sound strategy `music-led` (which `styles.py` already refuses
   because beat analysis does not exist).
2. **Derive required axes from the brief**, as content fit — a system explanation wants `diagrammatic` +
   `layered`; a claim evaluation may want `split`; a reflective history piece may want `textural` + slow `parallax`.
3. **Score** with the existing `score_card`: `2*fit + novelty + repeat_penalty`, where novelty is axis-distance from the
   most recent decision record and the penalty fires when the 6-axis combination repeats inside the window.
4. **Keep the top 3, and require `check_distinct` to pass** — the existing code already hard-rejects if the three are not
   pairwise ≥3-axes distinct. This is the mechanism that makes "different directions" mean *structurally* different.
5. **Pick one and record why the other two lost**, via `creative.record`, which enforces a ≥8-character reason per
   rejection. The record also sets `requires_explicit_approval` when the chosen card is not `validated` — a flag that
   today **nothing reads**; §7 makes it a real checkpoint.

### 4.2 Style cards are contracts, and they need to be earned

A card is currently accepted with `status: "unvalidated"` and `evidence: []`, and `validate_card` **refuses** `validated`
without evidence. That is the right shape. The gap is that all three existing cards are unvalidated, so every candidate
today would set `requires_explicit_approval`. Two consequences to design for:

- **A card may not claim a capability that is not installed**, and may not claim a *validated* look it has not rendered
  here. Status is per-machine, not per-repo: `validated` should name the environment (the design library already uses
  `validated_in: ["mac-hf0.8.114"]`, which is the pattern to keep).
- **A style card is not a palette.** The six axes make that structural, and `check_distinct` proves it.

### 4.3 What the style layer deliberately does not do

It does not claim the chosen style *looks better*. That is a subjective judgement and only the bake-off (doc F) can inform
it. Any statement about quality must come from the independent critic plus human review, never from the score.

---

## 5. Storyboard and style-frame review

Cheap checkpoints before expensive ones — the ordering matters more than the artifacts:

| Checkpoint | Cost if wrong here | Artifact | Blocking? |
|---|---|---|---|
| 1. Content/source verification | Cheapest to fix, most damaging to get wrong | claim→source list; illustrative data labelled | **Yes** — accuracy gate |
| 2. Narrative structure | Cheap | scene purposes + `arc`; validated by `direction.validate_plan` + `director.coherence_issues` | Advisory |
| 3. Hook + payoff options | Cheap | 2–5 hook options from §3, one chosen, reasons recorded | Advisory |
| 4. Three competing directions | Cheap | `creative.propose` output where the top 3 are ≥3-axes distinct | Advisory |
| 5. **Style frames** (3–5 full-size stills, one per key beat) | Moderate — a still is cheap, a render is not | a labelled `sheet/1` + a frame-checklist tick per card | **Yes, when the chosen card is not `validated`** (this is what `requires_explicit_approval` should gate) |
| 6. Storyboard approval | Moderate | every beat as a key frame, with timing | Advisory for shorts, recommended for long-form |
| 7. Motion + audio cue plan | Moderate | candidate timeline cues; do **not** gate cue audibility yet | Advisory |
| 8. Authoritative timeline | Moderate | one JSON clock (see §6) | Advisory |
| 9. Low-cost draft render | Expensive | 30 fps / reduced resolution draft | Advisory |
| 10. Labelled sheet + audio review | Expensive | `sheet/1` with drawing labels + loudness readings | **Yes** (already the review step) |
| 11. Specific defect repair | — | one fix per finding, re-verified | **Yes** |
| 12. Final render, technical QA, creative review, handoff | — | QA table + critic report + gate | **Yes** (already exists) |

**Mandatory vs optional.** For a **short** video the mandatory set is 1, 5 (only if the card is unvalidated), 10, 11, 12 —
four cheap-or-existing checkpoints. The full 12 steps apply to long-form or to a first use of an untested style. There is
an explicit **lite path** so that adding this layer never makes a 45-second Short slower than it is today.

**Style frames are the single highest-value new checkpoint**, because they are the last cheap moment to discover that a
direction does not work. Note the honest blocker: rendering style frames needs an unbroken `sheet/1` path, and on this Mac
`sheet.py` **fails closed** because the homebrew FFmpeg 9.0.2 was built without freetype, so `drawtext` is unavailable
**[read: `docs/CURSOR.md:105`]**. The documented workaround is `./contentos.sh preview … --sheet`; `--allow-unlabelled` is
explicitly not an acceptable substitute. **The `sheet/1` prerequisite is therefore a real dependency of this checkpoint.**

---

## 6. Authoritative timeline integration

Three overlapping notions exist today. Honest status:

- `sceneplan/1` (`production/sceneplan.py`) — a *plan*, anchored to narration word indices. Real, planning-only.
- `timeline/1` (`production/timeline.py`) — declared **shadow**: "Nothing reads this file yet". **Nothing imports it.**
- The live render path (`pipeline.s_compose`) — builds scenes inline from per-line WAV duration and emits one `span` per
  script word, colour-driven by GSAP `tl.set(...)` per word.

So the honest statement is: **there is no authoritative JSON timeline at runtime.** Timing is measured WAV durations plus
word highlighting, and word times come from `align.align_words`, a `difflib` alignment of *script* words onto *whisper.cpp*
ASR timestamps, where the script's spelling is displayed and ASR supplies only timing — each word labelled
`matched`/`span`/`interpolated`.

**Design.** Keep `timeline/1` as the single clock and extend it **additively**, with no schema break:

- `words[]` — the existing aligned words, each carrying its provenance (`matched` / `span` / `interpolated`) so caption
  timing can be described truthfully.
- `scenes[]` — resolved from `sceneplan.resolve()`.
- `cues[]` — audio cues, when audio design exists.
- `beats[]` — beat markers, only for music-led styles (which `styles.py` currently refuses).
- `transitions[]` — transition windows, so a transition can be validated against the clock rather than the log.
- `review_markers[]` — what the labelled sheet should sample.
- `timing_trust` — a single summary field: `asr-derived-unverified` until a human anchors word onsets. **This one field
  is what stops a downstream claim of accuracy that was never established.**

Compose keeps its current path until the shadow timeline proves equivalent, exactly as the prior roadmap prescribed.

---

## 7. Variety and repetition detection

Two layers exist and are complementary. Neither is wired into the pipeline; both are advisory measurements.

**Inside one video** — Rule A: at least half the scenes must use distinct backdrops.

**Across videos** — Rule B: a new video must differ from each of the last 5 shipped videos on ≥2 of 5 signature fields
(`structure`, `temperature`, `texture`, `base`, `accents`). Measured from rendered frames, from frame margins only.

**Across creative decisions** — `variety_report`: axes differing from the previous video (fails below 2), 6-axis combo
repeat inside the window, plus counts of transition families and motion grammars used.

**Proposed additions** (the gaps this layer does not cover):

| Pattern to detect | Detection | Why it matters |
|---|---|---|
| Repeated opening composition | Compare the first ~1 s frame across the last N | The most visible channel-level sameness |
| Repeated scene layout | Compare per-scene backdrop/layout signature sequences | Catches "same video, new words" |
| Repeated transitions | Exists (`transition_family` count) — extend to the *sequence* | A repeated wipe pattern reads as a template |
| Repeated animation curves | Reuse `motion_audit.ease_inventory` across videos | Sameness in motion that the eye notices but cannot name |
| Excessive static stretches | `qa.py` already measures `freezedetect` at >3 s | Note: a `frozen_frames` WARN on text slides is **expected, not a defect** |
| Gratuitous motion | `motion_audit` ydif + Rule R4 territory | Motion without meaning is noise |
| Similar endings across unrelated topics | Compare the last ~1 s frame + the final scene's purpose | The closing-callback rule should not become the same ending every time |
| Palette drift | Measure and **report**, but never count toward novelty | Palette distance is not variety — the existing test already enforces that palette is not an input |

**The governing rule: never sacrifice accuracy, accessibility, clarity or audience fit to maximise novelty.** A high-novelty
direction that lowers legibility is rejected at the correctness filter. Consistency inside a video and across a series
(logo, caption treatment, safe zones) is *desirable*; accidental sameness between unrelated videos is not.

---

## 8. Technical versus creative quality assessment

Hard separation, already respected in the code and worth stating as a rule:

| | Technical QA | Creative review |
|---|---|---|
| Who | `qa.py` (9 checks), `finalcheck.py`, `visual_gate.py`, Rule A/B | An independent critic + the owner |
| Output | PASS/FAIL/WARN against configured thresholds | A judgement, with a spread across runs |
| Overrides | **None** — a `FAIL` blocks export | May never override a `FAIL` |
| Thresholds | `config/quality.yaml`; **not to be changed** to make something pass | Not applicable |
| Independence | Deterministic | **A builder never grades its own video.** `critic.py` already validates an independent report and recomputes the verdict |

Two rules that follow, and that this audit recommends making explicit in `AGENTS.md`:

1. **A creative score must never override a hard failure.**
2. **Critic scores are a noisy aid.** Report the spread over ≥3 runs; never average it away, and never present it as
   ground truth. An LLM-judged score is not evidence of professional quality.

---

## 9. Human approval boundaries

| Gate | Exists? | Content |
|---|---|---|
| Accuracy / sources verified | Documented, weakly enforced | Claims carry sources; illustrative data labelled |
| **Style frames approved** | **New, recommended** | Only when the chosen card is not `validated`; the existing `requires_explicit_approval` flag becomes its trigger |
| `SCRIPT_APPROVED` | Yes | Script + title |
| `PRODUCTION_APPROVED` | Yes | The composed project |
| Review: labelled sheet + critic | Yes | Post-render |
| `PUBLISH_APPROVED` | Yes, and publish is disabled | Never auto-granted |

**Gates are keyed by `content_id` alone**, so a previously approved script that is then changed needs a **fresh** approval.
That is existing behaviour and it is load-bearing: it means a creative revision after gate 1 invalidates the approval.

The style-frame checkpoint must be **advisory-by-default and skippable**, with a lite path for Shorts, so that it cannot
become a fifth hard stop on a pipeline that currently has three.

---

## 10. Sample decisions for six content categories

Illustrative — **none rendered, no winner claimed.** Each shows the brief's inputs reaching a recorded decision with
rejected alternatives. That record, not the outcome, is the deliverable of this layer.

| Category | Brief inputs that drive it | Chosen direction | Rejected, with reason | Sound |
|---|---|---|---|---|
| **Architecture lesson** — how two services talk | `learning_objective`, `prior_knowledge: high`, `visual_referents: abstract-only`, `factual_density: high` | `blueprint-diagram`: `diagrammatic` + `layered` + `draw-on` + `even` rhythm; hook = *progressive reveal of an architecture* | Photographic montage — no referents exist, and the card would require a non-installed capability. Type-driven kinetic — the density is already high, kinetic type competes with the diagram | narration-led, near-silent |
| **Surprising AI workflow** | `content_type: ai-workflow`, `register: curious`, `screenshots: true` | `punch-split`: `split` + `snap-cut` + `punctuated`; hook = *concrete before/after* (same measurement both sides) | Full-bleed UI recreation — feasibility unproven on this renderer. Iconographic cards — same axes as the previous video, so `novelty` would be 0 and the combo repeat penalty would fire | short tick on each reveal |
| **Historical explainer** | `register: reflective`, `entertainment_goal` set, `energy: calm` | `slow-parallax-story`: `textural` + `parallax` + `accelerating` toward the turning point; hook = *reveal a hidden mechanism* | Diagrammatic timeline — cold for a story. Typographic only — no emotional register available | ambient bed, near-zero cues |
| **Product launch** | `entertainment_goal`, `energy: high`, `visual_referents: available` | `punch-split` variant with word-locked reveals; hook = *one word triggers an event* — **only if timing is anchored**, otherwise fall back to *start with the result* | Isometric diagram — hides the product. Documentary collage — wrong register for a launch | measured accents on hero reveals |
| **Science concept** | `learning_objective`, `visual_referents: abstract-only`, `energy: medium` | `blueprint-diagram` with a procedural/canvas treatment **listed as experimental** | Pure text cards — no mechanism shown. Stock footage — no rights record, and no referents exist | quiet cues |
| **Practical how-to** | `learning_objective`, `prior_knowledge: low`, `screenshots: true`, `factual_density: high` | `blueprint-diagram` with `stacked-cards` + `eased-glide`; hook = *animate the problem first* | `punch-split` — snap-cuts fight step-by-step procedural clarity. Kinetic typography — reading speed becomes the bottleneck | narration-led, cue at each step boundary |

The last two rows show the governing rule in action: the **experimental** capability is named but the validated fallback is
what would ship, and a style that reduces clarity for a low-prior-knowledge, high-density audience is filtered out before
scoring rather than scored down.

---

## 11. What this layer still cannot do

- It cannot say which direction looks better — only a bake-off with an independent reviewer can inform that.
- It cannot make a hook's retention claim. Every hook in §3 is a hypothesis with a named observation, not a finding.
- It cannot use sound design meaningfully yet: `styles.py` refuses `music-led`, and there is no music, SFX or ducking in
  the factory at all.
- It cannot gate on word-accurate cueing while timing is `asr-derived-unverified`.
- It cannot validate a style on this machine until the design library and the new cards gain real render evidence —
  today **0 of 76 library entries and 0 of 3 style cards** are validated here.
- It cannot yet render a style-frame sheet through `sheet.py` on this Mac, because `drawtext` is unavailable in the
  installed FFmpeg build.
