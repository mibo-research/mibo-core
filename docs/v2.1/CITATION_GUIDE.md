# Citation and version boundaries — unpublished drafts

Prepared 7 November 2026. Owner-confirmed metadata and disclosure scope do not
constitute public registration, publication or execution permission. No new DOI,
public timestamp or release date has been assigned. A clean local source pin,
when produced, is recorded in generated `SOURCE_PROVENANCE.json`, not a public
registration and not a self-referential field in a tracked citation.

| Object | Local version | Citation source | Public identifier |
| --- | --- | --- | --- |
| New Core protocol package | 2.1-draft | Root `CITATION.cff` and `zenodo-metadata.draft.json` | None; unpublished |
| W03 URL-string analysis amendment | 1.1-draft | `../analysis/W03-URL-variation-v1.1-DRAFT/CITATION.cff` | None; unpublished |
| Published Core parent | 2.0 | Byte-identical `reference/PUBLISHED_CORE_v2.0.CITATION.cff` | 10.5281/zenodo.22264635 |
| Frozen instrument / Codebook / SAP | 1.0 | Selected exact reference copies and source provenance | 10.5281/zenodo.21936410 |

The two new drafts have different version sequences. Do not label the W03
analysis amendment “Core v1.1”, or call its analysis version “2.1”. The collector
scientific protocol version remains `2.1`; the document version `2.1-draft`
communicates that registration is incomplete, not a different runtime protocol.

Root citation metadata now describes the local draft, not a released v2.1.
The README's current **published** release remains v2.0. Its DOI, release date
and historical citation remain unchanged. Earlier DOIs identify those earlier
objects only: never copy the v2.0 DOI or release date onto a new v2.1 citation.
The preserved W03 v1.0 GitHub registration is likewise not a new v1.1 identifier.

For private review, cite Kento Sasano and explicitly state the applicable local
draft version, “unpublished prospective draft, prepared 7 November 2026”.
After separate authorization and actual registration, bind the new version's
real identifier, timestamp, reviewed full source commit and final artifact
hashes consistently. Reserved identifiers must not be described as published.

The tracked metadata worksheet's `reviewed_source_commit: null` avoids putting
a commit ID into that commit itself. The clean-commit packager derives
`PUBLICATION_METADATA_BOUND_DRAFT.json` with the actual local source pin and
the tracked worksheet SHA-256, without inventing a DOI or publication date.

Protocol text is CC BY 4.0. Original software is separately MIT-licensed only
within the scope of `LICENSE_NOTICE.md`; component/third-party terms remain.
