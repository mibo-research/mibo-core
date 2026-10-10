#!/usr/bin/env python3
"""Read-only, content-blind Core v2 wave evidence audit (standard library only).

No provider calls; no archive writes. Counts are technical evidence, not judged
valid responses, independent observations, or evidence of a causal repair effect.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
from retry_policy import RETRY_ELIGIBLE

SAFE_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}$")
IDENTITY_FIELDS = ("wave_id", "site_id", "service_lineage_id", "query_form_id", "language", "window_id", "replication", "query_sha256")
STATUS_FIELDS = ("verified_capture", "failed", "window_expired", "incomplete_write", "evidence_missing", "unsubmitted_unknown")
EXPIRED = "window_expired_before_attempt"
TECHNICAL_RETRY = RETRY_ELIGIBLE


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def _time(value):
    if not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt.astimezone(timezone.utc) if dt.tzinfo is not None else None


def _iso(value):
    return value.isoformat().replace("+00:00", "Z") if value else None


def _json(path):
    with Path(path).open(encoding="utf-8") as f:
        value = json.load(f)
    if not isinstance(value, dict):
        raise ValueError("Expected object evidence")
    return value


def _rows(path, wave_id):
    with Path(path).open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    required = ("attempt_id", "protocol_version", *IDENTITY_FIELDS)
    if not rows or any(any(not r.get(k) for k in required) for r in rows):
        raise ValueError("Manifest required fields missing")
    for row in rows:
        for field in ("attempt_id", "protocol_version", "site_id", "service_lineage_id", "query_form_id", "language", "window_id"):
            if not SAFE_TOKEN.fullmatch(row[field]):
                raise ValueError("Manifest identifier format invalid")
        if row["wave_id"] != wave_id or str(row.get("attempt")) != "1":
            raise ValueError("Manifest wave or initial attempt mismatch")
        if not re.fullmatch(r"[a-f0-9]{64}", row["query_sha256"]):
            raise ValueError("Manifest query digest invalid")
    if len({r["attempt_id"] for r in rows}) != len(rows):
        raise ValueError("Duplicate initial manifest ID")
    if len({r["site_id"] for r in rows}) != 1:
        raise ValueError("Manifest must have one site")
    return rows


def _bounds(protocol, row):
    matches = [w for w in protocol.get("waves", []) if w.get("wave_id") == row["wave_id"]]
    if len(matches) != 1:
        raise ValueError("Wave bounds missing or ambiguous")
    wave = matches[0]
    start, close = _time(wave.get("start_utc")), _time(wave.get("close_utc"))
    if not start or not close or close - start != timedelta(hours=48):
        raise ValueError("Wave bounds invalid")
    if row["window_id"] == "STD":
        return start, close
    key = {"WA": "window_a", "WB": "window_b"}.get(row["window_id"])
    cfg = wave.get(key) if key else None
    if not isinstance(cfg, dict):
        raise ValueError("Registered row window missing")
    return start + timedelta(hours=cfg["start_offset_hours"]), start + timedelta(hours=cfg["end_offset_hours"])


def _tree(root):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Raw root is missing or symlink")
    for p in root.rglob("*"):
        if p.is_symlink() or not (p.is_file() or p.is_dir()):
            raise ValueError("Raw tree contains symlink or special file")
    return root.resolve()


def _input_fingerprint(baseline_manifest, specs):
    """Detect concurrent input replacement/change; does not modify or seal files."""
    paths = {Path(baseline_manifest).resolve()}
    for spec in specs:
        root = _tree(spec["raw_root"])
        paths.update(p for p in root.rglob("*") if p.is_file())
        paths.update(Path(spec[key]).resolve() for key in ("manifest", "protocol", "freeze"))
    result = []
    for path in sorted(paths):
        stat = path.stat()
        result.append((str(path), stat.st_size, stat.st_mtime_ns, stat.st_ino))
    return result


def _sealed(root):
    path = root / "SHA256SUMS.txt"
    if not path.exists():
        return None, []
    entries, issues = {}, []
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split("  ", 1)
        if len(parts) != 2 or not re.fullmatch(r"[a-f0-9]{64}", parts[0]):
            issues.append("invalid_seal_manifest")
            continue
        digest, name = parts
        target = Path(name)
        if target.is_absolute() or ".." in target.parts or name in entries:
            issues.append("invalid_seal_manifest")
            continue
        entries[name] = digest
        p = root / target
        if not p.is_file() or sha(p) != digest:
            issues.append("sealed_file_missing_or_hash_mismatch")
    return entries, issues


def _record_identity(value, row, version, *, capture=False):
    required = ("attempt_id", "protocol_version")
    if any(not value.get(k) for k in required) or value.get("protocol_version") != version:
        return False
    # Captures in early versions carry structural identity in their raw envelope.
    for key in IDENTITY_FIELDS:
        if key in value and str(value[key]) != str(row[key]):
            return False
    for key in ("protocol_file_sha256", "provider_freeze_sha256"):
        if key in value and value[key] != row.get(key):
            return False
    return True


def _baseline_design(rows, protocol):
    """Require the complete registered design, including non-admitted lineages."""
    config = Path(__file__).parent / "config"
    forms = _json(config / "instrument_v1.0.json")["forms"]
    services = _json(config / "services_v1.0.json")["services"]
    known_forms = {f["query_form_id"]: f for f in forms}
    known_services = {s["service_lineage_id"]: s for s in services}
    wave = next(w for w in protocol["waves"] if w["wave_id"] == rows[0]["wave_id"])
    registered = _json(config / "core_v2_protocol.v2.0.json")
    registered_wave = next(w for w in registered["waves"] if w["wave_id"] == wave["wave_id"])
    if wave != registered_wave:
        raise ValueError("Audit input changes registered wave schedule")
    expected = set()
    for sid in known_services:
        for form in forms:
            windows = ("WA", "WB") if wave.get("calibration_wave") and form["anchor"] and form["language"] == "EN" else ("STD",)
            for window in windows:
                for rep in range(1, 11):
                    expected.add((sid, form["query_form_id"], window, str(rep)))
    actual = []
    for row in rows:
        form = known_forms.get(row["query_form_id"])
        if row["service_lineage_id"] not in known_services or not form or row["query_sha256"] != form["sha256"] or row["language"] != form["language"]:
            raise ValueError("Baseline frozen panel or query identity mismatch")
        service = known_services[row["service_lineage_id"]]
        expected_id = ("MIBO2-SITE-" + row["site_id"] + "-" + row["wave_id"].replace("MIBO2-", "") + "-" + service["short_id"] + "-ACI-" + form["item_id"].replace("MIBO-", "") + "-" + row["language"] + "-" + row["window_id"] + "-R" + str(row["replication"]).zfill(2) + "-A01")
        if row["attempt_id"] != expected_id:
            raise ValueError("Baseline initial attempt ID mismatch")
        actual.append((row["service_lineage_id"], row["query_form_id"], row["window_id"], row["replication"]))
    if len(actual) != len(expected) or set(actual) != expected:
        raise ValueError("Baseline must contain complete registered planned design")


def _inspect_namespace(spec, baseline, wave_id):
    version = str(spec["version"])
    if not SAFE_TOKEN.fullmatch(version):
        raise ValueError("Invalid namespace version")
    root = _tree(spec["raw_root"])
    protocol = _json(spec["protocol"])
    freeze = _json(spec["freeze"])
    rows = _rows(spec["manifest"], wave_id)
    if {r["attempt_id"] for r in rows} != set(baseline):
        raise ValueError("Namespace manifest must preserve complete baseline design")
    admitted = spec.get("lineages")
    if not isinstance(admitted, list) or not admitted or any(not SAFE_TOKEN.fullmatch(str(s)) for s in admitted):
        raise ValueError("Explicit namespace lineage scope required")
    if protocol.get("protocol_version") != version:
        raise ValueError("Protocol namespace version mismatch")
    ph, fh = sha(spec["protocol"]), sha(spec["freeze"])
    planned = {}
    for row in rows:
        if row["protocol_version"] != version or row.get("protocol_file_sha256") != ph or row.get("provider_freeze_sha256") != fh:
            raise ValueError("Manifest frozen-input hash mismatch")
        if row["attempt_id"] not in baseline or any(str(row[k]) != str(baseline[row["attempt_id"]][k]) for k in IDENTITY_FIELDS):
            raise ValueError("Namespace changes baseline logical observation identity")
        _bounds(protocol, row)
        if row["service_lineage_id"] in admitted:
            cfg = freeze.get("core_api", {}).get(row["service_lineage_id"], {})
            if row.get("model_id") != cfg.get("model_id") or not isinstance(cfg.get("request_profile"), dict):
                raise ValueError("Manifest model or profile freeze mismatch")
            planned[row["attempt_id"]] = row
    if set(admitted) != {r["service_lineage_id"] for r in planned.values()}:
        raise ValueError("Namespace admitted scope not found in manifest")
    sealed, namespace_issues = _sealed(root)
    for folder in ("metadata", "failures", "dispatch", "api_raw", "deviations"):
        if (root / folder).exists() and not (root / folder).is_dir():
            raise ValueError("Expected evidence directory")
    parents, links, records, starts, stops, unlinked = {}, {}, [], [], [], []
    malformed = 0
    for folder in ("metadata", "failures", "dispatch"):
        for p in sorted((root / folder).glob("*.json")):
            try:
                v = _json(p)
            except (ValueError, OSError, UnicodeError):
                malformed += 1
                continue
            if p.name.startswith("first-dispatch-"):
                sid = v.get("service_lineage_id")
                dt = _time(v.get("actual_observation_start_at_utc"))
                if sid in admitted and dt:
                    starts.append({"service_lineage_id": sid, "at_utc": _iso(dt), "evidence_kind": "first_adapter_dispatch_intent_only"})
                continue
            if p.name.startswith("retry-link-"):
                child, parent = v.get("retry_attempt_id"), v.get("original_attempt_id")
                if not isinstance(child, str) or not SAFE_TOKEN.fullmatch(child) or not isinstance(parent, str) or not SAFE_TOKEN.fullmatch(parent):
                    malformed += 1
                    continue
                if child in parents and parents[child] != parent:
                    namespace_issues.append("conflicting_retry_link")
                parents[child] = parent
                links[child] = v
                continue
            aid, parent = v.get("attempt_id"), v.get("retry_of_attempt_id")
            if not isinstance(aid, str) or not SAFE_TOKEN.fullmatch(aid):
                malformed += 1
                continue
            if parent:
                if not isinstance(parent, str) or not SAFE_TOKEN.fullmatch(parent):
                    malformed += 1
                    continue
                if aid in parents and parents[aid] != parent:
                    namespace_issues.append("conflicting_retry_link")
                parents[aid] = parent
            records.append((p, folder, v))
    if malformed:
        namespace_issues.append("malformed_evidence_record")
    for p in sorted((root / "deviations").glob("*.json")):
        try:
            v = _json(p)
        except (ValueError, OSError, UnicodeError):
            namespace_issues.append("malformed_deviation_record")
            continue
        sid = v.get("service_lineage_id")
        kind = v.get("type")
        if sid in admitted and kind in {"lineage_suspended_after_retry_exhaustion", "lineage_suspended_for_environment_mismatch", "registered_wave_started_late", "registered_wave_closed", "collector_stopped"}:
            stops.append({"service_lineage_id": sid, "type": kind, "at_utc": _iso(_time(v.get("at_utc") or v.get("recorded_at_utc")))})
    by_initial = defaultdict(list)
    def initial(aid):
        seen, current = set(), aid
        for depth in range(4):
            if current in seen:
                return None, None
            seen.add(current)
            if current in planned:
                return current, depth + 1
            current = parents.get(current)
            if not current:
                break
        return None, None
    referenced = set()
    failures_by_id = {v["attempt_id"]: v for _, kind, v in records if kind == "failures"}
    for aid, value in links.items():
        records.append((root / "metadata" / ("retry-link-" + aid + ".json"), "retry_schedule", {**value, "attempt_id": aid}))
    for p, folder, value in records:
        aid = value["attempt_id"]
        oid, number = initial(aid)
        if oid is None:
            namespace_issues.append("unlinked_or_cyclic_attempt")
            continue
        row = planned[oid]
        issues = []
        expected_attempt_id = oid[:-2] + str(number).zfill(2)
        if aid != expected_attempt_id:
            issues.append("attempt_id_retry_number_mismatch")
        if not _record_identity(value, row, version):
            issues.append("attempt_identity_mismatch")
        if value.get("attempt") is not None and str(value["attempt"]) != str(number):
            issues.append("retry_number_mismatch")
        if number > 3:
            issues.append("retry_limit_exceeded")
        rel = str(p.relative_to(root))
        if sealed is not None and (rel not in sealed or sha(p) != sealed.get(rel)):
            issues.append("metadata_not_bound_to_seal")
        record = {"attempt_id": aid, "attempt": number, "version": version, "evidence_kind": folder, "submitted_confirmed": False, "dispatch_intent": False, "verified_capture": False, "incomplete_write": False, "failure": False, "window_expired": False, "started_at_utc": None, "completed_at_utc": None, "issues": issues, "review_notes": [], "metadata_sha256": sha(p)}
        begin, end = _bounds(protocol, row)
        started, completed = None, None
        if folder == "dispatch":
            started = _time(value.get("dispatch_at_utc"))
            record["dispatch_intent"] = True
            record["timestamp_kind"] = "collector_dispatch_intent_before_provider_adapter"
        elif folder == "retry_schedule":
            pass
        elif folder == "failures":
            failed_at = _time(value.get("failed_at_utc"))
            record["completed_at_utc"] = _iso(failed_at)
            record["failure"] = value.get("failure_kind") != EXPIRED
            record["window_expired"] = value.get("failure_kind") == EXPIRED
            # A local failure file is not evidence that a request reached a provider.
            code = value.get("http_status")
            record["submitted_confirmed"] = isinstance(code, int) and 100 <= code <= 599 and not record["window_expired"]
            record["http_status"] = code if isinstance(code, int) and 100 <= code <= 599 else None
            kind = value.get("failure_kind")
            record["failure_kind"] = kind if kind in TECHNICAL_RETRY | {EXPIRED, "request_environment_mismatch"} else "unclassified"
        else:
            raw_name = value.get("raw_file")
            raw = root / str(raw_name) if isinstance(raw_name, str) else None
            valid_path = bool(raw and not Path(raw_name).is_absolute() and ".." not in Path(raw_name).parts and raw.is_file())
            if not valid_path:
                issues.append("raw_missing_or_unsafe_path")
                record["incomplete_write"] = True
            else:
                referenced.add(raw.resolve())
                digest = sha(raw)
                record["raw_sha256"] = digest
                if digest != value.get("raw_file_sha256"):
                    issues.append("raw_hash_mismatch")
                if sealed is not None and (str(raw.relative_to(root)) not in sealed or digest != sealed.get(str(raw.relative_to(root)))):
                    issues.append("raw_not_bound_to_seal")
                try:
                    # Parse envelope structure only; answer, request payload, and usage are never inspected or emitted.
                    envelope = _json(raw)
                    if envelope.get("attempt_id") != aid or not _record_identity(envelope, row, version):
                        issues.append("raw_envelope_identity_mismatch")
                    if any(str(envelope.get(k)) != str(row[k]) for k in IDENTITY_FIELDS):
                        issues.append("raw_envelope_required_identity_missing")
                    if envelope.get("model_id_requested") != row.get("model_id"):
                        issues.append("raw_requested_model_mismatch")
                    record["returned_model_id_sha256"] = _canonical_hash(envelope.get("model_id_returned"))
                    started, completed = _time(envelope.get("started_at_utc")), _time(envelope.get("completed_at_utc"))
                    record["submitted_confirmed"] = isinstance(envelope.get("http_status"), int) and 100 <= envelope["http_status"] <= 599
                    if not isinstance(envelope.get("http_status"), int) or not 200 <= envelope["http_status"] <= 299:
                        issues.append("capture_http_status_not_successful")
                    if not started or not completed or completed < started:
                        issues.append("capture_times_missing_or_invalid")
                    for key, rawtime in (("started_at_utc", started), ("completed_at_utc", completed)):
                        if key in value and _time(value[key]) != rawtime:
                            issues.append("metadata_raw_time_mismatch")
                except (ValueError, OSError, UnicodeError):
                    issues.append("raw_envelope_unreadable")
                if value.get("status") != "valid_confirmatory_api_capture":
                    issues.append("capture_status_unrecognized")
            record["verified_capture"] = not issues
        if started and not (begin <= started < end):
            issues.append("attempt_start_outside_registered_window")
        if completed and completed > end:
            # The executor gates request start, not completion. Do not invent a
            # retrospective scientific exclusion rule for an in-flight response.
            record["review_notes"].append("capture_completed_after_registered_window_close")
        record["started_at_utc"] = _iso(started)
        if completed:
            record["completed_at_utc"] = _iso(completed)
        if number > 1:
            link = links.get(aid)
            due = _time(link.get("due_at_utc")) if link else None
            parent_fail = failures_by_id.get(parents.get(aid))
            previous = _time(parent_fail.get("failed_at_utc")) if parent_fail else None
            record["retry_due_at_utc"] = _iso(due)
            if not link or not due or not previous:
                issues.append("retry_link_or_prior_failure_missing")
            else:
                wait = 600 if number == 2 else 1800
                extra = parent_fail.get("retry_after_seconds")
                if isinstance(extra, (int, float)):
                    wait = max(wait, extra)
                if due < previous + timedelta(seconds=wait):
                    issues.append("retry_due_before_registered_wait")
                if parent_fail.get("failure_kind") not in TECHNICAL_RETRY:
                    issues.append("retry_after_ineligible_failure")
                if not (begin <= due < end):
                    issues.append("retry_due_outside_registered_window")
                if started and started < due:
                    issues.append("retry_started_before_due")
        if issues:
            record["verified_capture"] = False
        by_initial[oid].append(record)
    for p in sorted((root / "api_raw").glob("*.json")):
        if p.resolve() not in referenced:
            # Filename can link incomplete raw-before-metadata writes, without opening its body.
            oid, _ = initial(p.stem)
            if oid:
                by_initial[oid].append({"attempt_id": p.stem, "attempt": None, "version": version, "evidence_kind": "orphan_raw", "submitted_confirmed": False, "dispatch_intent": False, "verified_capture": False, "incomplete_write": True, "failure": False, "window_expired": False, "started_at_utc": None, "completed_at_utc": None, "raw_sha256": sha(p), "issues": ["raw_without_metadata"]})
            else:
                unlinked.append(sha(p))
    if unlinked:
        namespace_issues.append("unlinked_raw_capture")
    # duplicate capture/failure files and conflicting attempts never silently collapse.
    for oid, evidence in by_initial.items():
        terminal_ids = Counter(r["attempt_id"] for r in evidence if r["evidence_kind"] in {"metadata", "failures"})
        if any(n > 1 for n in terminal_ids.values()):
            for record in evidence:
                record["issues"].append("duplicate_or_conflicting_terminal_record")
                record["verified_capture"] = False
    profiles = {}
    for sid in admitted:
        cfg = freeze.get("core_api", {}).get(sid, {})
        profiles[sid] = _canonical_hash(cfg.get("request_profile"))
    return {"version": version, "manifest_sha256": sha(spec["manifest"]), "protocol_sha256": ph, "freeze_sha256": fh, "seal_sha256": sha(root / "SHA256SUMS.txt") if sealed is not None else None, "seal_present": sealed is not None, "issues": sorted(set(namespace_issues)), "malformed_evidence_records": malformed, "unlinked_raw_sha256": unlinked, "profile_sha256_by_lineage": profiles, "first_dispatch_intents": starts, "stop_records": stops}, planned, by_initial, protocol


def audit_wave(*, baseline_manifest, namespaces, wave_id, now=None):
    """Return disclosure-safe report; never mutate inputs or call external services."""
    if not re.fullmatch(r"MIBO2-W(?:0[1-9]|1[0-2])", wave_id):
        raise ValueError("Wave ID invalid")
    if not isinstance(namespaces, list) or not namespaces:
        raise ValueError("At least one explicit namespace required")
    before = _input_fingerprint(baseline_manifest, namespaces)
    rows = _rows(baseline_manifest, wave_id)
    baseline = {r["attempt_id"]: r for r in rows}
    variants, all_records, sources, protocols = defaultdict(list), defaultdict(list), [], {}
    roots = [str(Path(s["raw_root"]).resolve()) for s in namespaces]
    if len(roots) != len(set(roots)):
        raise ValueError("Duplicate input namespace root")
    for spec in namespaces:
        source, planned, records, protocol = _inspect_namespace(spec, baseline, wave_id)
        _baseline_design(rows, protocol)
        sources.append(source)
        for oid, row in planned.items():
            variant = {"version": source["version"], "protocol_sha256": source["protocol_sha256"], "freeze_sha256": source["freeze_sha256"], "request_profile_sha256": source["profile_sha256_by_lineage"][row["service_lineage_id"]], "model_id_sha256": _canonical_hash(row.get("model_id")), "window_start_utc": _iso(_bounds(protocol, row)[0]), "window_close_utc": _iso(_bounds(protocol, row)[1])}
            variants[oid].append(variant)
            all_records[oid].extend(records.get(oid, []))
            protocols[oid] = protocol
    observations, counters, cells = [], Counter(), defaultdict(lambda: {"planned": set(), "verified_capture": set()})
    observed_at = now or datetime.now(timezone.utc)
    if observed_at.tzinfo is None:
        raise ValueError("Audit timestamp must include timezone")
    for row in rows:
        oid = row["attempt_id"]
        record_list = all_records[oid]
        captures = [r for r in record_list if r["verified_capture"]]
        problems = sorted({x for r in record_list for x in r["issues"]})
        active_versions = {r["version"] for r in record_list}
        if len(active_versions) > 1:
            problems.append("same_logical_observation_records_across_versions")
        if len(captures) > 1:
            problems.append("multiple_captures_for_one_logical_observation")
        if captures and len(captures) == 1 and not problems:
            status = "verified_capture"
        elif any(r["incomplete_write"] for r in record_list):
            status = "incomplete_write"
        elif any(r["evidence_kind"] == "metadata" for r in record_list) or problems:
            status = "evidence_missing"
        elif any(r["failure"] for r in record_list):
            status = "failed"
        elif any(r["window_expired"] for r in record_list):
            status = "window_expired"
        elif any(r["dispatch_intent"] for r in record_list):
            status = "evidence_missing"
        else:
            status = "unsubmitted_unknown"
        submitted = any(r["submitted_confirmed"] for r in record_list)
        count = {"initial_attempt_id": oid, "service_lineage_id": row["service_lineage_id"], "query_form_id": row["query_form_id"], "language": row["language"], "window_id": row["window_id"], "status": status, "submitted_confirmed": submitted, "variant_count": len(variants[oid]), "variants": variants[oid], "variant_profile_difference": len({v["request_profile_sha256"] for v in variants[oid]}) > 1, "issues": sorted(set(problems)), "review_notes": sorted({note for r in record_list for note in r.get("review_notes", [])}), "attempt_evidence": record_list}
        observations.append(count)
        counters["planned"] += 1
        counters[status] += 1
        counters["submitted"] += int(submitted)
        counters["dispatch_intent_logical_slots"] += int(any(r["dispatch_intent"] for r in record_list))
        counters["multi_variant_planned_slots"] += int(len(variants[oid]) > 1)
        if not variants[oid]:
            counters["planned_without_namespace"] += 1
        # A candidate cell never pools protocol versions. Replication retries remain one slot.
        version = captures[0]["version"] if status == "verified_capture" else None
        for variant in variants[oid]:
            key = (variant["version"], row["service_lineage_id"], row["query_form_id"], row["language"], row["window_id"], variant["request_profile_sha256"], variant["model_id_sha256"])
            cells[key]["planned"].add(oid)
            if status == "verified_capture" and version == variant["version"]:
                cells[key]["verified_capture"].add(oid)
    cell_rows = []
    for key, counts in sorted(cells.items()):
        cell_rows.append(dict(zip(("version", "service_lineage_id", "query_form_id", "language", "window_id", "request_profile_sha256", "model_id_sha256"), key), planned=len(counts["planned"]), verified_capture=len(counts["verified_capture"]), technical_capture_candidate_n_ge_8=len(counts["verified_capture"]) >= 8))
    totals = {key: counters[key] for key in ("planned", "submitted", *STATUS_FIELDS, "dispatch_intent_logical_slots", "multi_variant_planned_slots", "planned_without_namespace")}
    totals["confirmed_submission_fraction_lower_bound"] = counters["submitted"] / counters["planned"]
    totals["technical_capture_candidate_cells_n_ge_8"] = sum(c["technical_capture_candidate_n_ge_8"] for c in cell_rows)
    totals["verified_capture_fraction"] = counters["verified_capture"] / counters["planned"]
    provider_rows = []
    for sid in sorted({r["service_lineage_id"] for r in rows}):
        subset = [r for r in observations if r["service_lineage_id"] == sid]
        starts = [r["started_at_utc"] for obs in subset for r in obs["attempt_evidence"] if r.get("started_at_utc")]
        ends = [r["completed_at_utc"] for obs in subset for r in obs["attempt_evidence"] if r.get("completed_at_utc")]
        provider_rows.append({"service_lineage_id": sid, "planned": len(subset), "submitted": sum(r["submitted_confirmed"] for r in subset), "earliest_recorded_adapter_or_request_start_utc": min(starts) if starts else None, "latest_recorded_capture_or_failure_utc": max(ends) if ends else None, **{s: sum(r["status"] == s for r in subset) for s in STATUS_FIELDS}})
    if before != _input_fingerprint(baseline_manifest, namespaces):
        raise ValueError("Input evidence changed during offline audit")
    return {"schema_version": "core-v2-content-blind-audit-1", "wave_id": wave_id, "audited_at_utc": _iso(observed_at), "audit_tool_sha256": sha(Path(__file__)), "input_change_check": "no_path_size_mtime_inode_change_detected_during_audit", "baseline_manifest_sha256": sha(baseline_manifest), "interpretation": {"submitted": "lower_bound_from_provider_http_response_evidence; dispatch_intent_and_local_failure_alone_do_not_prove_submission", "verified_capture": "structural_identity_raw_hash_and_registered_window_checked_only", "candidate_cells": "same_version_profile_model_provider_query_language_window; n_ge_8_is_technical_only; independent_content_validity_unjudged", "missingness": "no_log_is_unknown_not_proof_of_unsubmitted; no_imputation", "comparability": "different_versions_profiles_or_window_designs_not_automatically_comparable", "causality": "wave_difference_does_not_identify_repair_effect"}, "totals": totals, "providers": provider_rows, "namespaces": sources, "cells": cell_rows, "observations": observations}


def write_report(report, output_dir, *, forbidden_roots):
    """Create a new private report directory. Fail before writing if existing/inside input."""
    out = Path(output_dir)
    resolved = out.resolve()
    if resolved.is_relative_to(Path(__file__).resolve().parents[1]):
        raise ValueError("Private audit output cannot be in public source repository")
    for raw in forbidden_roots:
        root = Path(raw).resolve()
        if resolved == root or resolved.is_relative_to(root):
            raise ValueError("Audit output must be separate from raw inputs")
    out.mkdir(mode=0o700, parents=False, exist_ok=False)
    payload = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    path = out / "AUDIT_REPORT.json"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(payload)
        f.flush()
        os.fsync(f.fileno())
    table = io.StringIO(newline="")
    writer = csv.DictWriter(table, fieldnames=("initial_attempt_id", "service_lineage_id", "query_form_id", "language", "window_id", "status", "submitted_confirmed", "variant_count", "variant_profile_difference"))
    writer.writeheader()
    for row in report["observations"]:
        writer.writerow({k: row[k] for k in writer.fieldnames})
    fd = os.open(out / "OBSERVATION_STATUS.csv", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
        f.write(table.getvalue())
        f.flush()
        os.fsync(f.fileno())
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wave", required=True)
    parser.add_argument("--baseline-manifest", required=True, type=Path)
    parser.add_argument("--namespace-spec", required=True, type=Path, help="Private JSON list of version/raw_root/manifest/protocol/freeze/lineages")
    parser.add_argument("--output-dir", required=True, type=Path, help="New private directory outside every raw root")
    args = parser.parse_args(argv)
    try:
        with args.namespace_spec.open(encoding="utf-8") as f:
            specs = json.load(f)
        report = audit_wave(baseline_manifest=args.baseline_manifest, namespaces=specs, wave_id=args.wave)
        write_report(report, args.output_dir, forbidden_roots=[s["raw_root"] for s in specs])
    except (ValueError, OSError, KeyError, TypeError) as exc:
        # Exceptions may contain private filesystem or malformed input values.
        raise SystemExit("Offline audit aborted; inspect inputs privately (" + type(exc).__name__ + ")") from None
    print(json.dumps({"wave_id": args.wave, "totals": report["totals"], "content_validity": "unjudged"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
