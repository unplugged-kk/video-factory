# PF-05: immutable render snapshot proposal

Status: proposed; a process isolation probe ran, but no renderer uses a sealed snapshot yet. Existing pre/post hashes detect persistent changes, not every change between the checks.

## Local isolation probe

A cached `node:22-bookworm` image ran with `--pull=never --network=none --read-only` and no host mounts. A root bootstrap accepted fixture bytes over stdin into a tmpfs, made the file/root directory read-only to UID 1000, and ran an unprivileged Node child via `setpriv` with no new privileges. While the container was alive and after it signaled `SEALED`, the host changed its source. The child could not read the original host path or overwrite its staged copy and returned the original SHA-256. The host then restored the source. Evidence: `~/.contentos/checkpoints/video-factory-pf23.89gf1FNw/pf05-node-isolation-probe.log`, 14:20:07-14:20:08 IST, exit 0.

This proves the isolation mechanism for a fixture worker only. Docker daemon/control-plane access is trusted; this does not defend against an administrator or a principal allowed to control Docker. No HyperFrames browser, FFmpeg, font provisioning, MPT worker or output attestation ran in this probe. Next: use a pinned, local renderer environment and stage a real fixture plus manifest through the same no-host-mount boundary, then verify its output integrity and failure handling. Do not start a new rendering dependency or require Docker by default before that evidence.

## Threat model

Job source files and mutable job manifests are untrusted. A process can change and restore input paths while a renderer is running, and it can race mutable output paths. A sealed read boundary must isolate the renderer from those paths. A private directory and Unix mode bits alone do not protect against an equal-privilege writer who can change permissions. A read-only container mount alone does not stop a host writer. If the boundary cannot protect against the claimed writer on macOS, report that limitation and do not accept the lane as immutable. Administrator privileges and attestation-store compromise are outside the first proposed boundary.

## Lifecycle

- Resolve and stage dependencies per `DEPENDENCY_INTEGRITY_DESIGN.md`. Flatten declared symlink inputs into copies before sealing. Never hardlink the mutable source. Create an isolated immutable view, verify the canonical manifest against it, then show the review artifact from the sealed view.
- Bind approval and render attempts to the same job ID and snapshot digest. Give the renderer the snapshot view plus a separate isolated writable output area. Deny mutable source and network reads instead of relying on `cwd`. No live project path, ambient side input, or download-on-demand can influence frames.
- Validate and hash the renderer's output before it is exposed to the mutable job path. Prefer opened immutable output bytes for QA and ledger hash rather than separate reopen-by-name operations. Atomically install output and persist a ledger record binding job, snapshot, lane/toolchain, exact bytes and validation. Treat a crash between file publication and attestation as incomplete and not exportable. Validate exact attested bytes at export and retain the existing export-time digest check.
- Pipeline and Track B share the same sealing and attestation contract. Track B registration is an import of finished bytes, not proof of the rendering inputs, and must keep that distinction. MPT uses staged-media requests and a confined mount, not the shared jobs tree. Remotion's toolchain exception must not allow job media reads.

## Implementation order and acceptance

1. Prototype a sealed input boundary for HyperFrames and demonstrate filesystem/network confinement with an actual process before widening it. Evaluate a least-privilege render worker or verified read-only filesystem view owned by a different authority. Do not add Docker as a default dependency without that evidence.
2. Wire it through one Track A lane, then Track B, Remotion and MPT. Verify each bridge; a snapshot copy used as working directory without confinement is not sufficient.
3. Test replacement, deletion, symlink or directory substitution, concurrent source edits, edit-and-restore, staged B-roll changes, snapshot corruption and output replacement. An edit-and-restore test must either show the renderer never read the substituted bytes or reject the result, and must prove no untrusted output is attested or exported. Repeat with real renders where prerequisites exist.
