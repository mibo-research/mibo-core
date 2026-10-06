# MIBO Core v2.0.4 prospective Gemini Standard restoration amendment

Operations Lead: Kento Sasano. Approval to follow the recommendation to restore
Gemini Standard processing was received on 6 October 2026 at 12:35:46 JST
(2026-10-06T03:35:46Z). This approves the configuration and preparation described
here; it is not a completed private, hash-bound execution authorization.

## Reason and scope

The intended Gemini account is currently Tier 1. Official Google documentation
restricts Priority inference to Tier 2 and Tier 3. An earlier Priority readiness
response did not establish actual Priority processing. Preserve the complete
private Standard and Priority readiness history, including any HTTP success
whose actual tier was unconfirmed. Neither a successful transport response nor
an active billing account is treated as proof of Priority eligibility.

This amendment supplements v2.0 (DOI 10.5281/zenodo.22264635), the Agent amendment
at https://github.com/mibo-research/mibo-core/blob/3045cbacaa15d19699deb8e79d1c7465b7d2f343/docs/v2.0.1/AMENDMENT_v2.0.1.md,
the lineage admission amendment at
https://github.com/mibo-research/mibo-core/blob/71bd6cf4c3267ddf655eed21935837b19d54b030/docs/v2.0.2/AMENDMENT_v2.0.2.md,
and the retained Priority amendment at
https://github.com/mibo-research/mibo-core/blob/04a903824842a09dcbc6f89612a47e55bc1b2304/docs/v2.0.3/AMENDMENT_v2.0.3.md.

Only Google's still-unsubmitted execution path changes. Restore its exact
v2.0.1/v2.0.2 material request profile by omitting service_tier. This selects
Google's documented default Standard processing. Keep gemini-3.8-flash,
GenerateContent v1beta, max_output_tokens=4096, and all other material settings
unchanged. This is a prospective routing decision based on account eligibility,
not a client fallback in response to a confirmatory answer. No request is
resubmitted under another tier or model.

## Readiness correction and human admission

Publish this immutable amendment before the new private freeze and affected
confirmatory requests. Use a new sealed v2.0.4 snapshot only for Google. The
OpenAI, Anthropic and Perplexity v2.0.2 collector, freezes, authorization and data
continue unchanged. Hash-link the original failed four-provider readiness and
the complete private Standard/Priority readiness history. Do not edit or reset
the Priority block or convert its prior response into a Standard readiness PASS.

The eligibility correction permits one separately documented Standard readiness
block under this version: one fixed non-confirmatory probe plus at most two
technical retries, the first after at least ten minutes and the second after at
least an additional thirty minutes. Honor longer Retry-After values from both
retained earlier failures and this block. This prospective block does not erase
earlier exhaustion, relax the former Priority gate or retry a confirmatory row.
Repeated installers reuse the same global private anchor and cannot create
another block. An interrupted probe, nontechnical failure, model/environment
mismatch or exhausted block stops preparation and requires further review.

Readiness requires a new successful response to the fixed readiness prompt
under the restored profile and the exact requested model route. Preserve raw
returned modelVersion metadata; if it identifies another model, stop rather
than admit or retry. The former actual-Priority header requirement does not
apply to the restored Standard profile. No actual Priority processing is claimed.
After PASS, display the full concrete hashes and obtain an explicit private
Operations Lead authorization for Google alone before starting its service.

## Design, timing and custody

Keep all four intended lineages, 24 query forms, query hashes, k=10, deterministic
seed/order, logical Attempt IDs, twelve-wave schedule, hypotheses, thresholds,
confirmatory retry rules and missingness/comparability criteria fixed. The full
W01 manifest retains 1120 intended rows; only its 280 Google rows execute under
v2.0.4. If any Google confirmatory attempt or failure exists in v2.0, v2.0.1,
v2.0.2 or v2.0.3, block full-queue migration rather than replay it. Unclassifiable
old attempts also block migration. Preserve both manifest hashes and a logical
row-ID mapping instead of asserting that different version hashes are identical.

W01 remains 6 October 09:00 JST through 8 October 09:00 JST. Window A remains
6 October 09:00-21:00; Window B remains 7 October 09:00-21:00. Expired rows remain
missing and are never backfilled. Registration, freeze, readiness, human
authorization, service activation and first actual dispatch retain real times;
no earlier 09:00 or 10:00 completion/start is asserted.

Google attempts, failures, retries and deviations use
<MIBO_DATA_ROOT>/v2.0.4/JP01/MIBO2-W01/. Other lineages retain v2.0.2 records.
Archive the prospective eligibility correction and version linkage privately.
Analysis discloses mixed-version execution, deferred Google admission, actual
start times, prior readiness failures and provider/window missingness. No
automatic pooling, relabeling, favorable-answer selection, changed threshold or
imputation is authorized. A successful probe does not guarantee all 280 rows.

## Official sources

- https://ai.google.dev/gemini-api/docs/generate-content/priority-inference?hl=en
- https://ai.google.dev/gemini-api/docs/rate-limits?hl=en
- https://ai.google.dev/gemini-api/docs/billing?hl=en

No new Zenodo DOI is asserted. Credentials, billing-account identifiers, private
authorization records and readiness/confirmatory responses stay outside GitHub.
