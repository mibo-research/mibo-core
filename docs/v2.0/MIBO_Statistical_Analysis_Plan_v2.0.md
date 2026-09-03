# MIBO Core v2.0 Statistical Analysis Plan

## 1. Version boundary

This plan applies only to the MIBO Core v2.0 API Core Interface (`ACI`). v1.0
Ecological Live, Paired Live Reference, Frozen Reference, and API Shadow data
are excluded from the v2.0 confirmatory dataset.

## 2. Observational unit and cell

An attempt is one API submission identified by a deterministic Attempt ID. A
valid observation is the retained provider response to that attempt, including
a refusal, safety response, nonanswer, or clarification request.

The primary cell is defined by protocol version, wave, site, service lineage,
`ACI` condition, Query Form, language, and window. The target is ten valid
independent observations per required cell. Cells with fewer observations
remain in the dataset and are reported as incomplete.

## 3. Outcomes

Outcome definitions and coding rules are inherited unchanged from the v1.0
Query Codebook associated with DOI `10.5281/zenodo.21936410`. Coding occurs on a
derived analysis copy after raw-wave freeze. AI-assisted coding may be used only
under the existing human-responsibility, blinded-validation, and provenance
rules; it may not modify raw records.

## 4. Analysis populations

- **Intended population:** every initial row in the validated frozen manifest.
- **Attempt population:** every submitted initial or eligible retry attempt.
- **Valid-observation population:** retained completed responses, including
  substantive refusals and nonanswers.
- **Primary cell population:** cells with at least eight valid observations.

Invalid administration, technical failure, and unsubmitted missingness are
separate statuses. No machine response is imputed.

## 5. Within-cell distribution

For binary outcomes, report the observed proportion and its uncertainty. For
ranked, ordinal, count, or continuous outcomes, report the corresponding
distribution, dispersion, and robust descriptive summaries. For text-derived
categories, report category probabilities and minority response patterns.

The first confirmatory question is whether within-cell dispersion is materially
large enough that a single response would not represent the observed API
condition. The same v1.0 decision framework and outcome-specific normalization
rules are used without post-outcome alteration.

## 6. Longitudinal change

For each preregistered service–outcome–language trajectory, compare the current
wave distribution with the registered baseline or immediately preceding wave
as specified in the analysis execution record.

A candidate longitudinal change requires:

- a normalized difference of at least `.15`; and
- false-discovery-rate control under the v1.0 multiple-testing family.

A sustained change additionally requires the next registered wave to move in
the same direction with a normalized difference of at least `.10`. Candidate
and sustained status are reported separately.

The interpretation is change in the prospectively frozen API condition. It is
not consumer-UI change and not a causal model-update effect.

## 7. Calibration-wave re-observability

W01, W04, W07, and W10 repeat the four English Anchor Items in Window B, 24
hours after Window A begins. The G-study estimates session and adjacent-window
variance for the registered JP01 API condition. A D-study reports the number of
replications needed to reach the registered `Phi >= .80` decision standard.

With only one registered runtime site, v2.0 cannot estimate a site facet or
claim cross-site generality. A future multisite API calibration requires a
separate prospective registration.

## 8. Missingness and sensitivity reporting

Report intended, attempted, valid, failed, retried, window-expired, and missing
counts by wave, lineage, Query Form, language, and window. Sensitivity summaries
may describe results under alternative minimum cell counts but cannot replace
the registered primary rule of at least eight valid observations.

No fallback provider or model, carry-forward response, synthetic completion, or
other imputation is allowed.

## 9. Model and deployment changes

The exact model ID and material settings are wave-level metadata. A changed
identifier between waves is reported as a deployment change and is not adjusted
away. Returned-model discrepancies are retained as integrity events. Analyses
may stratify by prospectively frozen configuration but may not retrospectively
exclude an inconvenient deployment change.

## 10. Prohibited pooling and claims

The confirmatory v2.0 analysis must not:

- pool v1.0 and v2.0 observations;
- relabel API outputs as Ecological Live;
- import API Shadow rows;
- treat different provider lineages as interchangeable model replicates;
- interpret a between-wave contrast as a model-update causal effect; or
- suppress valid refusals, minority outputs, or service outages.

## 11. Analysis lock

Before substantive coding begins, the Analysis Execution Record must identify
the frozen raw-wave hash, code commit, outcome implementation, multiple-testing
family, baseline contrast, exclusions, and software environment. Any change
after outcome inspection is labeled exploratory or documented as a prospective
amendment for a later wave.
