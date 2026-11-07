# Core v2.1 scoring qualification specification v1.0

Status: OWNER-APPROVED POLICY, LOCAL DRAFT, NOT PUBLICLY REGISTERED OR EXECUTED.
Approval: `OWNER_DECISION_BASELINE_SCORING_20261107.json`.
Machine policy: `automation/config/core_v21_scoring_qualification.json`.
Code: `automation/core_v21_scoring.py`; no transport or credential handling.

## 1. Separate three different states

1. **Operational admission:** a rating satisfies the fixed schema, variable
   domain, non-self provider-family assignment and H/external-verification hold.
   This does not establish semantic correctness.
2. **Reference benchmark:** a variable/judge-specific metric is compared with
   a fixed threshold only when independent, locked reference labels and
   disjoint-validation provenance are available. The code checks supplied,
   hash-bound evidence; it does not independently establish the reference's
   truth or compute the empirical metrics.
3. **Scientific use:** without independent reference, AI codes remain
   auxiliary/exploratory. A declared benchmark pass is not global model
   certification, automatic Claim Registry admission, human validation, or
   final verification of any H variable.

This prospective amendment does not claim that AI agreement satisfies the old
v1.0 human-reference, audit or claim-review requirements. No second-human
recruitment is requested by this policy. H/claim responsibilities are not waived.

## 2. Operational admission and aggregation

Require the exact applicable variable map and typed state/value/evidence
structure. CODED values must fit the registered binary/category/ordinal/count/
set/continuous domain. Numeric counts 8/9 are not missingness codes.
Non-CODED values are null. H/external-hold variables must have
HOLD_EXTERNAL_VERIFICATION, null value and empty evidence. Reject malformed or
out-of-domain ratings; never silently repair, reinterpret or use them.

For each source, use exactly the two other provider families. No self-family,
duplicate family, third-vote fallback, auto-promotion or retry-to-agreement.
Preserve both individual ratings. Aggregate by exact variable consensus only:
matching typed null states remain null, semantically unordered sets compare
after canonical ordering, and differences remain CONFLICT_HOLD. Never average
categories, ordinal values or conflicts. Operational consensus is not validation.

## 3. Development and validation separation

Keep 72 authored common development/calibration cases separate from at least
240 reserved validation responses, with the basic plan of 80 responses per
source family and 480 non-self-family ratings. All 12 items and both languages
remain covered. Lock actual IDs, raw capture hashes, stratification and
development/validation disjointness before validation scoring; do not tune on
that locked set. Changes after failed validation require a new unused set or
continued exploratory status, not repeated tuning on exposed validation labels.

The current allocation has no actual observation IDs/raw hashes and therefore
returns HOLD_UNSAMPLED. A synthetic partition shape/disjointness pass is not
an empirical sample lock or substantive label review. The 72 authored labels
are still development expectations, not independently validated gold.

## 4. Fixed independent-reference benchmarks

| Registered variable class | Metric | Threshold |
| --- | --- | ---: |
| Binary/nominal semantic code | Macro-F1 | >= .80 |
| Ordinal semantic code | Ordinal Krippendorff alpha | >= .80 |
| Deterministic extraction | Exact-match rate | >= .95 |

Do not replace ordinal alpha with weighted kappa, use AI consensus as reference,
or pool rotating-pair agreement into a correctness claim. A variable class
without a prospectively specified metric remains held; do not silently map
counts/sets to an easier metric. Undefined/nonfinite values, no comparable
labels, absent provenance or insufficient total validation size cannot pass.
An insufficient/constant-category or sparse result must be disclosed and may
remain non-estimable; never replace an undefined metric with zero or one.

The decision input identifies the variable and judge family and binds the
judge freeze, prompt/schema, independent reference, locked validation partition,
metric-computation record and stratified diagnostics with SHA-256 values.
Report judge/variable/language/source-pair results, denominators, disagreements,
holds and category coverage. The offline gate consumes an audited metric
summary; empirical computation and independent-reference verification remain
separate future work, not results of the engineering tests.

## 5. Consequences and collection boundary

Operational failure: rating not admitted. Reference absent or evidence invalid:
auxiliary/exploratory only. Validly supplied metric below threshold: no sole
confirmatory claim. Declared benchmark met: eligible only for variable-specific
confirmation review; no automatic H, model-level or human-validity certification.

The deterministic I03 URL-string primary analysis does not need an AI grader.
Uncompleted AI qualification does not by itself block that analysis or the
separately authorized source collection. This does not authorize collection:
public registration, source freeze, terms/access, storage/runtime checks,
named hash-bound authorization, original field window and execution sentinels
still apply. Scoring has its own later freeze, qualification evidence and
permission. None of the APIs is invoked by this policy or its offline tests.
