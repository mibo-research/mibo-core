# MIBO Core v2.0.1 prospective amendment — DRAFT

Prepared: 6 October 2026 (JST).
Status: proposal for Operations Lead review; not approved, registered, or
execution-authorized. No approval time or registration identifier is supplied
by this draft. Codex assisted with software implementation and synthetic tests.

## Scope and prior record

This proposed version supplements MIBO Core v2.0, DOI
`10.5281/zenodo.22264635`. That version, its public files, private freezes,
authorizations, and retained attempts remain intact. This draft does not certify
completion of any pre-wave requirement at 09:00 JST.

The estimand remains the distribution returned by a prospectively frozen,
stateless, environment-closed provider API configuration. The fixed four
lineages, 24 JA/EN Query Forms and hashes, k=10, seed formula, execution order,
calibration counts, registered windows, hypotheses, analysis thresholds and
missingness policy are carried forward. The v2.0 statistical analysis plan
applies with every derived record explicitly identified as v2.0.1; records from
different protocol versions are not automatically pooled.

## Replacement for the Perplexity wire requirement in section 4

For v2.0.1, the Perplexity lineage uses the Agent API and the
`direct-model-no-tools-v1` contract:

- One exact, human-selected `perplexity/` model and one user message.
- No preset, saved profile, model fallback list, tools, skills, history,
  researcher system/developer instruction or previous-response identifier.
- Omit all tools; set `tool_choice="none"`, `max_steps=1`, `stream=false`,
  `background=false`, and `store=false`.
- Preserve the prospectively frozen output budget and supported material
  sampling/reasoning settings. Unsupported settings are not silently replaced.
- Require the exact returned model, completed response and closed-environment
  metadata. Retain a mismatching response as an environment failure, suspend
  that lineage, and do not retry or submit its remaining queue blindly.

The legacy `web_search_options.disable_search=true` field belongs to the
v2.0 Sonar request. v2.0.1 does not assert that the Agent payload contains it.
The freeze's `disable_search=true` states the declared closed condition; the
Agent adapter implements it using the contract above. Other v2.0 request rules
remain binding. `store=false` is a provider retrieval control, not an assertion
of deletion or zero provider retention; statelessness also requires omitting
every continuation identifier.

## Timing and activation

The proposed first-wave field window remains 6 October 2026 09:00 JST through
8 October 2026 09:00 JST. Window A remains 6 October 09:00–21:00; Window B
remains 7 October 09:00–21:00. No endpoint is shifted to recover preparation
time. The complete twelve-wave schedule is unchanged in the machine draft.

If approved, activation after the scheduled opening requires an explicit
Operations Lead late-activation decision made before the first confirmatory
submission. The amendment must be public under its own immutable,
version-specific identifier before the new freeze and authorization. The
planned preparation/start time may be 09:00, but registration, readiness,
freeze, authorization, executor activation and each submission retain their
actual timestamps. Any preparation delay is documented prospectively; it is
not treated as a completed 09:00 gate.

If any original v2.0 attempt is already retained for this wave, the software
blocks migration into this version under the same wave. A separate prospective
decision is required. Expired windows retain missingness; they are not extended.

## Admission and custody

The API Terms/access review, exact human-selected provider freeze, four fixed
non-confirmatory readiness checks, deterministic manifest validation, healthy
private runtime, immutable code hashes and a new human execution authorization
remain required. Catalog checks and offline unit tests alone do not authorize
collection. The bundle builder continues to produce an unsigned, unauthorized
template; it does not complete a human authorization.

All v2.0.1 attempts, retry links, failures and deviations use
`<MIBO_DATA_ROOT>/v2.0.1/<Site ID>/<Wave ID>/`. The old v2.0, v1.0 and auxiliary
archives are preserved. Wave labels and the deterministic seed remain the same,
with the protocol version and namespace distinguishing records.

## Official technical sources

- https://docs.perplexity.ai/docs/agent-api/migrate-from-sonar/how-to
- https://docs.perplexity.ai/api-reference/agent-post
- https://docs.perplexity.ai/docs/agent-api/models

The draft machine configuration deliberately has no finalized registration,
registration time, eligible provider freeze or signed execution authorization.
It is not runnable as supplied.
