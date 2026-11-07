# MIBO Core v2.1 registration preparation

Status: LOCAL PROSPECTIVE DRAFT — NOT PUBLISHED, REGISTERED, FROZEN OR AUTHORIZED.
Prepared 7 November 2026. Proposed version label: 2.1; the registered parent
remains [Core v2.0](https://doi.org/10.5281/zenodo.22264635).

Owner update: the three-series design is to start at W03 (1 December 2026).
The separate W03 v1.1 analysis amendment is prepared locally, not published.
The subsequent approval fixed W03 baseline/W02 exclusion and the separate
operational/validity scoring policy. Neither reply authorizes APIs, signatures,
publication or a claim of completed empirical qualification.

Read in order:

1. [Amendment](AMENDMENT_v2.1_DRAFT.md): panel and version boundary.
2. [SAP transition](SAP_TRANSITION_v2.1_DRAFT.md): estimands, historical records and baseline.
3. [AI scoring plan](AI_SCORING_v2.1_DRAFT.md): non-self-family assignment,
   shared calibration, exact consensus, validation and verification holds.
4. [Publication checklist](REGISTRATION_CHECKLIST.md): unresolved decisions,
   disclosure checks and the explicit publication gate.
5. `zenodo-metadata.draft.json`: English, owner-confirmed authorship/declarations
   and component-specific CC BY 4.0 / MIT metadata; not an API payload.
6. [W03 analysis amendment](../analysis/W03-URL-variation-v1.1-DRAFT/REGISTRATION_DRAFT.md):
   720 full-design requests / 60 I03 slots, W03 baseline and no primary W02 contrast.
7. [Scoring qualification specification](SCORING_QUALIFICATION_SPEC_v1.0.md):
   operational admission, independent references and explicit non-pass states.
8. [Citation/version guide](CITATION_GUIDE.md): Core `2.1-draft` versus W03
   analysis `1.1-draft`; no new DOI or release date. The earlier v2.0 citation
   is preserved byte-for-byte under `reference/`.
9. [Technical source review](SOURCE_REVIEW.md): resolved engineering findings,
   canonical Git-byte verification and the local clean-commit pin boundary.

Affiliations/funding/COI remain unchanged under the owner's 7 November 2026
confirmation. The expanded AI-assistance disclosure covers drafting, coding,
offline verification and synthetic calibration examples/intended labels, which
remain unvalidated development materials. `OWNER_DECISION_METADATA_LICENSE_20261107.json`
records approval of those facts/scopes and original-software MIT, not approval
of final public bytes, substantive expected labels, empirical qualification,
publication or API execution. Do not re-request these metadata decisions.

## What has been implemented

The existing Python/standard-library Core collector now has a version-specific
three-lineage path: OpenAI/Responses, Anthropic/Messages, Google/GenerateContent.
It preserves prompts and hashes, `ACI`/`CLOSED`, the original calendar, `k=10`,
the seed formula, WA/WB bounds, retry rules, append-only storage and durable
claims/locks. Ordinary and calibration denominators are 720 and 840.
Historical versions still generate 960/1,120 rows. This is not a filtered or
renamed W01/W02 manifest.

The analysis-transition and AI qualification policies are fixed locally. The
new version still requires its own immutable public registration, the separately
published W03 analysis amendment, a fresh three-lineage private freeze, all-three readiness
evidence, and unsigned-to-human-completed hash-bound authorization. Model IDs
are never selected in code. A dedicated v2.1 execution sentinel is required
in addition to the old Core v2 sentinel; both are checked before each dispatch.
The direct v2.1 executor also checks the strict controlled-host/source/clock
gate. Metadata/readiness calls need a separate v2.1 approval sentinel.

## What is deliberately not completed

No publication/DOI reservation, PR, push, merge, private model freeze, human
signature, service installation/start/enablement, model metadata request,
observation, or scoring API call is made by this preparation. Current candidate
source identity is recorded only by a clean committed-source build, in generated
`SOURCE_PROVENANCE.json`. The installed W02 base commit
`d970efab834f193b7f3d12ecded20be6f0e8f445` is provenance, not the new source pin.
The packaging receipt records the current checkout parent separately and now
includes the owner-directed W03 amendment draft plus unchanged v1.0 dependency
code and registration references. The earlier independently registered version
is not edited or re-labeled.
The already staged disabled configuration on the VM is not this new deployment.

The canonical Codebook has been acquired and hash-compared. Authored label
review, real calibration, the separately reserved validation set, full
Entity/Source coding and externally verified H variables remain incomplete.
No synthetic test establishes model availability, scoring validity or absence
of bias. No second-human recruitment is required by this preparation.

## Local packaging

`automation/core_v21_registration.py` uses an explicit public-file allowlist,
checks the canonical-source hashes and disabled draft state, emits per-file
SHA-256 values and a deterministic ZIP, and has **no upload or publish action**.
The output is an auditable draft for owner review, not an executable deployment.
Complete applicable content review, review/commit the exact source, then
prepare the final registration artifact; only a subsequent explicit approval
may create/update a remote draft or publish it.

For a reviewed clean local HEAD, `--reviewed-commit <full 40-hex HEAD>` packages
immutable Git blobs rather than OS-filtered working files. A clean index and
worktree are required before/after reading the commit. The tracked metadata
worksheet intentionally keeps its own commit field null; the generated
`PUBLICATION_METADATA_BOUND_DRAFT.json` carries the real pin and worksheet
SHA-256. This derived file stays unpublished/unarmed, with every API permission
false. Neither a local commit nor its hash is a public registration.
