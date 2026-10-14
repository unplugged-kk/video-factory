# E — Multi-niche and multi-platform strategy

**Proposal only.** No niche is implemented here, no platform adapter is built, and **no platform behaviour or monetisation
rule is asserted without an official source**. Where this document does not have official evidence it says so and marks the
row for later research — that is deliberate, because several platform facts are changing and third-party pages disagree
with the first-party ones.

---

## 1. Two axes that must not be conflated

The core architectural rule: **a niche decides what the video is; a platform decides how it is packaged.** They are
different modules with different inputs, and neither may reach into the other.

```
        creative brief (doc C)
                │
        ┌───────┴────────┐
        │  NICHE MODULE  │   audience, fact-check rules, narrative shapes,
        │  (what & why)  │   suitable creative families, rights policy
        └───────┬────────┘
                │  one approved creative concept
                ▼
   ┌────────────────────────────────────────┐
   │  PLATFORM PACKAGING (per target)       │  duration, aspect, hook, caption
   │  derived from config/platforms.json    │  treatment, pacing, packaging
   └────────────────────────────────────────┘
```

The reason this matters: the prior roadmap already separated *niche strategy* from *platform rendering*, and the existing
code respects it — `production/platforms.py` owns duration/aspect budgets from `config/platforms.json`, while
`intelligence/styles.py` owns visual language and knows nothing about platforms. **Keep that boundary.** A single approved
concept may need an X cut of ≤140 s and a YouTube/Threads/LinkedIn cut of ~3 min, and the correct response is two render
manifests over one creative concept, not two creative concepts.

---

## 2. The niche module (a contract, not a hard-coded workflow)

A new niche should be **a data file plus, at most, one small policy function** — never a new pipeline. Proposed schema,
deliberately parallel to the existing `style/1` card discipline (a named reviewer, an evidence field, an explicit status):

```jsonc
{
  "schema": "niche/1",
  "id": "ai-workflow",
  "name": "AI tools & workflows",
  "status": "unvalidated",                 // unvalidated | validated  (validated needs render evidence)
  "reviewed_by": { "name": "…", "date": "YYYY-MM-DD" },
  "audience": { "who": "…", "prior_knowledge": "medium", "language": ["en"] },
  "value_proposition": "one sentence: what the viewer can do afterwards",
  "objective_kind": "learning",            // learning | entertainment | evaluation

  "content_types": ["ai-workflow"],        // must exist in styles.CONTENT_TYPES
  "narrative_shapes": [                    // drawn from direction.PURPOSES
    ["hook", "setup", "mechanism", "example", "recap"]
  ],

  "fact_checking": {
    "required": true,
    "min_sources_per_claim": 1,
    "recency_days": 180,                   // claims older than this need a date qualifier
    "label_illustrative": true,            // synthetic examples must be labelled
    "forbidden": ["performance numbers without a cited measurement",
                  "capability claims taken from vendor marketing alone"]
  },

  "creative_families": ["blueprint-diagram", "punch-split"],   // style-card ids, not free text
  "typical_cost": { "scenes": "6-9", "length_kind": "short", "render": "standard" },

  "originality_risks": [
    "the same tool demo repeated across episodes",
    "screenshot of a UI that changes before the video ships"
  ],

  "sourcing": {
    "assets": ["screenshots"],
    "rights_required": ["owned", "licensed"],   // 'unknown' blocks publication, per supplied-audio/1
    "no_third_party_footage": true
  },

  "platforms": ["youtube-shorts", "threads"],    // candidates, subject to §4
  "research_later": [
    "monetisation eligibility rules",
    "whether automated posting is permitted for this account type"
  ]
}
```

**Why a schema rather than prose.** The existing registries already teach the lesson: `style/1` refuses a card that claims
a `validated` status without evidence, refuses a `requires[]` capability that is not `installed`, and refuses two cards
that differ on fewer than 3 axes. A niche file should be able to make the same class of refusal — e.g. a niche whose
`fact_checking.required` is `true` cannot be used with a brief that has no `evidence[]`.

**One policy hook, not a framework.** The only per-niche code that should ever exist is a small validator: "does this brief
satisfy this niche's rules?" Everything else — narrative shape, creative families, cost — is data.

---

## 3. Candidate niches

Each is assessed for what would have to be true for it to work, not for whether it sounds attractive. **None is
implemented.** Cost is expressed in *scenes and renders*, not time, because no render has been measured (doc D §1).
"Rights" means what must be owned or licensed before publication.

| Niche | Audience & value proposition | Fact-checking requirement | Typical narrative shapes | Suitable creative families | Production cost | Originality / rights risk |
|---|---|---|---|---|---|---|
| **AI & software engineering** *(the current core; `content_type: ai-workflow`)* | Engineers; "you can do X after this" | **High** — version-sensitive; a claim about tool behaviour must be dated and sourced, not taken from release marketing | hook → setup → mechanism → example → recap | `blueprint-diagram`, `punch-split` | 6–9 scenes, standard render | Repeated tool demos across episodes; screenshots that change; **screenshot rights** |
| **Cloud / DevOps / technical education** | Practitioners and learners | **High** — architecture claims must be correct or they teach harm | hook → mechanism → example → contrast → recap | `blueprint-diagram` (layered, draw-on) | 7–12 scenes; diagram-heavy | Every channel has a "VPC explained"; requires a genuinely different structural axis to stand out |
| **Business, startups, product launches** | Founders, operators, buyers | **Medium–high** — figures, funding, and market claims need sources; vendor marketing is not a source | hook → contrast → mechanism → example → cta | `punch-split`, product-hero treatments | 6–10 scenes | Claims about a company's metrics; **product imagery and logos are owned by others** |
| **Science & technology explainers** | Curious general audience | **High** — an error here is misinformation; illustrative data must be labelled as illustrative | hook → setup → mechanism → example → recap | `blueprint-diagram`, procedural/canvas (**experimental**) | 8–14 scenes | Simplification flattens to inaccuracy; stock imagery rights; the canvas family is unproven on this renderer |
| **History & documentary storytelling** | General audience, reflective register | **High** — dates, attributions, and contested claims need care and a stated position | hook → setup → contrast → mechanism → recap (callback) | `slow-parallax-story` (textural, parallax) | 8–14 scenes | **Archival imagery rights are the hard problem**; near-certain copyright issues with footage and photographs |
| **Finance & economics education** | Learners and hobbyists | **Very high** — plus a **policy constraint**: the licence matrix already prohibits AI personas presenting financial advice as an expert | hook → mechanism → example → contrast → recap | `blueprint-diagram`; conservative type-driven | 6–10 scenes | Regulatory and liability exposure; must stay explanatory, never advisory |
| **Career & learning content** | Early-career viewers | **Low–medium** — mostly first-person, but any salary or market figure needs a source | hook → setup → example → contrast → cta | `punch-split`, typographic | 5–8 scenes | Generic advice is the failure mode; needs a specific, defensible point of view |
| **Practical how-to** | Task-completing viewers | **Medium** — steps must actually work; a broken procedure is worse than no video | hook → setup → mechanism → example → recap | `blueprint-diagram` with stacked cards, eased glide | 6–10 scenes | Voice-heavy and low visual variety; the pace of on-screen change is the retention risk |
| **Interviews & podcast clips** | Followers of a guest | **High** — quoting someone accurately is a rights *and* accuracy matter | hook (the best line) → setup → contrast → recap | caption-forward, minimal motion | Low render, **high input** | **Must own or license the recording and the speaker's permission**; the factory has no footage-editing path today (repo 4 in doc A is the reference) |
| **Product demonstrations** | Buyers | **Medium** — feature claims must match the shipped product | hook (the result) → setup → mechanism → example → cta | product-hero, word-locked reveals | 5–8 scenes | Product UI changes; screen-recording rights; may be a client deliverable with its own licence terms |

**Two niches are policy-blocked before they are considered:** anything presenting **health, legal, financial or political
advice as an expert persona** is already prohibited by this project's own content rules, and **Odia/Hindi voice output is
not built** (no TTS for those languages). A niche whose audience requires a language the pipeline cannot speak is not a
candidate yet.

**Discovered constraints worth recording.** Some niches need inputs the pipeline does not accept today:
interviews and podcast clips require **footage** rather than a script; practical how-to benefits from **screenshots and
screen recordings**; history needs **archival imagery**. Each of those is a *supplied-asset* problem, and the
`supplied-audio/1` model (provenance plus a rights status where `unknown` blocks publication) is the correct pattern to
generalise to images and footage — **not** a new asset pipeline per niche.

---

## 4. Platform packaging — official evidence only

Existing state: `config/platforms.json` (schema `platforms/1`), code in `contentos/production/platforms.py`, tests in
`tests/test_platforms.py`, and research recorded in `docs/factory-v2/13-platform-limits.md`. The owner ceiling is a hard
300 s for short-form with a 180 s default target; the checker applies both the owner ceiling and the platform limit.
**Re-published here with confidence labelled, and not re-verified against first-party pages this session.**

| Platform | Short-form | Long-form | Confidence | Note |
|---|---|---|---|---|
| YouTube | Shorts up to **3 min**, vertical or square, max 1080p | 15 min default; longer after verification; absolute max 256 GB / 12 h | **Official** (YouTube Help) | The Shorts limit rose from 60 s in Oct 2024 |
| Instagram | Reels **3 min** safe limit; aspect 1.91:1 to 9:16; ≥30 fps; ≥720 px | not recorded | **Official** for aspect/fps/size; length from a first-party executive statement | Vendor and press reports claim longer in-app limits with no first-party page |
| X | **140 s**, 512 MB (standard account) | Premium: under 4 h, 16 GB | **Official** help page | Premium is paid, so **off** unless explicitly opted in |
| Threads | **5 min (300 s)**, 1 GB, 23–60 fps, HEVC or H.264, MOV or MP4 | none recorded | **Official** (API docs + first-party post) | 9:16 recommended |
| LinkedIn | 10 min and 5 GB are widely cited | same | **Third-party only** | The first-party help page could not be read; **must be verified before relying on it** |
| TikTok | 3 min or 10 min depending on the source | n/a | **Conflicting** | First-party help gives no number; blocked in India; **disabled by default** |

**Not researched at all:** Facebook Reels, Snapchat Spotlight, and the Indian apps Moj, Josh and ShareChat. Do not add
them to `platforms.json` on a vendor list — add them when a first-party limit is found.

**Where the packaging actually lives today.** `production/platforms.py` answers "does this duration and aspect fit?" It does
**not** yet answer "how should the hook, pacing and caption treatment differ per platform". That gap is real and is
covered in §5.

---

## 5. Platform packaging is more than a duration check

A duration/aspect budget is necessary but not sufficient. For each target platform a packaging layer must be able to vary:

| Dimension | Why it cannot be a global setting |
|---|---|
| **Duration** | With one ≤3 min master, an X cut of ≤140 s is mandatory rather than optional |
| **Aspect** | The QA checker reads `formats` from `config/quality.yaml`; 9:16 and 16:9 have **different max durations** (180 s vs 3600 s) — so a platform that accepts 16:9 changes the legal length |
| **Opening hook** | Vertical short-form and long-form do not share an opening. A hook chosen for one may be wrong for the other, and doc C §3's hook framework must therefore be applied **per target**, not once per concept |
| **Caption treatment** | Caption size, safe zones and reading load scale with aspect. Note that safe-zone zones are **platform-specific and change**, and are currently hard-coded heuristics in `visual_gate.py` labelled "NOT published platform specs" — they must move to config and be marked `unverified` before any platform-specific packaging is claimed |
| **Pacing and cut rhythm** | A 3 s hold is fine in long-form and long in a Short |
| **Packaging text** | Title, description, tags — already partly modelled as optional spec fields that feed the sidecar and are **never guessed when absent** |
| **Disclosure** | Realistic AI-altered or synthetic content needs a disclosure field; clearly animated content is exempt. This is per-platform policy, not a global constant |

**Rule:** packaging a single concept for N platforms produces **N render manifests**, each independently QA'd. It never
produces one manifest with conditional logic inside it, because then neither output is individually verifiable.

---

## 6. What must be researched later, against official policy evidence

**None of the following may be asserted from a vendor blog, a news article, or another tool's documentation.** Each needs
a first-party source (a help page, an official API reference, or developer terms) recorded with a date.

| # | Question | Why it matters | Evidence required |
|---|---|---|---|
| 1 | Which platforms permit **automated** posting for the intended account type, and on what review path? | Determines whether a publish adapter is even legal to build | First-party API docs + the app-review requirements |
| 2 | What are the **identical-vs-different** rules for reposting one master across platforms? | Duplicate-content policies are enforced at channel level; the licence matrix already flags this | First-party policy text |
| 3 | **Monetisation eligibility** per platform, per format | The brief explicitly asks this be researched later, not assumed | First-party monetisation policy pages |
| 4 | AI-content **disclosure** obligations per platform | Already partly known; changes often | First-party disclosure policy |
| 5 | Format limits for the platforms in §4 marked third-party or conflicting (LinkedIn, TikTok) | The current row is third-party evidence only | First-party help page |
| 6 | Whether an automated-posting **cost** applies (X is already noted as pay-per-post, ~$0.015 per post) | Any paid path needs explicit owner approval | First-party pricing page |
| 7 | Music/font licensing for monetised video per platform | Separate from software licensing; a track that is fine for a private upload may not be for monetised | First-party audio-library terms |
| 8 | Safe-zone geometry per platform, per aspect, with a date | Currently hard-coded heuristics | First-party UI documentation, or a dated measurement |

**And the standing rule from the existing matrix:** every asset (music, stock clip, font, image, voice) gets a row in a
rights ledger with a source URL, licence, attribution text and approver; QA fails if a used asset has no row.

---

## 7. What must never be claimed

These are the failure modes to design against, stated plainly so a future agent does not quietly reintroduce them:

1. **"All platforms support the same formats, APIs and monetisation."** They do not, and the current research shows
   disagreement *between first-party and third-party sources* on at least two platforms.
2. **"Automated publishing is available."** It is not built, publishing is disabled, and no upload adapter exists. Any
   publish work needs research items 1–6 first.
3. **A duration is valid because a vendor says so.** The checker must cite the first-party row it used.
4. **A niche is production-ready because it sounds appealing.** A niche module is `validated` only with real render
   evidence on this machine, and the schema should refuse `validated` without it — exactly as `style/1` does.
5. **A platform's limit from memory.** Re-read the first-party page; limits moved twice in the period the existing
   `platforms.json` was written.

---

## 8. The ordered path to expansion (detail in doc F)

1. **Nothing platform-related.** Fix the correctness items and finish the creative layer first — a per-platform adapter
   built on an unvalidated look multiplies an unvalidated look by N.
2. **Move safe-zone geometry from code to `config/`, marked `unverified`, with a dated source.** This is the one
   platform-adjacent change that is safe now, because it is a data move that removes a hard-coded heuristic.
3. **Build the niche contract and one niche as data**, using the existing `content_type` vocabulary so no new code path is
   created.
4. **Add one packaging field at a time**, starting with the hook-per-target split, because it is pure data derived from the
   existing hook framework.
5. **Only then** research items 1–6 and consider a publish adapter — which remains disabled by policy until the owner
   approves both the research and the change.
