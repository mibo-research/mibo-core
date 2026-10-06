# MIBO Core v2.0.2 prospective lineage admission amendment

Operations Lead: Kento Sasano. Approval of the three-provider-first proposal
was received on 6 October 2026 at 10:42:36 JST (2026-10-06T01:42:36Z).
This approval changes admission policy; it is not a completed private execution
authorization. No completed preparation or observation at 09:00 or 10:00 is asserted.

## Preserved design and records

This amendment supplements v2.0 (DOI 10.5281/zenodo.22264635) and the approved
v2.0.1 Agent amendment, published at
https://github.com/mibo-research/mibo-core/blob/3045cbacaa15d19699deb8e79d1c7465b7d2f343/docs/v2.0.1/AMENDMENT_v2.0.1.md.
The four intended lineages, exact approved models and material request profiles,
24 query forms, query hashes, k=10, seed, deterministic execution order, complete
manifest, twelve-wave schedule, calibration windows, hypotheses, thresholds,
technical retry rules and closed Agent contract remain fixed. Prior versions and
private readiness failures remain intact. Migration is blocked if any v2.0 or
v2.0.1 confirmatory attempt is already retained for this wave.

## Replace the all-four readiness start gate

Readiness and human execution authorization apply separately to each lineage.
The Operations Lead may explicitly authorize a named subset whose exact model
metadata, Terms/profile review and fixed synthetic generation checks have passed.
An unsuccessful readiness check prevents only that lineage from submitting
confirmatory queries. The initial approved scope is OpenAI (MIBO-SL-001),
Anthropic (MIBO-SL-002), and Perplexity (MIBO-SL-004). Google (MIBO-SL-003) is
deferred. A scoped report must disclose both its admitted subset and the failed
Google check; a scoped PASS does not mean all four providers passed.

The complete W01 manifest retains 1120 intended rows, including 280 Google rows.
The initial executor processes only the 840 authorized rows. This is a software
admission count, not a guarantee that every submitted row succeeds. Original
passing readiness evidence may be reused only after file hashes, exact IDs,
unchanged profiles and fixed non-confirmatory prompt are verified. It must remain
identified as reused evidence with its actual original timestamps.

## Google deferral and later admission

Google receives no registered MIBO prompt while deferred. The exact model remains
gemini-3.8-flash with the approved GenerateContent profile. No automatic selection,
fallback, Priority-tier change or transport substitution is authorized.

After this prospective amendment, one separate documented Google readiness
recovery block is permitted: one fixed synthetic probe and at most two technical
retries, the first after at least 10 minutes and the second after at least an
additional 30 minutes. A longer provider Retry-After is honored. Each probe and
failure is private and append-only; this block does not erase or reset prior
v2.0.1 evidence and is never used to retry a confirmatory observation. A model or
environment mismatch stops the block. Exhaustion requires further prospective
review; it does not permit another block or a model change.

A passing fixed technical probe alone never promotes Google. The Operations Lead
must issue a separate, dated, hash-bound Google execution authorization before
its first confirmatory request. A separate executor can then use the original
unchanged manifest and freeze for only the Google lineage. The sealed collection
code and initial authorization are not modified during the active wave.

## Timing, missingness and analysis

W01 remains 6 October 09:00 JST through 8 October 09:00 JST. Window A remains
6 October 09:00–21:00 and Window B 7 October 09:00–21:00. Google can participate
only in the unexpired original windows. Expired rows are retained as uncollected
missing observations, never backfilled into another window. A Google admission
after Window A closes cannot recover Window A observations. No window is shifted.

Registration, freeze, scope readiness, human authorization, executor activation
and request times are recorded truthfully. The full manifest remains the intended
denominator. Reports disclose readiness deferral, unequal start times and missing
rows by provider/window, and distinguish pending rows during an open window from
final missingness after closure. The v2.0 analysis plan continues to apply subject
to its original minimum-data and comparability criteria; three-provider readiness
does not certify a complete four-provider panel or justify changed thresholds,
imputation, automatic pooling across versions or a complete-panel analysis claim.

## Custody and execution

v2.0.2 attempts, failures, retry links and admission deviations use
<MIBO_DATA_ROOT>/v2.0.2/<Site ID>/<Wave ID>/. A new immutable public registration
must precede the new private freeze and human authorization. Scoped bundles
remain unsigned templates. Only an explicit private human action authorizes
execution of the reviewed concrete hashes and named subset.
