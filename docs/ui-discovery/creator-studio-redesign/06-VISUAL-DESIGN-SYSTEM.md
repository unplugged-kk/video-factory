# 06 / Visual design system: Cutting Room

**Research date:** 2026-11-24. **Scope:** expressive media-led design with legible controls. **Evidence / sources:** [screens](05-SCREEN-SPECIFICATIONS.md), prior `design-system-and-visual-direction.md`, [WCAG 2.2](https://www.w3.org/TR/WCAG22/), [research](11-COMPETITIVE-RESEARCH.md). **Verified:** existing Studio includes both theme fixtures; proposed tokens not contrast-certified or rendered.

| Semantic token | Dark | Light | Application |
|---|---|---|---|
| canvas / panel / raised | `#141320 / #1D1C2B / #28263B` | `#F4F2F9 / #FFFFFF / #EAE6F3` | canvas, editor surround, overlay |
| text / secondary | `#F6F1FF / #C5BED5` | `#221D31 / #524865` | labels, details; never use disabled as secondary |
| accent / on accent | `#D7BBFF / #211634` | `#5426A1 / #FFFFFF` | one primary action, active route indicator |
| focus / boundary | `#F7C951 / #827897` | `#6B4213 / #74668C` | 2 px outline, 2 px offset; dividers cannot substitute for focus |
| good / warning / danger / info | `#7AE2B6 / #FFD083 / #FFADB9 / #A9CDFF` | `#0D6949 / #784400 / #A11939 / #1D4D91` | icon + verb + severity; text chips over panel only |

System sans with locale fallbacks and `monospace` for receipt/digest. Heading 32/38 desktop, 26/32 mobile; section 20/28; body 16/24; dense labels 14/20. No custom network fonts; test Devanagari wraps and bold weights. Space 4/8/12/16/24/32/48; radius 6 control, 12 panels, 18 media; elevations only for overlap. Desktop 12-column nominal grid, 224 px rail, main widths flexible; drawers max 420 px. Actions ≥44 px target in touch layouts; verify WCAG target size at all widths. Never crop 9:16 footage to imply content; letterbox and show aspect badge.

| Component | Contract |
|---|---|
| Media card | image/poster, title, aspect, capability chip, separate overlay-free play control with name; no autoplay in grids |
| Batch table | semantic headers, compact one-line state, explicit detail button, focus-preserving updates; persistent selected count |
| Campaign board | columns grouped by real episode status and list alternative; chip “inherits r2” or “override” with explainable origin |
| Timeline / progress | discrete stage list with timestamps and attempt numbers; determined progress only when backend emits actual numerator and denominator |
| Activity log | ordered receipts linked to stage and actor if known; no synthetic agent avatar or typing indicators |
| Status | icon + plain word, severity and evidence (Ready, Blocked, Not run, Stale, Partial, Failed, Exported) |
| Drawer / dialog | layout drawer for optional evidence; dialog for confirmation only, focus trap/restore and Escape, long digest wraps |
| Form | explicit visible labels, help linked to input, error summary after validate, disabled reason adjacent |
| Empty / loading / error | actionable text; stable skeleton for available data, no flashing; stale banner with retry; preserve unaffected content |

Colorful editorial rhythm from real posters, accent tabs and distinctive section illustrations, not dashboard KPI gradients. Use 100 ms hover, 160 ms selection and up to 220 ms drawer entry (opacity/transform); animate no status change by color alone, never animate polling. Reduced motion swaps slides and shimmer for immediate changes. Outline stays visible in forced colors; test both themes with AA text and non-text contrast, media captions, 200% zoom and high contrast, and never set error text directly over footage.

Prototype acceptance: record a contrast matrix for every used foreground/background pair, including status text on panel and raised surfaces, focus against adjacent surfaces, and non-text control boundaries. Verify 4.5:1 normal text, 3:1 qualifying large text and 3:1 applicable non-text contrast; check disabled legibility even where exempt. Do not put essential labels directly on footage. Manually check 320 CSS px reflow, 200% zoom, forced colors, reduced motion, visible/unobscured keyboard focus and long Devanagari/Odia labels even where production is blocked. Use letterboxed actual fixture media in review, not a cropped thumbnail substitute. This is an exit test, not a certification today.

**Assumptions:** system typography with local fonts is acceptable. **Open questions:** owner preference on Cutting Room vs existing Precision Workbench, and sample poster palette after contrast checks.
