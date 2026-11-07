# W03 / Core v2.1 technical source review

Review date: 7 November 2026. Base commit:
`30e48170f7387002e506baabd36884f12cc7a250`.
Scope: engineering review and local clean-commit/source-package preparation.
This is not independent scientific validation, public registration, an exact
model freeze, an operational signature, or permission for any provider call.

The owner explicitly requested source-diff review, a clean local commit if
sound, package regeneration and offline verification, without publication or
observation/scoring APIs. No push, PR, merge, remote draft or runtime change
is included.

## Reviewed scope and invariants

- Version-scoped manifest generation, three first-party families, 720 ordinary /
  840 calibration initial cells, durable locks/archive namespaces and restart.
- Original 24 prompt forms/hashes, k=10, calendar, retry rules and refusal handling.
- Both execution sentinels, separate readiness gate, private exact freezes,
  prospective registration and human hash-bound authorization.
- W03 STD baseline, no W02 primary contrast or automatic fallback, separate W04
  WA/WB calibration; deterministic URL-only descriptions and no factual scoring.
- Reciprocal non-self judges, typed domains, exact consensus, H/external holds,
  unreferenced auxiliary use and declared-reference qualification limits.
- Canonical references and unchanged historical W03 source/registration.
- Owner-confirmed authorship/disclosures, CC BY 4.0 / scoped MIT, version/citation
  boundaries and allowlisted secret-free draft packaging.

## Technical findings resolved in this candidate

1. A hash-matching readiness capture could previously be paired with a true
   summary flag even when its actual JSON named another model. The v2.1 gate
   now re-parses exact-model/catalog captures and checks provider, HTTP success,
   model identity, timestamp bounds and no-recorded-credential declaration.
   Parsing an existing capture makes no API call and selects no replacement.
2. Cross-version replay protection had a one-direction gap: a previously
   registered single-lineage legacy scope could miss another lineage's retained
   v2.1 record. Whenever either namespace is v2.1, any retained same-wave attempt
   now blocks switching versions, regardless of lineage overlap. Old W01/W02
   design/data are not modified.
3. A clean Git index can coexist with OS-filtered CRLF working files. A reviewed
   pin must therefore use immutable Git blobs, not merely hash the working tree.
   The source helper reads raw object bytes using Git cat-file, verifies each
   blob against Git's object ID, rejects private/unsafe paths, links and
   submodules, and bypasses checkout/export transformation attributes,
   and checks clean HEAD before/after. Per-file package hashes remain SHA-256.

This checkout is shared by Windows Git and WSL Git. Its local CRLF-normalization
setting follows the original Windows checkout so both clients agree on clean
state; frozen `-text` reference copies keep their exact bytes. The new root
README rule is anchored to avoid applying it to historical nested READMEs.
The byte-identical v2.0 citation retains CRLF under `-text`; only that file's
whitespace attribute recognizes CRLF without rewriting it. The three frozen
Markdown imports retain intentional hard-line-break spaces under a scoped
blank-at-eol exception; their canonical SHA-256 checks still reject any byte
change. Newly authored source/docs keep the ordinary whitespace checks.

Regression tests cover these cases. Final full-suite counts and exact source
identity are recorded externally after staging/committing, not invented here.
The canonical Git index is tested before the actual commit; the clean committed
tree is tested again afterwards. Legacy W01 structural/strict validation remains
mandatory. All runs use stripped credentials, an isolated loopback-only Linux
network namespace and denied Python socket/DNS calls.

## Source pin without self-reference

A tracked file cannot contain its own final commit ID. The tracked metadata
worksheet therefore retains `reviewed_source_commit: null`. A build with
`--reviewed-commit <full HEAD>` requires a clean repository and generates:

- `SOURCE_PROVENANCE.json`: actual local commit, tree and parents;
- `PACKAGE_STATUS.json`: completed local source pin, never registration or API
  authorization;
- `PUBLICATION_METADATA_BOUND_DRAFT.json`: the tracked worksheet's exact
  declarations plus the actual source pin and its worksheet SHA-256.

Committed source members remain byte-identical to Git and the canonical test
snapshot. The bound metadata is explicitly derived, not falsely called a
committed source file. Rebuilding from the same clean commit must reproduce the
same ZIP hash. Earlier r1–r5 artifacts remain immutable.

The installed collection-source binding, exact models, public identifiers,
registration timestamps, empirical qualification, authored-label substantive
review and final public-artifact approval remain separate unfinished gates.
A local source commit is not a public registration or an execution permission.
