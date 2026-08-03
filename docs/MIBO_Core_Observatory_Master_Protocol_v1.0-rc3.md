# MIBO Core Observatory Master Protocol v1.0-rc3

## A Sentinel Panel Survey of Public Generative-AI Information Behavior

**Document status:** Integrated Release Candidate for Preregistration  
**Authoritative language:** English  
**Planned observation start:** 1 September 2026  
**Protocol version:** 1.0-rc2  
**Document date:** 3 August 2026  

---

## Table of Contents

1. Background and Formal Definition
2. Research Objectives, Questions, and Hypotheses
3. Sentinel Panel Selection and Lineage Continuity
4. Fixed Query Instrument and Synchronized Survey Waves
5. Parallel Frozen and Live Lines
6. Within-Cell Replication and Distributional Observation
7. Generalizability-Theoretic Assessment of Re-observability
8. MIBO Network and International Mirror Replication
9. Missingness, Attrition, Ethics, Openness, Correction, Withdrawal, and AI-Assisted Analysis

---

# 1. Background and Formal Definition

## 1.1 Background

Publicly deployed generative-AI services have become important intermediaries between people and information. They select which entities to mention, determine the order in which information is presented, synthesize claims from multiple sources, recommend particular options, cite or omit evidence, express or suppress uncertainty, and sometimes refuse to answer.

These behaviors are not necessarily stable. A response may vary because of stochastic generation, model replacement, retrieval-system updates, changes in available information, alterations to system policies, interface modifications, geographic conditions, or other elements of the deployed service configuration. Consequently, a difference between two outputs cannot automatically be interpreted as meaningful behavioral change.

Most evaluations of generative AI are based on one-time tests, comparisons between model snapshots, or repeated measurements of whichever systems are available at a given time. Such designs can identify differences between observations, but they do not necessarily establish a persistent panel unit, follow the same service lineage across predefined survey waves, or distinguish longitudinal change from within-condition output variation.

MIBO addresses this problem by applying panel-survey methodology to the longitudinal observation of public generative-AI services.

## 1.2 Formal Definition of MIBO

> **MIBO is a sentinel panel survey of generative AI in the methodological sense. It identifies major public generative-AI service lineages as persistent panel units and repeatedly administers a version-controlled fixed query instrument across multiple synchronized survey waves.**

Its core design consists of three components:

1. **Parallel observation of a Frozen Line and a Live Line;**
2. **Ten independent replications within each observational cell, treating machine responses as distributions rather than single points; and**
3. **A generalizability-theoretic assessment of re-observability using multisite calibration data.**

MIBO also publishes its Japan-originated observation protocol as the **MIBO Mirror Observatory Kit**. Independent mirror observatories outside Japan reproduce designated parts of the protocol in order to evaluate the cross-site generalizability of both the observed findings and the measurement procedure.

For general public communication, MIBO may be described as:

> **The world’s first panel survey of generative AI.**

For academic communication, the preferred formulation is:

> **To our knowledge, MIBO is the first sentinel panel survey of generative AI in the methodological sense, following persistently identified public generative-AI service lineages with a version-controlled fixed query instrument across synchronized survey waves.**

The phrase *to our knowledge* shall be retained in scholarly publications unless a preregistered scoping review provides sufficient grounds for a stronger priority claim.

## 1.3 MIBO as a Panel Survey

The term **panel survey** is used as a methodological classification, not as a metaphor.

A panel survey repeatedly measures the same identified units using the same or functionally comparable instrument across multiple survey waves. MIBO implements this structure as follows:

| Panel-survey component | MIBO implementation |
|---|---|
| Target population | Publicly accessible, general-purpose generative-AI services |
| Panel unit | A persistently identified generative-AI service lineage |
| Panel identifier | A permanent Service Lineage ID |
| Survey instrument | A version-controlled fixed query instrument |
| Survey item | A standardized query and its defined coding scheme |
| Survey wave | A synchronized observation period |
| Unit state at each wave | The deployed answering configuration observed at that time |
| Within-wave response | An independently generated output |
| Within-wave replication | Ten independent sessions per observational cell |
| Within-unit change | Change within the same service lineage across waves |
| Between-unit difference | Difference between service lineages |
| Nonresponse | Refusal, error, timeout, access failure, or unusable output |
| Attrition | Discontinuation or permanent inaccessibility of a panel lineage |
| Refreshment sample | A newly admitted service lineage introduced under a predefined rule |

The panel member is not a particular model version. It is the continuing public service lineage.

A change from one displayed model version to another therefore does not automatically create a new panel unit. It may instead represent a time-varying state of the same service lineage. A new Panel ID is required only when the predefined continuity rules determine that the original lineage has ended or has become methodologically incomparable.

## 1.4 Object of Observation

MIBO observes **public generative-AI information behavior**.

This refers to externally observable patterns through which a deployed generative-AI service:

- selects entities, claims, sources, or options;
- orders and prioritizes information;
- synthesizes and explains information;
- cites, attributes, or omits sources;
- recommends actions, products, institutions, or policies;
- communicates uncertainty;
- refuses, restricts, or redirects a request;
- corrects or updates a prior position; and
- excludes information that could reasonably have been included.

MIBO does not directly infer whether a model internally “knows,” “believes,” “understands,” or “intends” anything. Its claims concern observable outputs under documented conditions.

The principal observational unit at a given survey wave is the **deployed answering configuration**, including, insofar as observable:

- the service lineage;
- displayed model or mode;
- interface or API;
- retrieval and browsing availability;
- tool configuration;
- locale and language;
- account tier;
- memory and personalization settings;
- observation site; and
- date and time of execution.

## 1.5 Core Methodological Architecture

### 1.5.1 Frozen–Live Architecture

MIBO distinguishes three linked observational conditions.

1. **Ecological Live Line:** the current public web-interface service that users encounter and that constitutes the principal longitudinal panel observation;
2. **Paired Live Reference:** a current eligible API model executed under the fixed MIBO research harness; and
3. **Frozen Reference:** a baseline version-identified API model executed under the same harness.

The Paired Live Reference and Frozen Reference form the primary decomposition pair. A public web interface shall not be directly subtracted from an API Frozen Reference and interpreted as a pure model-update effect.

A paired-harness contrast shall be described as a **model-update contrast** only when model state is the sole material difference. When another deployment component cannot be matched or verified, the result shall be described as a **deployment-update contrast**. Public-UI and API differences remain descriptive unless separately justified.

The first-year primary paired module is environment-closed: retrieval and tools are disabled under the common harness. An environment-open Frozen stratum may be introduced only through preregistration before Wave 1 or through a later protocol version.

Frozen References shall be included only where a defensible level of identity, availability, and comparability can be maintained. MIBO shall not construct an artificial Frozen condition merely to achieve symmetry across all services.

### 1.5.2 Ten Independent Within-Cell Replications

Each observational cell shall be measured through ten independent replications.

An observational cell is defined by the combination of:

- panel unit;
- survey wave;
- query item;
- language;
- Frozen or Live Line;
- observation site; and
- designated observation window.

The ten outputs constitute a conditional response distribution. MIBO therefore measures quantities such as appearance probability, refusal probability, rank distribution, source-selection frequency, response similarity, dispersion, and concentration rather than relying exclusively on a single output.

Each replication shall ordinarily use:

- a new session;
- no prior conversational history;
- standardized memory and personalization conditions;
- a recorded execution order;
- the same designated survey-wave window; and
- complete documentation of failures and retries.

The value \(k=10\) is the operational standard for MIBO 1.0. It is not assumed to be universally optimal. Subsequent decision studies may determine whether fewer or additional replications are required for particular outcomes.

### 1.5.3 Generalizability-Theoretic Re-observability

MIBO defines **re-observability** as a measurable property of a measurement design and the results obtained under it.

> **Re-observability is the dependability with which defined machine-information-behavior results can be recovered across admissible independent sessions, observation sites, and adjacent within-wave time windows.**

Generalizability theory will be used to estimate variance associated with:

- independent session replication;
- observation site;
- adjacent within-wave time window; and
- relevant interactions among these facets.

The objects of measurement in the calibration design are defined:

> **Service Lineage × Anchor Item × Calibration Wave**

combinations.

Service lineage, anchor item, calibration wave, language, and Frozen or Live status are substantive variables rather than undifferentiated sources of measurement error.

The primary re-observability indicator will be the **joint absolute dependability coefficient**, \(\Phi_{\mathrm{joint}}\). Directional coefficients for sessions, sites, and adjacent windows will be reported as diagnostic measures.

A measurement design will be classified as re-observable for a preregistered outcome when its joint absolute dependability coefficient meets the registered threshold. Individual findings may then be described as having been obtained under a re-observable measurement design.

The final coefficient thresholds and decision rules shall be specified in the Statistical Analysis Plan before confirmatory data collection.

## 1.6 MIBO Observatory System

MIBO consists of three organizational elements.

### MIBO Core Observatory

The Core Observatory conducts the fixed-panel longitudinal survey of public generative-AI information behavior. It maintains the common panel registry, survey instrument, synchronized-wave schedule, coding system, data structure, and claim-management procedures.

### MIBO Sub-Observatories

Sub-Observatories apply MIBO methods to defined domains, regions, or informational conditions. Planned examples include:

- MIBO-Okayama;
- MIBO-NOW;
- MIBO-Q;
- MIBO Economy;
- MIBO Politics; and
- MIBO Singularity.

Sub-Observatory data shall not automatically be pooled with Core Observatory data. Each Sub-Observatory requires a separate charter, protocol, and analytical scope.

### MIBO Network

The MIBO Network consists of the coordinating observatory in Japan and independent international mirror observatories using the MIBO Mirror Observatory Kit.

The Network is not an additional observational tier. It is the international replication structure through which selected Core procedures and findings are independently re-observed across sites.

## 1.7 Transition from the MIBO Pilot

Observations, methodological experiments, provisional claims, and related activities conducted before 1 September 2026 shall be classified as the:

> **MIBO Pilot: Developmental Observation Phase**

The Pilot was used to develop:

- panel-unit definitions;
- query structures;
- coding categories;
- replication procedures;
- metadata requirements;
- correction and withdrawal procedures;
- feasibility estimates; and
- the present confirmatory design.

Pilot data may be used for protocol development, hypothesis generation, variance estimation, training, and historical documentation. Unless explicitly stated in a preregistered analysis, Pilot data shall not be included in the primary confirmatory analyses of MIBO Core Observatory v1.0.

The transition to MIBO 1.0 therefore represents a transition from exploratory observational development to a version-controlled, preregistered sentinel panel survey.

## 1.8 Purpose of MIBO Core Observatory v1.0

The purpose of MIBO Core Observatory v1.0 is to establish a durable and internationally reproducible method for observing longitudinal changes in public generative-AI information behavior.

Its first-year objectives are to:

1. maintain a persistent panel of major public generative-AI service lineages;
2. administer the same fixed query instrument across synchronized survey waves;
3. distinguish within-condition output variation from sustained longitudinal change;
4. compare Live and Frozen observational lines where defensible;
5. operationalize and estimate re-observability;
6. enable independent international mirror replication; and
7. produce auditable records of findings, corrections, amendments, and withdrawals.

MIBO’s principal contribution is not the volume of outputs collected. It is the establishment of a survey-methodological framework in which changes in generative-AI behavior can be followed, quantified, challenged, and independently re-observed.

---

# 2. Research Objectives, Questions, and Hypotheses

## 2.1 Primary Aim

The primary aim of MIBO Core Observatory v1.0 is to determine whether longitudinal changes in public generative-AI information behavior can be distinguished from ordinary within-condition output variation and independently re-observed across admissible sessions, sites, and adjacent observation windows.

MIBO does not seek to rank generative-AI services or estimate the behavior of all existing systems. It follows a purposively selected sentinel panel of major public service lineages and estimates change within those identified lineages.

The hypotheses in this Master Protocol define the confirmatory structure of the study. Their exact outcome variables, effect measures, thresholds, and decision rules will be finalized in the preregistered Statistical Analysis Plan before the first confirmatory wave.

## 2.2 Primary Research Questions

### RQ1: Longitudinal change

> How does the information behavior of each identified generative-AI service lineage change across synchronized survey waves?

This question concerns within-lineage changes in outcomes such as:

- entity and source selection;
- ranking and prioritization;
- recommendation;
- citation and attribution;
- uncertainty expression;
- refusal; and
- correction.

### RQ2: Distributional variation

> To what extent do repeated outputs under the same documented conditions vary within an observational cell?

This question determines whether an observed difference represents:

- ordinary stochastic variation;
- an infrequent output;
- a distributional shift; or
- a sustained longitudinal change.

### RQ3: Frozen–Live divergence

> When Frozen and Live Lines can be observed under defensibly comparable conditions, how do their longitudinal trajectories differ?

This question examines whether observed changes are more consistent with:

- changes in the live deployment;
- changes in the information environment accessible to a fixed configuration; or
- changes that cannot be uniquely attributed to either source.

### RQ4: Re-observability

> Under what conditions can defined machine-information-behavior results be recovered across independent sessions, observation sites, and adjacent within-wave time windows?

This question operationalizes re-observability through generalizability-theoretic variance decomposition and decision studies.

### RQ5: Panel continuity

> Which observed changes represent state changes within a continuing service lineage, and which require the declaration of panel discontinuity or the establishment of a new lineage?

This question addresses model replacement, service redesign, interface change, access discontinuation, and other events that may threaten longitudinal comparability.

## 2.3 Confirmatory Hypotheses

MIBO Core Observatory v1.0 will test a limited set of design-level hypotheses. Exact outcome definitions, effect measures, aggregation rules, and decision thresholds will be fixed in the Statistical Analysis Plan before confirmatory observation begins.

### H1: Distributional Necessity Hypothesis

> Repeated outputs obtained within the same observational cell will exhibit non-negligible variation for at least some preregistered information-behavior outcomes.

Accordingly, estimates based on ten replications will provide greater measurement dependability than estimates based on a single output.

This hypothesis establishes whether machine responses must be treated as conditional distributions rather than point observations.

### H2: Detectable Longitudinal Change Hypothesis

> For at least some preregistered Service Lineage × Survey Item combinations, between-wave change will exceed the level of variation observed among replications within the relevant waves.

A change will not be classified as longitudinal drift merely because two individual responses differ. It must satisfy the preregistered distributional and persistence criteria.

### H3: Dual-Line Divergence Hypothesis

> For preregistered paired-harness comparisons that meet the comparability requirements, the longitudinal trajectory of the Paired Live Reference will differ from that of the Frozen Reference for at least some outcomes.

Where model state is the sole material difference, the contrast may be interpreted as a model-update contrast. Otherwise, it will be reported as a deployment-update contrast.

This hypothesis does not assume that the Paired Live Reference will always change more than the Frozen Reference.

### H4: Conditional Frozen-Line Environmental Sensitivity Hypothesis

> If an environment-open Frozen stratum using a matched and registered information-access layer is preregistered before the first confirmatory wave, at least some Frozen-Reference outcomes that depend on changing external information will vary across macro-waves despite the controlled model state.

When no such environment-open stratum is preregistered, H4 will be classified as **not assessed in MIBO 1.0**. Temporal change in the environment-closed Frozen Reference will then be described only as residual change under the nominally fixed configuration and will not be attributed to the external information environment.

### H5: Re-observability Hypothesis

> At least some preregistered Anchor Item outcomes will be measured with a joint absolute dependability coefficient meeting the predefined threshold across independent sessions, observation sites, and adjacent within-wave time windows.

Failure to meet the threshold will be treated as a substantive measurement finding rather than as a protocol failure.

## 2.4 Exploratory Research Questions

The following questions are exploratory and shall not be presented as confirmatory findings unless separately preregistered.

1. Which types of information behavior are most stable over time?
2. Which survey items show the greatest within-cell dispersion?
3. Do citation behavior and substantive answer content change at different rates?
4. Are changes gradual, abrupt, temporary, or persistent?
5. Do service lineages converge or diverge across successive waves?
6. Which observed changes coincide temporally with publicly documented service updates?
7. How do Japanese and English forms of the same survey item differ?
8. Which findings generalize across sites, and which remain geographically or linguistically dependent?
9. How many replications, sites, and adjacent time windows are required to attain acceptable dependability for different outcomes?

Temporal coincidence with a publicly reported update shall not, by itself, establish causation.

## 2.5 Primary Estimands

MIBO will distinguish four principal classes of estimands.

### 2.5.1 Within-lineage change

The change in a defined information-behavior outcome for the same Service Lineage ID between two or more macro-waves.

### 2.5.2 Between-lineage difference

The difference in a defined outcome between two or more panel lineages within the same synchronized survey wave.

### 2.5.3 Frozen–Live contrast

The difference between paired Frozen and Live Lines for the same survey item, language, site, and observation window, subject to the documented comparability conditions.

### 2.5.4 Re-observability

The dependability of the registered measurement design across replications, sites, and adjacent within-wave time windows.

These estimands shall not be combined into a single overall performance score.

## 2.6 Definition of Longitudinal Change

MIBO shall distinguish three levels of observed difference.

### Output difference

Two individual outputs are not identical.

### Distributional shift

The response distribution in one observational cell differs from the distribution in another cell according to a preregistered effect measure.

### Sustained longitudinal change

A distributional shift:

- exceeds the preregistered within-wave variation criterion;
- is not attributable solely to documented collection failure;
- is observed in the required number of replications; and
- satisfies the predefined persistence or confirmation rule.

Only the third level shall ordinarily be described as sustained longitudinal change.

## 2.7 Unit and Scope of Inference

The primary inferential scope of MIBO Core Observatory v1.0 is:

> the selected sentinel panel of persistently identified public generative-AI service lineages during the registered observation period.

MIBO will not claim that results from the sentinel panel statistically represent all generative-AI systems.

Broader generalization may be considered when supported by:

- replication across multiple panel lineages;
- independent mirror observations;
- consistency across sites and languages;
- stable re-observability estimates; and
- explicit justification of the relevant target population.

## 2.8 Success Criteria for the First Observation Year

The first year will be considered methodologically successful if MIBO:

1. maintains the registered sentinel panel or transparently documents attrition;
2. completes the planned synchronized survey waves with documented missingness;
3. obtains ten valid independent replications for the required cells or records all failures;
4. preserves the version-controlled survey instrument;
5. completes the planned Frozen–Live comparisons where technically defensible;
6. estimates the principal variance components for the Anchor Items;
7. conducts the planned international mirror observations;
8. publishes the protocol, metadata structure, analysis code, and permitted derived data; and
9. records corrections, amendments, and withdrawals without retrospective concealment.

Success does not require every hypothesis to be supported. A null result, failed re-observability test, or divergence between mirror sites may constitute an important scientific finding.

---

# 3. Sentinel Panel Selection and Lineage Continuity

## 3.1 Sentinel Panel Design

MIBO Core Observatory v1.0 will follow a purposively selected sentinel panel of major public generative-AI service lineages.

The panel is not a probability sample of all generative-AI systems. Its purpose is to maintain continuous observation of a small number of prominent and methodologically observable service lineages over time.

The sentinel design prioritizes:

- continuity of observation;
- public relevance;
- diversity of deployment characteristics;
- feasibility of standardized measurement; and
- transparent documentation of change.

The initial panel will consist of four service lineages.

The identities of the four lineages will be frozen in the **MIBO Service Registry v1.0** before the first confirmatory survey wave.

## 3.2 Eligibility Criteria

A service lineage is eligible for the Core Observatory when it satisfies all of the following criteria at the time of panel registration:

1. It provides general-purpose generative-AI answering functions.
2. It is publicly accessible to users in Japan through a standard service interface.
3. It is operated as a continuing named service rather than as a temporary research demonstration.
4. It supports standardized presentation of the registered query instrument.
5. Its access conditions can be documented with reasonable precision.
6. Independent sessions can ordinarily be initiated.
7. Memory, personalization, or prior conversation effects can be disabled or otherwise standardized.
8. Its expected operational continuity is sufficient for longitudinal observation.
9. Its terms of service do not prohibit the planned observational procedure.
10. Its inclusion contributes substantively to the diversity of the sentinel panel.

Public accessibility does not require that the service be free of charge. A publicly available subscription tier may be included when its conditions are documented and consistently maintained.

## 3.3 Selection Principles

The initial panel should include service lineages that differ meaningfully in relevant deployment characteristics, such as:

- provider;
- retrieval or browsing integration;
- default answering mode;
- geographic information environment;
- interface architecture; and
- model-update practices.

Selection shall not be based on an attempt to rank the services in advance.

The final selection rationale for each lineage will be documented before observation begins and will include:

- reason for inclusion;
- public access mode;
- account tier;
- standard observation interface;
- availability of a defensible Frozen Line;
- known limitations; and
- continuity risks.

## 3.4 Persistent Identification

Each panel lineage will receive a permanent **Service Lineage ID**.

The identifier shall remain unchanged across ordinary modifications to the service, including:

- displayed model-version changes;
- routine interface redesign;
- retrieval-system updates;
- safety-policy updates;
- branding adjustments;
- tool additions or removals; and
- changes to the default deployed configuration.

These changes are ordinarily treated as changes in the state of the same panel member rather than as the creation of a new member.

Each Service Lineage ID will therefore identify a continuing public service lineage, not a particular underlying model snapshot.

Frozen and Live observations will receive separate **Line IDs** linked to the same parent Service Lineage ID.

For example:

```text
Service Lineage ID: MIBO-SL-001
Live Line ID:       MIBO-SL-001-L
Frozen Line ID:     MIBO-SL-001-F
```

A Frozen Line is not assumed to exist for every service lineage.

## 3.5 Deployed Answering Configuration

At each survey wave, MIBO will record the observed state of each lineage as a **Deployed Answering Configuration**.

The record shall include, where observable:

- Service Lineage ID;
- Line ID;
- service name;
- displayed model or mode;
- interface;
- account tier;
- retrieval or browsing status;
- enabled tools;
- memory and personalization status;
- locale;
- query language;
- observation site;
- execution date and time;
- material interface or policy changes; and
- any known deviation from the registered observation condition.

The Deployed Answering Configuration is a time-varying state record. It does not replace the persistent Service Lineage ID.

## 3.6 Continuity Rules

A service lineage will ordinarily retain its Panel ID when:

- the public service continues under the same or clearly succeeding identity;
- users access it through substantially continuous service arrangements;
- the primary functional purpose remains general-purpose generative answering; and
- changes to models, retrieval, tools, or interface remain interpretable as changes within the continuing service.

A new Service Lineage ID may be required when:

1. the original service is formally terminated and replaced by a distinct service;
2. the provider explicitly presents the successor as a separate product lineage;
3. the access mode changes so fundamentally that longitudinal comparison is no longer defensible;
4. the original answering function is replaced by a substantially different interaction system;
5. two previously distinct services are merged without a defensible continuity rule; or
6. the MIBO Lineage Review determines that retaining the old identifier would misrepresent the observational history.

A change of underlying model alone does not require a new Service Lineage ID.

## 3.7 Lineage Review

Potential discontinuities will be reviewed using a standardized **Lineage Continuity Form**.

The review will consider:

- provider statements;
- continuity of service name and user access;
- continuity of purpose;
- continuity of interaction mode;
- continuity of account and subscription structure;
- continuity of historical conversations, where relevant;
- comparability of the query-administration procedure; and
- the scientific consequences of retaining or replacing the identifier.

The decision will be recorded as one of the following:

- **Continuous lineage**
- **Continuous lineage with a major configuration event**
- **Uncertain continuity**
- **Lineage terminated**
- **New lineage established**

All decisions and their rationales will be preserved in the Service Registry.

## 3.8 Configuration Events

Material changes within a continuing lineage will be recorded as **Configuration Events**.

Examples include:

- default model replacement;
- major retrieval-system change;
- introduction or removal of browsing;
- substantial safety-policy revision;
- major interface redesign;
- change in default personalization;
- change in regional availability; and
- change in account-tier functionality.

A Configuration Event does not automatically invalidate the panel.

Such events are among the principal phenomena that the Live Line is intended to capture.

Where the date of a change is uncertain, MIBO will record:

- the first wave in which the change was observed;
- the last wave in which the previous state was observed; and
- the source and confidence level of any external update information.

## 3.9 Nonresponse and Temporary Unavailability

Failure to obtain a valid output in a survey wave shall initially be treated as nonresponse rather than attrition.

Nonresponse categories include:

- refusal;
- service error;
- timeout;
- rate limit;
- authentication failure;
- regional access failure;
- interface failure;
- unusable output; and
- protocol execution failure.

Retries shall follow the preregistered retry rule. Failed attempts shall not be deleted from the operational record.

Temporary unavailability does not terminate a lineage. The Service Lineage ID remains active, and the relevant wave is recorded as missing or incomplete.

## 3.10 Panel Attrition

A service lineage will be classified as attrited when:

- the provider permanently discontinues the service;
- public access in the registered observation region is permanently withdrawn;
- the service ceases to satisfy the Core Observatory eligibility criteria; or
- continued observation is no longer legally, ethically, or technically defensible.

Attrition shall be reported as a substantive panel event.

Data collected before attrition will remain part of the longitudinal record. Missing post-attrition waves shall not be imputed as if the service had continued.

A temporarily unavailable lineage may resume under the same Service Lineage ID when continuity remains defensible.

## 3.11 Refreshment Samples

Newly important generative-AI services may emerge during the observation year.

Routine additions to the confirmatory Core panel will not be made during the first registered annual cycle.

A new service may be observed as a **Supplementary Refreshment Sample**, but:

- it will receive a new Service Lineage ID;
- its observation start date will be explicit;
- it will not be treated as if it had participated in earlier waves;
- it will not replace an attrited lineage retrospectively; and
- it will not enter the primary confirmatory panel analyses unless allowed by the preregistered analysis plan.

Formal admission to the Core sentinel panel will ordinarily occur during the annual panel review.

## 3.12 Observation Mode

For each service lineage, the Core Observatory will register one primary public observation mode.

The registered mode will specify:

- interface;
- account tier;
- geographic access condition;
- locale;
- memory setting;
- personalization setting;
- browsing or retrieval condition;
- tool condition; and
- session-initiation procedure.

The primary Core analysis will not combine UI and API observations as if they were the same mode.

Additional modes may be studied separately, but they must receive distinct configuration identifiers and shall not be pooled without explicit justification.

## 3.13 Account and Personalization Standardization

Unless a survey item explicitly requires otherwise, Core observations will use:

- dedicated research accounts;
- no personal conversation history;
- disabled memory where technically possible;
- disabled personalization where technically possible;
- no user-specific custom instructions;
- a new conversation for each independent replication; and
- a documented account tier that remains constant during the registered cycle.

When a service does not permit complete standardization, the remaining conditions will be documented as part of the Deployed Answering Configuration.

## 3.14 Panel Integrity

The following practices are prohibited in the confirmatory Core panel:

- retroactively changing a Service Lineage ID to improve apparent continuity;
- replacing an attrited lineage while presenting the replacement as the same panel member;
- silently changing account tier or observation mode;
- excluding a wave because its results are inconvenient;
- redefining continuity after examining outcome patterns; and
- merging distinct service lineages without a documented review.

All panel changes must be prospectively documented or entered into the protocol-deviation record.

## 3.15 Annual Panel Review

At the end of the first observation year, MIBO will conduct an annual panel review.

The review may consider:

- retention of existing lineages;
- admission of refreshment samples;
- retirement of inactive lineages;
- revision of the selection criteria;
- availability of Frozen Lines;
- changes to the standard observation mode; and
- implications for the next registered panel cycle.

Any revised panel will constitute a new registered panel version.

The first-year dataset will remain permanently associated with **MIBO Sentinel Panel v1.0**.


---

# 4. Fixed Query Instrument and Synchronized Survey Waves

## 4.1 Purpose of the Fixed Query Instrument

MIBO Core Observatory v1.0 will use a version-controlled fixed query instrument to measure change within the same service lineages across time.

The instrument is intended to ensure that differences between survey waves are not produced by unrecorded changes in question wording, presentation order, language form, or administration procedure.

The instrument will remain unchanged throughout the first registered annual cycle, except where continued use would be legally, ethically, or technically indefensible.

## 4.2 Instrument Structure

The fixed instrument will consist of:

- **12 conceptual survey items**;
- a Japanese form and an English form for each item;
- **24 administered query forms** in total; and
- **4 preregistered Anchor Items** selected from the 12 conceptual items.

Japanese and English forms are treated as two language forms of the same conceptual item, not as unrelated survey items.

Each conceptual item will receive a permanent **Item ID**. Each language form will receive a corresponding **Query Form ID**.

Example:

```text
Conceptual Item ID: MIBO-I03
Japanese Form ID:   MIBO-I03-JA
English Form ID:    MIBO-I03-EN
```

## 4.3 Information-Behavior Domains

The 12 conceptual items will cover six core domains of public generative-AI information behavior:

1. **Selection and prioritization**
2. **Citation and attribution**
3. **Recommendation**
4. **Synthesis and explanation**
5. **Uncertainty and refusal**
6. **Correction and updating**

Each domain will ordinarily be represented by two conceptual items.

The instrument is not intended to measure every possible generative-AI behavior. It provides a small, stable sentinel instrument suitable for repeated longitudinal administration.

## 4.4 Item Design Requirements

Each item must satisfy the following requirements before inclusion:

1. It elicits an observable information behavior relevant to one of the six domains.
2. It can be administered repeatedly without requiring a continuing conversation.
3. Its wording is sufficiently stable for longitudinal use.
4. Its expected output can be coded using a predefined scheme.
5. It does not require disclosure of sensitive personal information.
6. It does not depend on privileged or private data.
7. It can be administered under standardized session conditions.
8. It has a clear rationale for inclusion in the sentinel panel.
9. Its Japanese and English forms can be made functionally comparable.
10. It does not unnecessarily increase legal, ethical, or operational risk.

Items will not be selected merely because they produce striking or controversial outputs.

## 4.5 Fixed and Time-Sensitive Items

The instrument may include both:

- **stable-context items**, for which the underlying information environment is expected to change relatively slowly; and
- **time-sensitive items**, for which current information or recent developments may affect the response.

This distinction will be registered in advance.

Stable-context items help estimate changes associated with the service or deployment itself. Time-sensitive items help observe how the same service lineage interacts with a changing accessible information environment.

Time-sensitive items must be worded so that their reference period is explicit and consistently interpretable across survey waves.

## 4.6 Japanese and English Forms

Japanese and English forms will be developed through functional-equivalence review rather than literal translation alone.

The review will consider:

- requested task;
- information scope;
- degree of specificity;
- presuppositions;
- politeness and instruction strength;
- expected answer format;
- cultural or institutional references; and
- likely ambiguity.

A **Language Equivalence Record** will document:

- the original form;
- the translated form;
- translation decisions;
- known non-equivalences;
- reviewers;
- date of approval; and
- version number.

Language differences are substantive variables in MIBO. The project does not assume that Japanese and English forms will produce identical distributions.

## 4.7 Anchor Items

Four of the 12 conceptual items will be designated as Anchor Items.

Anchor Items will be used for:

- multisite mirror observation;
- adjacent-window calibration;
- generalizability-theory analysis;
- instrument continuity checks; and
- selected international comparisons.

Anchor Items should collectively represent more than one information-behavior domain and should be:

- feasible across all registered sites;
- minimally dependent on local institutional knowledge;
- suitable for repeated administration;
- codable with high reliability; and
- sufficiently sensitive to detect meaningful variation.

Anchor status will remain fixed during the first annual cycle.

## 4.8 Instrument Version Control

The first confirmatory instrument will be registered as:

> **MIBO Fixed Query Instrument v1.0**

The registered package will include:

- conceptual Item IDs;
- Japanese and English Query Form IDs;
- exact wording;
- presentation instructions;
- expected response format, where applicable;
- coding variables;
- language-equivalence records;
- item rationale;
- item classification;
- Anchor Item status; and
- cryptographic file hashes.

The instrument will be archived in a time-stamped repository before the first confirmatory wave.

## 4.9 Instrument Freeze

After registration, the wording of the fixed query forms shall not be changed during the first annual cycle merely to:

- improve response quality;
- reduce undesirable findings;
- adapt to a particular service;
- increase statistical significance;
- respond to an unexpected output; or
- align later waves with a newly preferred interpretation.

Minor formatting differences required by a service interface may be permitted only when they do not change the substantive query.

Any permitted formatting adaptation must be documented.

## 4.10 Instrument Amendments

An item may be suspended or amended during the registered cycle only when:

- continued administration creates a legal or ethical problem;
- the item becomes technically impossible to administer;
- the item no longer has a stable or interpretable meaning;
- a service change causes systematic protocol failure; or
- a serious wording defect invalidates the intended measurement.

An amendment requires:

1. a written justification;
2. a dated protocol-amendment record;
3. preservation of the original wording;
4. a new Query Form ID and version;
5. a statement of which analyses remain comparable; and
6. exclusion from the original confirmatory series where comparability is lost.

An amended form shall not be retrospectively treated as identical to the original form.

## 4.11 Survey-Wave Structure

MIBO Core Observatory v1.0 will conduct:

- **one survey wave per month**;
- for **12 consecutive months**;
- beginning on or after 1 September 2026.

Each survey wave will receive a permanent **Wave ID**.

Example:

```text
MIBO-W01
MIBO-W02
...
MIBO-W12
```

The planned calendar dates and field windows will be registered before the first wave.

## 4.12 Synchronized Field Window

Each monthly survey wave will ordinarily be completed within a common **48-hour field window**.

The purpose of synchronization is to reduce the risk that service comparisons reflect substantially different external information conditions.

All registered service lineages and language forms should be observed within the same field window wherever technically possible.

The field window will be defined using:

- Coordinated Universal Time;
- Japan Standard Time; and
- local time at each mirror site.

The exact start and end times will be recorded in the **Operations Schedule and Manual v1.0**.

## 4.13 Macro-Time and Micro-Time

MIBO distinguishes two forms of time.

### Macro-time

Macro-time refers to the sequence of monthly survey waves.

Differences across macro-waves are substantive longitudinal changes and are not treated merely as measurement error.

### Micro-time

Micro-time refers to adjacent observation windows within the same calibration wave.

Micro-time is used to evaluate whether a finding can be recovered over a short interval under otherwise comparable conditions.

This distinction prevents genuine longitudinal change from being absorbed into the error term of the re-observability analysis.

## 4.14 Administration Order

To reduce systematic order effects:

- service order will be randomized or counterbalanced;
- query order will be randomized within predefined constraints;
- Japanese and English forms will be administered according to a registered balancing scheme; and
- the order of Frozen and Live observations will be balanced where technically feasible.

The exact administration order will be generated before each wave and retained as part of the operational record.

Order will not be changed after outcomes are inspected.

## 4.15 Session Standardization

Unless an item explicitly requires otherwise, every query administration will use:

- a new conversation or session;
- no preceding prompts;
- no follow-up clarification;
- no user correction;
- no manual steering after submission;
- standardized memory and personalization conditions;
- the registered account and interface; and
- the exact registered query form.

A service-generated request for clarification will be recorded as an observable outcome unless a preregistered response rule applies.

Researchers shall not modify a query interactively to obtain a more complete or desirable answer.

## 4.16 Response Capture

For every administration, MIBO will preserve or record, as legally and technically permitted:

- exact query text;
- submitted language form;
- complete generated response;
- response timestamp;
- cited links or displayed sources;
- refusal or error messages;
- displayed model or mode;
- relevant interface indicators;
- retrieval or browsing indicators;
- session identifier;
- replication number;
- site identifier;
- execution order; and
- raw-output hash.

Where raw response redistribution is restricted, the response will be retained in the secure layer and represented publicly through permitted derived variables and cryptographic hashes.

## 4.17 Valid and Invalid Administrations

A replication will ordinarily be considered valid when:

- the exact query was successfully submitted;
- the registered observation conditions were met;
- the service returned a complete observable outcome;
- the response was captured without researcher alteration; and
- the required metadata were recorded.

A replication may be classified as invalid when:

- the wrong query form was submitted;
- prior conversation history affected the session;
- the wrong account or mode was used;
- the response was not captured;
- a technical interruption made the output incomplete; or
- a material protocol deviation occurred.

Refusals and substantive nonanswers are valid information-behavior outcomes and shall not be classified as invalid merely because they do not answer the question.

## 4.18 Retry Rule

Retries are permitted only under predefined operational conditions, such as:

- service error;
- timeout;
- interrupted output;
- authentication failure; or
- confirmed submission failure.

The original failed attempt will remain in the operational log.

A valid refusal shall not be retried simply to obtain an answer.

The maximum number of retries and the delay between retries will be specified in the **Operations Schedule and Manual v1.0** before the first wave.

## 4.19 Wave Completion

A survey wave will be classified as:

- **complete**;
- **complete with documented missing cells**;
- **partially completed**; or
- **not completed**.

A wave will not be excluded solely because it contains unusual findings, service failures, refusals, or major configuration events.

Missing observations will be reported at the cell level.

## 4.20 Wave Deviations

Any deviation from the registered wave procedure will be recorded in a **Wave Deviation Log**.

The record will include:

- Wave ID;
- affected Service Lineage ID;
- affected query forms;
- type of deviation;
- time of occurrence;
- cause;
- corrective action;
- impact on comparability; and
- inclusion or exclusion decision.

Deviations shall not be concealed through retrospective replacement of data.

## 4.21 Pilot Separation

Queries tested before 1 September 2026 may inform the design of the fixed instrument.

However, outputs generated during item development, translation review, dry runs, coder training, or operational testing will be classified as Pilot data.

Pilot outputs will not be included in the primary confirmatory analysis unless specifically allowed by the preregistered Statistical Analysis Plan.

The final query wording must be frozen only after Pilot testing is complete.

## 4.22 Annual Instrument Review

After completion of the first 12-wave cycle, the instrument will undergo a formal review.

The review may consider:

- item completion;
- coding reliability;
- within-cell variation;
- longitudinal sensitivity;
- language equivalence;
- burden and feasibility;
- ethical or legal concerns;
- performance of Anchor Items; and
- need for new information-behavior domains.

Any revised instrument will receive a new version number.

Data collected using v1.0 will remain permanently identified as the:

> **MIBO Fixed Query Instrument v1.0 panel series**

The first-year instrument will not be retrospectively rewritten to conform to later versions.

---

# 5. Parallel Frozen and Live Lines

## 5.1 Purpose

The Frozen–Live architecture is intended to separate ecological longitudinal observation from controlled update comparison.

MIBO follows the public service encountered by users while also maintaining a narrower paired-harness module capable of supporting more defensible update contrasts.

The design does not assume that every public service can support a valid Frozen Reference.

---

## 5.2 Three Linked Observation Conditions

### 5.2.1 Ecological Live Line

The **Ecological Live Line** follows the current public web-interface configuration of a registered service lineage across successive survey waves.

It is allowed to change through ordinary provider operations, including:

- model replacement;
- retrieval-system updates;
- changes to tools;
- safety-policy revisions;
- routing changes;
- interface modifications; and
- changes to default service behavior.

These changes are not protocol deviations. They are part of the longitudinal state of the panel member.

The Ecological Live Line is the primary observation for service-lineage panel inference.

### 5.2.2 Paired Live Reference

The **Paired Live Reference** uses the current eligible API model selected under a preregistered provider-specific rule and executed under the fixed MIBO research harness.

It is linked to the same persistent Service Lineage ID but is not treated as identical to the public web interface.

### 5.2.3 Frozen Reference

The **Frozen Reference** uses a baseline version-identified API model executed under the same MIBO research harness as the Paired Live Reference.

A valid Frozen Reference requires:

- a persistent and verifiable model identifier;
- a stable execution harness;
- documented system instructions;
- matched sampling and reasoning settings where controllable;
- matched tools and retrieval conditions;
- consistent account and access conditions; and
- sufficient expected availability during the registered cycle.

The Paired Live Reference and Frozen Reference constitute the confirmatory Frozen–Live comparison.

---

## 5.3 First-Year Environment-Closed Module

The first-year primary paired module is environment-closed:

- retrieval is disabled;
- tools are disabled;
- no uploaded files or private data are supplied; and
- both conditions use the same registered system instruction and harness.

This provides the clearest available comparison between current and frozen model conditions.

Temporal change in an environment-closed Frozen Reference shall be interpreted as residual change under a nominally fixed configuration, not as external information-environment change.

---

## 5.4 Conditional Environment-Open Module

An environment-open Frozen module may be included only when:

- a common information-access layer is matched across the Paired Live and Frozen conditions;
- the layer and its update process are documented;
- the module is preregistered before Wave 1; and
- its estimands and analysis are defined in advance.

Only such a matched environment-open design may support an accessible-information-environment contrast.

If it is not preregistered, H4 is not assessed in MIBO 1.0.

---

## 5.5 Paired-Harness Eligibility

A service lineage is eligible for primary Frozen–Live comparison only when the Paired Live and Frozen References can be made sufficiently comparable with respect to:

- query wording;
- query language;
- observation site and window;
- API endpoint family;
- system instructions;
- retrieval and tools;
- reasoning, effort, and decoding controls;
- account and geographic conditions;
- execution code;
- software environment; and
- response-capture procedure.

Remaining differences must be recorded prospectively in the **Frozen–Live Comparability Registry v1.0**.

A public web interface and an API model do not constitute an eligible Class A or Class B pair merely because they belong to the same provider.

---

## 5.6 Comparability Classification

Every paired-harness candidate will receive one classification before confirmatory data collection.

### Class A: Model-comparable pair

Model state is the sole material difference under the common harness.

Permitted interpretation:

> **Model-update contrast**

### Class B: Deployment-comparable pair

The common harness is retained, but at least one additional deployment component cannot be perfectly matched or verified.

Permitted interpretation:

> **Deployment-update contrast**

The unresolved component must be named.

### Class C: Descriptive reference pair

Material differences prevent an update-effect interpretation.

Permitted interpretation:

> **Descriptive cross-condition difference**

Class C observations do not enter the primary Frozen–Live decomposition.

---

## 5.7 Core Contrasts

Let:

- \(Y^{L,\mathrm{API}}_{t}\) denote the outcome distribution for the Paired Live Reference at wave \(t\); and
- \(Y^{F,\mathrm{API}}_{t}\) denote the outcome distribution for the Frozen Reference.

### 5.7.1 Within-wave paired contrast

\[
\Delta_{\mathrm{FL},t}
=
Y^{L,\mathrm{API}}_{t}
-
Y^{F,\mathrm{API}}_{t}
\]

For a Class A pair, this may be interpreted as a model-update contrast.

For a Class B pair, it is interpreted as a deployment-update contrast.

### 5.7.2 Frozen-Reference longitudinal contrast

\[
\Delta_{\mathrm{F},t}
=
Y^{F,\mathrm{API}}_{t}
-
Y^{F,\mathrm{API}}_{0}
\]

For the first-year environment-closed module, this is residual change under the nominally fixed configuration.

It is not interpreted as external information-environment change.

### 5.7.3 Ecological Live longitudinal contrast

\[
\Delta_{\mathrm{UI},t}
=
Y^{L,\mathrm{UI}}_{t}
-
Y^{L,\mathrm{UI}}_{0}
\]

This represents total observed change in the public service experienced by users.

---

## 5.8 Baseline Adjustment

Where the paired conditions are not equivalent at baseline, the primary update estimate will use:

\[
\Delta_{\mathrm{update},t}
=
\left(
Y^{L,\mathrm{API}}_{t}
-
Y^{F,\mathrm{API}}_{t}
\right)
-
\left(
Y^{L,\mathrm{API}}_{0}
-
Y^{F,\mathrm{API}}_{0}
\right)
\]

The unadjusted within-wave paired contrast will also be reported.

---

## 5.9 Interpretation

The paired API contrast and the ecological UI trajectory answer different questions.

- The **Ecological Live Line** asks how the public service lineage changed.
- The **paired API comparison** asks how the registered current and frozen reference conditions diverged under a common harness.

Agreement between the two may strengthen a substantive interpretation, but it does not make the UI and API the same observational mode.

MIBO will not identify a pure model effect when a material non-model difference remains uncontrolled.

---

## 5.10 Paired Administration

Paired API observations will be:

- collected within the same registered wave;
- executed at the same site and through the same harness;
- administered using the same language form;
- interleaved in a preregistered randomized block; and
- completed within the registered maximum block duration.

The public UI is observed separately under the ecological panel procedure.

---

## 5.11 Replication Structure

Each eligible paired cell will contain:

- 10 independent Paired Live Reference replications; and
- 10 independent Frozen Reference replications.

The comparison concerns the two distributions.

Replication numbers do not create arbitrary one-to-one output pairs.

---

## 5.12 Integrity Checks

Before every wave, the paired module will verify:

- exact model identifiers;
- model-selection rule;
- execution environment;
- system instructions;
- retrieval and tool state;
- reasoning and decoding settings;
- software dependencies;
- API availability; and
- known deprecation risks.

Configuration and code hashes will be preserved.

---

## 5.13 Frozen Contamination

A Frozen Reference is contaminated when a component intended to remain fixed changes without registration or cannot be verified.

Examples include:

- model alias reassignment;
- provider-side replacement under the same identifier;
- unrecorded system-instruction change;
- changed tool or retrieval behavior;
- changed default settings; or
- execution through a different harness.

Affected observations remain in the integrity record but may be excluded from the primary paired analysis or treated as the start of a new segment.

---

## 5.14 Frozen Attrition

Frozen attrition occurs when:

- the baseline model is withdrawn;
- the API or required endpoint is discontinued;
- continued access becomes prohibited;
- identity or integrity can no longer be verified; or
- comparability is permanently lost.

The Ecological Live Line continues.

A replacement baseline receives a new Frozen Mode ID and is not presented as uninterrupted continuation.

---

## 5.15 Configuration Events in the Ecological Live Line

When a major public-service configuration event is detected, MIBO records:

- the last observation under the prior state;
- the first observation under the new state;
- the known or estimated event date;
- the affected components;
- the evidence and confidence of classification; and
- any supplementary event observation.

The monthly panel remains primary.

---

## 5.16 Permitted Claims

| Condition | Permitted interpretation |
|---|---|
| Ecological Live UI across waves | Total public-service lineage change |
| Class A paired API comparison | Model-update contrast |
| Class B paired API comparison | Deployment-update contrast |
| Class C or UI–API comparison | Descriptive cross-condition difference |
| Matched environment-open Frozen module | Accessible-information-environment contrast |
| Environment-closed Frozen across waves | Residual change under nominally fixed configuration |

No stronger interpretation will be used solely because a result is large or striking.

---

## 5.17 Minimum First-Year Requirement

MIBO Core Observatory v1.0 will maintain Ecological Live Lines for all four registered sentinel panel members.

The paired module will aim to admit and retain at least two service lineages.

Failure to retain two valid Frozen References restricts the L2 decomposition but does not invalidate the ecological panel survey.

---

## 5.18 Scientific Role

The Ecological Live Line preserves real-world relevance.

The Paired Live and Frozen References provide a controlled comparison.

Together with within-cell replication, they allow MIBO to ask:

- Did the public response distribution change?
- Did a matched current reference diverge from the frozen baseline?
- Is the contrast a model-update, deployment-update, or descriptive difference?
- Is the difference sustained?
- Was it measured under a re-observable design?

The architecture therefore separates panel observation from controlled decomposition without falsely equating a commercial interface with an API snapshot.

# 6. Within-Cell Replication and Distributional Observation

## 6.1 Purpose

Public generative-AI services may produce different outputs when the same query is administered repeatedly under nominally identical conditions.

A single output therefore cannot reliably distinguish:

- ordinary stochastic variation;
- an infrequent but admissible response;
- a temporary disturbance;
- a distributional shift; and
- sustained longitudinal change.

MIBO addresses this problem by obtaining ten independent replications within each registered observational cell.

The purpose of replication is not to identify one “true answer.” It is to estimate the conditional distribution of observable information behavior under documented conditions.

## 6.2 Observational Cell

An observational cell is defined by the combination of:

- Service Lineage ID;
- Line ID, where applicable;
- Wave ID;
- Conceptual Item ID;
- Query Form ID;
- language;
- observation site;
- designated observation window; and
- registered observation mode.

For each required cell, MIBO Core Observatory v1.0 will target:

\[
k=10
\]

valid independent replications.

A change in any defining cell condition creates a different observational cell.

## 6.3 Meaning of Independence

Replications are operationally independent when each output is generated through a separately initiated session without conversational dependence on another replication.

Independence requires, as far as technically possible:

- a new conversation or session;
- no prior prompts;
- no copied response history;
- no researcher follow-up;
- no shared conversational context;
- standardized memory and personalization settings; and
- separate submission of the registered query form.

The term *independent* refers to the administration procedure. It does not imply that the underlying service outputs are statistically independent in every respect, because replications may share the same provider infrastructure, retrieval index, model state, and observation period.

Any known source of dependence will be documented.

## 6.4 Standard Replication Procedure

Each replication will ordinarily follow the same sequence:

1. Confirm the registered service, account, mode, and configuration.
2. Initiate a new session.
3. Confirm that no prior conversational context is present.
4. Submit the exact registered query form.
5. Allow the service to complete its response without intervention.
6. Capture the complete observable output.
7. Record the required metadata.
8. Assign the replication number.
9. Close or archive the session.
10. Begin the next replication through a newly initiated session.

Researchers shall not edit, correct, or steer the service between submission and response capture.

## 6.5 Replication Numbering

Each replication will receive a permanent Replication ID.

Example:

```text
MIBO-W03-SL001-I04-JA-L-S01-R01
MIBO-W03-SL001-I04-JA-L-S01-R02
...
MIBO-W03-SL001-I04-JA-L-S01-R10
```

The identifier will preserve the relationship among:

- survey wave;
- service lineage;
- item;
- language;
- Line;
- site; and
- replication number.

Replication IDs shall not be reassigned after data inspection.

## 6.6 Replication Order

Replication order may affect outputs through:

- short-term service load;
- retrieval-index changes;
- rate limiting;
- hidden session state;
- provider-side batching; or
- changes in the external information environment.

To reduce systematic order bias:

- query order will be randomized or counterbalanced;
- service order will be randomized or counterbalanced;
- Frozen-first and Live-first order will be balanced where applicable; and
- the ten replications shall not always be administered in an identical uninterrupted sequence.

The operational schedule will remain simple enough to complete the registered field window reliably.

## 6.7 Observation Window

The ten replications for a cell should be completed within the same designated observation window.

The window must be short enough to support interpretation as a common within-wave condition, but long enough to avoid excessive rate limiting or operational failure.

The maximum duration of the standard replication window will be specified in the Operations Schedule and Manual before the first confirmatory wave.

When a cell cannot be completed within the registered window:

- completed replications will be retained;
- the missing replications will be recorded;
- the reason will be documented; and
- the cell will be flagged for timing deviation.

Replications will not be silently moved to a later date and presented as if they were obtained in the original window.

## 6.8 Valid Replication

A replication is valid when:

- the correct query form was submitted;
- the correct service and observation mode were used;
- the registered session conditions were met;
- an observable service outcome was obtained;
- the output was captured without researcher alteration; and
- the required metadata were recorded.

Valid outcomes include:

- a substantive answer;
- a refusal;
- an expression of uncertainty;
- a request for clarification;
- a redirection;
- a safety response; and
- a completed response that omits the requested information.

A response is not invalid merely because it is incorrect, incomplete, unusual, or unhelpful.

## 6.9 Invalid Replication

A replication may be classified as invalid when:

- the wrong query was submitted;
- the wrong language form was used;
- prior conversation history was present;
- memory or personalization conditions differed materially;
- the wrong account or service mode was used;
- the output was interrupted and not recoverable;
- the response was not preserved;
- the service returned no observable outcome because of a technical failure; or
- a material protocol deviation occurred.

The invalid attempt will remain in the operational log.

It will not be overwritten or renumbered as though it had never occurred.

## 6.10 Retry Procedure

Retries are permitted only for operational failures, including:

- confirmed submission failure;
- service error;
- timeout;
- authentication failure;
- interrupted generation;
- temporary access failure; or
- corrupted response capture.

A substantive refusal, nonanswer, or clarification request is a valid output and shall not be retried merely to obtain a more desirable answer.

The retry record will include:

- original attempt ID;
- reason for retry;
- time interval before retry;
- number of retries;
- final disposition; and
- whether a valid replacement replication was obtained.

The maximum number of retries per intended replication will be preregistered.

## 6.11 No Outcome-Based Replacement

An output shall not be replaced because it:

- differs from the other nine replications;
- appears implausible;
- contains an error;
- lacks citations;
- produces an inconvenient finding;
- is unusually short or long; or
- weakens a hypothesized pattern.

Rare outputs are part of the conditional response distribution.

They may be flagged for coding review, but they shall not be removed without a predefined validity reason.

## 6.12 Treatment of Incomplete Cells

A cell may contain fewer than ten valid replications because of service failure, access loss, rate limits, or other documented conditions.

Incomplete cells will be classified by the number of valid replications obtained.

The Statistical Analysis Plan will define:

- the minimum number required for primary distributional estimation;
- whether partial cells enter particular analyses;
- how uncertainty is represented;
- whether sensitivity analyses are required; and
- how incomplete Frozen–Live pairs are treated.

MIBO will not generate artificial outputs or duplicate existing responses to complete a cell.

## 6.13 Distributional Measurement

The ten replications will be used to estimate item-specific response distributions.

Depending on the registered item and coding scheme, outcomes may include:

- probability that an entity appears;
- probability that a source is cited;
- probability of refusal;
- probability of expressing uncertainty;
- distribution of recommendation ranks;
- frequency of particular source domains;
- number of claims;
- number of citations;
- response-length distribution;
- semantic similarity among outputs;
- concentration or diversity of selected entities;
- agreement in substantive conclusions; and
- frequency of minority response patterns.

Not every measure will apply to every item.

The relevant measures will be specified before confirmatory analysis.

## 6.14 Point Estimates and Uncertainty

For binary outcomes, a cell may be summarized through an observed proportion:

\[
\hat{p}=\frac{1}{10}\sum_{r=1}^{10}y_r
\]

where \(y_r\) is the coded result for replication \(r\).

For ranked, categorical, count, or continuous outcomes, the appropriate registered distributional summary will be used.

Because \(k=10\) remains a small sample from the service’s conditional output distribution, estimates will be reported with appropriate uncertainty. Observed proportions such as \(1/10\) or \(9/10\) shall not be treated as exact underlying probabilities.

## 6.15 Drift Versus Within-Cell Variation

MIBO will not classify an output difference as drift solely because an answer observed in one wave does not appear in another.

The analysis will compare:

- variation among replications within Wave \(t\);
- variation among replications within Wave \(t+1\); and
- the difference between the two wave-level distributions.

A candidate distributional shift must exceed the registered level of ordinary within-cell variation.

A sustained longitudinal change must additionally satisfy the preregistered persistence or confirmation rule.

The exact statistical method may vary by outcome type and will be specified in the Statistical Analysis Plan.

## 6.16 Role in Frozen–Live Comparisons

For each eligible paired cell, MIBO will obtain separate distributions for:

- the Live Line; and
- the Frozen Line.

Frozen–Live interpretation will therefore compare two distributions rather than two individual responses.

The analysis may examine:

- differences in appearance probability;
- differences in refusal probability;
- differences in rank distributions;
- differences in source selection;
- differences in dispersion;
- differences in semantic clustering; and
- differences in the probability of predefined coded outcomes.

A single striking Live response and a single contrasting Frozen response shall not be treated as sufficient evidence of a Line effect.

## 6.17 Role in Re-observability Analysis

Within-cell replication provides the session-level component of the re-observability design.

For designated Anchor Items, replicated observations will contribute to the estimation of variance associated with:

- independent sessions;
- observation sites;
- adjacent within-wave windows; and
- their relevant interactions.

The ten-replication standard provides the initial basis for determining how much of the observed variation is attributable to session-level output instability.

Subsequent decision studies may estimate the dependability expected under alternative designs, such as:

- \(k=5\);
- \(k=10\);
- \(k=15\); or
- \(k=20\).

## 6.18 Rationale for \(k=10\)

The value \(k=10\) is adopted as the standard for MIBO Core Observatory v1.0 because it:

- makes distributional variation directly observable;
- remains operationally feasible across repeated waves;
- permits detection of recurring and minority response patterns;
- supports estimation of session-level variance;
- avoids reliance on a single output; and
- provides data for later decision studies.

MIBO does not claim that ten is universally sufficient or optimal.

The first-year data will be used to determine whether particular items or outcomes require fewer or more replications in future protocol versions.

## 6.19 Computational Deduplication

Two outputs that are textually identical remain separate valid replications when they were generated through separate valid sessions.

They shall not be collapsed into one observation.

Textual duplication is itself an observable property of the response distribution and may indicate high output concentration or deterministic behavior.

## 6.20 Human and AI-Assisted Coding

MIBO may use human coding, deterministic computational extraction, or validated generative-AI-assisted coding, depending on the nature of the registered outcome.

Deterministic extraction should be preferred when the target variable can be identified reliably through reproducible rules, such as:

- response length;
- number of citations;
- presence of a URL;
- named-entity extraction;
- response status; or
- exact textual duplication.

Generative-AI systems may be used for semantic coding when interpretation is required. Confirmatory AI-assisted coding shall follow the validation, audit, disclosure, and human-responsibility requirements specified in Section 9.35.

Where feasible, coders will not be shown:

- the service identity;
- Frozen or Live status;
- survey wave; or
- hypothesized direction of change

when this information is not required for valid coding.

Coding order may be randomized to reduce expectation and temporal effects.

## 6.21 Replication Integrity Audit

A sample of replication records will be audited for:

- session independence;
- exact query use;
- correct account and mode;
- response completeness;
- metadata completeness;
- retry compliance;
- timestamp validity; and
- correspondence between raw output and coded data.

Audit findings will be documented.

Material replication failures may lead to:

- exclusion of an affected replication;
- flagging of an affected cell;
- reclassification of a wave;
- protocol correction; or
- sensitivity analysis.

## 6.22 Prohibited Practices

The following practices are prohibited:

- selecting the most representative-looking output from the ten replications;
- reporting only the modal answer without the distribution;
- deleting outlying responses without a validity rule;
- continuing replication until a preferred result appears;
- stopping early after apparent convergence;
- adding extra replications only to cells with inconvenient findings;
- combining dependent responses from the same conversation as independent replications; and
- replacing valid refusals with retried answers.

Any additional replication conducted outside the registered design must be identified as supplementary.

## 6.23 Completion Standard

The standard completion target for each required cell is:

> **10 valid, independently administered replications within the designated observation window.**

A first-year wave may still be scientifically usable when some cells are incomplete, provided that:

- all missingness is documented;
- operational failures are preserved;
- inclusion rules are applied consistently; and
- uncertainty is not concealed.

The scientific value of the replication design lies not in obtaining ten polished answers, but in observing the actual distribution of behavior produced under the registered conditions.


---

# 7. Generalizability-Theoretic Assessment of Re-observability

## 7.1 Purpose

MIBO does not define reproducibility as the recovery of identical wording from a stochastic generative-AI service.

Its methodological objective is to determine whether defined information-behavior results can be recovered with acceptable dependability when the observation is repeated:

1. in independent sessions;
2. at independent observation sites; and
3. within an adjacent observation window.

MIBO refers to this property as **re-observability**.

Generalizability theory will be used to separate variation attributable to these observational conditions and to evaluate whether a measurement design is sufficiently dependable to support longitudinal claims.

## 7.2 Formal Definition

> **Re-observability is the dependability with which defined machine-information-behavior results can be recovered across admissible independent sessions, observation sites, and adjacent within-wave time windows.**

Re-observability is a property of a preregistered measurement design for a defined outcome.

MIBO may therefore state that:

> “The registered citation-selection outcome was measured under a re-observable design.”

MIBO will not describe an entire service or model as re-observable on the basis of a single item or wave.

## 7.3 Exact Reproduction Is Not Required

Two valid outputs may differ in wording while expressing the same coded information behavior.

Re-observability may therefore be evaluated using preregistered outcomes such as:

- appearance of a specified entity;
- citation of an official source;
- refusal;
- expression of uncertainty;
- recommendation category;
- rank position;
- source-domain type;
- coded substantive conclusion; or
- a defined distributional score.

Exact textual identity may be reported as an outcome, but it is not the general criterion for re-observability.

## 7.4 Calibration Module

The G-theory analysis will be conducted through a limited **Re-observability Calibration Module**, rather than by imposing the full multisite design on every Core item and every survey wave.

The first-year calibration design will include:

- 4 preregistered Anchor Items;
- the 4 registered Live service lineages;
- Japan and at least 2 independent international mirror sites;
- 2 adjacent observation windows within each calibration wave;
- 10 independent replications per cell; and
- 4 designated calibration waves during the first annual cycle.

The primary international calibration will use the registered English forms of the Anchor Items as the common **Bridge Instrument**.

Japanese and other local-language forms may be studied separately but are not required for the primary cross-site G-study.

Frozen Lines will be included in a secondary calibration analysis where technically valid and operationally feasible.

At the Japan site, Anchor Item × Live Line × English observations collected in Window A during a calibration wave will serve simultaneously as the corresponding Core observations. They will not be collected twice under nominally identical conditions. Window B will be the additional calibration observation.

## 7.5 Calibration-Wave Schedule

Four of the 12 monthly survey waves will be designated as calibration waves before confirmatory observation begins.

The intended spacing is approximately quarterly.

For example:

```text
Calibration 1: Wave 1
Calibration 2: Wave 4
Calibration 3: Wave 7
Calibration 4: Wave 10
```

The final Wave IDs will be specified in the preregistration.

Each calibration wave will contain:

- **Window A**; and
- **Window B**, conducted after a preregistered adjacent interval.

The interval should be long enough to constitute a separate observation opportunity but short enough to remain within the same macro-wave information environment. The exact interval, ordinarily between 12 and 24 hours, will be fixed in the Operations Schedule and Manual.

## 7.6 Objects of Measurement

The objects of measurement are defined:

> **Service Lineage × Anchor Item × Calibration Wave**

combinations.

With four service lineages, four Anchor Items, and four calibration waves, the initial calibration design may contain up to 64 objects of measurement.

For the primary G-study:

- Line is fixed as Live;
- language is fixed as the English Bridge Instrument; and
- calibration wave is part of the object definition.

The observation sites, adjacent windows, and independent sessions are the principal generalization facets.

Service differences, item differences, Frozen–Live differences, language differences, and macro-wave changes will not be treated as undifferentiated error.

## 7.7 Generalization Facets

### 7.7.1 Session facet

The session facet captures variation among independent replications conducted under the same registered site, window, and service conditions.

It addresses the question:

> Would the result be recovered if the same site repeated the observation in new sessions?

### 7.7.2 Site facet

The site facet captures variation associated with independent observation locations operating the same Mirror Observatory Kit.

It addresses the question:

> Would the result be recovered by another qualified observation site?

### 7.7.3 Adjacent-window facet

The adjacent-window facet captures short-interval variation within the same macro-wave.

It addresses the question:

> Would the result be recovered if the observation were repeated in a nearby time window?

Macro-wave variation is not included in this facet. Monthly change is a substantive longitudinal outcome rather than ordinary measurement error.

## 7.8 Basic Observation Structure

For an object \(o\), site \(s\), adjacent window \(w\), and session replication \(r\), the observed result may be represented as:

\[
Y_{oswr}
\]

The G-study will estimate variance associated with:

- the object of measurement;
- site;
- adjacent window;
- session replication;
- relevant object-by-facet interactions; and
- residual variation.

Session replications are operationally nested within each Site × Window combination.

The exact variance-component model will depend on the outcome scale and will be specified in the Statistical Analysis Plan.

## 7.9 Outcome-Specific Models

For approximately continuous or ordinal outcomes, MIBO may use linear mixed-effects variance-component models.

For binary, categorical, or count outcomes, MIBO may use generalized mixed-effects models appropriate to the registered outcome.

The same model will not be imposed mechanically on every variable.

Each confirmatory re-observability analysis must specify:

- the outcome;
- its scale;
- the objects of measurement;
- the facets;
- the variance model;
- the coefficient;
- the decision rule; and
- the uncertainty interval.

## 7.10 G-study

The **Generalizability Study**, or G-study, will estimate how much observed variation is associated with:

- stable differences among the defined objects;
- independent sessions;
- observation sites;
- adjacent windows;
- interactions among these components; and
- residual error.

The G-study will answer questions such as:

- Is most variation attributable to differences among service–item–wave objects?
- Does the same outcome vary substantially across independent sessions?
- Are measurements dependent on the observation site?
- Does a short delay within the same wave materially alter the measurement?
- Which interactions create the largest source of instability?

The variance components will be reported even when the final re-observability threshold is not satisfied.

## 7.11 D-study

The **Decision Study**, or D-study, will estimate the dependability expected under alternative observation designs.

The first-year D-study will consider designs such as:

- fewer or more session replications;
- two, three, or additional sites;
- one or two adjacent windows; and
- alternative combinations of sites, windows, and replications.

This will allow MIBO to determine whether future protocol versions can:

- reduce unnecessary observation burden;
- identify outcomes that require more than 10 replications;
- determine the benefit of adding mirror sites; and
- distinguish efficient routine observation from intensive calibration.

The \(k=10\) standard will not be changed during the registered first-year cycle on the basis of interim D-study results.

## 7.12 Dependability Coefficient

Because MIBO is principally concerned with recovering the absolute status of a defined result rather than only preserving the relative ranking of services, the primary coefficient will be the **joint absolute dependability coefficient**, denoted by:

\[
\Phi_{\mathrm{joint}}
\]

In general form:

\[
\Phi
=
\frac{\sigma^2_{\text{object}}}
{\sigma^2_{\text{object}}+\sigma^2_{\text{absolute error}}}
\]

The absolute-error term will be calculated for the registered D-study design using the estimated variance components.

A relative generalizability coefficient may be reported as a secondary measure when the research question concerns ranking or relative differentiation among objects.

## 7.13 Directional Diagnostic Coefficients

MIBO may report three directional dependability coefficients as diagnostic measures.

### Session dependability

\[
\Phi_{\mathrm{session}}
\]

This coefficient evaluates recovery across independent sessions under fixed site and adjacent-window conditions.

### Site dependability

\[
\Phi_{\mathrm{site}}
\]

This coefficient evaluates recovery across admissible observation sites after accounting for the registered number of session replications and windows.

### Adjacent-window dependability

\[
\Phi_{\mathrm{window}}
\]

This coefficient evaluates recovery across nearby observation windows within the same macro-wave.

These directional coefficients identify where instability arises. They do not replace the joint coefficient as the principal certification indicator.

## 7.14 Operational Certification Rule

For MIBO Core Observatory v1.0, a measurement design for a preregistered outcome will be classified as **re-observable** when:

\[
\Phi_{\mathrm{joint}} \geq .80
\]

The coefficient estimate will be accompanied by an uncertainty interval.

Directional coefficients will be used to diagnose whether residual instability is primarily:

- session-dependent;
- site-dependent;
- adjacent-window-dependent; or
- distributed across multiple facets.

The final uncertainty criterion and any additional decision rules will be specified in the Statistical Analysis Plan before confirmatory analysis.

A design that fails the threshold will not be described as re-observable under the registered conditions.

Failure to satisfy the threshold is a substantive finding and shall not be treated as failed data collection.

## 7.15 Outcome Specification

An outcome must be specified before its measurement design can be assessed for re-observability.

Each outcome submitted for assessment must identify:

- Service Lineage IDs;
- Anchor Item IDs;
- calibration waves;
- Query Form ID;
- Line and language;
- coded variable;
- calculation rule;
- observation universe;
- coefficient design; and
- decision threshold.

A broad statement such as:

> “This service uses good sources”

is not sufficiently defined for re-observability assessment.

## 7.16 Site Eligibility

A site may contribute to the primary G-study when it:

1. is operated by an independent research group;
2. uses the registered MIBO Mirror Observatory Kit version;
3. uses the required service access mode and account tier;
4. administers the exact English Bridge Instrument;
5. follows the registered synchronization window;
6. completes the required replication procedure;
7. records all required metadata;
8. preserves failed attempts and deviations;
9. passes the dry-run quality check; and
10. maintains an identifiable local research lead.

Site participation does not require institutional similarity to the coordinating observatory in Japan.

The purpose is to test whether the protocol travels across independent locations.

## 7.17 Independence of Mirror Observation

Mirror-site data collection must be operationally independent.

The Japan coordinating observatory may provide:

- the protocol;
- software;
- training;
- technical clarification;
- quality-control standards; and
- preregistered schedules.

It shall not:

- select which valid outputs the mirror site retains;
- remove inconvenient site differences;
- instruct a site to repeat a valid result;
- modify a site’s coded outcome after inspecting the pooled result; or
- prevent a mirror site from reporting nonreplication.

Mirror sites must be able to report disagreement with the coordinating observatory.

## 7.18 Site Deviations

A protocol deviation at one site will not automatically invalidate data from all sites.

The affected observations will be evaluated according to:

- type of deviation;
- number of affected cells;
- likely influence on the outcome;
- whether the deviation was systematic;
- whether comparability remains defensible; and
- the preregistered inclusion rule.

All deviations will remain visible in the site record.

Analyses may be reported:

- with all eligible sites;
- excluding a materially noncompliant site; and
- as a sensitivity comparison.

## 7.19 Missing Calibration Data

Missing replications, windows, or site observations will not be replaced through duplicated outputs or undocumented late collection.

The Statistical Analysis Plan will specify:

- the minimum valid replications per cell;
- the minimum site completion requirement;
- treatment of incomplete windows;
- estimation under unbalanced data;
- sensitivity analyses; and
- conditions under which certification is withheld.

Site re-observability will be assessed only when at least three eligible sites complete the required calibration data. With fewer than three completed sites, the site component will be classified as **not assessable**.

When insufficient data exist to estimate the joint coefficient defensibly, the design will be classified as:

> **Not assessable for re-observability**

rather than as re-observable or non-re-observable.

## 7.20 First-Year Interpretation

The first-year design uses Japan and at least two international mirror sites.

Three sites are sufficient to initiate cross-site variance estimation and demonstrate international protocol replication. However, they provide a limited basis for claims about the full universe of possible observation sites.

Accordingly:

- session and adjacent-window estimates may receive full first-year interpretation under the registered design;
- site estimates will be interpreted within the defined three-site universe; and
- claims of broad global generalizability will require subsequent replication with additional sites.

MIBO will distinguish:

> **re-observable across the registered sites**

from:

> **globally re-observable**

The second claim requires stronger accumulated evidence.

## 7.21 Relationship to Longitudinal Change

A longitudinal difference and a re-observable measurement design are separate properties.

A result may be:

- stable and measured dependably;
- changing and measured dependably;
- apparently stable but measured unreliably; or
- apparently changing but measured unreliably.

MIBO will therefore evaluate:

1. whether the response distribution changed across macro-waves; and
2. whether the relevant outcome was measured under a design meeting the re-observability criterion.

A change claim is strongest when both the pre-change and post-change states are obtained under a re-observable measurement design.

## 7.22 Relationship to Frozen–Live Analysis

Where eligible Frozen and Live Lines are included in the calibration module, MIBO may evaluate the dependability of:

- the Frozen outcome;
- the Live outcome; and
- the Frozen–Live contrast.

A large Frozen–Live difference that depends on one site or one session pattern will not be treated as a dependable update contrast.

## 7.23 Required Reporting

Every G-study report will include:

- calibration-wave identifiers;
- participating sites;
- Anchor Items;
- service lineages;
- Line and language conditions;
- valid and missing cell counts;
- estimated variance components;
- joint absolute dependability coefficient;
- directional diagnostic coefficients;
- uncertainty intervals;
- D-study results;
- certification decision; and
- relevant protocol deviations.

Reporting only the final coefficient without the variance decomposition is prohibited.

## 7.24 Prohibited Interpretations

MIBO shall not:

- equate re-observability with factual correctness;
- equate textual similarity with re-observability;
- describe an entire service as re-observable on the basis of one item;
- treat a site difference automatically as observer error;
- conceal a failed international replication;
- select the coefficient definition after seeing the result;
- alter the .80 threshold for an inconvenient finding; or
- infer global generalizability from the initial three-site design.

Re-observability concerns dependable recovery of an observed behavior, not the truth or social desirability of that behavior.

## 7.25 First-Year Methodological Deliverable

The principal first-year methodological output of this module will be:

> **a preregistered, multisite generalizability analysis of re-observability for longitudinal generative-AI information behavior.**

The analysis will establish:

- how much variation arises from independent sessions;
- how much arises across observation sites;
- how much arises across adjacent windows;
- whether the initial \(k=10\) design is adequate;
- which outcomes are measured under a re-observable design; and
- how the MIBO design should be adjusted in its next registered cycle.

The purpose of the calibration module is not to certify every observed result. It is to determine which measurement procedures can legitimately support durable and independently recoverable scientific claims.

---

# 8. MIBO Network and International Mirror Replication

## 8.1 Purpose

The MIBO Network enables independent research groups outside the coordinating observatory in Japan to reproduce selected MIBO observations using the same protocol.

Its purpose is to determine whether:

- the MIBO observation procedure can be implemented outside Japan;
- defined machine-information-behavior results can be recovered across sites;
- observed differences are attributable to service behavior rather than local execution practices; and
- the MIBO protocol has sufficient clarity and portability to function as an international research method.

The Network is not primarily a dissemination initiative. It is an integral part of the scientific design of MIBO.

> **International mirror replication provides the empirical basis for evaluating the site generalizability of MIBO observations.**

## 8.2 Organizational Position

The MIBO Observatory System consists of:

1. the **MIBO Core Observatory**;
2. the **MIBO Sub-Observatories**; and
3. the **MIBO Network**.

The Network is not a third category of observatory parallel to the Core and Sub-Observatories.

It is the replication structure connecting:

- the coordinating observatory in Japan; and
- independent international mirror observatories.

The Core Observatory defines the common panel methodology and maintains the authoritative protocol.

Mirror observatories independently implement the designated replication module.

## 8.3 Coordinating Observatory

The MIBO Core Observatory in Japan will serve as the coordinating observatory for MIBO 1.0.

Its responsibilities are limited to:

- maintaining the Master Protocol;
- maintaining the Fixed Query Instrument;
- releasing the Mirror Observatory Kit;
- defining synchronized observation windows;
- assigning Site IDs;
- providing technical clarification;
- conducting protocol training;
- maintaining the common metadata schema;
- receiving or linking eligible site datasets;
- performing the preregistered pooled analysis; and
- publishing protocol amendments and corrections.

The coordinating observatory does not control the substantive findings of mirror sites.

## 8.4 Mirror Observatory

A **MIBO Mirror Observatory** is an independent research site that implements the designated MIBO replication protocol.

Each mirror observatory will receive a persistent **Site ID**.

Example:

```text
MIBO-SITE-JP01
MIBO-SITE-XX01
MIBO-SITE-YY01
```

A mirror observatory must have:

- an identifiable institutional affiliation;
- a locally responsible investigator;
- access to the registered services;
- the technical ability to execute the required protocol;
- the ability to preserve observation records; and
- the freedom to report nonreplication or disagreement.

The first-year Network will include:

- the coordinating site in Japan; and
- at least two international mirror sites.

## 8.5 MIBO Mirror Observatory Kit

The MIBO protocol will be distributed through the:

> **MIBO Mirror Observatory Kit**

The Kit will be released in English and will contain the minimum materials required to reproduce the designated observations.

The first release will include:

1. **Master Protocol**
2. **Mirror Observation Manual**
3. **English Bridge Instrument**
4. **Anchor Item Codebook**
5. **Metadata Template**
6. **Execution Checklist**
7. **Dry-Run Dataset**
8. **Quality-Control Checklist**
9. **Protocol Deviation Form**
10. **Data Submission and Release Guide**
11. **Analysis Code for the Cross-Site G-study**
12. **Version Manifest and File Hashes**

The Kit should be executable without requiring continuous case-by-case direction from the coordinating observatory.

## 8.6 Authoritative and Local Materials

The authoritative Network materials will be maintained in English.

Mirror sites may prepare local-language explanatory documents for training or administration.

However:

- the English Master Protocol remains authoritative;
- the English Bridge Instrument must not be locally rewritten;
- explanatory translations must be clearly identified as translations;
- substantive discrepancies must be reported; and
- local-language instruments must receive distinct version identifiers.

This rule preserves a common international comparison while permitting local accessibility.

## 8.7 Global Bridge Instrument

The primary common instrument for international replication will consist of the four English Anchor Items.

The **Global Bridge Instrument** will be identical across participating sites with respect to:

- query wording;
- query order rules;
- administration conditions;
- coding definitions;
- replication number;
- observation windows; and
- required metadata.

The Bridge Instrument provides the common measurement link across sites.

It is deliberately limited to four items in the first year in order to make international participation feasible without weakening methodological comparability.

## 8.8 Local Extensions

Mirror sites may conduct additional local observations, including:

- local-language versions;
- regional services;
- local institutions;
- local information environments;
- country-specific policy questions; and
- locally defined Sub-Observatories.

These observations will be classified as **Local Extensions**.

Local Extensions:

- do not alter the Global Bridge Instrument;
- require separate Item IDs;
- require separate documentation;
- are not automatically pooled with Core data; and
- must be clearly distinguished in publications.

The common international comparison will rely only on the registered Bridge Instrument unless otherwise preregistered.

## 8.9 Site Admission

A proposed mirror site will be admitted to the first-year Network after completing a standard admission process.

The process will include:

1. identification of the local responsible investigator;
2. confirmation of service access;
3. review of relevant ethical and legal conditions;
4. completion of protocol training;
5. execution of a dry run;
6. submission of the required metadata;
7. review of protocol compliance; and
8. approval for participation in synchronized calibration waves.

The process is intended as a quality-control procedure, not as a complex accreditation system.

MIBO 1.0 will use a single designation:

> **Participating MIBO Mirror Observatory**

Additional certification levels will not be introduced during the first registered cycle.

## 8.10 Dry Run

Before participating in confirmatory mirror observation, each site will complete a dry run using the supplied training materials.

The dry run will evaluate:

- correct service access;
- exact query administration;
- session independence;
- completion of ten replications;
- timestamp accuracy;
- metadata completeness;
- response capture;
- retry compliance; and
- correct use of Site and Replication IDs.

Dry-run data are developmental data.

They will not be included in the primary confirmatory cross-site analysis.

## 8.11 Synchronized Mirror Waves

Mirror observations will be conducted during the four preregistered calibration waves.

For each calibration wave, all participating sites will implement:

- the same four Anchor Items;
- the same designated service lineages;
- the English Bridge Instrument;
- two adjacent observation windows;
- ten independent replications per required cell; and
- the same registered observation mode.

Each site will complete the observation within the common synchronized field window.

The coordinating observatory will distribute the schedule in UTC and provide equivalent local times for participating sites.

## 8.12 Site and Time Separation

Differences between sites may be confounded with differences in execution time when every site observes at a different local hour.

The calibration schedule will therefore record:

- UTC execution time;
- local execution time;
- time zone;
- Window A and Window B; and
- the interval between windows.

Where operationally feasible, execution times will be balanced across calibration waves so that one site is not always observed at the same relative time.

The design will remain simple enough to ensure reliable completion.

## 8.13 Independence of Data Collection

Mirror sites must collect their observations independently.

The coordinating observatory may provide technical support before or during a wave but shall not:

- observe the mirror site’s outputs before local collection is complete;
- direct the site to repeat a valid output;
- instruct the site to exclude an unusual response;
- determine local coding after inspecting pooled findings; or
- suppress a site-level disagreement.

Each site will preserve its own raw records and operational logs.

The local responsible investigator will attest that the site’s observations were conducted independently.

## 8.14 Common Observation Conditions

The primary cross-site comparison requires each site to use, as far as available:

- the same public service lineage;
- the same registered account tier;
- the same interface or access mode;
- the same language;
- the same memory and personalization condition;
- the same retrieval or browsing condition;
- the same query text; and
- the same replication procedure.

Any unavoidable local difference must be entered into the site metadata.

A site will not be excluded merely because its geographic location produces a genuine regional service difference. Such differences may be part of the phenomenon being observed.

## 8.15 Regional Service Variation

A public service may present different configurations across countries or regions.

When this occurs, MIBO will distinguish between:

- a protocol execution difference; and
- a genuine regional deployment difference.

Examples of genuine regional deployment variation may include:

- different model availability;
- different retrieval results;
- different safety behavior;
- different tool access;
- different account features; or
- different service routing.

Such differences will be documented as observed site-level conditions rather than automatically corrected or removed.

The G-study will help determine whether a result is stable across these admissible site conditions.

## 8.16 Site Metadata

Each mirror-site record will include:

- Site ID;
- country or territory;
- time zone;
- local responsible investigator;
- institution;
- registered service access mode;
- account tier;
- locale;
- language;
- memory and personalization settings;
- retrieval and tool conditions;
- observation timestamps;
- relevant regional service differences;
- deviation records; and
- Mirror Observatory Kit version.

Precise personal or residential location data are not required.

## 8.17 Data Custody

Each participating site will retain local custody of its original observation records.

The Network may use one of the following arrangements:

- transfer of permitted raw data;
- transfer of de-identified or derived data;
- secure access to locally retained records; or
- federated submission of coded variables and hashes.

The applicable arrangement will depend on:

- service terms;
- institutional policy;
- data-protection requirements; and
- the permissions attached to generated outputs.

The public Network dataset may contain derived variables even where raw outputs cannot be redistributed.

## 8.18 Common Data Structure

All participating sites will use the same registered data schema.

At minimum, every observation must link:

```text
Site ID
Service Lineage ID
Line ID
Wave ID
Window ID
Item ID
Query Form ID
Replication ID
Timestamp
Outcome status
Raw-output hash
Codebook version
Protocol version
```

Common variable names and permissible values will be defined in the Mirror Observatory Kit.

Site-specific variables may be added but may not replace the required common fields.

## 8.19 Data Submission

Each mirror site will submit or register its calibration dataset within the preregistered period after each synchronized wave.

The submission package will contain:

- observation-level data;
- metadata;
- missing-cell record;
- retry log;
- protocol-deviation log;
- configuration summary; and
- local investigator attestation.

Late data may be retained but will be identified as late and treated according to the Statistical Analysis Plan.

Data shall not be altered to increase agreement with another site.

## 8.20 Quality Review

The coordinating observatory will conduct a limited quality review before pooled analysis.

The review will assess:

- completeness;
- identifier validity;
- query-text conformity;
- session-independence evidence;
- timestamps;
- replication count;
- missingness;
- metadata consistency; and
- protocol deviations.

The quality review does not evaluate whether the mirror site obtained the “correct” result.

A valid disagreement between sites must remain in the pooled dataset.

## 8.21 Site Exclusion

A site may be excluded from a particular confirmatory analysis only for a predefined methodological reason, such as:

- use of the wrong query instrument;
- failure to use independent sessions;
- material mismatch in access mode;
- extensive missing metadata;
- observation outside the permitted field window;
- unresolvable data-integrity concerns; or
- failure to preserve the required operational record.

Exclusion decisions will be documented before the pooled outcome pattern is interpreted wherever possible.

The excluded data may remain available for descriptive or sensitivity analysis.

## 8.22 Protocol Deviations

Each site will maintain a local Protocol Deviation Log.

The log will record:

- affected cells;
- nature of the deviation;
- reason;
- timing;
- corrective action;
- potential impact; and
- proposed analytical treatment.

The Network will publish a consolidated deviation summary with each major release.

Protocol deviations will not be removed merely to create an appearance of perfect international standardization.

## 8.23 Mirror Nonreplication

A mirror-site finding may differ from the coordinating site.

Such a result will be described as:

- cross-site divergence;
- site dependence;
- failure of site re-observability; or
- nonreplication under the registered site conditions,

depending on the analysis.

Mirror nonreplication is not evidence that a site failed to perform its role.

> **A Network capable of contradicting the coordinating observatory is scientifically stronger than a Network designed only to confirm it.**

## 8.24 Cross-Site Analysis

The primary cross-site analysis will be the preregistered G-theory assessment described in Chapter 7.

Additional descriptive analyses may compare:

- response distributions;
- entity appearance rates;
- refusal rates;
- citation-source patterns;
- rank distributions;
- semantic clusters; and
- site-specific deployment conditions.

The analysis will distinguish:

- site differences in observed service behavior;
- site differences in measurement execution; and
- uncertainty that cannot be assigned uniquely to either source.

## 8.25 Publications and Credit

The Mirror Observatory Kit and Network outputs will use transparent contribution rules.

Participation in data collection alone does not automatically determine authorship on every publication.

Authorship will follow documented scholarly contribution, including contributions to:

- study design;
- local implementation;
- data stewardship;
- coding;
- analysis;
- interpretation; and
- manuscript preparation.

Each participating site will receive formal acknowledgment in relevant Network releases.

The Network will encourage mirror-site investigators to lead publications arising from site-specific or regional findings.

## 8.26 Independent Use of the Protocol

The MIBO Mirror Observatory Kit will be published so that qualified researchers can use the protocol without joining the formal first-year Network.

Independent users must:

- cite the protocol version;
- identify any modifications;
- avoid presenting modified procedures as identical to MIBO Core; and
- preserve the distinction between MIBO-compatible work and official Core Observatory data.

Independent use without authorship by the Japan coordinating team is an intended sign of successful methodological dissemination.

## 8.27 Protocol Versioning

Every Mirror Observatory Kit release will receive a version number.

For example:

```text
MIBO Mirror Observatory Kit v1.0
MIBO Mirror Observatory Kit v1.1
MIBO Mirror Observatory Kit v2.0
```

Minor revisions may correct documentation or software defects without changing the measurement design.

Substantive changes to:

- Anchor Items;
- replication structure;
- site requirements;
- observation windows;
- coding definitions; or
- re-observability rules

will require a new major or otherwise clearly distinguished version.

Each site must record the exact Kit version used.

## 8.28 First-Year Network Scope

The first-year MIBO Network will remain intentionally limited.

Its minimum scope is:

- one coordinating observatory in Japan;
- at least two international mirror observatories;
- four English Anchor Items;
- four calibration waves;
- two adjacent windows per calibration wave;
- ten replications per required cell; and
- one preregistered cross-site G-study.

The first year will not require:

- a large international membership organization;
- multiple certification categories;
- continuous weekly international observation;
- full replication of all 12 Core items; or
- permanent international governance bodies.

Expansion will be considered only after the initial protocol has been successfully implemented.

## 8.29 First-Year Network Success Criteria

The first-year Network will be considered operationally successful if:

1. the English Mirror Observatory Kit is publicly released;
2. at least two international sites complete the dry run;
3. at least two international sites participate in the registered calibration waves;
4. site-level missingness and deviations are fully documented;
5. the cross-site G-study is completed;
6. at least one outcome can be evaluated for site re-observability;
7. divergent site findings are reported without concealment; and
8. the pooled derived dataset and analysis code are released to the extent permitted.

Success does not require high cross-site agreement.

A finding that the protocol or result is site-dependent may be the most important first-year Network result.

## 8.30 Scientific Contribution of the MIBO Network

The MIBO Network transforms re-observability from a local aspiration into an empirical international question.

Without mirror observatories, MIBO can estimate session-level and short-window stability at one location.

With independent mirror observatories, MIBO can test whether:

- the same protocol works elsewhere;
- the same result appears elsewhere;
- site conditions alter the observed machine behavior; and
- the measurement method itself generalizes across research environments.

The strongest evidence that MIBO is a globally relevant research infrastructure will not be the international use of the services it studies.

It will be:

> **the independent international replication of a panel-survey protocol developed in Japan.**


---

# 9. Missingness, Attrition, Ethics, Openness, Correction, Withdrawal, and AI-Assisted Analysis

## 9.1 Purpose

MIBO Core Observatory v1.0 will treat missing data, service discontinuity, protocol deviations, ethical constraints, and changes to scientific claims as part of the observable research record.

The project will not present continuous commercial AI services as if they were stable laboratory instruments. Service failures, access restrictions, configuration uncertainty, panel attrition, and failed international replication may themselves provide important evidence about the conditions under which machine information behavior can be studied.

This chapter establishes the rules governing:

- missing observations;
- service and Frozen-Line attrition;
- protocol deviations;
- ethical and legal review;
- conflicts of interest;
- data retention and disclosure;
- preregistration and public release;
- claim registration;
- corrections;
- amendments;
- withdrawals; and
- AI-assisted data processing and analysis.

## 9.2 General Transparency Principle

MIBO will follow the principle that:

> **An observation record is scientifically useful only when its collection conditions, missingness, limitations, and later revisions remain inspectable.**

Accordingly, MIBO will not:

- conceal failed observations;
- silently replace missing cells;
- retrospectively alter identifiers;
- remove inconvenient replications;
- redefine outcomes after inspecting the results;
- present protocol deviations as planned procedures; or
- leave superseded claims publicly unmarked.

The preservation of error and correction histories is part of the research design.

## 9.3 Missingness Categories

Every planned observation cell will receive one of the following status classifications:

1. **Complete**
2. **Partially complete**
3. **Missing because of service nonresponse**
4. **Missing because of access failure**
5. **Missing because of protocol execution failure**
6. **Missing because of legal or ethical restriction**
7. **Missing because of panel attrition**
8. **Missing because of Frozen-Line attrition**
9. **Not scheduled by design**
10. **Not assessable**

A blank field without a missingness code is not permitted in the confirmatory dataset.

## 9.4 Service Nonresponse

Service nonresponse includes:

- error messages;
- timeout;
- rate limiting;
- regional service failure;
- authentication failure;
- unavailable mode;
- interrupted generation; or
- failure to return an observable output.

A substantive refusal, safety response, redirection, or request for clarification is not service nonresponse. It is a valid information-behavior outcome.

Failed attempts will remain in the operational record even when a later retry succeeds.

## 9.5 Missingness at the Replication Level

When one or more of the ten intended replications cannot be obtained:

- valid completed replications will be retained;
- failed attempts will remain documented;
- no valid output will be duplicated;
- no synthetic response will be generated; and
- the cell will be identified as incomplete.

The Statistical Analysis Plan will specify the minimum number of valid replications required for each primary analysis.

Analyses involving incomplete cells will report:

- the intended number of replications;
- the valid number obtained;
- the reason for missingness; and
- any sensitivity analysis.

## 9.6 Missingness at the Wave Level

A survey wave may be incomplete because one or more services, Lines, languages, items, sites, or observation windows could not be measured.

An incomplete wave will not automatically be excluded.

The wave will remain in the longitudinal record and will be classified as:

- complete;
- complete with missing cells;
- partially completed; or
- not completed.

The project will not move a wave retrospectively to a more convenient date and present it as if the original synchronized field window had been met.

## 9.7 Missing-Data Analysis

MIBO will not assume that missingness is random.

Missing observations may be associated with:

- provider changes;
- service demand;
- safety mechanisms;
- query content;
- account restrictions;
- geographic differences; or
- configuration instability.

The primary analysis will therefore emphasize observed-data estimation and transparent missingness reporting.

Where statistical models accommodate unbalanced data, their assumptions will be stated explicitly.

Imputation of substantive machine responses is prohibited in the primary analysis.

Imputation may be considered only for limited derived metadata and only when explicitly justified in the Statistical Analysis Plan.

## 9.8 Panel Attrition

Panel attrition occurs when a registered service lineage can no longer be observed under the Core eligibility and continuity rules.

Attrition may result from:

- permanent service discontinuation;
- withdrawal from the registered region;
- loss of public accessibility;
- legal or contractual restriction;
- transformation into a methodologically incomparable service; or
- permanent inability to meet the registered observation conditions.

Attrition is a substantive panel event.

The Service Lineage ID and historical observations will remain preserved.

The service will not be silently removed from previous descriptions of the panel.

## 9.9 Frozen-Line Attrition

A Frozen Line may end before its associated Live Line because:

- the fixed snapshot is withdrawn;
- a model alias is reassigned;
- the required execution environment becomes unavailable;
- configuration integrity can no longer be verified; or
- continued access becomes impermissible.

The corresponding Live Line may continue.

A new reference model introduced later will receive a new Line ID and will not be presented as uninterrupted continuation of the original Frozen Line.

Frozen-Line attrition will limit the available decomposition analyses but will not invalidate the broader Core panel.

## 9.10 Refreshment and Replacement

An attrited panel member will not be retrospectively replaced.

A newly admitted service lineage will be treated as a refreshment sample with:

- a new Service Lineage ID;
- an explicit observation start date;
- no fabricated earlier history; and
- separate eligibility for confirmatory analyses.

Routine refreshment of the Core panel will ordinarily occur only during the annual protocol review.

Supplementary observations of emerging services may be collected during the year but must remain analytically distinct from the registered primary panel.

## 9.11 Protocol Deviations

A protocol deviation is any material departure from the registered procedure.

Examples include:

- use of the wrong query form;
- collection outside the permitted field window;
- use of a different account tier;
- failure to initiate an independent session;
- changed memory or personalization settings;
- incorrect service mode;
- incomplete response capture;
- altered replication count; or
- unregistered change to the execution procedure.

Every deviation will be entered into the **MIBO Protocol Deviation Log**.

## 9.12 Deviation Classification

Protocol deviations will be classified as:

### Minor

Unlikely to materially affect interpretation or comparability.

### Material

May affect one or more outcomes or contrasts.

### Critical

Invalidates the intended measurement condition or creates a serious integrity concern.

For each deviation, the record will state:

- affected observation IDs;
- date and site;
- nature and cause;
- severity;
- corrective action;
- analytical treatment; and
- whether a protocol amendment is required.

A deviation will not be reclassified after results are known merely to preserve a preferred finding.

## 9.13 Protocol Amendments

A protocol amendment is a prospective change to the registered design.

Amendments may be required because of:

- service discontinuation;
- legal or ethical developments;
- technical impossibility;
- serious instrument defects;
- data-security requirements; or
- errors in the original protocol.

Every amendment will include:

1. a version number;
2. an effective date;
3. a description of the change;
4. a reason for the change;
5. the affected analyses;
6. the effect on longitudinal comparability; and
7. the distinction between observations collected before and after the amendment.

The original protocol will remain publicly available.

Amended procedures will not be described as having applied retrospectively.

## 9.14 Ethical Classification

Before confirmatory observation begins, MIBO will obtain a documented institutional determination concerning the ethical status of the project.

The determination will address whether the work constitutes:

- non-human-subject observational research;
- research requiring institutional notification;
- research requiring formal ethics review; or
- another locally applicable category.

The use of public generative-AI services does not remove the need to consider:

- account data;
- researcher exposure to harmful outputs;
- incidental personal information;
- copyrighted material;
- security-sensitive responses; and
- international data transfer.

The ethical determination and its date will be recorded in the protocol repository.

## 9.15 Human Participants

MIBO Core Observatory does not ordinarily recruit human participants or collect private personal responses from users.

Researchers operating the protocol are members of the research team rather than survey respondents.

If a later Sub-Observatory includes human participants, human evaluation, interviews, or user-generated personal data, it will require a separate protocol and ethical review.

Such data will not be treated as part of the Core Observatory merely because they use the MIBO name.

## 9.16 Incidental Personal Information

A public generative-AI response may contain names, contact details, allegations, or other information relating to identifiable persons.

MIBO will minimize unnecessary retention and redistribution of such material.

When incidental personal information appears:

- the raw output may be retained in the secure research layer where justified;
- public derived data should avoid unnecessary personal detail;
- sensitive allegations will not be amplified merely because the service generated them; and
- disclosure decisions will consider scientific necessity and potential harm.

Named public figures may appear when directly relevant to a registered item, but public release will remain limited to the information necessary for analysis.

## 9.17 Harmful and Security-Sensitive Outputs

Some outputs may contain:

- dangerous instructions;
- security vulnerabilities;
- personally harmful content;
- defamatory allegations; or
- other material unsuitable for unrestricted release.

MIBO will maintain a responsible-disclosure process for such observations.

The project may temporarily restrict:

- raw output;
- screenshots;
- detailed coding notes; or
- technical reproduction instructions

when immediate public release could create material harm.

Restriction of raw material does not justify concealing the existence of the observation, its analytical treatment, or the reason for restricted access.

## 9.18 Terms of Service and Access Compliance

Before each service is admitted to the Core panel, MIBO will document:

- the relevant access mode;
- the applicable terms of service;
- automation restrictions;
- rate limits;
- account requirements;
- output-use conditions; and
- any known restrictions on redistribution.

Where automated collection is not permitted or cannot be justified, the project will use a compliant manual or semi-manual procedure.

The scientific desirability of a measurement does not override legal or contractual constraints.

Terms-of-service changes will be reviewed as potential Configuration Events and may require protocol amendment.

## 9.19 Research Accounts and Credentials

MIBO observations will use dedicated institutional or research accounts where feasible.

Credentials will not be included in the public dataset.

The project will document:

- account tier;
- account creation and ownership;
- memory and personalization settings;
- relevant regional settings; and
- material changes to the account condition.

Personal accounts containing unrelated user histories should not be used for confirmatory Core observations.

## 9.20 Researcher Safety

Repeated interaction with public generative-AI systems may expose researchers or coders to disturbing, discriminatory, or harmful content.

The project will establish proportionate safeguards, including:

- advance notice of potentially harmful item categories;
- the ability to pause coding;
- escalation to the study lead;
- limited exposure to raw content when derived coding is sufficient; and
- access to institutional support where necessary.

No researcher will be required to repeatedly inspect harmful material when the scientific task can be completed through a safer procedure.

## 9.21 Conflicts of Interest

All principal investigators, analysts, data collectors, and site leads will disclose relevant relationships with:

- generative-AI providers;
- companies or institutions included in the query instrument;
- funders;
- consulting clients;
- advocacy organizations; or
- other entities that could reasonably be perceived as influencing the study.

Relevant relationships include:

- employment;
- consulting;
- research funding;
- gifts or service credits;
- equity ownership;
- advisory roles; and
- paid speaking engagements.

Conflict-of-interest declarations will be reviewed before the first wave and updated at least annually or when a material change occurs.

## 9.22 Provider Support

MIBO may accept publicly available service access, research credits, or technical clarification from providers only when:

- the support is disclosed;
- the provider has no control over the protocol, analysis, or publication;
- access conditions are documented;
- other services are not disadvantaged through undisclosed treatment; and
- the support does not prevent reporting of adverse findings.

Provider review of results before publication is not permitted except for narrowly defined responsible-disclosure concerns.

## 9.23 Preregistration

Before confirmatory collection begins, MIBO will publicly register:

- the Master Protocol;
- the initial Service Registry;
- the Fixed Query Instrument;
- the calibration-wave schedule;
- the primary research questions and hypotheses;
- the main outcome definitions;
- the Statistical Analysis Plan or its registered timetable;
- the missingness and exclusion rules; and
- the principal re-observability decision rules.

Files will be versioned, time-stamped, and cryptographically hashed where appropriate.

Embargo may be used only when justified and with a predefined public-release date.

## 9.24 Public and Secure Data Layers

MIBO will maintain two principal data layers.

### Public layer

The public layer should include, where legally and ethically permissible:

- protocol and amendments;
- query instrument;
- service and configuration metadata;
- observation status;
- derived coded variables;
- missingness records;
- protocol-deviation records;
- analysis code;
- aggregate results;
- Claim Registry;
- raw-output hashes; and
- AI Analysis Records for all material AI-assisted confirmatory analyses.

### Secure layer

The secure layer may include:

- complete raw outputs;
- screenshots;
- account identifiers;
- detailed operational logs;
- potentially harmful material;
- redistribution-restricted content; and
- adjudication notes.

The existence of a secure layer shall not be used to conceal methods or analytical decisions.

## 9.25 Data Retention

The project will preserve sufficient records to support later inspection and reanalysis.

The retention package will include:

- protocol versions;
- query versions;
- raw-output hashes;
- available raw outputs;
- metadata;
- coding records;
- analysis datasets;
- scripts;
- amendments;
- deviations; and
- claim histories.

Retention periods will comply with institutional and legal requirements.

Where raw content cannot be retained indefinitely, the project will preserve the maximum lawful combination of:

- hashes;
- derived variables;
- screenshots;
- source lists;
- timestamps; and
- provenance metadata.

## 9.26 Data and Code Releases

The preferred release schedule is:

- protocol release before observation;
- metadata and operational summaries at defined intervals;
- quarterly calibration summaries; and
- an annual integrated dataset and report.

A release may be delayed when necessary to:

- complete quality checks;
- protect sensitive information;
- resolve legal uncertainty; or
- conduct responsible disclosure.

Any delay and its reason will be publicly documented.

Later corrections will create a new release rather than silently replacing an archived version.

## 9.27 Claim Registry

MIBO will maintain a public **Claim Registry** linking scientific claims to the observations and protocol versions that support them.

Every registered claim will include:

- Claim ID;
- claim text;
- scope;
- Service Lineage IDs;
- Item IDs;
- Line and language;
- observation period;
- analysis version;
- confirmatory or exploratory status;
- current evidential status;
- last review date; and
- links to supporting records.

Possible claim statuses are:

1. **Candidate**
2. **Provisionally supported**
3. **Supported in the registered period**
4. **Independently re-observed**
5. **Amended**
6. **Corrected**
7. **Not supported**
8. **Withdrawn**
9. **Superseded**

The status history will remain visible.

Before a claim is entered into the Claim Registry, its evidential basis shall undergo the human review specified in Section 9.35.6. A claim based materially on AI-assisted coding must identify the applicable analytical configuration, validation result, and human-audit record.

## 9.28 Correction

A correction is required when a published record contains an error that does not invalidate the central claim.

Examples include:

- metadata error;
- mislabeled service or wave;
- coding error affecting a limited number of observations;
- calculation error with no material effect on the conclusion; or
- incomplete description of a limitation.

A correction will:

- identify the affected release;
- describe the error;
- state the corrected value;
- assess its consequence;
- receive a date and version; and
- link to both the original and corrected record.

The original archived release will not be erased.

## 9.29 Amendment of a Claim

A claim will be amended when new evidence changes its scope, strength, or wording without requiring complete withdrawal.

Examples include:

- a pattern initially thought to apply to all four services is later supported for only two;
- a result is reclassified as site-dependent;
- a model-update interpretation is reduced to a deployment-update interpretation; or
- an apparently persistent pattern is shown to be temporary.

The amended claim will receive a revised statement and retain a link to its earlier form.

Amendment is not treated as scientific failure. It is part of longitudinal claim management.

## 9.30 Withdrawal

A claim will be withdrawn when:

- its supporting data are invalid;
- the analysis contains a material error;
- the registered conditions were not met;
- later evidence directly contradicts the claim;
- a protocol deviation makes the interpretation indefensible; or
- the result cannot be reproduced under conditions required by the original claim.

A withdrawal notice will state:

- the original claim;
- the reason for withdrawal;
- the affected data and analyses;
- the date of decision; and
- whether a narrower claim remains supportable.

Withdrawn claims will remain searchable and visibly marked as withdrawn.

## 9.31 Nonreplication and Withdrawal

Failure of a mirror site to reproduce a finding does not automatically require withdrawal.

The appropriate response may be:

- reduction of the claim’s site scope;
- classification as site-dependent;
- additional calibration;
- amendment of the re-observability status; or
- withdrawal when the original claim explicitly required cross-site recovery.

The analytical consequence will depend on the claim’s registered scope.

A local finding must not be withdrawn merely because it is not globally generalizable, provided it was originally stated as local.

## 9.32 Annual Integrity Review

At the end of the first registered cycle, MIBO will conduct an integrity review covering:

- panel continuity;
- missingness;
- attrition;
- protocol deviations;
- amendments;
- data-release completeness;
- coding changes;
- re-observability decisions;
- corrections;
- claim amendments; and
- withdrawals.

The review will be published as part of the first-year report.

The report will distinguish:

- scientific findings;
- methodological findings;
- operational limitations; and
- unresolved issues.

## 9.33 Success and Failure

MIBO will not define success as confirmation of its original hypotheses.

The first-year program may be successful even if:

- Frozen Lines cannot be sustained for all intended services;
- some items show excessive stochastic variation;
- few outcomes meet the re-observability threshold;
- mirror sites diverge;
- a service lineage attrites; or
- an early claim must be withdrawn.

Methodological success requires that these outcomes be:

- observed under a defensible protocol;
- documented without concealment;
- analyzed according to registered rules; and
- incorporated into the next protocol version.

## 9.34 Final Integrity Principle

MIBO’s public value depends not only on its ability to identify machine-information-behavior patterns, but also on its ability to revise its own record.

The project therefore adopts the following principle:

> **A longitudinal observatory must preserve not only what it observed, but also when, why, and on what evidence it changed its mind.**

Corrections, amendments, nonreplications, and withdrawals are therefore permanent components of the MIBO scientific record, not exceptions to it.

## 9.35 AI-Assisted Data Processing and Analysis

### 9.35.1 General Principle

MIBO does not require data processing and analysis to be conducted exclusively by human researchers.

Generative-AI systems may be used as documented analytical instruments for:

- information extraction;
- semantic coding;
- translation support;
- clustering;
- anomaly detection;
- exploratory pattern discovery; and
- statistical-programming assistance.

The governing principle is:

> **AI may code; humans calibrate, verify, and decide.**

Generative-AI systems support the analytical process but do not assume scientific responsibility for the resulting claims.

### 9.35.2 Three Permitted Forms of AI Use

MIBO distinguishes three forms of AI-assisted analysis.

#### Automated processing

AI or conventional software may be used to extract directly verifiable features, including:

- names;
- organizations;
- URLs;
- citations;
- response length;
- output format; and
- other explicitly defined textual features.

Where deterministic and reproducible software can perform the task adequately, it should ordinarily be preferred over generative-AI interpretation.

#### Validated AI-assisted coding

A generative-AI system may code interpretive variables such as:

- refusal;
- uncertainty;
- recommendation category;
- source type;
- substantive position;
- correction; or
- other semantic categories defined in the codebook.

AI-generated coding may enter confirmatory analysis only after validation against a locked human reference set and completion of the registered human audit.

#### Exploratory AI analysis

Generative AI may be used to identify:

- possible themes;
- unusual response patterns;
- candidate clusters;
- provisional explanations; and
- new hypotheses.

Such outputs must be identified as exploratory. They shall not become confirmatory findings unless evaluated through a separately registered procedure.

### 9.35.3 Fixed Analytical Configuration

For each confirmatory AI-coding task, MIBO will ordinarily use one fixed analytical configuration consisting of:

- one analysis model;
- one analysis prompt;
- one output schema; and
- one codebook version.

The following information will be recorded:

- model provider and model identifier;
- available model or snapshot version;
- execution date;
- system and task prompts;
- relevant model settings;
- output schema;
- codebook version;
- data-processing procedure; and
- whether processing occurred locally or through an external service.

The complete prompt and relevant configuration files will be version-controlled and assigned a file hash.

A material change to the model, prompt, output schema, or codebook creates a new analytical configuration and requires renewed validation before it is used for confirmatory coding.

### 9.35.4 Human Reference Set

Confirmatory AI-assisted coding must be validated against a locked human reference set.

The reference set will:

- be drawn from relevant Pilot or validation data;
- represent the principal services, items, languages, and anticipated outcome categories;
- be independently coded by at least two human researchers;
- be resolved through human adjudication; and
- remain separate from the data used to develop or refine the AI-coding prompt.

The AI system shall not determine the final reference labels.

The size, composition, validation metric, and acceptance threshold for each coding task will be specified in the Statistical Analysis Plan before confirmatory coding begins.

Unless a different threshold is justified and preregistered, the default minimum acceptance threshold will be:

> **0.80 on the registered agreement or performance measure.**

The selected measure must be appropriate to the outcome type and may include:

- agreement;
- Krippendorff’s alpha;
- F1 score;
- sensitivity and specificity; or
- another preregistered metric.

AI coding that does not meet the registered criterion shall not serve as the sole basis for a confirmatory result.

### 9.35.5 Human Audit

After validation, a stratified sample of AI-coded confirmatory observations will be independently audited by human researchers.

The default audit rate will be:

> **10% of AI-coded confirmatory observations.**

The audit sample should represent, where applicable:

- service lineages;
- survey items;
- languages;
- survey waves;
- Frozen and Live Lines;
- common categories; and
- infrequent or ambiguous categories.

The Statistical Analysis Plan will specify:

- the audit measure;
- the minimum acceptable audit result; and
- the response to audit failure.

If the registered audit criterion is not met, the affected AI-coded variable will be suspended from confirmatory use until the research team has:

- identified the source of the disagreement;
- evaluated the affected observations; and
- completed an appropriate corrective procedure.

The project is not required to repeat human coding of all AI-coded data when validation and audit criteria are satisfied.

### 9.35.6 Human Review of Scientific Claims

Before a result is entered into the MIBO Claim Registry, at least two human researchers will review the evidence necessary to support the proposed claim.

The review will consider:

- the applicable coded data;
- relevant raw-response examples;
- ambiguous and boundary cases;
- validation and audit results;
- statistical output;
- missingness and deviations; and
- the proposed scope and wording of the claim.

This requirement concerns the evidential basis of the claim. It does not require two human researchers to recode every observation supporting it.

The final decision to register, amend, correct, narrow, or withdraw a claim belongs to the human research team.

### 9.35.7 Observation–Analysis Separation

The generative-AI service lineage that produced an observed response may also be used as an analytical model, but it shall not act as the sole evidential authority for confirmatory coding of its own outputs.

When the same service lineage is used for observation and analysis, confirmatory use requires:

- validation against the human reference set;
- the registered human audit; and
- human review of any resulting Claim Registry entry.

Unvalidated self-evaluation may be reported only as:

- exploratory analysis;
- sensitivity analysis; or
- a separate study of machine self-assessment.

### 9.35.8 Statistical Analysis

Confirmatory statistical analysis will be conducted through version-controlled, executable, and reproducible code.

Generative AI may assist researchers in:

- writing code;
- debugging;
- preparing tests;
- explaining functions; and
- documenting analytical workflows.

However, a human researcher must:

- inspect the final analysis code;
- execute it on the registered data;
- verify the relevant inputs and outputs;
- review diagnostic and error messages; and
- assume responsibility for the reported results.

A natural-language answer produced by a generative-AI system shall not, by itself, constitute a confirmatory statistical analysis.

### 9.35.9 Human-Reserved Decisions

Human investigators retain responsibility for:

- defining constructs;
- approving the codebook;
- determining the panel and survey instrument;
- preregistering hypotheses and thresholds;
- adjudicating reference labels;
- determining Service Lineage continuity;
- classifying Frozen–Live comparability;
- interpreting causal and longitudinal contrasts;
- interpreting generalizability and re-observability;
- approving Claim Registry entries;
- issuing corrections and amendments;
- withdrawing claims; and
- approving final scientific conclusions.

Generative-AI systems may provide relevant information or candidate interpretations but shall not make these decisions on behalf of the research team.

### 9.35.10 AI Analysis Record

Each release containing material AI-assisted analysis will include a concise **AI Analysis Record**.

The record will report:

| Field | Required information |
|---|---|
| Analysis task | Extraction, coding, exploration, or programming support |
| Analysis model | Provider, model identifier, and available version |
| Execution period | Dates on which processing occurred |
| Prompt version | Prompt identifier and file hash |
| Codebook version | Applicable coding specification |
| Validation | Reference-set design, metric, and result |
| Human audit | Audit proportion and result |
| Data environment | Local system or external service |
| Known limitations | Material weaknesses or constraints |

A separate administrative registry is not required when this information is maintained in the release record and version-controlled repository.

### 9.35.11 Data Protection

Restricted, confidential, or security-sensitive observation data shall not be submitted to an external generative-AI service unless the applicable:

- legal;
- contractual;
- ethical;
- institutional;
- confidentiality; and
- data-protection

requirements have been satisfied.

Where these conditions cannot be established, MIBO will use:

- local processing;
- approved institutional infrastructure;
- de-identified or minimized inputs;
- deterministic processing; or
- human coding.

The scientific usefulness of an external AI service does not override restrictions governing the observation data.

### 9.35.12 Disclosure and Responsibility

Material uses of generative AI in data processing, coding, analysis, code development, or manuscript preparation will be disclosed in the relevant:

- protocol;
- Methods section;
- data release; and
- AI Analysis Record.

Generative-AI systems shall not be listed as authors.

Human authors remain responsible for:

- the accuracy of the analysis;
- the integrity of the data;
- the validity of the interpretation;
- the completeness of disclosure; and
- the content of all published claims.

---

# Required Companion Documents Before Final v1.0

The Master Protocol will be promoted from **v1.0-rc3** to **v1.0** after the following companion documents are completed and frozen:

1. **MIBO Service Registry v1.0**
2. **MIBO Fixed Query Instrument v1.0**
3. **MIBO Query Codebook v1.0**
4. **MIBO Frozen–Live Comparability Registry v1.0**
5. **MIBO Operations Schedule and Manual v1.0**
6. **MIBO Statistical Analysis Plan v1.0**
7. **MIBO Mirror Observatory Kit v1.0**

At formal preregistration, the protocol record should include:

- effective date;
- repository URL;
- persistent identifier, where available;
- SHA-256 file hash; and
- a statement that the English version is authoritative.
