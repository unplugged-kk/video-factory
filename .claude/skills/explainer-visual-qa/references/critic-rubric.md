# Critic rubric (explainers)

You did not build this video. Judge only what is visible and audible plus the brief and research notes. Ignore the builder's explanations. A clean generic template fails.

Inspect: the brief and research notes, the narration text, contact sheets for each format at phone scale, the two frames around every scene cut, the QA report numbers.

## Scores, integer 0-10 each
- `hook_clarity`: the first 3 s state the value in the viewer's words, not subject jargon.
- `concept_specificity`: visuals could only belong to this subject; each key visual traces to a line of the script or research.
- `readability`: essential text and the focal action are legible at phone size.
- `composition`: hierarchy, framing, safe zones, no clipping, no large dead areas.
- `motion_causality`: motion explains cause and effect; nothing moves only to look alive.
- `continuity`: one persistent world; no snaps or pops at cuts; transitions carry meaning.
- `av_sync`: reveals and captions land on the spoken words.
- `restraint`: no decorative effects competing with the subject.

## Hard failures (any one forces `reject`)
`fabricated_data_unlabeled`, `text_clipped_or_unreadable`, `caption_out_of_sync`, `brand_mark_misuse`, `claim_unverified`, `dead_or_black_frames`, `generic_template_look`.
Invented but clearly labelled illustrations (for example an "ILLUSTRATIVE" tag) are not fabricated data.

## Output
JSON only, `critic: "independent"`, `scores`, `hard_failures` (list of ids), `verdict`, `notes` (each with `issue`, optional `time_s`). Cite a timestamp for every score below 8. The verdict must follow the scores: `python -m contentos.production.critic` recomputes it.

Adapted from the scored critic in Liamrjohnston/remotion-motion-graphics-skill (MIT), rewritten for narrated explainers.
