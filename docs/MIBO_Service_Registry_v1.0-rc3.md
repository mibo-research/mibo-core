# MIBO Service Registry v1.0-rc3

## Sentinel Panel of Public Generative-AI Service Lineages

**Document status:** Integrated Release Candidate  
**Parent protocol:** MIBO Core Observatory Master Protocol v1.0-rc3  
**Authoritative language:** English  
**Registry date:** 3 August 2026  
**Planned effective date:** 1 September 2026  
**Planned final freeze date:** 20 August 2026  

---

## 1. Purpose

This Registry identifies the initial sentinel panel units to be followed by the MIBO Core Observatory during its first registered annual cycle.

The Registry serves four purposes:

1. to assign persistent Service Lineage IDs;
2. to document why each lineage was selected;
3. to specify the standard Live observation condition; and
4. to record the provisional availability and comparability of Frozen Lines.

The panel is a purposive sentinel panel. It is not a probability sample of all generative-AI systems.

---

## 2. Initial Sentinel Panel

The first-year Core panel will consist of four major public generative-AI service lineages.

| Service Lineage ID | Registered lineage | Provider | Primary role in the sentinel panel | Status |
|---|---|---|---|---|
| MIBO-SL-001 | ChatGPT | OpenAI | Large-scale general-purpose conversational service with evolving model and tool deployment | Selected |
| MIBO-SL-002 | Claude | Anthropic | General-purpose conversational service with visible model and reasoning controls | Selected |
| MIBO-SL-003 | Gemini | Google | General-purpose service embedded in a large search and information ecosystem | Selected |
| MIBO-SL-004 | Perplexity | Perplexity AI | Search-native answer service with routine web retrieval and citation presentation | Selected |

These four lineages are selected because they:

- were included in the MIBO Pilot;
- provide continuity between the developmental and confirmatory phases;
- represent four distinct providers;
- are publicly accessible in Japan;
- support repeated independent text sessions;
- are internationally available or relevant;
- differ meaningfully in retrieval, model routing, citation, and interface architecture; and
- can be observed without expanding the initial panel beyond an operationally manageable size.

Selection does not imply that the four services statistically represent all generative-AI systems or that they are the four highest-performing systems.

---

## 3. Persistent Identification Rule

A Service Lineage ID refers to the continuing public service lineage, not to a particular model version.

The same Service Lineage ID will ordinarily be retained when the provider changes:

- the displayed model;
- the model generation;
- retrieval or browsing behavior;
- tools;
- safety policies;
- routing;
- interface design;
- account features; or
- product branding,

provided that the service remains a defensibly continuous public answering service.

Each monthly wave will separately record the observed **Deployed Answering Configuration**.

---

## 4. Common Live-Line Observation Standard

Unless a lineage-specific exception is entered below, the primary Live observation will use:

| Field | Registered standard |
|---|---|
| Observation surface | Public web interface |
| Account | Dedicated research account |
| Account class | Publicly available paid individual tier |
| Geographic condition | Japan |
| Interface language | Recorded at every wave |
| Query languages | Japanese and English |
| Conversation state | New conversation for every replication |
| Prior history | None |
| Custom instructions | None |
| Memory | Disabled where technically possible |
| Personalization | Disabled where technically possible |
| Connected private data | None |
| Uploaded files | None |
| Manual tool activation | None unless required by the registered item |
| Search or retrieval | Provider-default or automatic behavior of the registered mode |
| Model selection | Registered general-purpose default mode or named continuing mode |
| Reasoning or effort setting | Registered standard/default level |
| Output intervention | No clarification, correction, or follow-up by the researcher |
| Replications | 10 valid independent sessions per required cell |

The exact plan name, visible mode, settings, and interface state will be captured in the Configuration Freeze Record before Wave 1.

A provider update to the current Live configuration will be recorded as a Configuration Event, not treated automatically as a protocol deviation.

---

## 5. Lineage Records

### 5.1 MIBO-SL-001 — ChatGPT

| Field | Registry entry |
|---|---|
| Registered service lineage | ChatGPT |
| Provider | OpenAI |
| Live Line ID | MIBO-SL-001-L |
| Primary surface | ChatGPT web interface |
| Provisional account tier | ChatGPT Plus or the equivalent registered paid individual tier |
| Registered mode | General-purpose default/continuing text mode, finalized at configuration freeze |
| Retrieval condition | Provider-default or automatically invoked behavior; no manual search activation unless specified by an item |
| Personalization | Disabled where available |
| Pilot continuity | Yes |
| Frozen Line candidate | Yes |
| Provisional Frozen Line ID | MIBO-SL-001-F |
| Frozen implementation candidate | Version-pinned OpenAI API model under a fixed research harness |
| Provisional comparability class | Class B unless a same-harness Live API reference is separately registered |
| Principal continuity risk | Rapid changes in default routing, tools, and visible model availability |

**Selection rationale:** ChatGPT is retained as a core sentinel lineage because of its public prominence, continued presence in the MIBO Pilot, and frequent changes in model and product configuration that are directly relevant to longitudinal service observation.

---

### 5.2 MIBO-SL-002 — Claude

| Field | Registry entry |
|---|---|
| Registered service lineage | Claude |
| Provider | Anthropic |
| Live Line ID | MIBO-SL-002-L |
| Primary surface | Claude web interface |
| Provisional account tier | Claude Pro or the equivalent registered paid individual tier |
| Registered mode | Continuing general-purpose Claude model family and standard effort setting, finalized at configuration freeze |
| Retrieval condition | Provider-default behavior; web search not manually enabled unless included in the registered mode |
| Personalization | Disabled or minimized where available |
| Pilot continuity | Yes |
| Frozen Line candidate | Yes |
| Provisional Frozen Line ID | MIBO-SL-002-F |
| Frozen implementation candidate | Version-identified Claude API model under a fixed research harness |
| Provisional comparability class | Class B unless a same-harness Live API reference is separately registered |
| Principal continuity risk | Model retirement and changes to model, effort, thinking, and search controls |

**Selection rationale:** Claude is retained because it provides a distinct provider lineage, visible model-selection controls, and a contrasting deployment architecture while preserving continuity with the Pilot.

---

### 5.3 MIBO-SL-003 — Gemini

| Field | Registry entry |
|---|---|
| Registered service lineage | Gemini |
| Provider | Google |
| Live Line ID | MIBO-SL-003-L |
| Primary surface | Gemini web interface |
| Provisional account tier | Google AI Pro or the equivalent registered paid individual tier |
| Registered mode | General-purpose default/continuing Gemini text mode, finalized at configuration freeze |
| Retrieval condition | Provider-default integration with current information resources |
| Personalization | Disabled or minimized where available |
| Pilot continuity | Yes |
| Frozen Line candidate | Yes |
| Provisional Frozen Line ID | MIBO-SL-003-F |
| Frozen implementation candidate | Stable version-identified Gemini API model under a fixed research harness |
| Provisional comparability class | Class B unless a same-harness Live API reference is separately registered |
| Principal continuity risk | Changes in mode naming, model routing, regional availability, and information integration |

**Selection rationale:** Gemini is retained because it represents a major provider with close integration into a large-scale information ecosystem and offers a distinct environment for observing retrieval-sensitive behavior.

---

### 5.4 MIBO-SL-004 — Perplexity

| Field | Registry entry |
|---|---|
| Registered service lineage | Perplexity |
| Provider | Perplexity AI |
| Live Line ID | MIBO-SL-004-L |
| Primary surface | Perplexity web interface |
| Provisional account tier | Perplexity Pro or the equivalent registered paid individual tier |
| Registered mode | Standard general-purpose answer/search mode with provider routing, finalized at configuration freeze |
| Retrieval condition | Native web search and citation behavior |
| Personalization | Disabled or minimized where available |
| Pilot continuity | Yes |
| Frozen Line candidate | No primary Frozen Line planned for v1.0 |
| Frozen Line ID | Not assigned at registry freeze unless technical comparability is demonstrated |
| Principal continuity risk | Dynamic routing across underlying models and continuing changes to search, ranking, and citation systems |

**Selection rationale:** Perplexity is retained as the search-native sentinel lineage. Its inclusion ensures that the panel is not limited to conversational systems whose access to current information is optional or secondary.

---

## 6. Frozen-Line Decision Rule

A provisional Frozen candidate will be admitted to the confirmatory Frozen–Live analysis only after a pre-Wave-1 technical assessment confirms:

1. a persistent and verifiable model identifier;
2. a stable execution harness;
3. documented system and decoding conditions;
4. documented retrieval and tool conditions;
5. reasonable expected availability during the registered cycle;
6. a defensible relationship to the associated Live lineage; and
7. completion of a dry run using the registered query procedure.

Each admitted pair will be classified prospectively in the **MIBO Frozen–Live Comparability Registry v1.0** as:

- **Class A — model-comparable pair;**
- **Class B — deployment-comparable pair;** or
- **Class C — descriptive reference pair.**

No pair will be promoted to a stronger class after outcome inspection.

The Core Observatory will aim to retain at least two valid Frozen Lines during the first annual cycle. Failure to do so will restrict the dual-line estimands but will not invalidate the four-member Live sentinel panel.

---

## 7. Configuration Freeze Procedure

Between 17 and 20 August 2026, the research team will verify every lineage using the dedicated research account.

For each service, the freeze record will capture:

- current plan name;
- country and billing region;
- web interface URL;
- displayed service and model/mode names;
- default model or continuing mode;
- reasoning/effort setting;
- search, browsing, and tool state;
- memory and personalization settings;
- relevant privacy settings;
- ability to open independent sessions;
- rate and usage constraints;
- screenshot evidence;
- terms-of-service review date;
- date and time of verification; and
- verifier identity.

The exact state will be stored in:

> **MIBO Live Configuration Freeze Record v1.0**

A file hash will be generated after final approval.

---

## 8. Attrition and Refreshment

The four Service Lineage IDs are fixed for the first registered annual cycle.

A lineage that becomes temporarily inaccessible will remain in the panel and receive a missingness status.

A lineage will be classified as attrited only under the rules in the Master Protocol.

No new service will retrospectively replace an attrited panel member.

A newly important service may be observed as a **Supplementary Refreshment Sample**, but it will receive a new ID and remain outside the primary first-year confirmatory panel unless a preregistered amendment states otherwise.

Formal reconsideration of panel membership will occur at the annual panel review.

---

## 9. Services Not Included in the Initial Core Panel

The exclusion of another major service does not imply that it is scientifically unimportant.

The first-year panel is capped at four lineages to preserve feasibility, fixed-panel continuity, and completion quality.

Other services may be considered for:

- Supplementary Refreshment Samples;
- MIBO Sub-Observatories;
- MIBO-NOW;
- regional Local Extensions; or
- the second registered annual panel cycle.

In particular, services whose distinctive contribution concerns real-time social sensing may be better evaluated initially within MIBO-NOW than by expanding the Core panel.

---

## 10. Registry Change Control

Before the final freeze date, corrections to this release candidate may be made through documented revision.

After the Registry becomes effective:

- Service Lineage IDs may not be reassigned;
- selection rationales may not be rewritten to match observed outcomes;
- observation modes may change only through a recorded Configuration Event or protocol amendment;
- Frozen comparability classes may not be strengthened after outcome inspection; and
- all corrections will create a new archived registry version.

The final document will be titled:

> **MIBO Service Registry v1.0**

and will include:

- approval date;
- effective date;
- approving investigators;
- repository location;
- official verification records; and
- SHA-256 file hash.

---

## Appendix A. Official Sources Used for Pre-Freeze Verification

The final Registry will attach archived or dated verification records. The release-candidate selection was informed by the following official service and documentation pages:

- [ChatGPT Plus](https://help.openai.com/en/articles/6950777-what-is-chatgpt-plus)
- [ChatGPT release notes](https://help.openai.com/en/articles/6825453-chatgpt-release-notes)
- [OpenAI API models](https://developers.openai.com/api/docs/models)
- [Claude plans](https://support.anthropic.com/en/articles/11049762-choosing-a-claude-ai-plan)
- [Claude model settings](https://support.anthropic.com/en/articles/8664678-how-can-i-change-the-model-version-that-i-m-chatting-with)
- [Claude model documentation](https://docs.anthropic.com/en/docs/about-claude/models/overview)
- [Google AI Pro](https://support.google.com/googleone/answer/16476811)
- [Gemini API models](https://ai.google.dev/gemini-api/docs/models)
- [Gemini model deprecations](https://ai.google.dev/gemini-api/docs/deprecations)
- [Perplexity](https://www.perplexity.ai/)
- [Perplexity Pro](https://www.perplexity.ai/pro)
- [Perplexity product overview](https://www.perplexity.ai/hub)

---

## Appendix B. Final Approval Fields

| Field | Entry |
|---|---|
| Principal Investigator | To be completed |
| Methods Lead | To be completed |
| Data/Operations Lead | To be completed |
| Terms-of-Service Review | To be completed |
| Frozen-Line Technical Review | To be completed |
| Final approval date | To be completed |
| Effective date | 1 September 2026 |
| SHA-256 | To be generated at final freeze |
