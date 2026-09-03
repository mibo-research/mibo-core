# MIBO Core API-only Observatory v2.0 — prospective draft

Status: **not finalized; not prospectively registered; not authorized for observation**

This document records the requested prospective redesign of MIBO Core as an
API-only, fully automated observatory. It does not amend, overwrite, or relabel
MIBO Core v1.0 (DOI `10.5281/zenodo.21936410`) or any v1.0 wave record.

## Scientific change

The primary observation surface changes from consumer/public web interfaces to
provider APIs. The estimand is therefore controlled API behavior, not ecological
public-interface behavior. Results from v2.0 must not be pooled with or presented
as if they were v1.0 Ecological Live observations.

The v1.0 service lineages and exact 24 frozen query forms are carried forward
without wording changes. Each of the four lineages receives each query form ten
times, for 960 initial API requests per wave. Requests are independent,
stateless, and environment-closed. Retrieval, browsing, external tools, files,
connectors, and system-level prompt additions are prohibited. Perplexity is
admissible in this new protocol only with `disable_search=true`.

The proposed first v2.0 field window is 2026-10-06 00:00 UTC through
2026-10-08 00:00 UTC (2026-10-06 09:00 JST through 2026-10-08 09:00 JST), under
the new wave ID `MIBO2-W01`. This is a proposed calibration wave because it is
the first wave under a changed observation surface.

## Automation boundary

The controlled Google Cloud runtime may automatically:

- wait for the exact registered start time;
- execute all 960 initial requests in deterministic order;
- use only prospectively frozen exact model IDs and request settings;
- store request payloads minus credentials, raw responses, returned model
  metadata, timing, usage, failures, retry links, and hashes append-only;
- retry only registered technical failures, at most twice, after at least 10
  minutes and then an additional 30 minutes; and
- retain missingness without provider/model substitution or imputation.

Automation may never choose a model, change a query, substitute a provider,
enable retrieval, authorize itself, or alter the freeze after observation begins.

## Human decisions required once per wave

Before the runtime can execute, the Operations Lead must complete all of the
following prospectively:

1. finalize and register this v2.0 protocol and record its immutable identifier;
2. freeze the exact version-locked model ID and material generation settings for
   all four lineages from official provider evidence;
3. complete the dated API Terms/access review;
4. complete a synthetic, non-MIBO readiness dry run; and
5. sign the hash-bound execution authorization.

No individual observation requires human interaction after those gates close.

## Fail-closed implementation

The public repository contains only templates and synthetic tests. Private
completed freezes, authorizations, API keys, readiness evidence, and raw output
belong on the controlled runtime. The execution service requires the dedicated
sentinel `MIBO_CORE_V2_EXECUTION=ENABLED_AFTER_CORE_V2_GATE` in addition to all
file, hash, time-window, credential, and human-authorization checks.

The canonical machine-readable draft is
`automation/config/core_v2_protocol.draft.json`. Its draft status deliberately
makes manifest generation and execution fail until a finalized, prospectively
registered private copy exists.
