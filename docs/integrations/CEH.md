# CEH metadata provider (opt-in)

This standalone provider is disabled by default. It does not participate in pipeline routing, approvals, rendering,
ContentForge or publishing. Existing workflows continue even when CEH is absent or invalid.

`python -m contentos.ceh_catalog --task "kinetic typography"` returns a disabled fallback.

For an independently reviewed catalog snapshot:

```
python -m contentos.ceh_catalog --enable --catalog /absolute/path/catalog.json \
  --trusted-digest REVIEWED_SHA256 --task "kinetic typography" --renderer hyperframes \
  --environment /absolute/path/measured-environment.json
```

The environment declares measured runtimes/dependencies (name to numeric version), inputs, available asset ids,
agent, language and output_format. Unknown or incompatible requirements reject selection. No package manager, import,
network request, shell command or external skill loading follows catalog metadata. Guidance steps are returned as data;
they must not be treated as execution authority. Use existing job, script/production approval and QA workflows.

The v2 contract validates strict fields, explicit approval evidence, licence restrictions, exact provenance, entry and
catalog digests. A digest alone is not identity or authenticity. The trusted digest must come from independent review,
not be copied automatically from an untrusted file. Every catalog update requires a new reviewed digest.

The local ceh_contract.py is a reviewed protocol implementation snapshot of CEH ceh/catalog.py. Contract conformance
fixtures are tested with both implementations before updating. No live CEH Python dependency is loaded by VF.

Rollback: leave --enable absent. This branch introduces only new files; remove its modules/docs/tests or revert its
commit after deployment approval. No production configuration needs undoing because none was changed.
