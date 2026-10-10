# Decision engine (what to decide, and how to show your work)

Status: the *procedure* below is usable now by an agent. A `decide.py` that automates it is planned (slice 2); do not pretend it exists.

## 1. Classify
Pick 1-3 content types from: explainer, tutorial, product-demo, data-story, announcement, opinion, story, news, social-proof. A hybrid names the dominant type first; techniques and pacing follow the dominant type, the secondary type only adds sections.

## 2. Objective and audience
Write: audience (and what they already know), the single takeaway (one repeatable sentence), the action wanted (learn / try / follow / share / none). Different objectives for the same topic must give visibly different plans: a *learn* explainer shows the mechanism step by step; a *share* piece leads with the surprising claim and shortens the middle.

## 3. Format: hard constraints first, then score
Hard constraints (eliminate, do not score): platform maximum length and aspect (`platforms.py`), audio required or not, offline/paid limits, renderer availability. Then rate the survivors 1-5 on: retention fit, clarity of the takeaway, production cost, reuse across platforms, risk. Show the ratings and the reason for each; the numbers are your judgement and must be labelled that way.

## 4. Techniques, integrations, workflow
Techniques: catalogue query per scene purpose (`motion-selection.md`). Integrations: only tools whose status in `doctor`/`capabilities.json` is usable *for the claim you rely on*; an untested tool is "unverified", and an unverified tool is never the only path. Workflow: HyperFrames by default; the mpt lane only for stock-footage videos.

## 5. Record (see `templates/decision-record.example.json`)
Fields: request, classes, objective, audience, format (with eliminated options and why), techniques per scene with catalogue score components, integrations with status and fallback, expected bottlenecks, evidence cited (path or measurement), uncertainty (what you do not know and the cheapest test), approvals needed. Every recommendation cites evidence or says "no evidence yet".
