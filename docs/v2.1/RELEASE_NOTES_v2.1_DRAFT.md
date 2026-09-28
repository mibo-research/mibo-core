# MIBO Core v2.1 — prospective schedule amendment (draft)

**Status:** Not registered. This draft has no authority for confirmatory collection.

## Scientific change requested 28 September 2026

The first API Core Interface field window is advanced from 6 October 2026
00:00–8 October 2026 00:00 UTC to **1 October 2026 00:00–3 October 2026
00:00 UTC** (1 October 09:00–3 October 09:00 JST). For this calibration wave:

- Window A: 1 October 00:00–12:00 UTC (09:00–21:00 JST);
- Window B: 2 October 00:00–12:00 UTC (09:00–21:00 JST);
- non-Anchor standard forms: 1 October 00:00–3 October 00:00 UTC.

W02–W12 retain their v2.0 dates. The first inter-wave interval is 33 days.
The four lineages, 24 verbatim Query Forms and hashes, `k=10`, ACI API
surface, deterministic seed, 1,120 W01 requests, analysis plan, thresholds,
retry policy, missingness, and interpretation limits do not change.

The prior failed collection attempt remains outside the new confirmatory
baseline. The published v2.0 DOI and files are preserved. The version-specific
v2.1 DOI must be published *before* the first v2.1 request; public GitHub code
or a reserved-but-unpublished DOI alone does not close this gate.

## Operational release blockers

1. Reserve the DOI for a **new version of the existing Zenodo record** and put
   its exact version-specific DOI in the v2.1 protocol and machine-readable
   configuration. Publish the complete package before W01.
2. Review and deploy a v2.1-compatible implementation. The current v2.0
   collector rejects `protocol_version=2.1` and writes to a v2.0 namespace;
   changing just the JSON schedule is insufficient.
3. Complete the private four-provider freeze, Terms/access review, synthetic
   smoke checks, 1,120-row manifest validation, runtime health, and hash-bound
   human authorization for the *published* version and the 1 October window.
4. Keep collection disabled until all gates close. Failed gates mean a delayed
   or non-confirmatory start, with the deviation recorded prospectively.
