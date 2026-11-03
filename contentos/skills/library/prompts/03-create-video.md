# Prompt: Create a video through Video Factory

Inspect the repository instructions and the live capability registry first. Parse the request and resolve the relevant skill(s) from `config/skill-catalog.json`.

Inputs:
- Request/topic/script/audio/video: [provided by user]
- Target platform and aspect ratio: [infer if clear; otherwise ask]
- Language and duration: [provided or recommend]
- Style: [explicit user choice or creative-director recommendation]

Workflow:
1. Validate inputs and source rights.
2. Analyze the content and recommend a style if none is specified.
3. Select only skills that add value; explain overlaps and capability gaps.
4. Produce or update the authoritative episode manifest and timeline.
5. Generate a storyboard/contact sheet or low-resolution preview.
6. Follow the factory's script/production approval gates.
7. Render with the existing backend and run technical, audio, caption, safe-zone, visual, and content QA.
8. Fix failures and re-run affected checks.
9. Package the video, manifest, preview, QA report, asset ledger, and publishing metadata.
10. Stop before publishing unless explicitly approved.

Do not claim completion without a verified output path and actual test/render results.
