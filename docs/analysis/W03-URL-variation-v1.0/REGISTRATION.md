# MIBO W03: prospective derivative URL-string analysis v1.0

Registration date: 7 November 2026 (UTC). The enclosing public Git commit and
its timestamp provide the versioned registration evidence. This is a GitHub
analysis registration; it is not a new Zenodo DOI or an OSF registration.

## Scope and prior exposure

This is a separate empirical-paper analysis of repeated source URL strings.
It does not amend Core registered hypotheses, thresholds, query wording,
panel membership, retry policy, or field windows. W02 outputs and descriptive
citation summaries were inspected before this plan was chosen. All W02
findings remain exploratory. The prospective claim applies to W03, whose
observations have not yet been collected or inspected.

The PI approved proposal v0.2 (SHA-256 below). Version 1.0 records that plan,
its implementation, and the completed settings/manifest bindings. The old
v0.1 bootstrap draft is superseded. The sensitivity analysis is deterministic
leave-one-response-out; it is not a confidence interval.

## Design retained

- MIBO2-W03 / JP01 / ACI, CLOSED provider API; no retrieval or tools.
- 1 December 2026 00:00 UTC to 3 December 2026 00:00 UTC (09:00 JST on each date).
- Ordinary wave: no calibration Window A/B.
- Complete observation design: 4 lineages × 24 fixed query forms × 10 = 960 initial requests.
- Paper primary subset: I03 only (chronic sleep deprivation in adults), EN/JA,
  4 lineages × 2 languages × 10 = 80 planned slots per wave; 8 cells.
- Preserve refusals, safety responses and nonanswers as observations. Exclude
  technical missingness from response denominators and report it separately.
  Technical retries never increase the number of logical observations.

Frozen requested identifiers: `gpt-6.1-sol`, `claude-sonnet-5-5`,
`gemini-3.8-flash`, and `perplexity/sonar`. Material profiles are unchanged
from W02 and are reproduced in `analysis-spec.json`. A frozen identifier
does not guarantee immutable hosted weights or defaults. Returned model
metadata and any deployment changes must be disclosed.

## URL selection and primary measure

Reuse the literal W02 rule: citation URLs first, then URLs matched in displayed
answer text by `https?://[^\s<>"\]\)]+`; trim trailing periods, commas and
semicolons; preserve first occurrence; retain at most five. Treat the result
as an order-insensitive set of exact strings. Do not retrieve linked pages,
resolve redirects, normalize query strings, infer semantic source identity,
or judge whether a citation supports a claim. URL-free bibliographic sources
are outside this measure.

Within each lineage/language cell compute the mean of pairwise set Jaccard
similarities, `|A ∩ B| / |A ∪ B|`. One empty set gives zero; two empty sets
give an undefined pair, excluded from the mean and counted separately. If
no eligible pairs remain, the cell mean is undefined, never replaced by 0 or 1.
The 45 pairs in a complete cell are dependent, not 45 independent responses.

## W03 minus W02

Report each eligible cell's W03 mean minus its W02 mean. Require at least eight
technically retained responses in each wave, the same site, query-form hash,
language, lineage, ACI condition and ordinary window class, and reviewed
material request profiles. The implementation conservatively omits a primary
contrast if profile hashes differ. Do not silently pool profiles. A model-ID
change is disclosed as a deployment change with no causal model-update claim.
Undefined means yield no numerical contrast, while observations and missingness
remain in the descriptive tables.

Hold original cell eligibility fixed, omit one whole response from W02 and
one from W03, and evaluate all cross-wave omission combinations (100 at n=10
in both waves). Recalculate the contrast. Report the minimum and maximum
defined values, and the number of undefined combinations. Do not treat this
range as a confidence interval. Replication numbers do not pair subjects
between waves. No hypothesis tests, causal effects or service rankings are
planned in this paper analysis.

## Secondary descriptions and interpretation

Report distinct exact first-five sets with actual n (compare counts directly
only when n is equal), URL-free proportions, and mean pairwise Jaccard of
lowercase exact hostnames using the same five URLs, with no registrable-domain
merging. Count unparseable/missing hostname occurrences, omit those hosts from
that secondary set, and retain their literal URLs in the primary measure.
Cross-wave set overlap is exploratory.

Conclusions are limited to the specific I03 task, sampled deployments,
languages, site and observation windows. Similarity is not citation accuracy,
source quality, broad AI capability, search visibility or market share. This
study does not establish that an LLMO/AIO intervention caused a change.

## Human workload and optional AI coding

Primary measures are deterministic; additional human case grading is zero.
W02 AI-coded content stays `automated_ai`, `human_validation=false`, exploratory;
the nine indeterminate citation judgements stay indeterminate. No new W03
content grading is required. Any optional AI grading needs a separate
prospective freeze of exact grader IDs, prompts, agreement rules and bounded
adjudication before W03 outputs are inspected. No human-validated accuracy
claim follows from model agreement.

## Implementation and execution boundary

`automation/url_set_variation.py` accepts audited normalized JSON, runs offline
with the standard library, and exclusively creates its result (no overwrite).
Include all 80 planned I03 slots per wave. Each row names `wave_id`, `site_id`,
`service_lineage_id`, `item_id`, `language`, `query_sha256`, `condition`,
`window_id`, integer `replication`, `model_id`, `request_profile_sha256`,
`technical_status`, `text`, and `citations`. `technical_status` is `valid` or
`technical_missing`; a missing slot carries no retained answer text/citations.
Refusals are valid rows and may have an empty URL set. Input normalization
must retain technical-audit and original response hash bindings. It must not
use AI semantic validity judgements to remove responses.

```sh
python3 -B automation/url_set_variation.py --baseline W02-I03.private.json \
  --prospective W03-I03.private.json --out W02-W03-URL-results.private.json
python3 -B -m unittest discover -s automation/tests -p test_url_set_variation.py -v
```

No private raw outputs, API credentials or completed authorization records are
published. API collection retains Core v2.0.1, the existing private execution
gates, technical-only retries (max two, at least 10 then an additional 30
minutes; honor longer provider waits), and append-only capture. This public
registration does not sign authorization or start a collector. Institutional
approval/exemption is not inferred. The applicable existing determination and
account permissions belong in the private final review.

Any prospective revision must retain this version and record its timestamp,
reason and relation to output exposure. Post-exposure changes are deviations
or exploratory additions, not retroactive preregistration.

## File bindings

- approved proposal v0.2: `4df3965dcf0c13a959e9c5dd3cf8cd697106ad8c8aa4e414ddbd79977caefd8f`
- analysis specification: `1f33325c3b759884c622c07c5e75fca6a8e7157c7656fa4c4461a52629eba28a`
- analysis implementation: `914b61672d66ca0dd21f3bd4a89e70dd5d7589d4322f3106e95b9f32535216a6`
- synthetic test source: `8b28a9c973eb85cb590c331af7882764f799b1ca99f3006c99a9513dfc7f6efd`
- Core v2.0.1 protocol: `354d371e24a39f1574ad4e4152256e27ed584e651e1bb174e1de4bc58ed90bbc`
- W03 provider freeze: `6e74021e4c84c277f57eec41a1da89a76b38c9dbcbeeba0b9f5d783ecd0d56d5`
- W03 960-row manifest: `ae0c5cd95dcb014ebdff9dec1cc86fb2dd98ba6c100cb1179e60530b6a2baae9`
- four-provider synthetic readiness report: `ff18528c08c879ccab63ad63efc03ad4dfa4508161582968bfb3a9be05490fa7`
- historical W02 extraction script: `20ea28fa1ea3e5d850ce792ec3c82c1d3c23228f25436825487050cd65cb0814`
