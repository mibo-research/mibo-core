# MIBO Core API-only Observatory Protocol v2.0

**Version:** 2.0

**Status:** Final prospective protocol; registered before observation under version-specific Zenodo DOI `10.5281/zenodo.22264635`

**Prepared:** 3 September 2026

**Author:** Kento Sasano

**Prior protocol:** MIBO Core Protocol Package v1.0, DOI `10.5281/zenodo.21936410`

**Version-specific registration:** `10.5281/zenodo.22264635`

## 1. Purpose and version boundary

MIBO Core v2.0 is a prospective redesign of the primary MIBO Core observation
surface. It replaces per-observation operation of consumer web interfaces with
fully automated, stateless calls to provider APIs on a controlled private
runtime.

This is a scientific protocol change, not a software correction. It does not
amend, overwrite, relabel, or retroactively complete MIBO Core v1.0. No v2.0
record may be represented as a v1.0 Ecological Live observation. Data from the
two versions must remain separately identified and must not be pooled in a
confirmatory analysis.

The founding paper and v1.0 protocol remain the historical description of the
public-interface design. This document governs only observations prospectively
submitted after the v2.0 version-specific registration is public.

## 2. Primary observation condition

The sole primary condition in v2.0 is the **API Core Interface**, identified as
`ACI`.

`ACI` is distinct from all v1.0 conditions:

- it is not Ecological Live (`LUI`);
- it is not Paired Live Reference (`PLR`);
- it is not Frozen Reference (`FRZ`); and
- it is not the exploratory API Shadow Archive (`ASH`).

The v2.0 estimand is the longitudinal distribution of outputs returned by the
prospectively frozen provider API configuration. It is not the behavior of a
consumer UI and is not a causal model-update contrast.

## 3. Fixed panel and instrument

The four service lineages and all 24 Japanese/English Query Forms are carried
forward from MIBO Core v1.0 without changing wording, language membership,
item membership, or SHA-256 identity. The authoritative source for those
objects is DOI `10.5281/zenodo.21936410` and the machine-readable copies included
in this package.

The four required API lineages are:

1. `MIBO-SL-001` — OpenAI / ChatGPT lineage, observed through an eligible OpenAI API model;
2. `MIBO-SL-002` — Anthropic / Claude lineage, observed through an eligible Anthropic API model;
3. `MIBO-SL-003` — Google / Gemini lineage, observed through an eligible Gemini API model; and
4. `MIBO-SL-004` — Perplexity lineage, observed through an eligible Perplexity API model with search disabled.

Lineage continuity does not imply UI/API equivalence. Exact model identifiers
and material request settings are time-sensitive execution facts and are fixed
by a private, hash-bound Provider Freeze Record before each wave. Discovery
software may verify a human-selected identifier but may not select, promote,
replace, or reroute it.

## 4. Request environment

Every request is independent, stateless, and environment-closed:

- exactly one frozen Query Form is supplied as the user content;
- no conversation history is supplied;
- no researcher-authored system or developer instruction is supplied;
- retrieval, browsing, external tools, functions, connectors, files, cached
  content, and computer-use facilities are omitted or disabled;
- Perplexity requests require `web_search_options.disable_search=true`;
- streaming is disabled;
- provider-side storage is disabled where the API supports an explicit control;
  and
- credentials are never stored in request or response archives.

Provider-managed hidden instructions, safety systems, routing, and deployment
components that cannot be disabled are part of the observed API surface. They
must not be interpreted as controlled model-state differences.

## 5. Replication and deterministic manifests

The replication standard remains `k=10`. In an ordinary wave:

`4 lineages × 24 Query Forms × 10 replications = 960 initial requests`.

The deterministic seed is preserved verbatim:

`SHA-256("MIBO-v1.0|<Wave ID>|<Site ID>|<Mode ID>")`, with the first eight
hexadecimal characters interpreted as an integer. For v2.0, `Mode ID = ACI`.

The frozen manifest records the execution order, Attempt ID, lineage, Query
Form ID and hash, language, replication, window, exact model ID, protocol hash,
and Provider Freeze hash. Initial attempts use `A01`; eligible technical retries
use `A02` and `A03` and retain a deterministic link to the original attempt.

## 6. Calibration waves and counts

W01, W04, W07, and W10 are calibration waves. The four English Anchor Items are
observed in Window A and again in Window B, separated by 24 hours. Window A
Anchor observations are part of the standard Core count; Window B adds 160
requests.

- Window A: field-start offset 0–12 hours;
- Window B: field-start offset 24–36 hours;
- other Query Forms: the 48-hour standard field window.

A calibration wave therefore has 1,120 initial requests: 160 Window A Anchor,
800 standard non-Anchor, and 160 Window B Anchor requests. Across 12 waves, the
first v2.0 cycle contains 12,160 intended initial requests.

## 7. Registered first-cycle schedule

All timestamps are UTC. Each field window is 48 hours.

| Wave | Start | Close | Calibration |
|---|---|---|---|
| MIBO2-W01 | 2026-10-06 00:00 | 2026-10-08 00:00 | Yes |
| MIBO2-W02 | 2026-11-03 00:00 | 2026-11-05 00:00 | No |
| MIBO2-W03 | 2026-12-01 00:00 | 2026-12-03 00:00 | No |
| MIBO2-W04 | 2027-01-05 00:00 | 2027-01-07 00:00 | Yes |
| MIBO2-W05 | 2027-02-02 00:00 | 2027-02-04 00:00 | No |
| MIBO2-W06 | 2027-03-02 00:00 | 2027-03-04 00:00 | No |
| MIBO2-W07 | 2027-04-06 00:00 | 2027-04-08 00:00 | Yes |
| MIBO2-W08 | 2027-05-04 00:00 | 2027-05-06 00:00 | No |
| MIBO2-W09 | 2027-06-01 00:00 | 2027-06-03 00:00 | No |
| MIBO2-W10 | 2027-07-06 00:00 | 2027-07-08 00:00 | Yes |
| MIBO2-W11 | 2027-08-03 00:00 | 2027-08-05 00:00 | No |
| MIBO2-W12 | 2027-09-07 00:00 | 2027-09-09 00:00 | No |

For calibration waves, the Window A and Window B limits in Section 6 remain
binding inside the 48-hour field window.

## 8. Retry and missingness rules

Only a registered technical failure may trigger a retry. A refusal, safety
response, nonanswer, or clarification request is a substantive observation and
must not be retried because of its content.

- Retry 1 occurs at least 10 minutes after the failed initial attempt.
- Retry 2 occurs at least an additional 30 minutes after Retry 1.
- A longer provider `Retry-After` value extends but never shortens the delay.
- A retry must remain inside the row's registered Window A, Window B, or
  standard field window.
- No attempt may be moved to another provider, model, query, language, or
  observation surface.

Missingness is retained. There is no fallback model, provider substitution,
prompt rewriting, or imputation. A service-wide outage pauses the affected
lineage; repeated blind submission of every queued request is prohibited.

## 9. Prospective execution gate

The controlled runtime must fail closed unless all of the following are true:

1. this v2.0 protocol has a public version-specific registration identifier;
2. the deployed code snapshot and protocol files have recorded SHA-256 hashes;
3. the exact model ID and material request settings for all four lineages have
   been selected by the Operations Lead and frozen prospectively;
4. the dated API Terms/access review is complete;
5. official model-catalog evidence verifies the frozen identifiers;
6. one fixed, non-confirmatory synthetic smoke test passes for each lineage;
7. the 960- or 1,120-row deterministic manifest passes structural and strict
   integrity validation;
8. a human-signed execution authorization binds the protocol, manifest,
   Provider Freeze, terms review, and dry-run hashes;
9. the controlled runtime clock and append-only data root are healthy;
10. all required credentials are present on the private runtime; and
11. `MIBO_CORE_V2_EXECUTION=ENABLED_AFTER_CORE_V2_GATE` is explicitly set.

Automation must never complete or sign a human authorization record.

## 10. Capture, provenance, and custody

For every attempt, the private archive retains the exact request payload minus
credentials, raw provider response, returned model metadata, HTTP status,
timing, usage metadata where available, retry linkage, and cryptographic hashes.
All writes are exclusive-create and append-only under:

`<MIBO_DATA_ROOT>/v2.0/<Site ID>/<Wave ID>/`

No v2.0 record may be written to the v1.0 Core namespace or the API Shadow
namespace. Raw outputs, credentials, private configuration freezes, readiness
evidence, and completed authorizations are not published in the public GitHub
repository.

## 11. Confirmatory questions and limits

The v2.0 primary analysis asks:

1. whether within-cell output variation makes distributional observation
   necessary for the ACI condition;
2. whether a service–outcome–language trajectory shows sustained longitudinal
   change beyond within-cell variation; and
3. whether the English Anchor outcomes attain the prospectively registered
   adjacent-window re-observability standard in calibration waves.

The v1.0 operating thresholds are retained: a candidate longitudinal change
requires a normalized difference of at least `.15` with false-discovery-rate
control; sustained change requires the same direction in the next wave with a
difference of at least `.10`; and a cell requires at least eight valid
replications for primary analysis. Detailed inclusion and analysis rules are in
`MIBO_Statistical_Analysis_Plan_v2.0.md`.

No v2.0 result supports a claim about consumer-interface behavior, a causal
model-update effect, or cross-site generality unless a separate prospective
design explicitly supports that claim.

## 12. Corrections, amendments, and withdrawal

After the first v2.0 observation has been submitted, collection code and
scientific rules are locked for that wave. A technical repair requires a new
commit hash and a recorded deviation. A scientific change requires a future
prospective protocol version.

Corrections never overwrite retained raw observations. Amendments are dated,
versioned, and prospective. Withdrawal of a claim or public artifact does not
erase the audit trail unless removal is legally required for security, privacy,
or rights protection.
