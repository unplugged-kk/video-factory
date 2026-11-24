# Approval policy decision (PF-02, PF-03, PF-07)

Status: PF-02 approved by Kishore in the Phase 2 execution directive; implementation pending the sealed, authoritative subject. No gate definition or publishing change. PF-03 and PF-07 below remain designs.

## PF-02: approved owner decision

At `849ea6a` the CLI already supports a read-only `--show` and optional `--expect`; plain approval is still allowed. Studio's `POST /api/v1/jobs/{id}/approve` already rejects a missing or stale `seenDigest`. The digest alone does not fix an incomplete dependency subject.

**Approved:** Require explicit confirmation for human `SCRIPT_APPROVED` and `PRODUCTION_APPROVED` on every write surface. Keep the existing positional CLI shape so a job's two gates remain unambiguous:

```sh
./contentos.sh approve JOB_ID PRODUCTION_APPROVED --show
./contentos.sh approve JOB_ID PRODUCTION_APPROVED --expect SHA256_DIGEST
```

`--show` records nothing. Studio displays the exact script/title or sealed composition preview and dependency listing, and submits the digest displayed for that review. CLI and API use the same gate, job and subject validation before a grant is written. Preserve explicitly authorized private automation as a separate audited path, never an implicit substitute for a human grant. Do not retrofit an unbound historical grant into a bound one. Owners who script plain `approve` must migrate; publish remains disabled and not exposed by this policy.

The shared approval service must compare the authoritative expected digest atomically with the grant write and record authenticated human attribution. A database transaction by itself cannot freeze filesystem bytes; the transaction must bind the current sealed subject and revision. Missing, malformed, incorrect and stale confirmations fail, with no fallback. Private automation must use a separate authenticated principal with explicit job/gate scope, content binding and auditable attribution. A failed human approval must never convert to automation. The current private flag does not prove these properties.

Tests to carry into the approved migration: read-only show, missing/malformed digest, mismatch without new grant, successful confirmation, matching rules across CLI/API/Studio, nonmatching job/gate/snapshot, concurrent change, existing legacy rows, and explicit private-run policy. Existing `test_pf02_*`, `test_pf26_*`, `test_pf29_*` and Studio digest tests are starting coverage, not proof of mandatory confirmation.

## PF-03: metadata boundary

- Production approves script and render inputs. Export approves exact attested media plus an export envelope: intended project/destination, approved sidecar metadata where it ships, and provenance. Export validation continues to fail closed on missing render attestation.
- Publishing would independently approve target platform and account, title, description, thumbnail bytes, tags, category, language, audience, visibility and scheduling. Normalize explicitly; no silent defaults from `manifest.json`. Any change invalidates that approval, not the production identity. No upload path is authorized.

## PF-07: supersession boundary

Retain append-only approval history keyed to job, gate, digest and ordered approval revision. Define one current grant per job and gate. A transaction must make a successful replacement or revocation visible atomically; check the current revision again at export commit. Test concurrent approvals, failed replacements, wrong job and digest, revocation, and reversion of content. Reverting bytes does not restore a superseded grant. Decide legacy migration and private-run interactions together with PF-02 before changing grant semantics.
