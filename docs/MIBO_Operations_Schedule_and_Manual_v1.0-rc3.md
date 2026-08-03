# MIBO Operations Schedule and Manual v1.0-rc3

## Field Procedures for the First Registered Annual Cycle

**Document status:** Integrated Release Candidate  
**Parent protocol:** MIBO Core Observatory Master Protocol v1.0-rc3  
**Parent service registry:** MIBO Service Registry v1.0-rc3  
**Parent instrument:** MIBO Fixed Query Instrument v1.0-rc3  
**Parent codebook:** MIBO Query Codebook v1.0-rc3  
**Authoritative language:** English  
**Manual date:** 3 August 2026  
**Planned effective date:** 1 September 2026  
**Planned final freeze date:** 27 August 2026  

---

# 1. Purpose

This Manual converts the MIBO Core Observatory Master Protocol into a fixed and executable first-year field procedure.

It specifies:

- the 12 monthly survey waves;
- the authoritative 48-hour field windows;
- the four calibration waves;
- Window A and Window B;
- ecological Live web-interface collection;
- paired API Live–Frozen collection;
- within-cell replication;
- randomization;
- retry and late-data rules;
- raw-data capture;
- quality control;
- mirror-site submission; and
- operational roles.

The Manual is intentionally limited to procedures necessary for reliable completion. Substantive coding and statistical analysis are governed by the Query Codebook and Statistical Analysis Plan.

---

# 2. Authoritative Time Standard

Coordinated Universal Time (**UTC**) is the authoritative time standard.

Japan Standard Time (**JST**) and mirror-site local times are operational translations only.

If a local-time conversion conflicts with the registered UTC schedule, the UTC schedule controls.

All execution systems must synchronize their clocks through an operating-system or institutional time service before each wave.

---

# 3. First-Year Survey-Wave Calendar

Each wave begins at 00:00 UTC on the first Tuesday of the month and closes 48 hours later.

| Wave ID | Field window starts UTC | Field window closes UTC | Starts JST | Closes JST | Calibration wave |
|---|---|---|---|---|---|
| MIBO-W01 | 1 Sep 2026, 00:00 | 3 Sep 2026, 00:00 | 1 Sep 2026, 09:00 | 3 Sep 2026, 09:00 | Yes |
| MIBO-W02 | 6 Oct 2026, 00:00 | 8 Oct 2026, 00:00 | 6 Oct 2026, 09:00 | 8 Oct 2026, 09:00 | No |
| MIBO-W03 | 3 Nov 2026, 00:00 | 5 Nov 2026, 00:00 | 3 Nov 2026, 09:00 | 5 Nov 2026, 09:00 | No |
| MIBO-W04 | 1 Dec 2026, 00:00 | 3 Dec 2026, 00:00 | 1 Dec 2026, 09:00 | 3 Dec 2026, 09:00 | Yes |
| MIBO-W05 | 5 Jan 2027, 00:00 | 7 Jan 2027, 00:00 | 5 Jan 2027, 09:00 | 7 Jan 2027, 09:00 | No |
| MIBO-W06 | 2 Feb 2027, 00:00 | 4 Feb 2027, 00:00 | 2 Feb 2027, 09:00 | 4 Feb 2027, 09:00 | No |
| MIBO-W07 | 2 Mar 2027, 00:00 | 4 Mar 2027, 00:00 | 2 Mar 2027, 09:00 | 4 Mar 2027, 09:00 | Yes |
| MIBO-W08 | 6 Apr 2027, 00:00 | 8 Apr 2027, 00:00 | 6 Apr 2027, 09:00 | 8 Apr 2027, 09:00 | No |
| MIBO-W09 | 4 May 2027, 00:00 | 6 May 2027, 00:00 | 4 May 2027, 09:00 | 6 May 2027, 09:00 | No |
| MIBO-W10 | 1 Jun 2027, 00:00 | 3 Jun 2027, 00:00 | 1 Jun 2027, 09:00 | 3 Jun 2027, 09:00 | Yes |
| MIBO-W11 | 6 Jul 2027, 00:00 | 8 Jul 2027, 00:00 | 6 Jul 2027, 09:00 | 8 Jul 2027, 09:00 | No |
| MIBO-W12 | 3 Aug 2027, 00:00 | 5 Aug 2027, 00:00 | 3 Aug 2027, 09:00 | 5 Aug 2027, 09:00 | No |

The registered dates are not moved because of weekends, holidays, unusual findings, or partial service outages.

A change to a field window requires a prospective protocol amendment before the affected wave begins, except where immediate legal, ethical, or safety suspension is necessary.

---

# 4. Field-Window Structure

## 4.1 Standard waves

For non-calibration waves, all required Core observations must be submitted within the 48-hour field window.

The exact execution time of every observation is recorded.

## 4.2 Calibration waves

Calibration waves contain two adjacent 12-hour observation windows:

| Window | Relative time | UTC interval |
|---|---|---|
| **Window A** | Hours 0–12 | Wave start to Wave start + 12 hours |
| **Window B** | Hours 24–36 | Wave start + 24 hours to Wave start + 36 hours |

The interval between the start of Window A and the start of Window B is exactly 24 hours.

The final 12 hours of the 48-hour field window remain available for:

- completing non-calibration Core items;
- documented operational retries;
- integrity checks; and
- resolving capture failures.

No valid Window A or Window B observation may be moved outside its designated 12-hour interval.

## 4.3 Japan-site data reuse

At the Japan coordinating site, the following Window A observations serve simultaneously as ordinary Core observations:

> **English Anchor Item × Ecological Live UI × Japan site**

They must not be collected twice under nominally identical conditions.

Window B is an additional calibration observation.

---

# 5. Expected First-Year Observation Structure

## 5.1 Ecological Live Core

For each ordinary wave:

\[
4\text{ service lineages}
\times 12\text{ items}
\times 2\text{ languages}
\times 10\text{ replications}
=960\text{ intended observations}
\]

These are public web-interface observations at the coordinating site in Japan.

## 5.2 Calibration addition at the Japan site

For each calibration wave, Window B adds:

\[
4\text{ service lineages}
\times 4\text{ English Anchor Items}
\times 10\text{ replications}
=160\text{ additional observations}
\]

Window A Anchor observations are already included in the standard 960 Core observations.

## 5.3 International mirror-site calibration

Each participating international site collects, per calibration wave:

\[
4\text{ service lineages}
\times 4\text{ English Anchor Items}
\times 2\text{ windows}
\times 10\text{ replications}
=320\text{ intended observations}
\]

## 5.4 Paired API module

For each admitted paired provider and monthly wave:

\[
4\text{ English Anchor Items}
\times 2\text{ Lines}
\times 10\text{ replications}
=80\text{ intended observations}
\]

With two admitted providers, the paired module contains 160 intended observations per wave. With three, it contains 240.

The paired API module is conducted by the coordinating observatory unless an amendment states otherwise.

---

# 6. Operational Roles

The first-year operation requires four functional roles.

## 6.1 Operations Lead

The Operations Lead:

- confirms the wave schedule;
- verifies readiness;
- approves the randomization manifests;
- coordinates interruptions;
- classifies operational deviations; and
- signs the wave-completion record.

## 6.2 Service Operator

A Service Operator:

- uses the registered dedicated account;
- executes the exact web-interface procedure;
- captures the full response and displayed sources;
- records the required metadata; and
- reports deviations immediately.

One operator may be assigned to each service lineage. An operator may cover more than one lineage when workload permits.

## 6.3 API and Technical Lead

The API and Technical Lead:

- maintains the fixed paired harness;
- verifies model identifiers;
- executes paired Live–Frozen blocks;
- preserves raw API responses;
- records software and configuration hashes; and
- reports Frozen-Line contamination or attrition.

## 6.4 Data Steward

The Data Steward:

- validates identifiers;
- checks file completeness and hashes;
- preserves the raw-data manifest;
- conducts the operational integrity audit; and
- freezes the wave package.

One person may hold multiple roles, but the final operational audit should be performed or independently reviewed by someone other than the original collector where feasible.

Each mirror site identifies a local Site Lead who assumes the equivalent local responsibilities.

---

# 7. Pre-Wave Readiness Procedure

The readiness procedure begins no later than 24 hours before every wave.

The Operations Lead confirms:

1. the UTC field-window dates;
2. dedicated-account access;
3. registered account tiers;
4. memory and personalization settings;
5. absence of custom instructions;
6. registered model or mode;
7. retrieval, search, and tool state;
8. ability to start independent sessions;
9. current rate and usage limits;
10. available data-storage capacity;
11. time synchronization;
12. current terms-of-service or access restrictions;
13. known provider configuration announcements;
14. API model identifiers and availability;
15. the wave randomization manifest; and
16. operator availability.

The readiness record is completed before any confirmatory observation is submitted.

A failed readiness item must be:

- resolved before collection;
- documented as a known deviation; or
- escalated for suspension of the affected condition.

No confirmatory prompt is used for informal readiness testing.

---

# 8. Randomization and Counterbalancing

## 8.1 Reproducible random seed

Each execution manifest uses a reproducible seed derived from:

```text
SHA-256("MIBO-v1.0|<Wave ID>|<Site ID>|<Mode ID>")
```

The first eight hexadecimal characters are converted to an integer seed.

The generated manifest is saved before data collection and may not be regenerated after outcomes are inspected.

## 8.2 Ecological Live UI order

For each service lineage:

- query forms are executed in a randomized order;
- language order is mixed rather than fixed;
- every replication uses a new session; and
- the ten replications for a cell occur within the registered field window.

The preferred ordinary-wave structure is ten execution rounds. Each round contains one administration of each of the 24 Query Forms in randomized order.

This produces:

\[
10\text{ rounds} \times 24\text{ forms} = 240
\]

observations per service lineage.

A round is an execution organization device, not a conversational context. Every administration remains a new independent session.

## 8.3 Calibration-wave adjustment

During a calibration wave:

1. all ten replications of each English Anchor Item are completed during Window A;
2. the remaining 20 Query Forms are completed in randomized rounds during the 48-hour field window; and
3. all ten replications of each English Anchor Item are repeated during Window B.

The English Anchor Items are not repeated elsewhere in the same wave.

## 8.4 Paired API order

For each:

> **Provider × Anchor Item × Wave**

the API harness creates a 20-call randomized block containing:

- 10 Paired Live Reference calls; and
- 10 Frozen Reference calls.

The two Lines are interleaved according to the saved randomization manifest.

The block should be completed within two hours.

The principal analysis compares the two distributions. Replication numbers do not imply one-to-one matched output pairs.

---

# 9. Ecological Live Web-Interface Procedure

For every intended UI observation:

1. Confirm the Service Lineage ID and registered account.
2. Confirm the registered mode and settings.
3. Start a new conversation.
4. Confirm that no prior text or uploaded file is present.
5. Paste or enter the exact registered Query Form.
6. Submit once.
7. Do not add a follow-up, correction, or clarification.
8. Allow the response to finish.
9. Capture the full rendered response.
10. Capture all displayed citations, source cards, and links.
11. Save the response text in UTF-8 where possible.
12. Record the timestamp and required metadata.
13. Generate or record the raw-output hash.
14. Close or archive the session.
15. Proceed to the next item in the saved manifest.

The operator may scroll to capture the complete response.

The operator shall not:

- click a suggested follow-up;
- ask the service to continue;
- edit the prompt after submission;
- activate an unregistered tool;
- choose a different model because the answer is poor; or
- repeat a valid refusal.

If the service requests clarification, the request is captured as a valid outcome. No clarification is supplied unless an item-specific preregistered rule exists.

---

# 10. Paired API Procedure

For each admitted provider:

1. Verify the harness commit and environment lock.
2. Verify the API project and region.
3. retrieve or record available model metadata where supported;
4. confirm the Paired Live Reference model rule;
5. confirm the Frozen Reference identifier;
6. confirm identical system instructions;
7. confirm tools and retrieval are disabled;
8. confirm matched reasoning, effort, sampling, and output settings;
9. load the exact English Anchor Query Form;
10. execute the saved 20-call randomized block;
11. preserve the complete raw API response;
12. record response metadata and model identifiers;
13. record all errors and retries;
14. hash the raw file; and
15. complete the pair-integrity checklist.

A material unmatched condition requires immediate review of the pair’s Class A/B/C status.

The harness shall not be edited during a wave except to repair a technical defect that prevents execution. Any repair creates a recorded technical deviation and a new commit hash.

---

# 11. Response Capture Standard

## 11.1 UI observations

Every valid UI observation requires:

- exact query text;
- copied or exported response text where technically possible;
- complete rendered capture as image, PDF, or equivalent;
- displayed source titles and URLs;
- visible service/model/mode indicators where available;
- timestamp;
- Observation ID; and
- raw-output hash.

A rendered capture is required because copied text may omit citation placement, source cards, or interface indicators.


For registered response-length variables:

- English length is measured as whitespace-delimited words; and
- Japanese length is measured as Unicode characters excluding whitespace and line breaks.

These measures are descriptive and do not invalidate an otherwise valid response that exceeds the requested limit.

## 11.2 API observations

Every API observation requires:

- exact request payload, excluding credentials;
- complete raw response;
- HTTP or SDK status;
- returned model metadata;
- timing information;
- usage metadata where available;
- error record where applicable;
- Observation ID; and
- file hash.

## 11.3 Configuration captures

For every service lineage and wave, capture the relevant interface settings:

- once before the first observation; and
- once after the last observation.

If a material setting changes during the wave, capture it immediately and create a Configuration Event record.

---

# 12. File and Directory Structure

The standard structure is:

```text
MIBO/
  protocol_version/
    site_id/
      wave_id/
        manifests/
        configuration/
        ui_raw/
        api_raw/
        metadata/
        failures/
        deviations/
        audit/
        release/
```

UI raw files should use:

```text
<Observation ID>.<extension>
```

API raw files should use:

```text
<Observation ID>.json
```

No file is silently overwritten.

A corrected capture receives a new file version while preserving the original.

---

# 13. Observation and Attempt Identifiers

An **Attempt ID** is assigned before submission.

A valid output later receives or retains its linked **Observation ID**.

The identifier must encode or link to:

- Site ID;
- Wave ID;
- Service Lineage ID;
- Mode or Line ID;
- Item ID;
- Query Form ID;
- Window ID;
- Replication number; and
- attempt number.

Example:

```text
MIBO-SITE-JP01-W01-SL002-LUI-I03-EN-STD-R04-A01
```

A retry receives a new Attempt ID but remains linked to the same intended replication.

Identifiers are never renumbered because an attempt failed.

---

# 14. Technical Failure and Retry Rule

## 14.1 Retry-eligible failures

Retries are permitted for:

- confirmed submission failure;
- provider error;
- timeout;
- authentication interruption;
- rate limit;
- incomplete generation caused by technical interruption;
- corrupted capture; or
- temporary interface failure.

A valid refusal, safety response, nonanswer, or clarification request is not retry eligible.

## 14.2 Maximum retries

A maximum of two retries is permitted for each intended replication.

The standard schedule is:

1. **Retry 1:** after at least 10 minutes;
2. **Retry 2:** after at least an additional 30 minutes.

When a provider specifies a longer mandatory wait, the provider’s limit controls, provided the retry remains inside the registered field window.

## 14.3 Service-wide outage

When a service-wide outage is apparent, operators do not repeatedly submit every intended observation.

The Operations Lead pauses the affected lineage and schedules one documented recovery block later in the field window.

## 14.4 Retry outcome

If all permitted attempts fail:

- the replication remains missing;
- all attempts remain in the failure log; and
- no synthetic or duplicated output is inserted.

---

# 15. Validity Decisions During Collection

Operators make only procedural validity decisions during collection.

They may determine whether:

- the exact query was submitted;
- the correct account and mode were used;
- the session was new;
- the response completed technically;
- the response was captured; and
- a retry is operationally permitted.

Operators do not judge whether the answer is:

- correct;
- representative;
- persuasive;
- biased;
- high quality; or
- consistent with a hypothesis.

Substantive coding occurs after the raw wave package is frozen.

---

# 16. Field-Window and Late-Data Rule

## 16.1 Primary data

Only observations submitted within the registered 48-hour field window are eligible for the primary monthly Core dataset.

Calibration observations must additionally fall inside Window A or Window B.

## 16.2 Late supplementary data

A technically justified observation may be submitted up to 24 hours after field-window closure only when:

- the intended observation was attempted during the field window;
- the failure was documented;
- the late collection was approved by the Operations Lead; and
- the observation is marked **late supplementary**.

Late supplementary data do not replace missing primary observations and do not enter the primary confirmatory analysis unless the Statistical Analysis Plan explicitly permits a sensitivity analysis.

## 16.3 No retrospective wave shifting

After the 24-hour supplementary period, no new observation is collected under the closed Wave ID.

A later measurement must receive a supplementary Event Observation ID or belong to the next registered wave.

---

# 17. Paired-Condition Timing Rule

A paired API 20-call block should be completed within two hours.

If the block exceeds two hours:

- retain all valid calls;
- flag the block for timing deviation; and
- evaluate whether the pair remains eligible for primary comparison.

The Paired Live and Frozen conditions must not be collected on different days and treated as a synchronized pair.

Public UI observations have no direct pairwise timing relationship with the API Frozen condition.

---

# 18. Configuration Events During a Wave

If a material interface or model change is detected during collection:

1. pause new observations for the affected condition;
2. record the last known prior-state observation;
3. capture the new configuration;
4. notify the Operations Lead;
5. classify the event;
6. determine whether collection may continue; and
7. flag observations as pre-event or post-event where possible.

Valid pre-event observations are not deleted.

A wave may contain a documented configuration boundary. The Statistical Analysis Plan will determine its analytical treatment.

---

# 19. Quality Control Before Wave Freeze

The Data Steward completes the following checks.

## 19.1 Structural checks

- all expected manifest rows are present;
- identifiers are unique;
- Query Form IDs match the submitted text;
- timestamps fall within the permitted window;
- replication numbers are valid;
- service and mode identifiers are valid;
- files exist for every retained observation;
- hashes resolve to the retained files;
- retries are linked to original attempts; and
- missingness codes are complete.

## 19.2 Operational integrity audit

A stratified 5% sample of retained UI and API observations is checked against:

- new-session evidence;
- exact query wording;
- rendered or raw response;
- source capture;
- settings;
- timestamp; and
- metadata.

This 5% operational audit is separate from the 10% human audit of AI-assisted semantic coding.

## 19.3 Error correction

A metadata or file-link error may be corrected before wave freeze.

The original value and correction are preserved in the correction log.

A valid response is not recollected because of an inconvenient substantive result.

---

# 20. Wave Completion Classification

A wave is classified as:

## Complete

- every planned primary cell reaches 10 valid replications; and
- all required operational records are present.

## Complete with documented missing cells

- at least 90% of intended primary observations are valid;
- no lineage is completely unobserved; and
- all missingness is documented.

## Partially completed

- some valid confirmatory data exist, but:
  - fewer than 90% of intended observations are valid;
  - one or more lineages are entirely missing; or
  - a material integrity problem affects a substantial portion of the wave.

## Not completed

- no usable confirmatory wave dataset was obtained; or
- critical protocol failure makes the wave uninterpretable.

Completion status does not determine whether unusual results are publishable.

---

# 21. Wave Freeze and Release Package

The internal wave package should be frozen within seven calendar days of field-window closure.

The package contains:

- execution manifests;
- configuration records;
- raw UI and API files;
- observation metadata;
- failure and retry logs;
- missingness record;
- deviation log;
- operational audit;
- file-hash manifest; and
- signed Wave Completion Record.

After freeze:

- raw files are immutable;
- metadata corrections require a versioned correction;
- substantive coding is performed on a derived analysis copy; and
- no confirmatory observation is added silently.

The public-release schedule is governed by the Master Protocol and may differ from the internal freeze date.

---

# 22. Mirror-Site Procedure

Every mirror site follows Sections 2, 4, 6, 7, 8, 9, and 11–21 for the four English Anchor Items during calibration waves.

Each mirror site must:

1. complete the dry run before its first confirmatory calibration;
2. use the registered Kit version;
3. use dedicated research accounts;
4. collect Window A and Window B independently;
5. preserve its local raw records;
6. complete local quality checks; and
7. submit or register the site package within seven calendar days of field-window closure.

The Japan coordinating observatory may check procedural completeness but may not require recollection of a valid divergent response.

---

# 23. Data Transfer and Submission

A site submission package contains:

- observation-level metadata;
- required derived variables, if already coded;
- missingness record;
- retry log;
- deviation log;
- configuration summary;
- local file-hash manifest; and
- Site Lead attestation.

Raw outputs are transferred only when legally, contractually, ethically, and institutionally permitted.

Where raw transfer is not permitted, the site retains the raw data and supplies the approved derived data, provenance metadata, and hashes.

---

# 24. Interim Review

Operational metrics may be reviewed after every wave, including:

- completion rate;
- service failure rate;
- rate-limit burden;
- capture problems;
- storage use;
- deviation frequency; and
- operator workload.

Confirmatory outcome patterns are not used to alter:

- the fixed instrument;
- replication count;
- panel membership;
- Anchor outcomes;
- Frozen baseline; or
- analysis thresholds

during the registered annual cycle.

A safety, legal, or technical necessity may require amendment under the Master Protocol.

---

# 25. Security and Credential Handling

Credentials, API keys, cookies, recovery codes, and billing details are never stored in the public or analytical dataset.

They must be held in approved credential-management systems.

Raw captures must be reviewed before public release for:

- personal account identifiers;
- private conversation history;
- access tokens;
- email addresses;
- billing information; and
- other unintended sensitive information.

No operator shares credentials across independent institutions unless formally authorized.

---

# 26. Prohibited Operational Practices

The following are prohibited:

- changing the fixed query to improve an answer;
- collecting in a continuing conversation;
- using a personal account with unrelated history;
- manually selecting a preferred model during a default-mode observation;
- retrying a valid refusal;
- stopping a cell early after apparent convergence;
- adding extra replications only to surprising cells;
- replacing a missing response with a duplicate;
- collecting Window B outside its registered interval;
- changing the Frozen model without a new Line ID;
- regenerating a randomization manifest after seeing outputs;
- deleting failed attempts;
- coding substantive outcomes before the raw wave package is frozen; and
- moving a wave to avoid unfavorable or inconvenient conditions.

---

# 27. Pre-Wave Checklist

```text
[ ] UTC clock synchronized
[ ] Wave and field-window dates confirmed
[ ] Dedicated accounts accessible
[ ] Account tiers verified
[ ] Memory/personalization verified
[ ] Custom instructions absent
[ ] Registered UI modes verified
[ ] Search/tool conditions verified
[ ] API identifiers verified
[ ] Frozen identifiers verified
[ ] Harness commit verified
[ ] Storage available
[ ] Randomization manifests generated and locked
[ ] Operators assigned
[ ] Mirror sites confirmed, where applicable
[ ] Terms/access review complete
[ ] Readiness record signed
```

---

# 28. Post-Wave Checklist

```text
[ ] All manifests reconciled
[ ] Valid and failed attempts counted
[ ] Missingness codes complete
[ ] Raw UI captures present
[ ] Raw API responses present
[ ] Source links captured
[ ] Configuration captures present
[ ] File hashes verified
[ ] Retry log complete
[ ] Deviation log complete
[ ] 5% operational audit complete
[ ] Wave completion status assigned
[ ] Wave package frozen
[ ] Mirror submission received or status recorded
[ ] Wave Completion Record signed
```

---

# 29. First-Year Operating Principle

The first-year operation follows one governing rule:

> **Complete the small registered panel exactly as planned, preserve every failure, and do not improve the protocol retrospectively in response to the observed results.**

Operational efficiency may improve through better staffing, compliant automation, capture tools, and error checking, provided that the registered observation conditions remain unchanged.

---

# Appendix A. Calibration-Wave Windows

| Calibration wave | Window A UTC | Window B UTC | Window A JST | Window B JST |
|---|---|---|---|---|
| MIBO-W01 | 1 Sep 2026 00:00–12:00 | 2 Sep 2026 00:00–12:00 | 1 Sep 09:00–21:00 | 2 Sep 09:00–21:00 |
| MIBO-W04 | 1 Dec 2026 00:00–12:00 | 2 Dec 2026 00:00–12:00 | 1 Dec 09:00–21:00 | 2 Dec 09:00–21:00 |
| MIBO-W07 | 2 Mar 2027 00:00–12:00 | 3 Mar 2027 00:00–12:00 | 2 Mar 09:00–21:00 | 3 Mar 09:00–21:00 |
| MIBO-W10 | 1 Jun 2027 00:00–12:00 | 2 Jun 2027 00:00–12:00 | 1 Jun 09:00–21:00 | 2 Jun 09:00–21:00 |

---

# Appendix B. Required Operational Records

The following templates will be included in the MIBO Mirror Observatory Kit:

1. Pre-Wave Readiness Record
2. Execution Manifest
3. Configuration Capture Record
4. Attempt and Retry Log
5. Missingness Record
6. Protocol Deviation Form
7. Configuration Event Form
8. Operational Integrity Audit Form
9. Wave Completion Record
10. Site Lead Attestation
11. File-Hash Manifest

---

# Appendix C. Final Approval Fields

| Field | Entry |
|---|---|
| Principal Investigator | To be completed |
| Operations Lead | To be completed |
| Data Steward | To be completed |
| API/Technical Lead | To be completed |
| Mirror Coordination Lead | To be completed |
| Dry-run completion date | To be completed |
| Final approval date | To be completed |
| Effective date | 1 September 2026 |
| Final document SHA-256 | To be generated at final freeze |
