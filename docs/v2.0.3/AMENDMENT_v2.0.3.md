# MIBO Core v2.0.3 prospective Gemini Priority amendment

Operations Lead: Kento Sasano. The explicit instruction to change Gemini to
Priority processing was received on 6 October 2026 at 11:16:30 JST
(2026-10-06T02:16:30Z). This is approval of the configuration change, not a
completed private execution authorization or proof of account eligibility.

## Scope

This version supplements v2.0 (DOI 10.5281/zenodo.22264635), the immutable
v2.0.1 Agent amendment at
https://github.com/mibo-research/mibo-core/blob/3045cbacaa15d19699deb8e79d1c7465b7d2f343/docs/v2.0.1/AMENDMENT_v2.0.1.md,
and the v2.0.2 lineage admission amendment at
https://github.com/mibo-research/mibo-core/blob/71bd6cf4c3267ddf655eed21935837b19d54b030/docs/v2.0.2/AMENDMENT_v2.0.2.md.
The Google model remains gemini-3.8-flash, GenerateContent v1beta, output budget
4096, with temperature/top-p/reasoning overrides omitted. Add only the explicit
top-level request-body field service_tier="priority" to its material wire profile.
No model, endpoint, tools, query, seed, k=10, hypothesis, threshold, registered
window or confirmatory technical retry rule is changed.

## Access, pricing and returned tier

Official Google documentation makes Priority available to Tier 2 and Tier 3
projects, at a per-token price 75–100% above Standard. An active billing account
alone is not evidence of eligibility. Google can automatically downgrade a
Priority request to Standard when dynamic Priority limits are exceeded; those
requests are billed at Standard rates. This amendment approves requesting
Priority, including this documented provider-side downgrade behavior. It does
not claim a strict always-Priority service or guarantee resolution of HTTP 503.

The client never resubmits a request as Standard, changes a model or chooses a
profile based on an answer. It retains the requested service_tier, the actual
x-gemini-service-tier response header and provider modelVersion, when supplied,
alongside the request, response, usage and real times. A successful confirmatory
response processed as Standard is retained and marked as a provider downgrade,
not retried to obtain a preferred tier. Missing/unknown tier metadata is explicitly
marked unknown, never asserted to be Priority. Header monitoring does not change
the interpretation of valid refusals, safety responses or nonanswers.

## Prospective readiness and admission

Publish this immutable registration before the new private Google profile
freeze and any affected confirmatory request. Only Google may execute under
v2.0.3. The unaffected OpenAI, Anthropic and Perplexity configurations and their
sealed v2.0.2 services continue unchanged. Their prior passing technical evidence
may be carried as cross-version provenance after exact profile and hash checks;
it does not authorize new v2.0.3 submissions for those three lineages.

The controlled VM runs a fixed non-confirmatory Google readiness prompt with
the requested Priority profile. Technical readiness requires an HTTP success,
the exact requested model route and an actual response header reporting Priority.
The current account's Priority access remains unverified until this evidence
exists. A Standard or missing/unknown header is preserved but does not pass
Priority readiness or authorize collection. One documented new-profile readiness
block permits one probe plus at most two technical retries, at least ten minutes
and then an additional thirty minutes apart; honor longer Retry-After and preserve
all prior Standard and Priority failures. A mismatch or ambiguous tier stops the
block rather than repeatedly buying probes. After a PASS, display the concrete
new hashes and obtain a separate private human Google execution authorization.

## Wave linkage and custody

The full W01 intended design is still four lineages and 1120 rows, with 280 Google
rows. A v2.0.3 full manifest preserves all original logical Attempt IDs, query
hashes, deterministic order, seed, replications and windows. Only its 280 Google
rows are executable. It prospectively replaces the still-unsubmitted Google
v2.0.2 path; it does not overwrite an old manifest or pretend the manifests have
the same configuration hash. Record a row-ID mapping and both hashes. If any
Google confirmatory request/failure already exists in an older version, block
this migration rather than replaying its full queue. Keep the old evidence and
obtain a separate prospective continuation design before changing such a path.

Google attempts, errors, retries and deviations use v2.0.3/JP01/MIBO2-W01/.
The other three lineages retain their v2.0.2 namespace and immutable freezes.
A wave-level provenance table identifies each lineage's protocol, exact profile,
code hash, admission time and actual tier metadata. Cross-version observations
are not automatically pooled or relabeled as a homogeneous v2.0.2 panel. Analysis
must disclose this mixed-version execution, changed Google routing policy,
provider/window missingness and downgrade frequencies, and preserve the original
analysis eligibility and comparability rules. No favorable-answer selection,
imputation or altered threshold is authorized.

W01 still closes 8 October 2026 at 09:00 JST. Window A is 6 October 09:00–21:00;
Window B is 7 October 09:00–21:00. Late activation never extends these times.
Preparation, registration, freeze, probes, authorization, activation and
submissions retain actual timestamps. No 09:00 or 10:00 completion is asserted.

## Official technical sources

- https://ai.google.dev/gemini-api/docs/generate-content/priority-inference?hl=en
- https://ai.google.dev/gemini-api/docs/rate-limits?hl=en

No new Zenodo DOI is asserted. API keys, account details, private human
authorization and readiness/confirmatory responses remain outside the public repo.
