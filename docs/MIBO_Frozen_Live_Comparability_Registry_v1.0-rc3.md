# MIBO Frozen–Live Comparability Registry v1.0-rc3

## Prospective Classification of Dual-Line Comparisons

**Document status:** Integrated Release Candidate  
**Parent protocol:** MIBO Core Observatory Master Protocol v1.0-rc3  
**Parent service registry:** MIBO Service Registry v1.0-rc3  
**Parent instrument:** MIBO Fixed Query Instrument v1.0-rc3  
**Authoritative language:** English  
**Registry date:** 3 August 2026  
**Planned effective date:** 1 September 2026  
**Technical freeze window:** 17–20 August 2026  

---

# 1. Purpose

This Registry defines which Frozen–Live comparisons may enter the first-year confirmatory decomposition analysis and which interpretations are permitted.

Its primary purpose is to prevent a difference between a public web service and an API model from being misreported as a pure model-update effect.

The Registry distinguishes:

1. **Ecological Live observation**, which follows the public web service users encounter; and
2. **Paired-harness observation**, which compares a current and a frozen model condition under the same controlled API harness.

Only paired-harness observations may support a model-update or deployment-update contrast.

---

# 2. Minimal First-Year Design

The first-year Frozen–Live module will remain intentionally limited.

It will use:

- the four English Anchor Items;
- ten independent replications per required cell;
- monthly synchronized Core waves;
- one fixed API harness per provider;
- one current Live Reference condition;
- one Frozen Reference condition; and
- at least two provider lineages that pass the technical eligibility test.

The four Anchor Items are:

| Item ID | Domain |
|---|---|
| MIBO-I03 | Citation and attribution |
| MIBO-I05 | Recommendation |
| MIBO-I07 | Synthesis and explanation |
| MIBO-I09 | Uncertainty and refusal |

Japanese forms and the remaining eight items will continue to be observed in the ecological Live panel, but they are not required in the first-year paired-harness module.

This limitation preserves the methodological contribution while avoiding an unnecessarily large dual-line workload.

---

# 3. Line and Mode Structure

## 3.1 Ecological Live condition

The ecological Live condition is the registered public web-interface observation.

Example identifier:

```text
MIBO-SL-002-L-UI
```

It follows the provider’s current public deployment, including changes to:

- model routing;
- system policies;
- retrieval;
- tools;
- interface;
- personalization defaults; and
- other provider-controlled components.

It is the primary panel observation for ecological longitudinal inference.

## 3.2 Paired Live Reference condition

The paired Live Reference is the provider’s current eligible API model, selected at each wave by a preregistered rule and executed under the fixed MIBO harness.

Example identifier:

```text
MIBO-SL-002-L-API
```

The current-model selection rule must be based on provider documentation and fixed before results are inspected.

## 3.3 Frozen Reference condition

The Frozen Reference is the baseline API model identifier fixed before Wave 1 and executed under the same MIBO harness.

Example identifier:

```text
MIBO-SL-002-F-API
```

The baseline must remain identifiable and available. If the provider withdraws it or its fixed status can no longer be verified, Frozen-Line attrition is declared.

## 3.4 No direct causal subtraction between UI and API

The following subtraction is not eligible for a model-update interpretation:

```text
Public web Live − API Frozen
```

A web UI and an API differ in too many potentially material components.

The public UI may be compared descriptively with the paired API conditions, but it is not the counterfactual control for them.

---

# 4. Required Paired Harness

For each admitted provider, the Live Reference and Frozen Reference will use the same:

- API provider and endpoint family;
- research project and billing account;
- geographic execution environment;
- system instruction;
- query text;
- language;
- tool configuration;
- retrieval configuration;
- temperature and sampling settings where available;
- reasoning or effort setting where available;
- maximum-output setting;
- response schema;
- retry rule;
- logging procedure;
- execution code;
- software environment; and
- response-capture process.

Only the registered model identifier or model-selection rule may differ in a Class A comparison.

If another material component differs, the comparison is Class B or Class C.

---

# 5. Comparability Classes

## 5.1 Class A — Model-comparable pair

A pair is Class A when:

- both conditions use the same API harness;
- the Frozen model is demonstrably version-fixed;
- the Live Reference model at each wave is demonstrably identifiable;
- all registered non-model conditions are matched; and
- model state is the principal material difference.

Permitted interpretation:

> **Model-update contrast**

## 5.2 Class B — Deployment-comparable pair

A pair is Class B when the same general harness is used, but at least one additional deployment component cannot be perfectly matched or verified.

Examples include:

- non-equivalent reasoning controls;
- changed tool implementation;
- unverifiable alias resolution;
- provider-side changes under the same model identifier; or
- other documented configuration differences.

Permitted interpretation:

> **Deployment-update contrast**

A Class B result must name the unresolved component.

## 5.3 Class C — Descriptive reference pair

A pair is Class C when material differences prevent an update-effect interpretation.

Examples include:

- public web UI versus API;
- different providers;
- different retrieval systems;
- different system instructions;
- different tool availability; or
- a Frozen model whose identity cannot be verified.

Permitted interpretation:

> **Descriptive cross-condition difference**

Class C data do not enter the primary Frozen–Live decomposition.

## 5.4 Not eligible

A candidate is not eligible when:

- no defensible Frozen model can be maintained;
- the provider forbids or technically prevents the registered use;
- the two conditions cannot use a common harness;
- model identity cannot be documented; or
- expected availability is insufficient for longitudinal observation.

---

# 6. Prospective Candidate Matrix

The following classifications are provisional. Final admission and class assignment will occur before Wave 1 and before outcome inspection.

| Service Lineage | Ecological Live UI | Paired API candidate | Frozen candidate | Provisional status | Maximum permitted class before technical test |
|---|---:|---:|---:|---|---|
| MIBO-SL-001 ChatGPT/OpenAI | Yes | Yes | Yes, pending pinning verification | Reserve candidate | Class B |
| MIBO-SL-002 Claude/Anthropic | Yes | Yes | Yes | Primary candidate | Class A |
| MIBO-SL-003 Gemini/Google | Yes | Yes | Yes | Primary candidate | Class A, subject to version verification |
| MIBO-SL-004 Perplexity | Yes | No primary paired module | No primary Frozen Line | Not admitted to v1.0 paired module | Class C only |

The first-year confirmatory paired module will admit no more than three lineages and requires at least two.

The intended minimum is:

- Anthropic; and
- Google,

with OpenAI retained as a reserve or additional candidate if the version-fixed condition passes technical verification.

Perplexity remains essential to the ecological Live panel as the search-native lineage but is not required to support a Frozen pair.

---

# 7. Provider-Specific Provisional Records

# 7.1 MIBO-SL-001 — OpenAI

| Field | Provisional entry |
|---|---|
| Ecological Live Mode ID | MIBO-SL-001-L-UI |
| Paired Live Mode ID | MIBO-SL-001-L-API |
| Frozen Mode ID | MIBO-SL-001-F-API |
| Proposed endpoint family | OpenAI Responses API |
| Proposed Live Reference rule | Current generally available flagship general-purpose text model selected under the preregistered rule |
| Proposed Frozen rule | Explicit baseline model ID fixed before Wave 1 |
| Tools | Disabled for primary paired module unless a separately registered environment-open stratum is added |
| Retrieval | Disabled for primary paired module |
| Provisional class | Class B |
| Reason for caution | The official model catalog distinguishes model IDs and aliases, but the release-candidate review has not yet established that the selected baseline ID is guaranteed to remain behaviorally fixed for the annual cycle |
| Admission condition | Technical test must verify identifier persistence, response metadata, availability, and deprecation risk |

A Class A promotion is permitted only before Wave 1 and only if official documentation or technical evidence establishes that the selected baseline is version-fixed and that the Live Reference model is identifiable under the same harness.

---

# 7.2 MIBO-SL-002 — Anthropic

| Field | Provisional entry |
|---|---|
| Ecological Live Mode ID | MIBO-SL-002-L-UI |
| Paired Live Mode ID | MIBO-SL-002-L-API |
| Frozen Mode ID | MIBO-SL-002-F-API |
| Proposed endpoint family | Claude Messages API |
| Proposed Live Reference rule | Provider’s current generally available general-purpose model selected by the preregistered model-selection rule |
| Proposed Frozen rule | One pinned Claude model ID fixed before Wave 1 |
| Tools | Disabled |
| Retrieval | Disabled |
| Thinking/effort | Explicitly fixed where supported and matched across conditions where possible |
| Provisional class | Class A |
| Basis | Anthropic documents that every Claude model ID is a pinned snapshot |
| Principal risk | Model deprecation or differences in effort/thinking support between baseline and current models |
| Admission condition | Dry run must demonstrate matched settings and expected availability |

If effort or thinking controls cannot be matched, the pair will be downgraded to Class B before Wave 1.

---

# 7.3 MIBO-SL-003 — Google

| Field | Provisional entry |
|---|---|
| Ecological Live Mode ID | MIBO-SL-003-L-UI |
| Paired Live Mode ID | MIBO-SL-003-L-API |
| Frozen Mode ID | MIBO-SL-003-F-API |
| Proposed endpoint family | Gemini API stable endpoint |
| Proposed Live Reference rule | Current eligible model chosen by the preregistered rule; a `latest` alias may be used only if its resolved version can be recorded |
| Proposed Frozen rule | Specific stable Gemini model fixed before Wave 1 |
| Tools | Disabled |
| Retrieval/grounding | Disabled for the primary paired module |
| Thinking controls | Explicitly fixed and matched where available |
| Provisional class | Class A, conditional |
| Basis | Google distinguishes stable model identifiers from `latest` aliases and states that `latest` may be hot-swapped |
| Principal risk | Stable model behavior is described as usually unchanged rather than absolutely immutable; model deprecation may occur |
| Admission condition | Technical test must record the resolved model condition and demonstrate that the Frozen identifier remains stable enough for the registered inference |

If alias resolution or Frozen stability cannot be verified, the pair will be downgraded to Class B.

---

# 7.4 MIBO-SL-004 — Perplexity

| Field | Provisional entry |
|---|---|
| Ecological Live Mode ID | MIBO-SL-004-L-UI |
| Paired Live Mode ID | Not registered for v1.0 |
| Frozen Mode ID | Not registered for v1.0 |
| Primary role | Search-native ecological Live sentinel |
| Provisional class | Class C for any UI–API comparison |
| Reason | The public service combines retrieval, ranking, model routing, and citation presentation; an API reference would not isolate the public UI deployment |
| Future option | A separate Sonar or Agent API experiment may be registered as a Sub-Observatory or later protocol module |

Perplexity’s exclusion from the paired module does not reduce its status as a Core Live panel member.

---

# 8. Current-Model Selection Rule

For each admitted provider, the paired Live Reference model will be selected at each wave by the following rule:

1. Use the provider’s generally available, self-serve, general-purpose model family that most closely corresponds to the registered capability tier.
2. Do not switch solely because a preview or experimental model is released.
3. Switch only when:
   - the provider designates a new generally available successor;
   - the registered prior Live Reference is deprecated or no longer represents the chosen tier; or
   - the preregistered selection rule otherwise requires the change.
4. Record:
   - provider documentation;
   - exact model identifier;
   - model-list response where available;
   - selection date;
   - effective wave; and
   - reason for the change.
5. Do not select a model after inspecting its MIBO outcomes.

A current-model change is a planned state change in the paired Live Reference, not a protocol deviation.

---

# 9. Frozen Baseline Selection Rule

The Frozen baseline will be selected before Wave 1 according to the following order:

1. Prefer a provider-documented pinned snapshot.
2. Otherwise prefer a specific stable model identifier rather than a `latest` alias.
3. Reject a preview, experimental, or silently routed identifier unless the frozen state can be independently verified.
4. Prefer a model expected to remain available for the registered annual cycle.
5. Record the provider’s deprecation policy and known retirement date.
6. Preserve the exact:
   - model identifier;
   - endpoint;
   - system instruction;
   - settings;
   - SDK and API versions;
   - tool state;
   - region;
   - harness commit; and
   - environment lock file.

The Frozen baseline is not replaced under the same ID after attrition.

---

# 10. Environment Strata

The primary paired module is **environment-closed**:

- tools disabled;
- retrieval disabled;
- no external files;
- no private data;
- no web grounding; and
- the same system instruction in both conditions.

This stratum provides the clearest model/deployment comparison.

An **environment-open** Frozen module may be added only through a preregistered amendment or a later protocol version. It must use a common retrieval layer under MIBO control.

Provider-native web search will not be used to claim a pure information-environment effect unless the retrieval mechanism is matched and documented.

---

# 11. Technical Eligibility Test

Between 17 and 20 August 2026, each candidate pair will undergo a dry run.

The test will verify:

1. API and account access;
2. exact model identifiers;
3. current-model selection rule;
4. Frozen identifier persistence;
5. provider model-list metadata where available;
6. matched endpoint and prompt;
7. matched tools and retrieval;
8. matched reasoning/effort settings;
9. matched sampling and output settings;
10. independent-session execution;
11. ten-replication feasibility;
12. response capture and hashing;
13. rate-limit feasibility;
14. estimated annual cost;
15. known deprecation risk; and
16. terms-of-service compliance.

The test will use Pilot or dry-run prompts, not confirmatory outcome data.

---

# 12. Final Classification Form

Each candidate will receive one final pre-Wave-1 record.

| Field | Required entry |
|---|---|
| Service Lineage ID |  |
| Ecological Live Mode ID |  |
| Paired Live Mode ID |  |
| Frozen Mode ID |  |
| Live Reference model-selection rule |  |
| Frozen model identifier |  |
| Endpoint and API version |  |
| System-prompt hash |  |
| Harness commit hash |  |
| Tools/retrieval state |  |
| Sampling/reasoning settings |  |
| Expected availability |  |
| Known deprecation date |  |
| Material unmatched components |  |
| Final class | A / B / C / Not eligible |
| Permitted interpretation |  |
| Technical reviewer |  |
| Approval date |  |

A blank field prevents Class A classification.

---

# 13. Analysis Rules

## 13.1 Eligible observations

Only cells from pre-admitted pairs and the four registered English Anchor Items enter the primary Frozen–Live analysis.

## 13.2 Primary contrast

For each admitted pair and wave:

\[
\Delta_{\mathrm{FL},t}=Y^{L,\mathrm{API}}_t-Y^{F,\mathrm{API}}_t
\]

Where baseline differences exist, the preregistered baseline-adjusted contrast will also be used.

## 13.3 Interpretation

| Final class | Permitted wording |
|---|---|
| A | Model-update contrast |
| B | Deployment-update contrast, naming the unresolved components |
| C | Descriptive cross-condition difference |
| Not eligible | No confirmatory Frozen–Live contrast |

## 13.4 Public UI relationship

The ecological public UI trajectory will be analyzed separately.

Agreement between the UI Live line and the paired API Live Reference may strengthen an interpretation but does not make them the same observational condition.

---

# 14. Attrition and Downgrading

A Frozen pair will be reviewed when:

- the baseline model is deprecated;
- the model identifier is redirected;
- API behavior changes under the same identifier;
- a setting becomes unavailable;
- the Live and Frozen controls cease to match; or
- the provider changes relevant terms or access.

A pair may be downgraded prospectively from Class A to B or C.

A pair may not be upgraded after outcome inspection.

Data collected before a downgrade retain the class valid at the time, subject to later integrity review.

If fewer than two eligible pairs remain, the project will:

- continue the ecological Live panel;
- report Frozen-Line attrition;
- complete available descriptive analyses; and
- refrain from overstating L2 decomposition.

---

# 15. Prohibited Practices

The following are prohibited:

- calling UI–API differences model-update effects;
- selecting a Frozen model after viewing confirmatory outputs;
- silently changing the Frozen model;
- using a `latest` alias as Frozen;
- treating a renamed or redirected identifier as unchanged without verification;
- changing tools or retrieval in only one line;
- upgrading a pair’s class because the result appears persuasive;
- substituting a new baseline under the old Frozen ID; and
- claiming pure information-environment change from unmatched provider-native retrieval systems.

---

# 16. Release-Candidate Decision

The release-candidate plan is:

| Candidate | rc1 decision |
|---|---|
| Anthropic | Proceed to Class A technical test |
| Google | Proceed to Class A/Class B technical test |
| OpenAI | Proceed as reserve Class B candidate; promote only with pinning evidence |
| Perplexity | Ecological Live only; no v1.0 paired module |

This plan is designed to secure at least two defensible paired lineages without forcing an artificial Frozen condition on all four Core services.

---

# Appendix A. Official Technical Evidence Reviewed

The final Registry will preserve dated copies or archival records of the official documentation used in classification.

## Anthropic

Official documentation states that every Claude model ID is a pinned snapshot and explains the distinction between dated IDs and earlier aliases.

- https://platform.claude.com/docs/en/about-claude/models/overview

## Google

Official documentation distinguishes stable, preview, latest, and experimental model identifiers. It states that stable identifiers point to a specific stable model and that `latest` aliases may be hot-swapped.

- https://ai.google.dev/gemini-api/docs/models
- https://ai.google.dev/gemini-api/docs/deprecations

## OpenAI

Official documentation exposes specific model IDs and aliases. Final frozen eligibility depends on verification that the selected baseline identifier provides sufficiently fixed behavior and availability for the registered cycle.

- https://developers.openai.com/api/docs/models
- https://developers.openai.com/api/docs/deprecations

## Perplexity

Official documentation describes Sonar and Agent APIs as web-grounded and configurable systems. The first-year Registry does not treat an API configuration as a frozen counterfactual for the public Perplexity UI.

- https://docs.perplexity.ai/docs/getting-started/overview
- https://docs.perplexity.ai/docs/sonar/quickstart
- https://docs.perplexity.ai/docs/agent-api/quickstart

Documentation reviewed: 3 August 2026.

---

# Appendix B. Required Companion Revision

Before final preregistration, the following terminology should be reflected consistently in the companion documents:

- **Ecological Live:** public web-interface panel observation;
- **Paired Live Reference:** current API model under the fixed harness; and
- **Frozen Reference:** baseline API model under the same harness.

This is a clarification of observational mode, not the creation of additional panel members. All conditions remain linked to the same persistent Service Lineage ID.

---

# Appendix C. Final Approval Fields

| Field | Entry |
|---|---|
| Principal Investigator | To be completed |
| Methods Lead | To be completed |
| API/Technical Lead | To be completed |
| Terms-of-Service Review | To be completed |
| Anthropic final class | To be completed |
| Google final class | To be completed |
| OpenAI final class | To be completed |
| Eligible paired lineages | To be completed |
| Final approval date | To be completed |
| Effective date | 1 September 2026 |
| Final document SHA-256 | To be generated at final freeze |
