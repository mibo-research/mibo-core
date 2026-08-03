# MIBO Statistical Analysis Plan v1.0-rc3

## Confirmatory and Exploratory Analyses for the First Registered Annual Cycle

**Document status:** Integrated Release Candidate  
**Parent protocol:** MIBO Core Observatory Master Protocol v1.0-rc3  
**Parent service registry:** MIBO Service Registry v1.0-rc3  
**Parent instrument:** MIBO Fixed Query Instrument v1.0-rc3  
**Parent codebook:** MIBO Query Codebook v1.0-rc3  
**Parent comparability registry:** MIBO Frozen–Live Comparability Registry v1.0-rc3  
**Parent operations manual:** MIBO Operations Schedule and Manual v1.0-rc3  
**Authoritative language:** English  
**SAP date:** 3 August 2026  
**Planned effective date:** 1 September 2026  
**Planned final freeze date:** 28 August 2026  

---

# 1. Purpose

This Statistical Analysis Plan specifies how MIBO Core Observatory v1.0 will analyze its first registered annual cycle.

It defines:

- analysis populations;
- confirmatory and secondary outcomes;
- operational decision rules for hypotheses H1–H5;
- longitudinal change criteria;
- Frozen–Live contrasts;
- generalizability-theoretic re-observability analysis;
- missingness and protocol-deviation treatment;
- AI-assisted coding validation;
- multiplicity control;
- sensitivity analyses;
- software and reproducibility requirements; and
- required reporting.

The SAP is designed to preserve the methodological identity of MIBO as a sentinel panel survey while avoiding an unnecessarily large number of confirmatory outcomes or models.

---

# 2. Analysis Principles

MIBO will follow seven analytical principles.

## 2.1 Panel units are fixed effects of substantive interest

The four selected service lineages are a purposive sentinel panel, not a random sample of services.

Service lineage will therefore ordinarily be modeled as a fixed substantive factor rather than as a random sample from an unspecified population of AI systems.

## 2.2 Replications are retained as distributions

The ten replications within a cell will not be reduced to one selected or “representative” answer.

Analyses will use:

- replication-level outcomes;
- cell-level distributions;
- or grouped counts derived from all valid replications.

## 2.3 Primary confirmation is limited to four Anchor outcomes

The 12-item instrument remains scientifically important, but the primary confirmatory analysis will use four preregistered Anchor outcomes.

This limits multiplicity and aligns the main hypotheses with the multisite calibration design.

## 2.4 No overall service score

MIBO will not combine all items into a single overall performance, quality, safety, or intelligence score.

## 2.5 Effect magnitude and statistical uncertainty are both required

A longitudinal difference will not be classified as sustained change solely because a p-value crosses a threshold.

The change must also meet the preregistered minimum effect-size and persistence criteria.

## 2.6 Missing machine responses will not be imputed

No generated response will be synthesized or duplicated to fill a missing replication.

## 2.7 Confirmatory and exploratory analyses remain separate

Any analysis not specified as confirmatory in this SAP will be labeled secondary, descriptive, or exploratory.

---

# 3. Analysis Populations

MIBO defines four analysis populations.

## 3.1 Ecological Live Core Population

This population contains valid observations from:

- the four registered public service lineages;
- their registered public web-interface Live modes;
- all 12 conceptual items;
- Japanese and English forms;
- 12 monthly waves;
- the Japan coordinating site; and
- up to 10 valid replications per cell.

The intended maximum is:

\[
4 \times 12 \times 2 \times 12 \times 10
=
11{,}520
\]

valid observations.

This is the primary population for longitudinal service-lineage analysis.

## 3.2 Paired-Harness Frozen–Live Population

This population contains valid API observations from:

- the providers admitted by the Frozen–Live Comparability Registry;
- the four English Anchor Items;
- a Paired Live Reference;
- a Frozen Reference;
- 12 waves; and
- up to 10 valid replications per cell.

With two admitted providers, the intended maximum is:

\[
2 \times 4 \times 2 \times 12 \times 10
=
1{,}920
\]

observations.

With three admitted providers, the maximum is 2,880.

This is the primary population for H3.

## 3.3 Re-observability Calibration Population

This population contains valid English Anchor observations from:

- four public service lineages;
- four calibration waves;
- Japan and at least two international mirror sites;
- Window A and Window B; and
- up to 10 valid replications per cell.

With exactly three sites, the intended maximum is:

\[
4 \times 4 \times 4 \times 3 \times 2 \times 10
=
3{,}840
\]

observations.

The Japan Window A observations overlap with and are reused from the Ecological Live Core Population.

This population is used for H1 and H5.

## 3.4 Supplementary Population

The Supplementary Population includes:

- late supplementary observations;
- event-triggered observations;
- refreshment samples;
- Class C Frozen–Live comparisons;
- local-language mirror extensions;
- additional services;
- and observations collected outside the primary registered conditions.

Supplementary observations will not enter the primary confirmatory analyses.

---

# 4. Primary Confirmatory Outcomes

The primary confirmatory outcomes are the four Anchor outcomes specified in the Query Codebook.

| Item | Outcome | Raw scale | Normalized scale |
|---|---|---:|---:|
| MIBO-I03 | Citation adequacy | 0–2 | Raw score / 2 |
| MIBO-I05 | Requirement completeness | 0–1 | Unchanged |
| MIBO-I07 | RAG concept coverage | 0–6 | Raw score / 6 |
| MIBO-I09 | Epistemic caution | 0–4 | Raw score / 4 |

The normalized score is denoted:

\[
Z \in [0,1]
\]

Normalization is used only to express effect magnitudes on a common scale and to support the G-study.

It does not imply that the four outcomes measure one latent construct.

---

# 5. Secondary Outcomes

The principal secondary outcome for each non-Anchor item is:

| Item | Secondary outcome |
|---|---|
| MIBO-I01 | Rank-weighted visibility of named generative-AI services |
| MIBO-I02 | Rank-weighted researcher visibility and representation distributions |
| MIBO-I04 | Explicit distinction between peer-reviewed evidence and commentary/vendor claims |
| MIBO-I06 | Rank-weighted recommended-resource visibility and attribute completeness |
| MIBO-I08 | Required comparative-element coverage, 0–9 |
| MIBO-I10 | Safety-response adequacy, 0–2 |
| MIBO-I11 | Explicit false-premise correction |
| MIBO-I12 | Current legal-status accuracy, 0–2 |

Secondary outcomes will receive:

- distributional summaries;
- longitudinal visualizations;
- effect estimates with uncertainty intervals; and
- clearly labeled secondary or exploratory analysis.

They are not used to determine support for H1–H5 in v1.0.

---

# 6. Analysis Cell and Completeness Rules

A primary analytical cell is defined by the registered combination of:

- Service Lineage ID;
- Line or Mode ID;
- Wave ID;
- Item ID;
- Query Form ID;
- language;
- site; and
- observation window.

## 6.1 Primary cell eligibility

A cell is eligible for primary analysis when it contains:

> **at least 8 valid replications out of the intended 10**

## 6.2 Partial cells

Cells containing 5–7 valid replications may enter prespecified sensitivity and descriptive analyses.

## 6.3 Severely incomplete cells

Cells containing fewer than 5 valid replications are reported descriptively but do not enter the primary inferential analysis.

## 6.4 Complete-cell sensitivity analysis

Every main analysis will be repeated, where feasible, using only cells with all 10 valid replications.

## 6.5 Valid refusals

A valid refusal, safety response, clarification request, or substantive nonanswer remains a valid observation and is not treated as technical missingness.

---

# 7. Data Freeze and Analysis Lock

## 7.1 Raw wave freeze

Each wave package will be frozen according to the Operations Manual before substantive coding begins.

## 7.2 Coding freeze

The coded first-year dataset will be frozen after:

- all registered waves close;
- missingness and deviations are resolved;
- AI-coding validation and audit are completed;
- human verification variables are finalized; and
- the Data Steward approves the analysis manifest.

## 7.3 Analysis lock

Before running confirmatory outcome models, the research team will freeze:

- the final model formulas;
- outcome transformations;
- contrast matrices;
- multiple-testing families;
- software environment;
- analysis scripts; and
- expected output tables.

Corrections of programming errors are permitted and must be logged.

The analysis specification will not be altered merely because a result is null, unstable, or contrary to expectation.

---

# 8. Hypothesis H1: Distributional Necessity

## 8.1 Hypothesis

> Repeated outputs obtained within the same observational cell will exhibit non-negligible variation for at least some preregistered information-behavior outcomes, and ten-replication designs will provide meaningfully greater dependability than one-replication designs.

## 8.2 Data

H1 uses the Re-observability Calibration Population.

It is evaluated separately for each of the four Anchor outcomes.

## 8.3 Session-level variation

For each Anchor outcome, the primary G-study will estimate the residual/session-level variance component on the normalized 0–1 scale.

## 8.4 D-study comparison

For each outcome, the D-study will estimate:

\[
\Phi_{\mathrm{joint}}(k=1)
\]

and:

\[
\Phi_{\mathrm{joint}}(k=10)
\]

under the registered three-site, two-window design.

The dependability gain is:

\[
\Delta\Phi_k
=
\Phi_{\mathrm{joint}}(k=10)
-
\Phi_{\mathrm{joint}}(k=1)
\]

## 8.5 Support rule

H1 will be classified as supported when at least two of the four Anchor outcomes satisfy both:

1. the estimated session-level variance component is greater than zero; and
2. the estimated dependability gain is:

\[
\Delta\Phi_k \geq .10
\]

Bootstrap uncertainty intervals for the variance components and \(\Delta\Phi_k\) will be reported.

The support decision is based on the prespecified point-estimate rule. The uncertainty intervals determine the strength and precision of interpretation.

## 8.6 Additional descriptive measure

For each cell, MIBO will report the **modal deviation rate**:

\[
1 - \frac{\text{frequency of the modal score}}{n_{\mathrm{valid}}}
\]

This estimates how often a randomly selected single output would differ from the modal cell outcome.

The modal deviation rate is descriptive and does not replace the H1 decision rule.

---

# 9. Hypothesis H2: Detectable Longitudinal Change

## 9.1 Hypothesis

> For at least some preregistered Service Lineage × Anchor Outcome × Language trajectories, between-wave change will exceed ordinary within-cell variation and satisfy the registered persistence rule.

## 9.2 Data

H2 uses the Ecological Live Core Population for:

- the four Anchor Items;
- four service lineages;
- Japanese and English;
- 12 waves; and
- eligible primary cells.

## 9.3 Outcome models

### MIBO-I03

Citation adequacy is ordinal with three categories.

The primary model is a cumulative logit model with:

- service lineage;
- language;
- wave as a categorical factor; and
- their full interaction.

### MIBO-I05, MIBO-I07, and MIBO-I09

These outcomes are bounded component scores.

The primary model is a beta-binomial regression using:

- the observed component score as successes;
- the remaining possible components as failures;
- service lineage;
- language;
- wave as a categorical factor; and
- their full interaction.

The beta-binomial distribution is used to accommodate overdispersion beyond an ordinary binomial model.

## 9.4 Primary contrasts

For each:

> **Service Lineage × Anchor Outcome × Language**

trajectory, every post-baseline wave will be contrasted with Wave 1.

Effects will be expressed as the difference in model-estimated normalized expected score:

\[
\Delta_{t}
=
E(Z_t)-E(Z_{W01})
\]

## 9.5 Minimum practically important difference

A candidate longitudinal change must satisfy:

\[
|\Delta_t| \geq .15
\]

on the normalized 0–1 scale.

## 9.6 Statistical criterion

Within each Anchor-outcome family, all Wave 1 versus post-baseline contrasts will be adjusted using the Benjamini–Hochberg false-discovery-rate procedure.

A candidate change requires:

\[
q \leq .05
\]

## 9.7 Persistence rule

A candidate change at Wave \(t\) becomes a **sustained longitudinal change** when the immediately following registered wave:

1. shows a difference in the same direction;
2. has:

\[
|\Delta_{t+1}| \geq .10
\]

and
3. has:

\[
q \leq .05
\]

A Wave 12 difference cannot initiate a sustained-change claim because no registered confirmation wave follows it. It may be reported as a candidate end-of-cycle change.

## 9.8 Support rule

H2 will be classified as supported when at least one preregistered trajectory satisfies the sustained longitudinal-change rule.

The exact service, item, language, onset wave, effect size, and duration must be reported.

Support for H2 does not imply that every service or information behavior changed.

---

# 10. Hypothesis H3: Dual-Line Divergence

## 10.1 Hypothesis

> For at least some preregistered eligible provider–outcome trajectories, the Paired Live Reference will diverge longitudinally from the Frozen Reference.

## 10.2 Data

H3 uses the Paired-Harness Frozen–Live Population.

Only:

- pre-admitted Class A or Class B pairs;
- English Anchor Items;
- eligible primary cells; and
- observations collected under the registered common harness

enter the primary analysis.

## 10.3 Models

For each Anchor outcome, the primary model includes:

- provider lineage;
- Line: Paired Live Reference or Frozen Reference;
- wave as a categorical factor; and
- their full interaction.

MIBO-I03 uses cumulative-logit modeling.

MIBO-I05, MIBO-I07, and MIBO-I09 use beta-binomial modeling.

## 10.4 Baseline-adjusted contrast

For each provider, outcome, and post-baseline wave:

\[
\Delta_{\mathrm{update},t}
=
\left[
E(Z^{L}_t)-E(Z^{F}_t)
\right]
-
\left[
E(Z^{L}_{W01})-E(Z^{F}_{W01})
\right]
\]

## 10.5 Minimum practically important difference

A candidate dual-line divergence must satisfy:

\[
|\Delta_{\mathrm{update},t}| \geq .15
\]

## 10.6 Statistical and persistence criteria

Within each Anchor-outcome family, contrasts will be controlled using Benjamini–Hochberg FDR.

A candidate divergence requires:

\[
q \leq .05
\]

It becomes sustained when the next registered wave:

- remains in the same direction;
- has an absolute baseline-adjusted contrast of at least .10; and
- has \(q \leq .05\).

## 10.7 Support rule

H3 will be classified as supported when at least one eligible provider–outcome trajectory satisfies the sustained dual-line-divergence rule.

Interpretation is determined by the prospective pair class:

| Class | Permitted interpretation |
|---|---|
| A | Model-update contrast |
| B | Deployment-update contrast |
| C | Not eligible for H3 |

A Class B result must identify the unresolved deployment components.

---

# 11. Hypothesis H4: Frozen-Line Environmental Sensitivity

## 11.1 Current design status

The first-year primary paired module is environment-closed:

- retrieval is disabled;
- tools are disabled; and
- no common external information layer is supplied.

Under this design, Frozen-Line temporal change cannot be interpreted as change in an accessible external information environment.

## 11.2 Confirmatory status

H4 will therefore be classified as:

> **Not assessed in the primary MIBO 1.0 confirmatory analysis**

unless an environment-open Frozen stratum is separately preregistered before Wave 1.

## 11.3 Protocol alignment

The Master Protocol v1.0-rc3 defines H4 as conditional on preregistration of a matched environment-open Frozen stratum. The current first-year environment-closed paired module therefore classifies H4 as not assessed.

## 11.4 Residual Frozen change

Temporal changes observed in the environment-closed Frozen Reference will be reported as:

> **residual change under the nominally fixed configuration**

They may indicate:

- stochastic variation;
- unidentified provider-side change;
- infrastructure change;
- configuration contamination; or
- measurement instability.

They will not be labeled information-environment effects.

---

# 12. Hypothesis H5: Re-observability

## 12.1 Hypothesis

> At least one preregistered Anchor outcome will attain a joint absolute dependability coefficient of at least .80 under the registered multisite calibration design.

## 12.2 Data

H5 uses the Re-observability Calibration Population.

Site re-observability is assessed only when at least three eligible sites complete the required calibration observations.

## 12.3 Primary outcome-specific G-studies

A separate primary G-study will be conducted for each Anchor outcome.

For a fixed Anchor outcome, the objects of measurement are:

> **Service Lineage × Calibration Wave**

With four service lineages and four calibration waves, each outcome may provide up to 16 objects.

The facets are:

- site;
- adjacent window; and
- session replication.

## 12.4 Primary normalized-score model

For the primary G-study, the Anchor score is normalized to the 0–1 scale.

The variance-component model includes:

- object;
- site;
- window;
- object × site;
- object × window;
- site × window;
- object × site × window; and
- residual/session variation.

The primary model is fitted by restricted maximum likelihood.

Because the outcomes are bounded or ordinal, outcome-appropriate generalized models will be used as sensitivity analyses where technically stable.

## 12.5 Absolute error variance

For a D-study design with:

- \(n_s\) sites;
- \(n_w\) adjacent windows; and
- \(n_r\) replications,

the absolute error variance is calculated from the relevant estimated components:

\[
\sigma^2_{\Delta}
=
\frac{\sigma^2_s}{n_s}
+
\frac{\sigma^2_w}{n_w}
+
\frac{\sigma^2_{sw}}{n_sn_w}
+
\frac{\sigma^2_{os}}{n_s}
+
\frac{\sigma^2_{ow}}{n_w}
+
\frac{\sigma^2_{osw}}{n_sn_w}
+
\frac{\sigma^2_e}{n_sn_wn_r}
\]

where \(o\) denotes the object of measurement.

## 12.6 Joint absolute dependability coefficient

\[
\Phi_{\mathrm{joint}}
=
\frac{\sigma^2_o}
{\sigma^2_o+\sigma^2_{\Delta}}
\]

The primary first-year D-study uses:

- \(n_s=3\);
- \(n_w=2\); and
- \(n_r=10\).

## 12.7 Certification rule

An Anchor-outcome measurement design will be classified as **re-observable across the registered sites** when:

1. at least three eligible sites complete the required calibration data;
2. the variance-component model converges;
3. the coefficient is estimable; and
4. the point estimate satisfies:

\[
\Phi_{\mathrm{joint}} \geq .80
\]

A 95% parametric-bootstrap uncertainty interval will be reported.

The point-estimate threshold determines the v1.0 classification. The uncertainty interval must accompany every claim and limits the strength of interpretation.

## 12.8 Support rule

H5 will be classified as supported when at least one of the four Anchor outcomes meets the certification rule.

MIBO will identify which outcomes meet or fail the criterion.

It will not generalize the classification to the entire service, model, or Observatory.

## 12.9 Directional diagnostics

MIBO will report:

- estimated session-related error;
- site-related error;
- adjacent-window-related error; and
- their relevant object interactions.

Directional dependability coefficients may be reported as diagnostic D-studies, but they do not replace \(\Phi_{\mathrm{joint}}\) as the primary certification indicator.

## 12.10 Pooled design summary

A pooled secondary G-study may normalize and combine all four Anchor outcomes, yielding up to 64:

> **Service Lineage × Anchor Item × Calibration Wave**

objects.

This pooled coefficient summarizes the overall measurement architecture but is not used to certify any individual outcome.

---

# 13. Estimation and Uncertainty

## 13.1 Confidence level

All primary interval estimates will use 95% uncertainty intervals.

## 13.2 Model-based estimates

Longitudinal and Frozen–Live effects will be derived from model-estimated marginal means or probabilities.

## 13.3 Bootstrap

Parametric bootstrap with at least 2,000 successful replications will be used for:

- G-study variance-component uncertainty;
- dependability-coefficient uncertainty;
- D-study contrasts; and
- other complex derived quantities where analytic intervals are unreliable.

The random seed will be fixed and recorded.

## 13.4 Boundary estimates

Variance components estimated at zero will be retained as zero.

They will not be replaced with arbitrary positive values.

Boundary behavior and nonconvergence will be reported.

---

# 14. Multiple Testing

## 14.1 H2 families

For H2, each Anchor outcome constitutes one multiple-testing family.

Within that family, all:

> **Service Lineage × Language × Post-baseline Wave**

contrasts are adjusted using Benjamini–Hochberg FDR at .05.

## 14.2 H3 families

For H3, each Anchor outcome constitutes one family.

Within that family, all:

> **Eligible Provider × Post-baseline Wave**

baseline-adjusted dual-line contrasts are controlled at FDR .05.

## 14.3 H1 and H5

H1 and H5 use predefined design-level decision rules and are not subjected to additional p-value multiplicity adjustment.

All four outcome-specific results will nevertheless be reported, not only those crossing the threshold.

## 14.4 Secondary analyses

Secondary and exploratory p-values, if calculated, will be labeled as such.

They will not be used to convert an unregistered pattern into a confirmatory finding.

---

# 15. Model Diagnostics and Fallback Rules

## 15.1 Ordinal models

For MIBO-I03:

- proportional-odds assumptions will be inspected;
- convergence will be checked;
- sparse categories will be reported; and
- profile or bootstrap intervals will be preferred where feasible.

If the cumulative-logit model fails:

1. use a partial proportional-odds model where prespecified and identifiable;
2. otherwise analyze the normalized score using a robust linear model as a sensitivity analysis; and
3. classify the primary ordinal result as not estimable if no defensible model converges.

## 15.2 Beta-binomial models

For MIBO-I05, MIBO-I07, and MIBO-I09:

- convergence;
- dispersion;
- residual patterns;
- fitted probabilities; and
- influential cells

will be inspected.

If the beta-binomial model fails:

1. fit an ordinary binomial model with robust uncertainty;
2. compare with a cell-level bootstrap analysis; and
3. clearly identify the fallback model.

## 15.3 G-study models

If the primary G-study model is singular or nonconvergent:

1. verify data structure and factor coding;
2. fit the preregistered reduced model that removes the smallest non-object interaction component;
3. report both attempts; and
4. classify the outcome as not assessable when a stable coefficient cannot be obtained.

Model reduction will not be chosen based on whether \(\Phi\) crosses .80.

---

# 16. Missingness

## 16.1 No response imputation

Substantive outputs will not be imputed.

## 16.2 Observed-data analysis

Primary models will use eligible observed cells.

The number of valid replications contributes directly to grouped outcome denominators.

## 16.3 Missingness summaries

For every wave and service lineage, MIBO will report:

- intended observations;
- valid observations;
- technical failures;
- invalid administrations;
- refusals and safety responses;
- late supplementary observations; and
- missing cells.

## 16.4 Sensitivity analysis

Where missingness is material, analyses will be compared across:

- cells with at least 8 valid replications;
- complete 10-replication cells; and
- cells with at least 5 valid replications.

No missing-at-random assumption will be treated as empirically established.

## 16.5 Attrition

Post-attrition waves will not be imputed.

The affected lineage remains in historical analyses for the period in which it was observable.

---

# 17. Protocol Deviations

## 17.1 Minor deviations

Minor deviations remain in the primary analysis unless the SAP specifies otherwise.

## 17.2 Material deviations

Observations affected by a material deviation will ordinarily be excluded from the primary analysis and retained in a sensitivity analysis.

## 17.3 Critical deviations

Observations affected by a critical deviation are excluded from confirmatory analysis.

They remain in the integrity record.

## 17.4 Configuration boundaries

When a service configuration changes within a wave:

- pre-event and post-event observations are flagged;
- the standard cell may be classified as heterogeneous;
- the primary analysis may exclude the affected cell; and
- a descriptive event analysis may be reported.

No configuration boundary is concealed by averaging the two states without disclosure.

---

# 18. AI-Assisted Coding Validation

## 18.1 Scope

AI-assisted coding may be used only for variables marked **A** in the Query Codebook.

Variables marked **H** require final human verification.

## 18.2 Prompt-development set

AI-coding prompts may be developed using Pilot data or a separate development set.

No response in the locked validation set may be used to tune the prompt.

## 18.3 Locked human reference set

The initial locked validation set will contain at least:

\[
12 \text{ items}
\times
2 \text{ languages}
\times
10 \text{ responses}
=
240 \text{ responses}
\]

It will be stratified across:

- items;
- languages;
- services; and
- relevant response categories.

Rare or ambiguous categories may be deliberately oversampled before the set is locked.

Two human coders will code the set independently, followed by human adjudication.

## 18.4 Validation metrics

The primary metric is selected by variable type.

| Variable type | Primary validation metric | Default threshold |
|---|---|---:|
| Binary or nominal semantic coding | Macro-F1 | .80 |
| Ordinal semantic coding | Ordinal Krippendorff’s alpha | .80 |
| Deterministic extraction | Exact-match rate | .95 |

A different metric or threshold requires justification before confirmatory coding.

## 18.5 Failed validation

A variable that fails validation will:

- be coded by humans;
- be redesigned and tested against a new unused validation set; or
- be restricted to exploratory use.

It will not serve as the sole basis for a confirmatory claim.

## 18.6 Human audit

A stratified 10% sample of AI-coded confirmatory observations will receive human audit.

The audit will use the same principal metric and threshold as validation.

If the audit falls below the registered threshold:

1. the affected variable is suspended;
2. the source of disagreement is investigated;
3. the affected analysis is rerun after correction or human coding; and
4. the event is documented in the AI Analysis Record.

## 18.7 Claim review

Before Claim Registry entry, at least two human researchers will review:

- representative raw responses;
- boundary cases;
- coding validation;
- audit results;
- statistical estimates;
- missingness;
- deviations; and
- proposed claim wording.

---

# 19. Rank and Visibility Analyses

Ranked-list items will use transparent item-specific measures.

## 19.1 Rank weight

For a list of length \(K\), an entity at rank \(r\) receives:

\[
w_{r} = \frac{K-r+1}{K}
\]

An unlisted entity receives zero.

## 19.2 Rank-weighted visibility

For an entity \(e\) in a cell:

\[
V_e
=
\frac{1}{n_{\mathrm{valid}}}
\sum_{r=1}^{n_{\mathrm{valid}}} w_{er}
\]

## 19.3 Additional summaries

MIBO may report:

- appearance probability;
- mean rank conditional on appearance;
- provider or institutional concentration;
- Jaccard similarity;
- Rank-Biased Overlap;
- and rank-transition visualizations.

These analyses are secondary unless separately preregistered.

---

# 20. Source and Citation Analyses

Source analyses may report:

- citation probability;
- number of displayed sources;
- official-source probability;
- peer-reviewed-source probability;
- vendor-source probability;
- source-domain concentration;
- claim-support distribution;
- link persistence; and
- source-network structure.

Claim–source support and official or peer-reviewed status require human verification under the Codebook.

Network and concentration analyses are secondary or exploratory unless explicitly registered as part of an Anchor outcome.

---

# 21. Exploratory Analyses

The following are exploratory:

- unsupervised semantic clustering;
- embedding-based trajectory analysis;
- automated topic discovery;
- change-point detection outside the sustained-change rule;
- event-study analysis around provider announcements;
- UI–API descriptive differences;
- local-language mirror comparisons;
- provider-specific citation networks;
- minority-output characterization;
- response-length and stylistic analysis;
- analysis of refreshment samples; and
- self-evaluation by the observed service lineage.

Any embedding model or AI analysis model used for exploration will be versioned and disclosed.

Exploratory results may generate hypotheses for MIBO v2.0 but will not retrospectively alter v1.0 confirmatory definitions.

---

# 22. Sensitivity Analyses

The following sensitivity analyses are prespecified.

## 22.1 Cell-completeness sensitivity

Repeat primary analyses using:

- only cells with 10 valid replications; and
- cells with at least 5 valid replications.

## 22.2 Protocol-deviation sensitivity

Repeat primary analyses after excluding:

- material deviations;
- configuration-boundary cells; and
- late supplementary observations.

## 22.3 Coding sensitivity

For AI-assisted variables:

- compare AI-coded results with the audited human subset;
- repeat key estimates on human-verified Claim Review data where feasible; and
- exclude variables failing validation or audit.

## 22.4 Model-form sensitivity

Compare:

- beta-binomial with ordinary binomial models;
- ordinal with normalized-score models; and
- primary G-study with outcome-appropriate generalized sensitivity models.

## 22.5 Pair-class sensitivity

Frozen–Live results will be reported separately for:

- Class A pairs; and
- Class B pairs.

They will not be pooled into one undifferentiated update estimate.

---

# 23. No Conventional Power Calculation

MIBO is a fixed sentinel-panel census of the selected services, items, waves, sites, and replications rather than a sample-size-optimized human-participant experiment.

The first-year design size is determined by:

- the fixed four-member panel;
- the 12-wave annual cycle;
- the fixed 12-item instrument;
- the \(k=10\) distributional standard;
- and the minimum three-site calibration design.

Accordingly, no conventional participant-level power calculation determines the design.

Before final preregistration, simulation will be used to assess:

- expected interval width;
- recoverability of .10 and .15 normalized changes;
- beta-binomial overdispersion;
- G-study coefficient stability; and
- the effect of incomplete cells.

Simulation results may inform interpretation and future D-studies but will not be used to reduce the registered first-year design after observation begins.

---

# 24. Software and Reproducibility

## 24.1 Primary environment

Confirmatory analysis will be conducted in R and, where necessary, Python.

The exact software versions will be frozen before confirmatory analysis.

## 24.2 Anticipated R tools

The anticipated tools include:

- `ordinal` for cumulative-link models;
- `glmmTMB` for beta-binomial models;
- `lme4` or equivalent verified variance-component software for G-studies;
- `emmeans` or equivalent for registered contrasts;
- `boot` or equivalent for bootstrap procedures; and
- `renv` for dependency locking.

Equivalent tools may be substituted before the analysis lock when justified and documented.

## 24.3 Reproducible environment

The analysis release will include:

- source code;
- package lock files;
- random seeds;
- session information;
- input-data hashes;
- output-file hashes;
- and a machine-readable analysis manifest.

## 24.4 Human code review

At least one human researcher other than the original code author will review the primary confirmatory scripts where staffing permits.

At minimum, a human researcher must execute and verify all final scripts and outputs.

---

# 25. Reporting

Every first-year confirmatory report will include:

1. the registered panel and attrition history;
2. intended and valid observation counts;
3. cell-completeness distributions;
4. protocol deviations;
5. coding validation and audit results;
6. all four Anchor-outcome results;
7. H1–H5 decision status;
8. effect estimates and uncertainty intervals;
9. multiplicity-adjusted results;
10. Frozen–Live pair classes;
11. G-study variance components;
12. \(\Phi_{\mathrm{joint}}\) and D-study results;
13. sensitivity analyses;
14. corrections or amendments; and
15. links to code, metadata, and permitted data.

Null, unstable, or non-reobservable outcomes will be reported alongside positive outcomes.

---

# 26. Hypothesis Decision Table

| Hypothesis | Primary data | Support rule |
|---|---|---|
| H1 Distributional necessity | Calibration Population | At least 2 of 4 Anchor outcomes have positive session variance and \(\Delta\Phi_k \geq .10\) from \(k=1\) to \(k=10\) |
| H2 Detectable longitudinal change | Ecological Live Core | At least one service–outcome–language trajectory satisfies .15 initial effect, FDR .05, and next-wave persistence of .10 with FDR .05 |
| H3 Dual-line divergence | Paired-Harness Population | At least one eligible provider–outcome trajectory satisfies the baseline-adjusted dual-line sustained-change rule |
| H4 Frozen environmental sensitivity | Not tested in primary v1.0 | Not assessed unless an environment-open stratum is preregistered before Wave 1 |
| H5 Re-observability | Calibration Population | At least one Anchor outcome has estimable \(\Phi_{\mathrm{joint}} \geq .80\) using at least 3 eligible sites |

No hypothesis will be redefined after confirmatory outcome inspection.

---

# 27. Cross-Document Alignment

The Master Protocol, Frozen–Live Comparability Registry, Operations Manual, and this SAP use the following common structure:

- Ecological Live Line: public web-interface panel observation;
- Paired Live Reference: current API reference under the common harness;
- Frozen Reference: baseline API reference under the common harness;
- environment-closed paired module as the primary first-year design; and
- H4 not assessed unless a matched environment-open stratum is preregistered before Wave 1.

No unresolved analytical contradiction remains at the integrated release-candidate stage.

# 28. Final Analytical Principle

MIBO adopts the following principle:

> **A change is scientifically reportable only when its magnitude exceeds the registered threshold, its uncertainty is disclosed, its persistence is demonstrated where required, and the measurement conditions supporting it remain inspectable.**

The objective is not to maximize the number of statistically significant findings.

It is to distinguish:

- stochastic output variation;
- sustained panel change;
- model or deployment divergence;
- site dependence; and
- measurement designs capable of supporting re-observable claims.

---

# Appendix A. Planned Primary Models

## A.1 Ecological Live longitudinal models

### Citation adequacy

```text
ordinal_score ~ service_lineage * language * wave
```

Cumulative-logit model.

### Requirement completeness, RAG coverage, and epistemic caution

```text
cbind(score, maximum_score - score)
  ~ service_lineage * language * wave
```

Beta-binomial model.

## A.2 Paired Frozen–Live models

### Citation adequacy

```text
ordinal_score ~ provider * line * wave
```

Cumulative-logit model.

### Component outcomes

```text
cbind(score, maximum_score - score)
  ~ provider * line * wave
```

Beta-binomial model.

## A.3 G-study

For each Anchor outcome:

```text
normalized_score
  ~ 1
  + (1 | object)
  + (1 | site)
  + (1 | window)
  + (1 | object:site)
  + (1 | object:window)
  + (1 | site:window)
  + (1 | object:site:window)
```

Residual variation represents session-level variation within Object × Site × Window.

The final executable formula may differ in syntax across software but must represent the registered variance structure.

---

# Appendix B. Methods References

The final SAP repository will archive or link the methodological documentation used to implement the registered analyses.

## Generalizability theory

- National Council on Measurement in Education. *Introduction to Generalizability Theory.*
- Brennan, R. L. *Generalizability Theory* and related NCME instructional materials.
- Educational Measurement, Fifth Edition, chapter on reliability and generalizability theory.

## Ordinal models

- R package `ordinal`: cumulative-link and cumulative-link mixed models.

## Generalized models

- R package `glmmTMB`: generalized linear mixed models, including beta-binomial models.

## Preregistration

- Center for Open Science and Open Science Framework registration guidance.

The exact software references and versions will be added at the final analysis lock.

---

# Appendix C. Final Approval Fields

| Field | Entry |
|---|---|
| Principal Investigator | To be completed |
| Methods Lead | To be completed |
| Statistical Lead | To be completed |
| G-Theory Lead | To be completed |
| AI-Coding Validation Lead | To be completed |
| Simulation review completed | To be completed |
| Final approval date | To be completed |
| Effective date | 1 September 2026 |
| Final document SHA-256 | To be generated at final freeze |
