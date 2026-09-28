# MIBO Core v2.1 — W01 readiness ledger (draft)

Target: 1 October 2026 00:00 UTC / 09:00 JST. State at 28 September:
**no private gate is verified by this public document**. An empty box means
unverified, not known failure. Completed private evidence stays off GitHub.

| Due (JST) | Gate | Acceptance evidence | State |
|---|---|---|---|
| 28 Sep | Scientific amendment and date | PI confirms 09:00 JST start, W02–W12 retained, and no prior valid W01 | [ ] |
| 28 Sep | Version-specific registration | New Zenodo version DOI inserted into final protocol and JSON; version is public before first request | [ ] |
| 29 Sep | Question/target/condition crosswalk | 24 form hashes match v1.0; four exact human-selected model IDs; request profiles and ACI rules signed | [ ] |
| 29 Sep | Terms, accounts and cost | Four dated official Terms/access decisions; keys present privately; billing and rate limits adequate | [ ] |
| 29 Sep | v2.1 runtime | Reviewed clean commit; protocol-version binding; separate `v2.1` storage; UTC/NTP, disk, network and append-only health | [ ] |
| 30 Sep | Synthetic smoke | Four official model checks and four fixed non-confirmatory prompts pass; returned IDs match; no registered question used | [ ] |
| 30 Sep | Deterministic manifest | 1,120 rows; WA 160, STD 800, WB 160; four lineages × 280; exact hashes, no duplicates; strict validation | [ ] |
| 30 Sep | Human execution authorization | PI reviews protocol, freeze, Terms, smoke, manifest and code hashes, signs private record, then enables sentinel | [ ] |
| 1 Oct before 09:00 | Go/no-go | All evidence current and bound to published version; runtime waiting against synchronized UTC; otherwise stop and log deviation | [ ] |

The fixed instrument, service lineage and collection conditions are three
independent checks. Passing only one or two repeats the previous failure.
A provider failure does not authorize replacement, prompt changes or a
post-hoc time shift.
