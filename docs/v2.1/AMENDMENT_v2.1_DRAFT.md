# MIBO Core Three-Series Prospective Amendment — v2.1 DRAFT

Prepared: 7 November 2026. Status: unregistered draft; owner selected W03.
Owner-confirmed author metadata (7 November 2026): Kento Sasano (笹埜健斗),
ORCID [0009-0009-3853-8029](https://orcid.org/0009-0009-3853-8029).
Affiliations: Okayama University; Keio Research Institute at SFC, Keio University.
Document version: `2.1-draft`; scientific protocol version: `2.1`.
This is not a signed operations authorization.

## 1. Authority and reason

Parent: [Core Protocol Package v2.0](https://doi.org/10.5281/zenodo.22264635).
Frozen instrument and inherited Codebook/SAP:
[Core Package v1.0](https://doi.org/10.5281/zenodo.21936410).
The owner directed removal of Perplexity from the prospective Core panel and
adoption of three-family reciprocal AI scoring with common calibration, to
make operation feasible for a single researcher. This changes the scientific
panel and coding procedure; it is not a software-only repair or a statement
that v1.0/v2.0 human-reference requirements have already been satisfied.

## 2. Prospective panel and condition

The only future active Core lineages are MIBO-SL-001 (OpenAI/ChatGPT lineage),
MIBO-SL-002 (Anthropic/Claude), and MIBO-SL-003 (Google/Gemini).
These are first-party provider API observations, not consumer ChatGPT/Claude/
Gemini interface observations. The sole condition remains `ACI`, `CLOSED`,
stateless, with retrieval/tools disabled. There is no fallback provider/model,
automatic selection, added Perplexity stratum or promotion from missingness.
Exact source and judge models/settings require new private prospective freezes.
Historical W01/W02 reference profiles do not constitute those freezes.

## 3. Preserved design

All 12 items/24 JA/EN forms, exact wording and query hashes, `k=10`, original
12-wave calendar, 48-hour windows, W01/W04/W07/W10 calibration designation,
Window A [0,12h) and Window B [24,36h), and the registered seed formula remain
unchanged. Ordinary waves contain 3 × 24 × 10 = 720 initial cells.
Calibration waves contain 3 × (20 × 10 + 4 × 10 × 2) = 840 initial cells:
WA 120, WB 120, STD 600. Requests are freshly generated from the versioned
scope and seed; the old four-lineage execution order is not filtered/reused.

Technical retries remain at most two: at least 10 minutes for Retry 1 and an
additional 30 minutes for Retry 2, honoring longer provider waits and the
original row window. Valid refusal/safety/nonanswer/clarification is a retained
observation, not a content-triggered retry. Missingness is never imputed.

## 4. Transition and registration boundary

Historical v1.0, v2.0–v2.0.4, W01/W02 freezes, authorizations, observations,
denominators and registered interpretation remain intact. v2.1 writes only to
`v2.1/<site>/<wave>/`; global lineage locks and cross-version attempt checks
prevent replay in another namespace. No already-started wave may be converted.
Perplexity exclusion in v2.1 is a changed intended panel, not retroactive
deletion of missing/observed Perplexity from older waves.

The owner selected W03 (1 December 2026 00:00 UTC) for three-series activation
and directed preparation of a separate W03 analysis amendment; see
`OWNER_DECISION_W03_20261107.json`. This closes the effective-wave choice, not
publication, actual execution or an exact model/settings freeze. The later
baseline approval below is recorded separately.
The existing four-lineage W03 derivative registration (960 requests; I03 80
slots; W02 comparison) remains an unchanged historical public record.
The [new v1.1 analysis draft](../analysis/W03-URL-variation-v1.1-DRAFT/REGISTRATION_DRAFT.md)
proposes the W03 v2.1/720-request binding and I03 60-slot subset. It withholds
automatic W02 contrasts pending explicit review. Both the analysis amendment
and Core v2.1 must be publicly registered before the original W03 start.
The owner has also approved W03 as the new STD baseline, W02 exclusion from
current primary comparisons, no automatic later-wave fallback and separate
W04 WA/WB calibration. See [dependency review](W03_DEPENDENCY_REVIEW.md) and
`OWNER_DECISION_BASELINE_SCORING_20261107.json`. These are fixed local policies,
not empirical qualification or registration facts.
Registration must precede the selected original start. A missed window is not
shifted or backfilled. A final version needs its own immutable version DOI or
full-commit registration permalink, actual public timestamp and exact source pin.

## 5. Coding change and limits

Each response is scored independently by the two other source-provider
families, with all three judges sharing Core-specific calibration. See the
separate AI scoring and SAP transition drafts. Typed missing/hold states and
canonical variable scales remain intact; there is no Education-style global
0–4 quality scale. AI consensus does not verify factuality, identity, medical/
legal correctness, source authority, claim support, neutrality or human validity.
H/external-verification and final claim responsibility are not waived.

Operational scoring admission is explicitly distinct from independent-reference
validity. Unreferenced AI codes are auxiliary/exploratory. A separately reserved
>=240 validation set does not become gold through AI agreement. The retained
variable-specific reference benchmarks and all failure/undefined holds are in
`SCORING_QUALIFICATION_SPEC_v1.0.md`. Actual reference verification, empirical
metrics and authored-label review are not completed. This does not by itself
block the deterministic I03 URL analysis or independently authorized collection.

## 6. Safety, licensing and disclosure

Observation and scoring execution remain disabled. A separate dated access/
terms review, encrypted research-data storage confirmation, private freezes,
technical readiness, offline test evidence and named hash-bound human
authorization are required before any future execution; prior attestations are
not silently extended to new exact models. No USD 5 cap or encrypted API-key
file requirement is reinstated. Answer sharing is confined to the approved
non-self provider-family coders and documented terms; no secrets/raw answers
are deposited publicly.

Protocol text is CC BY 4.0, consistent with prior public protocol records.
First-party original software in the scope of `LICENSE_NOTICE.md` is MIT-licensed
under `LICENSE_CODE_MIT.txt`. Existing component and third-party terms remain
unchanged; frozen historical releases are not relicensed. Language is English.
The owner confirmed unchanged affiliations and existing funding/COI disclosures,
the expanded AI-assistance disclosure scope and this license separation on
7 November 2026; see `OWNER_DECISION_METADATA_LICENSE_20261107.json`.
This confirms metadata/declaration facts and preparation only, not the final
public artifact, publication, a source pin, empirical qualification or execution.
See [citation/version boundaries](CITATION_GUIDE.md); the earlier Core v2.0 DOI
is the published parent, not the identifier of this unpublished draft.

## 7. Owner-confirmed publication declarations

### Funding

This research received no external financial or in-kind support and was self-funded by the author. Scrumy Inc. and Booost Inc. provided no financial or in-kind support for this research.

### Competing interests

Kento Sasano is the chief executive officer and an equity holder of Scrumy Inc., a company operating in AI governance, AI security, and AI marketing. He also serves as an AI strategy advisor to Booost Inc. These relationships are disclosed because their activities may be perceived as relevant to AI evaluation and governance. The author retains responsibility for the research design, interpretation, and manuscript. No other competing interests are declared.

### AI-assistance disclosure

Codex assisted with protocol and scoring-specification drafting, software implementation, synthetic offline verification, and authoring bilingual synthetic development/calibration examples and their intended labels. These examples and labels are unvalidated development materials, not independent reference labels, measured study responses, or evidence of scoring accuracy. The author retains responsibility for research design, verification, interpretation, and publication. Generative-AI systems are not authors. No new empirical observation or scoring API calls were made in this preparation.
