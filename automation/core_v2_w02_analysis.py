"""Offline, content-blind QC and human-coded Anchor summaries for JP01 W02."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import re
from statistics import median
import sys

import core_v2_runner as runner
from core_v2_wave_audit import STATUS_FIELDS

HERE = Path(__file__).resolve().parent
CONFIG = HERE / "config"
WAVE = "MIBO2-W02"
SITE = "JP01"
VERSION = "2.0.1"
WINDOW = "STD"
SCHEMA = "mibo-w02-jp01-analysis-1"
ANCHORS = {
    "MIBO-I03": ("i03_anchor_citation_adequacy", 2),
    "MIBO-I05": ("i05_anchor_requirement_completeness", 9),
    "MIBO-I07": ("i07_anchor_concept_coverage", 6),
    "MIBO-I09": ("i09_anchor_epistemic_caution", 4),
}
CODING_FIELDS = (
    "initial_attempt_id", "capture_attempt_id", "validity",
    "response_kind", "score_status", "score_points",
)
VALIDITY = ("valid", "invalid_administration", "undetermined")
RESPONSE_KINDS = ("answer", "refusal", "safety_response", "substantive_nonanswer", "clarification_request")
SCORE_STATES = ("scored", "not_applicable", "cannot_determine", "unscored")


class ContractError(ValueError):
    """A fixed diagnostic that carries no input content."""


def require(condition, message):
    if not condition:
        raise ContractError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def hex_digest(value, size=64):
    return isinstance(value, str) and re.fullmatch(f"[0-9a-f]{{{size}}}", value) is not None


def json_object(data):
    def unique(pairs):
        result = dict(pairs)
        require(len(result) == len(pairs), "Duplicate JSON key")
        return result

    value = json.loads(data, object_pairs_hook=unique)
    require(isinstance(value, dict), "JSON input must be an object")
    return value


def execution_environment():
    files = [
        "core_v2_w02_analysis.py", "core_v2_runner.py", "core_v2_wave_audit.py",
        "core_v2_execution_state.py", "core_v2_archive.py", "raw_archive.py",
        "retry_policy.py", "mibo_runner.py",
        "config/instrument_v1.0.json", "config/services_v1.0.json", "config/waves_v1.0.json",
        "config/core_v2_agent_protocol.v2.0.1.json",
    ]
    return {
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "python_executable_sha256": runner.sha256_file(Path(sys.executable)),
        "platform_system": platform.system(),
        "platform_machine": platform.machine(),
        "dependencies": "python-standard-library",
        "randomness": "none",
        "source_sha256": {name: digest((HERE / name).read_bytes()) for name in files},
    }


def registered_design():
    require(not runner.v1.verify_frozen_config(), "Frozen instrument or registry failed integrity verification")
    forms = json_object((CONFIG / "instrument_v1.0.json").read_bytes())["forms"]
    services = json_object((CONFIG / "services_v1.0.json").read_bytes())["services"]
    protocol, _ = runner.load_protocol(CONFIG / "core_v2_agent_protocol.v2.0.1.json")
    window = runner.wave(protocol, WAVE)
    require(not window["calibration_wave"], "Expected the registered W02 standard window")
    require(len(forms) == 24 and len(services) == 4, "Unexpected frozen instrument or panel size")
    require({form["item_id"] for form in forms if form["anchor"]} == set(ANCHORS),
            "Unexpected frozen Anchor items")
    design = {}
    for service in services:
        for form in forms:
            key = (service["service_lineage_id"], form["query_form_id"], form["language"], WINDOW)
            for rep in range(1, 11):
                oid = runner.attempt_id(SITE, WAVE, service["short_id"], form["item_id"],
                                        form["language"], WINDOW, rep, 1)
                design[oid] = (key, form["item_id"])
    require(len(design) == 960, "Unexpected registered W02 slot identities")
    return design, window


def audited_slots(report, seal_sha256, design, window):
    require(hex_digest(seal_sha256), "Expected an independently retained SHA-256")
    require(report["schema_version"] == "core-v2-content-blind-audit-1" and report["wave_id"] == WAVE,
            "Expected a W02 content-blind audit report")
    require(report.get("capture_evidence_mode") == "sealed_technical_sidecars",
            "W02 requires the sealed technical sidecar audit")
    require(len(report["namespaces"]) == 1, "Expected one W02 namespace")
    ns = report["namespaces"][0]
    require(ns["version"] == VERSION and ns["seal_present"] is True and ns["seal_sha256"] == seal_sha256,
            "Audit namespace or seal digest does not match the approved W02 input")
    require(ns["issues"] == [] and ns["malformed_evidence_records"] == 0 and ns["unlinked_raw_sha256"] == [],
            "Resolve namespace-wide audit issues before aggregation")
    require(report["audit_tool_sha256"] == runner.sha256_file(HERE / "core_v2_wave_audit.py"),
            "Audit program differs from the W02 checkout")
    require(hex_digest(report["baseline_manifest_sha256"]) and
            ns["manifest_sha256"] == report["baseline_manifest_sha256"],
            "Use the sealed W02 manifest for both the baseline and namespace")
    require(all(hex_digest(ns[k]) for k in ("protocol_sha256", "freeze_sha256")),
            "Audit protocol or freeze digest is invalid")
    expected_lineages = {key[0] for key, _ in design.values()}
    require(set(ns["profile_sha256_by_lineage"]) == expected_lineages, "Audit panel differs from W02")
    opens, closes = (runner.parse_aware_utc(window[k]) for k in ("start_utc", "close_utc"))
    slots, model_hashes = {}, defaultdict(set)
    for obs in report["observations"]:
        oid = obs["initial_attempt_id"]
        require(oid in design and oid not in slots, "Foreign or duplicate initial slot")
        key, item = design[oid]
        actual_key = tuple(obs[k] for k in ("service_lineage_id", "query_form_id", "language", "window_id"))
        require(actual_key == key, "Audit slot identity differs from the registered design")
        require(obs["variant_count"] == 1 and len(obs["variants"]) == 1, "Expected a single W02 variant per slot")
        variant = obs["variants"][0]
        require(variant["version"] == VERSION and
                (variant["window_start_utc"], variant["window_close_utc"]) ==
                (window["start_utc"], window["close_utc"]), "Audit variant changes version or window")
        require(variant["protocol_sha256"] == ns["protocol_sha256"] and
                variant["freeze_sha256"] == ns["freeze_sha256"] and
                hex_digest(variant["request_profile_sha256"]) and
                variant["request_profile_sha256"] == ns["profile_sha256_by_lineage"][key[0]] and
                hex_digest(variant["model_id_sha256"]), "Audit variant differs from the frozen identity")
        model_hashes[key[0]].add(variant["model_id_sha256"])

        evidence = obs["attempt_evidence"]
        require(all(e["version"] == VERSION for e in evidence), "Foreign-version attempt evidence")
        status = obs["status"]
        require(status in STATUS_FIELDS, "Unrecognized technical status")
        attempt_ids = {oid[:-2] + suffix for suffix in ("01", "02", "03")}
        submitted = {e["attempt_id"] for e in evidence if e["submitted_confirmed"] is True}
        require(submitted <= attempt_ids and obs["submitted_confirmed"] is bool(submitted),
                "Audit submission flags disagree")
        failures = {e["attempt_id"] for e in evidence if e["failure"] is True}
        expired = {e["attempt_id"] for e in evidence if e["window_expired"] is True}
        require((failures | expired) <= attempt_ids, "Foreign failure or window-expiration evidence")
        candidates = [e for e in evidence if e["verified_capture"] is True]
        capture = ""
        late = False
        if status == "verified_capture":
            require(len(candidates) == 1 and obs["issues"] == [],
                    "Expected one unambiguous verified capture for a valid technical slot")
            candidate = candidates[0]
            capture = candidate["attempt_id"]
            require(capture in submitted, "Verified capture has no matching HTTP submission evidence")
            start, end = (runner.parse_aware_utc(candidate[k]) for k in ("started_at_utc", "completed_at_utc"))
            require(opens <= start < closes and end >= start, "Verified capture is outside the W02 start window")
            late = end > closes
        slots[oid] = {
            "key": key, "item": item, "technical_status": status, "capture_attempt_id": capture,
            "submitted_attempts": len(submitted), "submitted_retry_attempts": len(submitted - {oid}),
            "technical_failure_attempts": len(failures), "window_expired_attempt_records": len(expired),
            "completed_after_close": late,
        }

    require(set(slots) == set(design), "Audit does not cover all 960 registered slots")
    require(all(len(hashes) == 1 for hashes in model_hashes.values()), "Multiple frozen model identities per lineage")
    expected = Counter(row["technical_status"] for row in slots.values())
    expected["planned"] = len(slots)
    expected["submitted"] = sum(row["submitted_attempts"] > 0 for row in slots.values())
    require(all(report["totals"][name] == expected[name] for name in ("planned", "submitted", *STATUS_FIELDS)),
            "Audit totals disagree with slot evidence")
    return slots


def approved_coding(data, slots):
    reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig"), newline=""), strict=True)
    require(tuple(reader.fieldnames or ()) == CODING_FIELDS, "Unexpected human coding CSV columns")
    coded = {}
    for row in reader:
        require(None not in row and all(value is not None for value in row.values()), "Malformed coding row")
        oid = row["initial_attempt_id"]
        require(oid in slots and oid not in coded and slots[oid]["capture_attempt_id"] and
                slots[oid]["capture_attempt_id"] == row["capture_attempt_id"],
                "Coding must identify one verified capture per logical slot")
        validity, kind, state = (row[k] for k in ("validity", "response_kind", "score_status"))
        require(validity in VALIDITY, "Unknown validity state")
        anchor = ANCHORS.get(slots[oid]["item"])
        if validity == "valid":
            require(kind in RESPONSE_KINDS or (not anchor and not kind), "Response category is invalid or missing")
        else:
            require(not kind, "Response category disagrees with validity")
        require(state in SCORE_STATES if anchor and validity == "valid" else state == "not_in_scope",
                "Score status disagrees with validity or Anchor scope")
        points = row["score_points"]
        if state == "scored":
            require(points in {str(n) for n in range(anchor[1] + 1)}, "Anchor score is out of range")
        else:
            require(not points, "Only scored observations may carry a numeric score")
        coded[oid] = row
    require(set(coded) == {oid for oid, slot in slots.items() if slot["capture_attempt_id"]},
            "Human coding must cover every verified capture explicitly")
    return coded


def csv_bytes(rows, fields):
    handle = io.StringIO(newline="")
    writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return handle.getvalue().encode("utf-8")


def ratio(value, denominator):
    return format(value / denominator, ".12g") if denominator else ""


def summarize(slots, coding=None):
    cell_fields = ("protocol_version", "wave_id", "site_id", "line_id",
                   "service_lineage_id", "query_form_id", "language", "window_id")
    cells = defaultdict(list)
    observations = []
    for oid, slot in sorted(slots.items()):
        cell = dict(zip(cell_fields, (VERSION, WAVE, SITE, "ACI", *slot["key"])))
        row = {"initial_attempt_id": oid, **cell, **{k: v for k, v in slot.items() if k not in ("key", "item")}}
        if coding is not None:
            row.update({k: coding.get(oid, {}).get(k, "") for k in CODING_FIELDS[2:]})
        cells[slot["key"]].append(row)
        observations.append(row)

    qc, anchors, frequencies = [], [], []
    for rows in cells.values():
        cell = {k: rows[0][k] for k in cell_fields}
        status = Counter(row["technical_status"] for row in rows)
        summary = {
            **cell, "n_planned": len(rows),
            "n_submitted_slots_lower_bound": sum(row["submitted_attempts"] > 0 for row in rows),
            "n_submitted_attempts_lower_bound": sum(row["submitted_attempts"] for row in rows),
            "n_submitted_retry_attempts_lower_bound": sum(row["submitted_retry_attempts"] for row in rows),
            "n_technical_failure_attempts": sum(row["technical_failure_attempts"] for row in rows),
            "n_window_expired_attempt_records": sum(row["window_expired_attempt_records"] for row in rows),
            **{"n_" + name: status[name] for name in STATUS_FIELDS},
            "n_completed_after_close": sum(row["completed_after_close"] for row in rows),
        }
        if coding is not None:
            valid = [row for row in rows if row["validity"] == "valid"]
            n_valid = len(valid)
            summary.update({
                "n_valid": n_valid,
                **{"n_" + name: sum(row["validity"] == name for row in rows) for name in VALIDITY[1:]},
                **{"n_" + name: sum(row["response_kind"] == name for row in valid) for name in RESPONSE_KINDS},
                "n_response_kind_unclassified": sum(not row["response_kind"] for row in valid),
                "primary_eligible": n_valid >= 8, "complete_10": n_valid == 10, "sensitivity_5_plus": n_valid >= 5,
            })
            anchor = ANCHORS.get(cell["query_form_id"].rsplit("-", 1)[0])
            if anchor:
                outcome, maximum = anchor
                states = Counter(row["score_status"] for row in valid)
                points = [int(row["score_points"]) for row in valid if row["score_status"] == "scored"]
                counts = Counter(points)
                n_scored = len(points)
                anchor_key = {**cell, "outcome": outcome, "score_denominator": maximum}
                anchors.append({
                    **anchor_key, "n_valid": n_valid, **{"n_" + state: states[state] for state in SCORE_STATES},
                    "primary_eligible": n_valid >= 8,
                    "min_points": min(points) if points else "",
                    "median_points": median(points) if points else "",
                    "max_points": max(points) if points else "",
                    "normalized_mean": ratio(sum(points), n_scored * maximum),
                    "modal_deviation_rate": ratio(n_valid - max(counts.values()), n_valid)
                    if n_valid and n_scored == n_valid else "",
                })
                for score in range(maximum + 1):
                    frequencies.append({**anchor_key, "score_points": score, "n": counts[score],
                                        "proportion_among_scored": ratio(counts[score], n_scored)})
        qc.append(summary)

    tables = {"W02_CELL_QC.csv": qc, "W02_OBSERVATION_STATUS.csv": observations}
    if coding is not None:
        tables.update({"W02_ANCHOR_CELLS.csv": anchors, "W02_ANCHOR_FREQUENCIES.csv": frequencies})
    return {name: csv_bytes(rows, tuple(rows[0])) for name, rows in tables.items()}


def verify_approval(approval, input_hashes, environment, audited_at):
    require(approval["schema_version"] == SCHEMA and approval["decision"] == "approved" and
            approval["analysis_record_id"] == "MIBO2-W02-JP01-ACI-AER-001" and approval["coding_method"] == "human",
            "Expected the approved human-coding W02 record")
    require(isinstance(approval["approved_by"], str) and bool(approval["approved_by"].strip()) and
            hex_digest(approval["reviewed_code_commit"], size=40), "Approval is missing the signer or code commit")
    require(runner.parse_aware_utc(approval["approved_at_utc"]) >= runner.parse_aware_utc(audited_at),
            "Approval predates its input audit")
    require(approval["input_hashes"] == input_hashes and approval["environment"] == environment,
            "Audit, seal, code or environment differs from the approved record")


def write_private(output, artifacts):
    output = output.resolve()
    require(not output.is_relative_to(HERE.parent), "Private output must be outside the source repository")
    require(not any((parent / "SHA256SUMS.txt").exists() for parent in output.parents),
            "Private output must be outside sealed input directories")
    output.mkdir(mode=0o700)
    created = []
    try:
        for name, data in artifacts.items():
            path = output / name
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            created.append(path)
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
    except OSError:
        for path in created:
            path.unlink()
        output.rmdir()
        raise


def run(args):
    coding_args = (args.coding, args.expected_coding_sha256, args.approval)
    require(not any(coding_args) or all(coding_args), "Coded mode requires coding, coding SHA-256 and approval")
    audit_bytes = args.audit_report.read_bytes()
    hashes = {"audit_report_sha256": digest(audit_bytes), "wave_seal_sha256": args.expected_seal_sha256}
    report = json_object(audit_bytes)
    design, window = registered_design()
    slots = audited_slots(report, args.expected_seal_sha256, design, window)
    environment = execution_environment()
    coding, approval_hash, reviewed_commit = None, None, None
    if args.coding:
        approval_bytes = args.approval.read_bytes()
        approval = json_object(approval_bytes)
        verify_approval(approval, hashes, environment, report["audited_at_utc"])
        data = args.coding.read_bytes()
        require(digest(data) == args.expected_coding_sha256, "Human coding digest mismatch")
        coding = approved_coding(data, slots)
        hashes["human_coding_sha256"] = digest(data)
        approval_hash = digest(approval_bytes)
        reviewed_commit = approval["reviewed_code_commit"]

    artifacts = summarize(slots, coding)
    manifest = {
        "schema_version": SCHEMA, "wave_id": WAVE, "site_id": SITE, "protocol_version": VERSION,
        "mode": "human_coded_descriptives" if coding is not None else "technical_qc",
        "environment": environment, "input_hashes": hashes,
        "audit_tool_sha256": report["audit_tool_sha256"],
        "capture_evidence_mode": report["capture_evidence_mode"],
        "baseline_manifest_sha256": report["baseline_manifest_sha256"],
        "approval_sha256": approval_hash, "reviewed_code_commit": reviewed_commit,
        "output_sha256": {name: digest(data) for name, data in artifacts.items()},
    }
    artifacts["W02_RUN_MANIFEST.json"] = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    write_private(args.output_dir, artifacts)
    print(f"W02 {manifest['mode']} complete: 960 registered slots, 96 planned cells.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-report", required=True, type=Path)
    parser.add_argument("--expected-seal-sha256", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--coding", type=Path)
    parser.add_argument("--expected-coding-sha256")
    parser.add_argument("--approval", type=Path)
    try:
        run(parser.parse_args(argv))
    except ContractError as exc:
        print(f"W02 analysis rejected: {exc}.", file=sys.stderr)
        return 1
    except (KeyError, TypeError, AttributeError, IndexError, UnicodeError, csv.Error, OSError, ValueError):
        print("W02 analysis rejected input or output. Check the private input contract and approvals.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
