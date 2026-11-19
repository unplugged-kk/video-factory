# Architecture findings (independent pass 2)

Branch `feat/p1-1-lookmap`, HEAD `86eeaa2`. This is the review the `architect` agent was assigned twice and
could not deliver (HTTP 429 both times), re-run under a working model. It reads a first pass at
`ARCHITECTURE_FINDINGS.md` and marks each claim **CONFIRMED**, **FALSE** or **INCOMPLETE**, with the evidence.

## 0. Verdict on the first pass, up front

| First-pass claim | Verdict |
|---|---|
| `visual_layer.py` holds a hardcoded backdrop table | **CONFIRMED** - `visual_layer.py:15-29` |
| Palette/typography/layout come from `visual_layer` + `style_card` | **FALSE** - see §1.2. They are hardcoded in the composer's f-string. |
| `style_card` is wired only into the Remotion lane; HyperFrames has no equivalent call | **FALSE** - `pipeline.py:247` calls it on the HyperFrames path |
| `intelligence/looks.py` is the only reader of `config/presets`, and only validates | **CONFIRMED** - its whole API is `load_dir/check/validate_all/combine/main` |
| `lookmap.py` does not close the gap | **CONFIRMED, and stronger** - the module's own docstring says so |
| `extra_gates.check_end_hold` returns PASS unconditionally | **CONFIRMED** - `extra_gates.py:47` |
| `RESEARCH_APPROVED` granted, never enforced | **CONFIRMED** - 2 hits repo-wide, both grants |
| `local-first-policy.yaml` `exceptions:` is dead | **CONFIRMED** - `providers.py:47-48` reads only `allow_paid` |

The first pass got the diagnosis right and two of the mechanics wrong. The wrong mechanics matter, because
they point the fix at the wrong file.

## 1. Spec to pixels, for real

### 1.1 There is no single compose path. There are three, chosen by three different spec keys.

`pipeline.py:234-245`, in order:

1. `spec["render"] == "remotion"` → `renderers/remotion.py`
2. `spec["render"] == "mpt"` → MoneyPrinterTurbo
3. `spec["visual_style"]` truthy → `scenekit.compose` (`pipeline.py:239-245`)
4. otherwise → the inline HyperFrames template (`pipeline.py:246-315`)

**`spec["look"]` is read by nothing.** I grepped for every form of the key: the only hits are inside
`lookmap.py` itself. So a spec carrying a `look:` id reaches a composer that has never heard of the field,
which falls through to branch 4 and emits the same bytes. That is the whole bug in one sentence, and it is
sharper than "the builder does not read presets" - the field name does not even appear on the path.

### 1.2 The default composer is a hardcoded f-string, and that is where the pixels come from

`pipeline.py:301-315` writes `project/index.html` from one f-string. Every visual constant is inline:

- `pipeline.py:303` - `background:#090a0f` on `body`; `#root` = `radial-gradient(circle at 50% 20%,#1a1e36,#08090e)`
- `pipeline.py:304` - `.scene` grid rows `minmax(0,1fr) auto`, `row-gap:40px`, `padding:120px {side_padding}px {bottom_padding}px`
- `pipeline.py:306` - `.tag` `font:700 34px ui-monospace`, `color:#a5b4fc`
- `pipeline.py:307` - `h1` `font-size:{int(U*0.085)}px`, `font-weight:900`
- `pipeline.py:308` - `.cap` `font-size:{int(U*0.058)}px`, `color:#fff`
- `pipeline.py:294` - caption highlight colour `#fbbf24` is literal in the GSAP tween

None of these read any config file. **This**, not `visual_layer.py`, is the module whose literals decide the
frame.

### 1.3 What the two hooks actually change, on the default path

Both are called on the HyperFrames path - `pipeline.py:247` (`style_card`) and `pipeline.py:283`
(`visual_layer`) - so the first pass's "Remotion only" claim is wrong. But both are **off by default**:
`registry.get()` returns a pass-through unless `spec['features'][name]` is truthy (`registry.py:56-60`).

When enabled, `visual_layer_hook` does exactly two things (`visual_layer.py:56-63`, `109-115`):

- replaces the scene's opening `<div class="scene clip" id="sN"` with a version carrying
  `style="background:<BACKDROP>"` - the backdrop chosen as `BACKDROPS[(scene_idx-1) % 7]`
  (`visual_layer.py:57`), i.e. **indexed by scene number, never by look**;
- prepends one absolutely-positioned `<div class="visual-decor">` at `z-index:0` with a border-radius
  string chosen by substring-matching six family names (`sketch`, `product`, `kinetic`, `data`, `spatial`,
  `hybrid`) against `style_id` (`visual_layer.py:71-104`).

It never touches `#root`'s background, the `h1` size, the caption colour or the grid. So even with the
feature on, two looks differ only in a per-scene backdrop that cycles by position, and a decoration's corner
radius. **Two different look ids therefore cannot produce different frames.** That is the mechanical proof.

`style_card_hook` is the one hook that genuinely carries style *data* - it sets `ctx["style_card"]`
(`style_card.py:117`) after selecting a card - but the only consumer of `ctx["style_card"]` is the
`style_id` substring test above, so it too reduces to six decorations.

## 2. Style data and its readers

| Location | Read by | On compose path? |
|---|---|---|
| `config/presets/` (57 files) | `intelligence/looks.py` only - validate/list/combine | **No.** Dead data. |
| `config/design-library.json` | `intelligence/designs.py:35` (recommender) | **No** |
| `config/motion-catalogue.json` | `intelligence/catalogue.py:25` (catalogue join) | **No** |
| `config/visual-languages.seed.json` | `intelligence/visual.py:47` (output ledger) | **No** - it records what shipped |
| `config/styles/*.json` (3 files) | `intelligence/styles.py`, `intelligence/creative.py` | **No** - "Shadow mode: no pipeline reads cards yet" (`intelligence/styles.py:9`) |
| `contentos/scenekit/styles.py` | `scenekit.compose` | **Yes**, but only on the `visual_style` branch. It defines styles in **Python**, not JSON - it does not open `config/styles/` at all. |

So the arrangement is worse than "one dead catalogue". There are **two parallel style vocabularies with
disjoint data stores**: `look/1` presets (dead) and `scenekit-style/1` (live, Python-only, unreachable from
the default path). `config/styles/` is a third, shadow-mode set that feeds neither.

`contentos/intelligence/*` is a coherent advisory layer - six modules, real schemas, real validators - and not
one of them is imported by a composer.

## 3. Smallest edits that make `spec['look']` change frames

1. **`pipeline.py:234`** - add a dispatch branch: if `spec.get("look")`, resolve it through
   `intelligence.looks.load_dir()` + `scenekit.lookmap.to_style()` and route to scenekit, or inject the
   resolved values into the template below. Without this branch nothing else helps.
2. **`pipeline.py:303-308`** - replace the six literal colours/sizes in the f-string with values from that
   resolved style, falling back to today's literals when no look is given, so existing output is
   byte-identical.
3. **`visual_layer.py:57`** - choose the backdrop from the resolved style instead of
   `(scene_idx-1) % len(BACKDROPS)`. Until this line changes, backdrop variety is a property of scene count,
   not of style.

**On the uncommitted `lookmap.py`:** it does not close the gap, and it says so itself -
`lookmap.py:1`: *"P1-1 M1, compile only, nothing in the pipeline calls it yet"*. `to_style`
(`lookmap.py:148-203`) and `compile_all` (`lookmap.py:216-225`) are a genuine translator from `look/1` to
scenekit styles, with contrast and luminance maths a recolour cannot game. It is the right half. But it emits
into `st["look"]` (`lookmap.py:200`) for a scenekit state dict, and scenekit is only reachable via
`visual_style` - a key nothing sets today. So it inherits the same defect one level down: **a translator with
no caller.** Edit 1 above is what turns it into a capability.

## 4. Controls that are recorded but never enforced

| Control | Location | What happens when it says no |
|---|---|---|
| `RESEARCH_APPROVED` | granted `pipeline.py:615`; 2 hits repo-wide, both grants | nothing reads it |
| `check_end_hold` | `features/extra_gates.py:38-47` | returns `PASS` unconditionally; `END_HOLD_WARN_SEC = 3.50` (`:20`) is unused |
| whole Lane F | `features/extra_gates.py` | all three gates return only PASS/WARN; `s_qa` aborts only on FAIL (`pipeline.py:337-338`) → the abort is unreachable via this lane |
| `exceptions:` | `config/local-first-policy.yaml:15` | `providers.py:47-48` reads `tier_rank` and `allow_paid`; `exceptions` is never read |
| `visual_layer` Rule A | docstring `visual_layer.py:3` claims "≥ 4 distinct in 7 scenes to satisfy Rule A" | the rotation is mechanical, so the rule is satisfied by arithmetic, not by design |

The pattern is consistent enough to state as a rule for future review: in this codebase, **existence of a
control proves nothing; only the call site that handles its negative case proves anything.** Five of the
audit's real defects were exactly this shape.

## 5. What I did not verify

- Whether any real spec on disk sets `visual_style` (so whether scenekit has ever rendered). Not checked.
- `scenekit.compose` beyond its entry point and `styles.py`'s headers.
- The Remotion path, beyond confirming `pipeline.py:234` and `remotion.py:78`.
- No renders. Every claim here is from source, not from frames.
