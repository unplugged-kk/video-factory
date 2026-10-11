# Jev evaluation - repository assessment (Phase 2)

Date: 2026-10-11. Nothing was installed or executed from any upstream repository. All upstream reading was through web
fetches of public pages and registries. Labels: **[verified]** seen directly in a fetched page/registry or in local code;
**[doc]** stated by upstream docs, not tested; **[claim]** upstream marketing/qualitative statement; **[not verified]** I could
not check it.

Caveat on method: the GitHub pages were read through a fetch tool that returns a summary of the page, not raw bytes, and
three requests failed (GitHub `src/` tree listing: robots-blocked; GitHub REST API for commits/repo metadata: client error;
`docs.typesafe.ai` sub-pages were not fetched). So **no upstream source file of the extension was read**. Findings about its
internals come from its README, `package.json`, `CHANGELOG.md` and `docs/implementation.md`.

## 1. The candidate: `championswimmer/pi-skill-picker-jev`

| Item | Finding |
|---|---|
| URL | `https://github.com/championswimmer/pi-skill-picker-jev` - exists, public [verified]. The page did not present it as a fork (it has 1 star and 1 fork of its own); I did not check for a parent repo explicitly |
| Maintainer | owner account `championswimmer`; npm maintainer `championswimmer`; `package.json` author "Arnav Gupta" [verified]. I did not check whether this person is affiliated with TypeSafe |
| License | MIT (sidebar + LICENSE file listed; `package.json` `MIT`) [verified] |
| Releases | no GitHub releases/tags; npm: 0.1.0 (2026-09-30), 0.1.1 (2026-09-30), 0.2.0 (2026-10-01), **0.3.0 (2026-10-06, latest)** [verified, npm registry] |
| Maturity | first publish 11 days ago; four versions in six days; 44 commits on `main` (page); 1 star. Commit dates **[not verified]** (API fetch failed). Very young, single maintainer |
| What it is | a **Pi coding-agent extension**: `pi.extensions: ["./src/extension.ts"]`; peer dependencies `@earendil-works/pi-coding-agent` and `pi-tui` `>=0.87.1`; Node `>=22` [verified] |
| What it does | at agent start it ranks the skills Pi discovered against the current task and replaces only the skills section of the system prompt with the selected subset; commands `/skill-picker`, `/skill:name` [doc] |
| Backends | (1) hosted default via **OpenRouter** with model `typesafe/jev-1.13`, needing Pi's OpenRouter credentials; (2) a user-supplied "TypeSafe-compatible HTTP endpoint"; (3) Pi's own classifier mode [doc]. So the default path is **not** a direct TypeSafe API call and does not use the official SDK |
| Dependencies | no runtime dependencies in any version; dev: typescript ^5.9, @types/node ^22.15, Pi packages 0.99.2 [verified, npm + package.json] |
| Data sent (hosted) | the current request, bounded recent conversation context, completed tool text (depending on trigger mode), skill names and descriptions; not full skill files [doc] |
| Failure behaviour | **fail-closed**: if ranking fails or credentials are missing, the full catalog stays hidden (not replaced by "show everything"). Separate gate: skip filtering when fewer than 30 eligible skills (`minSkills`, default 30; 0 disables) [doc] |
| Scoring | score-style usefulness ratings, normalized, "not probabilities"; defaults threshold 0.625, maxNew 6; batches of 50 skills, up to 6 concurrent requests [doc] |
| Local writes | settings in the Pi agent directory, a per-project allowlist, session entries, a JSONL usage sidecar for priced hosted decisions [doc] |
| Timeouts / retries / caching / schemas / wire protocol | **not documented** in the pages I read [not verified] |
| Tests | `npm test` = `node --experimental-strip-types --test test/*.test.ts`, plus `typecheck` and `release:check`; a `test/` dir and a `.github/workflows` dir exist [verified]. Test content, coverage and CI status [not verified] |
| Benchmarks | **none claimed with numbers** (changelog and docs give config defaults only; docs point to `docs/scoring-research.md`, not read). Qualitative claims of smaller prompts are **[claim]**; there is nothing to reproduce |

## 2. Is it usable in our stack?

- **Not as an extension.** It is built on Pi's extension events (`before_agent_start`, `context_with_system`). The agents
  that run this factory are Claude Code / Codex / Cursor; I found no equivalent hook that lets an external service replace
  their skills list, but I did not test their hook systems [not verified]. Installing it would only affect Pi sessions. Pi **is** present on the Mac (`~/.local/bin/pi`, `pi --version` -> 1.1.0 [ran]; I did not verify this is the same
  product line as the `@earendil-works` packages), but its `settings.json` `packages` list contains only `ponytail` and
  `pi-commandcode-provider` [ran]: **the skill picker is not installed there**.
- **Only the idea transfers**: rank installed-skill descriptions with a classifier instead of listing all of them. The
  `Candidate A` baseline I measured [ran, 2026-10-11]: `~/.claude/skills` has **436 entries, 25 dangling symlinks, 408 readable
  `SKILL.md`**, whose descriptions total about 125.6k characters (**~31k tokens, an estimate at 4 chars/token**, not a
  measured tokenizer count; real injection into any model request was not measured). The project-local set
  (`.claude/skills`) is 8 entries, ~2.5k characters, so for the factory's own workflows the catalog is already small. The
  extension's own 30-skill gate would not even trigger there.
- **Our real constraint is runtime hooks, not Jev.** A Claude Code agent cannot be handed a pre-filtered skill list by an
  external service without a hook we have not verified; that needs its own investigation before any Jev call is worth
  measuring (see recommendation in section 6).

## 3. TypeSafe, the SDKs and the API

| Item | Finding |
|---|---|
| Product | TypeSafe AI "System One" models answer typed questions about a state and return structured results; Jev is the flagship System One model [doc, `docs.typesafe.ai` landing page] |
| Primitives | `choice` (returns choice, probabilities, confidence), `score` (score, probabilities, confidence), `noul` (value 0-1; confidence not stated) [doc]. Docs recommend atomic questions combined in your own code, and say questions in one request run in parallel and in isolation [doc] |
| JS SDK | `typesafe-ai/typesafe-sdk-js`, MIT, 5 commits; npm `@typesafe-ai/sdk` **0.6.0 (2026-09-15)**, versions 0.0.0-bootstrap.0 / 0.5.7 / 0.6.0, no dependencies, Node >= 20, maintainers `alliesafe`, `diogo149`; quickstart `new TypeSafeClient()` + `systemOne` with a `choice` question; key via `TYPESAFE_API_KEY` [verified] |
| Python SDK | `typesafe-ai/typesafe-sdk-python`, MIT, 3 commits, 7 stars; `uv add typesafe-sdk`; `client.system_one(...)` with `Choice(instructions=..., criteria=...)`; key via `TYPESAFE_API_KEY`. PyPI listing and Python version [not verified] |
| Both repo URLs given in the brief | exist and are under the `typesafe-ai` org [verified]. Releases sections on GitHub are empty; releases exist on npm only |
| Wire protocol | not in any page I read. **It is visible in ContentForge's working client** (`server/decision/jev.ts`) [verified, local code]: `POST {TYPESAFE_BASE_URL or https://api.typesafe.ai/v1}/systemone`, header `Authorization: Bearer <key>`, JSON `{state, model, questions}` with `model` default `jev-latest`; response `{model, answers{id: {type, ...}}, usage{input_tokens, output_tokens}}`; 3 attempts with 500 ms / 1 s backoff on 429 and 529; timeout 30 s (`TYPESAFE_TIMEOUT_MS`); keys redacted from error text. A comment in `format.ts` says the `choice` contract (string `instructions`, object `criteria` whose keys are the options) was "verified against the live API" [doc, owner's note] |
| ContentForge does **not** use the official SDK | `jev.ts` calls `fetch` directly (no `@typesafe-ai/sdk` import). Drift risk if TypeSafe changes the protocol; the SDK is 4 weeks old and pre-1.0 |
| Latency, pricing, rate limits, retention, privacy terms, SLAs | **not documented** on the pages I could read [not verified]. ContentForge's map targets "p95 < 1 s" as a goal, not a measurement |
| What leaves the machine | the full `state` and `questions` JSON you send. Anything we pass (scripts, research text, internal skill names) goes to TypeSafe (and to OpenRouter in the extension's default mode) |

## 4. Authentication and secrets

- API: `TYPESAFE_API_KEY` bearer key [doc + local code]. CLI transport: `cmd -p ... -m typesafe/jev` using the `cmd` CLI;
  `~/.local/bin/cmd` exists on the Mac [ran]. No `TYPESAFE_*` / `JEV_*` variables are set in the shell environment [ran].
  I did not read ContentForge's `.env` or `~/.pi/agent/auth.json`.
- contentos reaches Jev only via ContentForge with a pasted session cookie (`CONTENTFORGE_COOKIE`), which expires with the
  login session. That is the practical blocker for any live measurement (401 today [ran]).

## 5. Compatibility assessment

| Question | Answer |
|---|---|
| Whole extension appropriate? | **No.** Pi-only, 11 days old, hosted default via a third party, no benchmark evidence |
| Only the decision interface reusable? | **Yes, and it already exists**: `server/decision/jev.ts` + registry in ContentForge, and `contentos/jev.py` as the adapter. The extension adds nothing we lack for typed decisions |
| New runtime dependency? | none needed. The official SDK would be optional (replace hand-written `fetch`); not required |
| Licensing | MIT for the extension and both SDKs. TypeSafe API terms of service [not verified] |
| Conflict with mandatory rules | none identified, provided any Jev call stays optional and fails open/closed as ContentForge declares |

## 6. What this means for the next phases (recommendation so far, not final)

1. **Do not install the Pi extension.** It cannot be wired into our agents and offers no measured advantage.
2. **Do not build a second `DecisionProvider` stack in contentos.** ContentForge already owns the Jev transport, schemas,
   policies, fallback classes, ledger and shadow harness. A parallel one in contentos would break the "no second
   orchestration framework" rule. Any new video-production decision type should be **a new definition in ContentForge's
   registry** (or a contentos-side *client* of that engine), and only if it clears the benchmark.
3. **Measurement is the real work.** The strongest candidates by feasibility are the bounded-choice ones with a closed option
   list (video format strategy B, scene treatment D, renderer/capability choice C), because the existing capability registry
   already gives closed option sets and deterministic validators. Candidate A (skill selection) is a different problem
   (runtime hooks) and Candidate E (failure triage) already has a working deterministic classifier with only three classes.
4. **Blockers needing you** (nothing else blocks Stage 1 offline work): a way to call Jev for measurement - either a
   `TYPESAFE_API_KEY` supplied to a benchmark-only environment, or a fresh `CONTENTFORGE_COOKIE` (and an OK to use
   TypeSafe credits); and a decision on who labels ground truth for video-production decisions.

Sources (accessed 2026-10-10/11): github.com/championswimmer/pi-skill-picker-jev (README, `docs/implementation.md`,
`CHANGELOG.md`, `package.json`); registry.npmjs.org/pi-skill-picker-jev and /@typesafe-ai/sdk; github.com/typesafe-ai/typesafe-sdk-js
and -python (landing pages); docs.typesafe.ai (landing page); local: `~/git/ContentForge/server/decision/jev.ts`,
`decisions/format.ts`, `decisions/agent.ts`, `registry.ts`, `JEV_DECISION_MAP.md`, `~/git/video-factory/contentos/jev.py`.
