# Phase 2 dependency identity (PF-22 / PF-23)

Status: proposed design, not a manifest implemented in the pipeline. Baseline `849ea6a`.

## Observed boundaries

- `contentos/pipeline.py:production_digest` hashes the composition tree and selected WAVs. A path mentioned by a document is not evidence of its target's bytes. Track A and Track B both use the production subject; registered hand-built jobs instead bind the finished video.
- `contentos/mpt.py:request` validates local material paths under the jobs root and emits container paths. `compose` writes the request and joins narration; `render` passes those paths into Docker or passes stock search terms. Neither those local media bytes nor stock selected at render time appear in the production digest. `assets-rights.json` is written after the render, hence not review evidence. Actual container selection behavior remains unverified.
- `project_remotion/node_modules` is currently a mutable linked toolchain exception. An asset cannot use that exception as a provenance or containment policy.

## Proposed contract

1. Each renderer supplies a complete list of job-controlled inputs and explicit runtime requirements. Resolve inputs before production review. For declared external files, copy bytes into the reviewed project; validate regular files and containment by descriptor-relative traversal, without following symlinks at the snapshot boundary. Import outside files only as explicit sources, never by renderer fallback. Reject missing, malformed, special, or unstaged inputs.
2. Manifest entries are canonical records with a project-relative logical path, input role, byte size, SHA-256, and source and rights information. Provenance distinguishes an original URL or local supplier from the actual bytes; rights distinguish a verified license from user-supplied or unknown terms. Neither URL nor filename is identity. Do not record auth query parameters, tokens or credentials. Specify path normalization and bytewise ordering, reject duplicate paths and aliases, and hash canonical structured bytes with a version/domain tag. Render verification recomputes the identity from actual staged bytes, not a claimed digest field.
3. Include script, normalized production spec, composition HTML/JS/CSS/config, stills, video, B-roll, narration, audio bed inputs, music, effects, and deliberately selected fonts. Record toolchain versions separately; resolve system fonts explicitly or document the dependency as unverified. Bind publishing metadata to its own reviewed envelope, not to mutable job state or by implication from a production approval.
4. Resolve stock search and download before production review, then render with exactly the staged material list. For MPT, call the local-material flow for both supplied media and prefetched free stock; preserve stock origin and rights in the authoritative manifest. Verify with a mocked MPT boundary, then with the real container only if available. A remote-source fallback must fail closed, not substitute media.
5. A manifest does not confine the renderer. HyperFrames and Remotion can execute JavaScript and resolve dynamic resources; static HTML/CSS parsing is lint, not a security boundary. Test effective deny-by-default filesystem and network access for each lane, including renderer subprocesses. Until a lane can enforce this, do not claim it meets PF-22.

## First acceptance slices

- Walk completeness: missing symlink target or unreadable composition directory yields no current production digest. Keep existing valid digests unchanged.
- MPT local staging: moving an original input after staging is safe; a missing/corrupt staged input yields no acceptable digest. Capture container argv and verify that it contains only reviewed paths. Verify legacy requests cannot silently use unstaged inputs. Test material order and provenance as well as individual hashes.
- All lanes: test a changed path target, missing file, alternate path spelling, external CSS/font/media and denied resource access, then prove normal render and export from a sealed snapshot. Do not expand the lookmap asset surface before this boundary is enforced.
