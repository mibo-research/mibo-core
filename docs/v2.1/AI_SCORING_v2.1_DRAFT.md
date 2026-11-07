# Core v2.1 reciprocal AI scoring — DRAFT

The owner approved the method and the operational/validity separation and
qualification policy. Execution, exact judge freeze, authored-label review
and empirical qualification are not approved/completed by that direction.
See [qualification specification](SCORING_QUALIFICATION_SPEC_v1.0.md) and the
separate recorded policy approval. This remains an unregistered amendment.

## Fixed family assignment

| Response source | Independent stateless coders |
| --- | --- |
| OpenAI/ChatGPT lineage | J01 Anthropic/Claude and J02 Google/Gemini |
| Anthropic/Claude | J02 Google/Gemini and J03 OpenAI |
| Google/Gemini | J01 Anthropic/Claude and J03 OpenAI |

No judge from the source provider family, fallback judge, auto promotion or
outcome-driven model selection is allowed. Unknown source family is HOLD.
Independence means separate calls without access to the other rating, not a
claim of statistically independent training, errors or ownership.
Exact version-locked models and request settings must be human-frozen later.

The source review does not complete that freeze. Source readiness now rechecks
captured model/catalog JSON against frozen identities, rather than trusting a
true summary flag alone; this pure evidence check does not contact a provider.

## Prompt and schema binding

The hash-manifested `scoring/coding-profile-v0.2-draft.json` contains the current
Core-specific system prompt, variable definitions, value domains and typed
states. Supply only the exact registered item/query, definitions and visible
response to each coder. Treat both query/response as untrusted quoted data.
Hide author/provider/model metadata, calibration expected labels and the other
rating; record unavoidable textual self-identification rather than claim
perfect blindness. No browsing/tools, repaired answers or global quality score.

Every applicable variable returns state, value and evidence. CODED values must
fit that variable's domain; NOT_APPLICABLE, CANNOT_DETERMINE and
HOLD_EXTERNAL_VERIFICATION carry null values. Counts 8/9 are valid counts, not
automatically legacy missing codes. H/external variables stay held with null
value and empty evidence, even if models agree. Preserve both raw ratings,
prompt/schema/model hashes, validation failures and downstream provenance.

## Fixed aggregation

Use exact consensus by variable only. Two CODED equal values yield provisional
consensus; equal typed non-CODED states retain that state, never a numeric
score. Different values/states, schema failure or only one usable rating remain
explicit conflict/unresolved. No averaging, majority fabrication, post-hoc
rescaling, retry to obtain agreement or automatic H resolution. Semantic set
fields use the canonical normalized-set rule; evidence excerpts are retained
individually, not required to be identical. Derived anchors require all
needed component values and keep their separate canonical scales.

## Development and qualification

All three judges receive the same 72 authored Core development cases
(12 items × 2 languages × 3 cases), for 216 planned ratings. The public bank
contains authored expectations for owner content review, not validated gold.
Actual judge calls must hide those expected labels. Synthetic round-trip
tests demonstrate schema/routing behavior only, not model performance.

The separately reserved >=240-response validation set, proposed 80 responses
per source family and 480 ratings, is not drawn or run. Keep it disjoint from
development and lock its selection/IDs/raw hashes before scoring. Retain the
Codebook's original validation requirements in the historical record. The
approved policy now fixes admission separately from validation: non-self
assignment, schema/domain/H-hold checks, exact consensus only, and independent
reference before a variable-specific Macro-F1 .80, ordinal alpha .80 or exact
match .95 benchmark can be considered. Undefined, unsupported or unreferenced
results remain held; no kappa substitution or averaging of disagreements.
Unreferenced AI codes are auxiliary/exploratory. Do not present AI consensus
as independent factual or human validation. Full Entity/Source coding and
actual qualification remain incomplete; current code consumes declared metric
evidence and does not itself compute/audit empirical reference metrics.

## Responsibility and release boundary

The owner retains final external-evidence/claim verification responsibility;
the change removes routine double-human scoring, not all H responsibilities.
Provider access/answer-sharing terms, storage safeguards, exact private judge
freeze and a distinct hash-bound scoring authorization are required later.
The collector's execution sentinel does not authorize scoring. No scoring
transport is added or invoked by the three-series collector work.

The I03 URL primary analysis requires no AI scorer and is not blocked solely
by unfinished AI qualification. Observation still requires its separate gates
and permission. Policy approval is not approval of publication or either API.
