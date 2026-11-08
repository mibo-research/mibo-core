# JP01 W02 offline QC and Anchor analysis

This implementation covers `MIBO2-W02 / JP01 / v2.0.1 / ACI / STD`. It uses
the registered four lineages, 24 forms, and ten planned replications per cell.
It emits single-wave descriptive tables. A separate analysis record governs
longitudinal contrasts and calibration designs.

## 1. Prepare and verify the technical inputs

Use a reviewed immutable checkout and a clean Python 3.12 environment. The
entry point uses only the Python standard library and no random sampling.
Work inside the approved private research environment. The original wave,
archive, audit report, approval, coded CSV, and outputs stay private.

Verify the sealed archive and derived read-only copy against the independently
retained receipt digest. Keep `PRIVATE_RUNS` in an existing owner-only
directory on the approved research host. `RESTORED_DATA_ROOT` is a dedicated
read-only mount containing only the sealed wave tree. `SEALED_EXPORT` is
the directory holding the archive and receipt. Set the two expected digests
from the independently retained closure record.

```sh
set -eu
umask 077
python3 -B automation/core_v2_archive_verify.py \
  --archive "$SEALED_EXPORT/MIBO2-W02-sealed.tar.gz" \
  --receipt "$SEALED_EXPORT/CLOSE_RECEIPT.json" \
  --expected-receipt-sha256 "$RECEIPT_SHA256" \
  --wave MIBO2-W02 --site JP01 --restored-data-root "$RESTORED_DATA_ROOT"

w02_root="$RESTORED_DATA_ROOT/v2.0.1/JP01/MIBO2-W02"
PRIVATE_AUDIT="$PRIVATE_RUNS/w02-audit"
python3 -B - "$w02_root" "$PRIVATE_RUNS/w02-namespace.json" <<'PY'
import json
from pathlib import Path
import sys

root, output = map(Path, sys.argv[1:])
closure = root / "closure"
with output.open("x", encoding="utf-8") as handle:
    json.dump([{
        "version": "2.0.1",
        "raw_root": str(root),
        "manifest": str(closure / "FROZEN_MANIFEST.csv"),
        "protocol": str(closure / "FROZEN_PROTOCOL.json"),
        "freeze": str(closure / "FROZEN_FREEZE.json"),
        "lineages": ["MIBO-SL-001", "MIBO-SL-002", "MIBO-SL-003", "MIBO-SL-004"],
    }], handle)
PY
python3 -B runtime/audit-core-v2-wave.py --wave MIBO2-W02 \
  --baseline-manifest "$w02_root/closure/FROZEN_MANIFEST.csv" \
  --namespace-spec "$PRIVATE_RUNS/w02-namespace.json" \
  --sealed-sidecars-only --output-dir "$PRIVATE_AUDIT"
```

The audit uses the sealed technical capture sidecars for HTTP, timing and
identity, and reads raw responses as opaque bytes for SHA-256 verification.
The W02 analysis entry point requires that audit mode and the auditor digest
from the same checkout. See [the audit runbook](W02_AUDIT_TOOL.md) for details.

Run technical QC into a new private directory outside both the repository and
the sealed tree. `WAVE_SEAL_SHA256` is the independently retained digest of
the wave-level `SHA256SUMS.txt`.

```sh
python3 -B automation/core_v2_w02_analysis.py \
  --audit-report "$PRIVATE_AUDIT/AUDIT_REPORT.json" \
  --expected-seal-sha256 "$WAVE_SEAL_SHA256" \
  --output-dir "$PRIVATE_RUNS/w02-technical-qc"
```

Review the 960 slot statuses, 96 cell denominators and the run manifest before
coding. A confirmed submission is a lower bound supported by HTTP evidence.
Retry evidence is counted by distinct attempt and joined to one initial slot.
A recovered failure remains in attempt counts. A valid start before window
close can have a later completion, which appears in the QC table. Resolve
namespace-wide audit issues before using the report. Slot-level technical
states remain visible for review in the private audit.

## 2. Lock the analysis and prepare human coding

Before reading the answers, record PI approval and the reviewed Git commit
in the private Analysis Execution Record. Run technical QC from the same
reviewed commit and execution environment that will run the coded stage.
The approved record supplied as JSON has these fields:

| Field | Value |
| --- | --- |
| `schema_version` | `mibo-w02-jp01-analysis-1` |
| `analysis_record_id` | `MIBO2-W02-JP01-ACI-AER-001` |
| `decision` | `approved` |
| `coding_method` | `human` |
| `approved_by`, `approved_at_utc` | PI name and actual timezone-aware approval timestamp, on or after the input audit |
| `reviewed_code_commit` | Full lowercase 40-character Git commit for the reviewed checkout |
| `input_hashes`, `environment` | Exact objects from the technical-stage `W02_RUN_MANIFEST.json` |

The PI approval is an external human act in the controlled environment.
The program checks the supplied record, input hashes and execution
fingerprint. The study team verifies signer identity and checkout provenance.

After approval, blind and score the derived observations under the frozen
codebook and complete adjudication. Join the locked coding to the original
slot IDs privately. The UTF-8 CSV has this exact header:

```text
initial_attempt_id,capture_attempt_id,validity,response_kind,score_status,score_points
```

Provide one row per technically verified capture. Use `valid`,
`invalid_administration`, or `undetermined`. A valid Anchor row requires
`answer`, `refusal`, `safety_response`, `substantive_nonanswer`, or
`clarification_request`. Valid non-Anchor rows can leave the response category
blank, which appears as unclassified. Nonvalid rows leave it blank.

For valid Anchor rows, use `scored`, `not_applicable`,
`cannot_determine`, or `unscored`. Enter integer points only for `scored`.
I03 accepts 0–2, I05 accepts 0–9 attributes, I07 accepts 0–6, and I09 accepts
0–4. The resulting I05 score is the integer count divided by 9. Non-Anchor
and nonvalid rows use `not_in_scope` with blank points. Record and lock the
coding file's SHA-256 after adjudication, in the private run record.

```sh
python3 -B automation/core_v2_w02_analysis.py \
  --audit-report "$PRIVATE_AUDIT/AUDIT_REPORT.json" \
  --expected-seal-sha256 "$WAVE_SEAL_SHA256" \
  --approval "$PRIVATE_LOCK/approval.json" \
  --coding "$PRIVATE_LOCK/human_coding.csv" \
  --expected-coding-sha256 "$LOCKED_CODING_SHA256" \
  --output-dir "$PRIVATE_RUNS/w02-human-descriptives"
```

## 3. Outputs and checks

- `W02_CELL_QC.csv` and `W02_OBSERVATION_STATUS.csv` cover all scheduled
  cells and slots. Technical-only output has technical counts and states.
  Coded output adds adjudicated validity, response categories and the
  `n_valid ≥ 8`, complete-10 and sensitivity-5-plus flags.
- `W02_ANCHOR_CELLS.csv` has 32 planned cells and separates valid, scored,
  not applicable, cannot determine and unscored counts. Modal deviation
  appears only when all valid observations in a nonempty cell are scored.
- `W02_ANCHOR_FREQUENCIES.csv` contains every legal integer score per Anchor
  cell. Its proportions use scored observations as the denominator.
- `W02_RUN_MANIFEST.json` records input and output hashes and the execution
  fingerprint. Retain it with the outputs and confirm that every listed
  output digest matches before using the run. Each output directory is new
  and private.

The integration tests generate sealed synthetic audit inputs through the
existing auditor and exercise both CLI paths, including a complete 960-slot
run, linked retry, late completion, validity boundaries, nonresponses and
hash, approval and scope mismatches.

```sh
python3 -m unittest discover -s automation/tests -p 'test_core_v2_w02_analysis.py' -v
```

[W02 audit procedure](W02_AUDIT_TOOL.md) · [Core v2.0 analysis plan](v2.0/MIBO_Statistical_Analysis_Plan_v2.0.md)
