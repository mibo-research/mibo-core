#!/usr/bin/env python3
"""Offline, human-signed close for a registered Core v2 wave; no API dispatch."""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import grp
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tarfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "automation"))
import core_v2_executor as executor
import core_v2_runner as runner

LINEAGES = {"MIBO-SL-001", "MIBO-SL-002", "MIBO-SL-003", "MIBO-SL-004"}
SENTINEL = "MIBO_CORE_V2_EXECUTION"


class CloseError(ValueError):
    """A deliberately safe, content-blind operator diagnostic."""


def utc():
    return datetime.now(timezone.utc)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for block in iter(lambda: fh.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def read(path):
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CloseError("Expected a JSON object: " + Path(path).name)
    return value


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def write(path, value):
    with Path(path).open("xb") as fh:
        fh.write(value.encode("utf-8") if isinstance(value, str) else value)
        fh.flush()
        os.fsync(fh.fileno())


def path_at(value, base):
    path = Path(value)
    if not path.is_absolute():
        path = base / path
    if path.is_symlink():
        raise CloseError("Unexpected symlink input")
    return path.resolve()


def tree_hashes(root):
    items = [root] + list(root.rglob("*"))
    if any(p.is_symlink() or not (p.is_file() or p.is_dir()) for p in items):
        raise CloseError("Unexpected symlink or special file in raw wave")
    return {str(p.relative_to(root)): sha(p) for p in sorted(items) if p.is_file()}


def environment(path):
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise CloseError("Unsupported environment file syntax")
        key, value = line.split("=", 1)
        if key in values or not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", key):
            raise CloseError("Invalid or duplicate environment key")
        tokens = shlex.split(value)
        if len(tokens) != 1:
            raise CloseError("Unsupported environment value")
        values[key] = tokens[0]
    return values


def verify_stopped(entry, config):
    """Read unit state and effective files without displaying their secret values."""
    unit = entry["unit"]
    if not re.fullmatch(r"[A-Za-z0-9_.@-]+\.service", unit):
        raise CloseError("Invalid collector unit")
    output = subprocess.check_output(["systemctl", "show", unit,
        "-p", "ActiveState", "-p", "MainPID", "-p", "UnitFileState",
        "-p", "ControlGroup", "-p", "Result", "-p", "FragmentPath",
        "-p", "DropInPaths", "-p", "Environment"], text=True)
    state = dict(line.split("=", 1) for line in output.splitlines() if "=" in line)
    if (state.get("ActiveState") != "inactive" or state.get("MainPID") != "0"
            or state.get("UnitFileState") != "disabled"):
        raise CloseError("Collector must be inactive and disabled: " + unit)
    if state.get("DropInPaths"):
        raise CloseError("Unit drop-ins require separate review; close aborted")
    if Path(state.get("FragmentPath", "")).resolve() != entry["unit_file"]:
        raise CloseError("Installed unit identity mismatch")
    values = environment(entry["environment_file"])
    if values.get(SENTINEL) != "DISABLED" or os.environ.get(SENTINEL) == executor.EXECUTION_SENTINEL:
        raise CloseError("Execution sentinel must explicitly be DISABLED")
    direct = dict(token.split("=", 1) for token in shlex.split(state.get("Environment", "")) if "=" in token)
    if SENTINEL in direct and direct[SENTINEL] != "DISABLED":
        raise CloseError("Unit execution sentinel is enabled")
    unit_lines = entry["unit_file"].read_text(encoding="utf-8").splitlines()
    env_lines = [line.split("=", 1)[1] for line in unit_lines if line.startswith("EnvironmentFile=")]
    if env_lines != [str(entry["environment_file"])]:
        raise CloseError("Unit environment files differ from reviewed close configuration")
    commands = [line.split("=", 1)[1] for line in unit_lines if line.startswith("ExecStart=")]
    if len(commands) != 1:
        raise CloseError("Exactly one reviewed collector command required")
    command = re.sub(r"\$\{([A-Za-z_][A-Za-z_0-9]*)\}",
                     lambda match: values.get(match[1], "<UNRESOLVED>"), commands[0])
    tokens = shlex.split(command)
    scripts = [Path(token).resolve() for token in tokens if token.endswith("/automation/core_v2_waiter.py")]
    if len(scripts) != 1:
        raise CloseError("Unexpected collector command")
    expected = {"--protocol": entry["protocol"], "--manifest": entry["manifest"],
        "--freeze": entry["freeze"], "--authorization": entry["authorization"],
        "--data-root": config["data_root"], "--wave": config["wave_id"]}
    for key, value in expected.items():
        if tokens.count(key) != 1 or tokens.index(key) + 1 >= len(tokens):
            raise CloseError("Collector input argument missing or repeated")
        actual = tokens[tokens.index(key) + 1]
        if (actual != value if key == "--wave" else Path(actual).resolve() != value):
            raise CloseError("Collector input differs from close configuration: " + key)
    cg = state.get("ControlGroup")
    if cg:
        group = (Path("/sys/fs/cgroup") / cg.lstrip("/")).resolve()
        if not group.is_relative_to(Path("/sys/fs/cgroup")):
            raise CloseError("Invalid collector control group")
        if group.exists() and any(p.read_text().strip() for p in group.rglob("cgroup.procs")):
            raise CloseError("Collector child process remains active")
    source = scripts[0].parent.parent
    install = source / "INSTALL_PROVENANCE.json"
    if not install.is_file():
        raise CloseError("Installed source provenance missing")
    return {key: state[key] for key in ("ActiveState", "MainPID", "UnitFileState", "Result") if key in state}, {
        "installed_source": str(source), "source_commit_sha": read(install)["source_commit_sha"],
        "installed_waiter_sha256": sha(scripts[0]), "install_provenance_sha256": sha(install)}


def verify_no_collector():
    for path in Path("/proc").glob("[0-9]*/cmdline"):
        try:
            tokens = path.read_bytes().split(b"\0")
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        if any(token.rsplit(b"/", 1)[-1] in {b"core_v2_waiter.py", b"core_v2_executor.py"} for token in tokens):
            raise CloseError("Active collector process remains; close aborted")


def original(aid, parents, planned):
    seen = set()
    for depth in range(3):
        if aid in seen:
            raise CloseError("Retry cycle detected")
        seen.add(aid)
        if aid in planned:
            return aid, depth + 1
        aid = parents.get(aid)
        if not aid:
            break
    raise CloseError("Attempt cannot be linked to a registered initial row")


def inspect_records(root, rows, version, protocol):
    planned = {row["attempt_id"]: row for row in rows}
    records, parents, referenced, captured, failed = [], {}, set(), set(), set()
    links, terminals = {}, {}
    counts, done = Counter(), set()
    for folder, kind in (("metadata", "capture"), ("failures", "failure")):
        for path in (root / folder).glob("*.json"):
            value = read(path)
            if path.name.startswith("retry-link-"):
                child, parent = value["retry_attempt_id"], value["original_attempt_id"]
                if child in links:
                    raise CloseError("Duplicate retry link")
                links[child] = value
            elif value.get("attempt_id"):
                child, parent = value["attempt_id"], value.get("retry_of_attempt_id")
                if path.stem != child:
                    raise CloseError("Stored attempt filename mismatch")
                records.append((value, kind))
            else:
                continue
            if child in parents and parents[child] != parent:
                raise CloseError("Conflicting retry links")
            parents[child] = parent
    for value, kind in records:
        initial, attempt = original(value["attempt_id"], parents, planned)
        row = planned[initial]
        expected_attempt = row if attempt == 1 else executor._clone_retry_row(row, attempt)
        if value["attempt_id"] != expected_attempt["attempt_id"]:
            raise CloseError("Stored retry Attempt ID is not deterministic")
        expected_parent = None if attempt == 1 else (row["attempt_id"] if attempt == 2 else executor._clone_retry_row(row, attempt - 1)["attempt_id"])
        if parents[value["attempt_id"]] != expected_parent:
            raise CloseError("Stored retry parent is not the preceding attempt")
        if value["attempt_id"] in done:
            raise CloseError("Conflicting duplicate terminal attempt")
        for key in ("protocol_version", "wave_id", "site_id", "service_lineage_id", "query_form_id", "window_id"):
            if (kind == "failure" or key in value) and value.get(key) != row[key]:
                raise CloseError("Stored attempt identity mismatch: " + key)
        if (kind == "failure" or "attempt" in value) and int(value.get("attempt", 0)) != attempt:
            raise CloseError("Stored retry number mismatch")
        done.add(value["attempt_id"])
        if kind == "capture":
            raw = (root / value["raw_file"]).resolve()
            if (not raw.is_relative_to(root) or not raw.is_file()
                    or sha(raw) != value.get("raw_file_sha256")
                    or value.get("status") != "valid_confirmatory_api_capture" or initial in captured):
                raise CloseError("Capture hash, status, path or duplicate mismatch")
            envelope = read(raw)
            if any(envelope.get(key) != row[key] for key in ("protocol_version", "wave_id", "site_id", "service_lineage_id", "query_form_id", "window_id")) or envelope.get("attempt_id") != value["attempt_id"]:
                raise CloseError("Raw envelope identity mismatch")
            if int(envelope.get("attempt", 0)) != attempt or envelope.get("retry_of_attempt_id") != parents[value["attempt_id"]]:
                raise CloseError("Raw envelope retry identity mismatch")
            for key in ("query_sha256", "protocol_file_sha256", "provider_freeze_sha256", "replication", "execution_order", "random_seed"):
                if envelope.get(key) != row[key]:
                    raise CloseError("Raw envelope frozen design mismatch: " + key)
            if envelope.get("model_id_requested") != row["model_id"] or not 200 <= envelope.get("http_status", 0) < 300:
                raise CloseError("Raw envelope model or HTTP status mismatch")
            started = runner.parse_aware_utc(envelope.get("started_at_utc"))
            completed = runner.parse_aware_utc(envelope.get("completed_at_utc"))
            lower, upper = executor._row_bounds(protocol, row)
            if not lower <= started < upper or completed < started:
                raise CloseError("Capture time is inconsistent with registered row window")
            for key in ("started_at_utc", "completed_at_utc"):
                if key in value and value[key] != envelope[key]:
                    raise CloseError("Capture metadata time differs from raw envelope")
            terminals[value["attempt_id"]] = (kind, envelope)
            referenced.add(raw)
            captured.add(initial)
            status = "captured"
        else:
            if value.get("query_sha256") != row["query_sha256"]:
                raise CloseError("Failure query hash mismatch")
            runner.parse_aware_utc(value.get("failed_at_utc"))
            terminals[value["attempt_id"]] = (kind, value)
            failed.add(initial)
            status = "failure:" + str(value.get("failure_kind")) + ":" + str(value.get("http_status"))
        counts[("attempt", row["service_lineage_id"], row["query_form_id"], row["language"], row["window_id"], str(attempt), status)] += 1
    if referenced != {path.resolve() for path in (root / "api_raw").glob("*.json")}:
        raise CloseError("Unlinked raw capture found")
    retry_due = {}
    for child, link in links.items():
        initial, attempt = original(child, parents, planned)
        row = planned[initial]
        parent = parents[child]
        expected = executor._clone_retry_row(row, attempt)
        if attempt not in {2, 3} or child != expected["attempt_id"]:
            raise CloseError("Retry link target is not a deterministic retry")
        parent_record = terminals.get(parent)
        if parent_record is None or parent_record[0] != "failure":
            raise CloseError("Retry requires a retained parent technical failure")
        failure = parent_record[1]
        for key in ("protocol_version", "wave_id", "site_id"):
            if (key == "protocol_version" or key in link) and link.get(key) != row[key]:
                raise CloseError("Retry link scope identity mismatch")
        if link.get("failure_kind") != failure.get("failure_kind"):
            raise CloseError("Retry link failure kind differs from parent")
        _, upper = executor._row_bounds(protocol, row)
        decision = executor.decide_retry(attempt=int(failure["attempt"]),
            failure_kind=failure["failure_kind"],
            failed_at=runner.parse_aware_utc(failure["failed_at_utc"]),
            provider_retry_after_seconds=failure.get("retry_after_seconds"),
            field_close=upper)
        due = runner.parse_aware_utc(link.get("due_at_utc"))
        if not decision.retry or int(decision.next_attempt) != attempt:
            raise CloseError("Retry parent failure is not eligible under registered rules")
        if due < runner.parse_aware_utc(decision.due_at_utc) or due >= upper:
            raise CloseError("Retry due violates registered wait or window")
        retry_due[child] = due
    for aid, (kind, value) in terminals.items():
        initial, attempt = original(aid, parents, planned)
        if attempt > 1:
            if aid not in retry_due:
                raise CloseError("Retained retry has no verified retry link")
            stamp = value["started_at_utc"] if kind == "capture" else value["failed_at_utc"]
            if runner.parse_aware_utc(stamp) < retry_due[aid]:
                raise CloseError("Retry started or terminated before registered due time")
    for path in (root / "dispatch").glob("*.json"):
        value = read(path)
        if value.get("attempt_id") != path.stem or path.stem not in done:
            raise CloseError("Unresolved or inconsistent dispatch; no automatic resend or close")
        initial, _ = original(path.stem, parents, planned)
        if any(value.get(key) != planned[initial][key] for key in ("protocol_version", "wave_id", "site_id", "service_lineage_id", "query_form_id")) or ("window_id" in value and value["window_id"] != planned[initial]["window_id"]):
            raise CloseError("Dispatch identity mismatch")
        dispatch_time = runner.parse_aware_utc(value.get("dispatch_at_utc"))
        lower, upper = executor._row_bounds(protocol, planned[initial])
        if not lower <= dispatch_time < upper:
            raise CloseError("Dispatch intent time is outside registered window")
        if path.stem in retry_due and dispatch_time < retry_due[path.stem]:
            raise CloseError("Retry dispatch intent predates registered due time")
        terminal_kind, terminal = terminals[path.stem]
        end = terminal["started_at_utc"] if terminal_kind == "capture" else terminal["failed_at_utc"]
        if dispatch_time > runner.parse_aware_utc(end):
            raise CloseError("Dispatch intent occurs after terminal evidence")
    suspended = set()
    for path in (root / "deviations").glob("*.json"):
        value = read(path)
        if value.get("type") in {"lineage_suspended_after_retry_exhaustion", "lineage_suspended_for_environment_mismatch"}:
            sid = value.get("service_lineage_id")
            if sid not in {row["service_lineage_id"] for row in rows}:
                raise CloseError("Suspension lineage is outside assigned scope")
            suspended.add(sid)
    cells = []
    for row in rows:
        aid, sid = row["attempt_id"], row["service_lineage_id"]
        status = ("captured" if aid in captured else "failed_no_capture" if aid in failed
                  else "missing_after_lineage_suspension" if sid in suspended else "missing_without_capture")
        cells.append([aid, sid, row["query_form_id"], row["language"], row["window_id"], status])
        counts[("planned_cell", sid, row["query_form_id"], row["language"], row["window_id"], "", status)] += 1
    summary = {sid: {"planned": sum(row[1] == sid for row in cells),
        "captured": sum(row[1] == sid and row[-1] == "captured" for row in cells),
        "without_capture": sum(row[1] == sid and row[-1] != "captured" for row in cells)}
        for sid in sorted({row["service_lineage_id"] for row in rows})}
    return cells, counts, summary


def prepare(config_path, *, current=None):
    config_path = Path(config_path).resolve()
    config = read(config_path)
    if config.get("schema_version") != "core-v2-wave-close-1":
        raise CloseError("Unknown close configuration schema")
    if not re.fullmatch(r"MIBO2-W(?:0[1-9]|1[0-2])", config.get("wave_id", "")) or not re.fullmatch(r"[A-Za-z0-9_-]+", config.get("site_id", "")):
        raise CloseError("Invalid registered wave/site identifier")
    for key in ("data_root", "backup_parent"):
        config[key] = path_at(config[key], config_path.parent)
        if not config[key].is_dir():
            raise CloseError("Configured data or backup directory missing; no automatic creation")
    entries = config.get("namespaces")
    if not isinstance(entries, list) or not entries:
        raise CloseError("Namespace assignments required")
    assigned, versions, units, work = set(), set(), set(), []
    field_close, calibration = None, None
    current = current or utc()
    if current.tzinfo is None:
        raise CloseError("Close time must be timezone aware")
    for entry in entries:
        version = entry["version"]
        if version in versions or entry["unit"] in units:
            raise CloseError("Repeated namespace or collector unit")
        versions.add(version); units.add(entry["unit"])
        scope = entry.get("lineages")
        if not isinstance(scope, list) or not scope or len(set(scope)) != len(scope) or not set(scope) <= LINEAGES or assigned & set(scope):
            raise CloseError("Invalid or overlapping lineage assignment")
        assigned.update(scope)
        for key in ("protocol", "manifest", "freeze", "authorization", "unit_file", "environment_file"):
            entry[key] = path_at(entry[key], config_path.parent)
            if not entry[key].is_file():
                raise CloseError("Required close input missing: " + key)
        hashes = {key: sha(entry[key]) for key in ("protocol", "manifest", "freeze", "authorization")}
        if hashes != entry.get("expected_hashes"):
            raise CloseError("Reviewed input hash mismatch")
        protocol, _ = runner.load_protocol(entry["protocol"])
        if protocol["protocol_version"] != version:
            raise CloseError("Namespace protocol version mismatch")
        wave = runner.wave(protocol, config["wave_id"])
        close = executor.parse_utc(wave["close_utc"])
        if field_close is not None and (field_close != close or calibration != wave["calibration_wave"]):
            raise CloseError("Mixed namespaces disagree on registered wave design")
        field_close, calibration = close, wave["calibration_wave"]
        if current < close:
            raise CloseError("Registered field window remains open")
        rows = runner.read_csv(entry["manifest"])
        errors = runner.validate_manifest(rows, protocol_path=entry["protocol"], freeze_path=entry["freeze"])
        if errors:
            raise CloseError("Full manifest validation failed: " + "; ".join(errors))
        expected = runner.generate_manifest(protocol_path=entry["protocol"], freeze_path=entry["freeze"], wave_id=config["wave_id"], site_id=config["site_id"])
        if rows != expected:
            raise CloseError("Full manifest differs from deterministic registered design")
        auth = executor.load_authorization(entry["authorization"], protocol_path=entry["protocol"], manifest_path=entry["manifest"], freeze_path=entry["freeze"], protocol=protocol, wave_id=config["wave_id"], site_id=config["site_id"])
        admitted = set(auth.get("admitted_lineages", LINEAGES))
        if set(scope) != admitted:
            raise CloseError("Assigned scope differs from private execution authorization")
        root = config["data_root"] / ("v" + version) / config["site_id"] / config["wave_id"]
        if entry.get("raw_root") and path_at(entry["raw_root"], config_path.parent) != root:
            raise CloseError("Raw root differs from registered namespace")
        if not root.is_dir():
            raise CloseError("Raw wave is absent/unexecuted; do not create a completion record")
        if (root / "closure").exists() or (root / "SHA256SUMS.txt").exists() or not root.stat().st_mode & 0o222:
            raise CloseError("Raw wave already sealed or partially closed; do not rewrite")
        before = tree_hashes(root)
        if not before or not any((root / folder).is_dir() for folder in ("metadata", "failures", "api_raw", "dispatch")):
            raise CloseError("No retained execution evidence; do not certify an unexecuted wave")
        selected = [row for row in rows if row["service_lineage_id"] in scope]
        cells, counts, summary = inspect_records(root, selected, version, protocol)
        per_lineage = 280 if calibration else 240
        if any(value["planned"] != per_lineage for value in summary.values()):
            raise CloseError("Registered per-lineage denominator mismatch")
        state, source = verify_stopped(entry, config)
        work.append({"root": root, "entry": entry, "before": before, "hashes": hashes,
            "cells": cells, "counts": counts, "summary": summary,
            "provenance": {"protocol_version": version, "unit": entry["unit"], "unit_state": state,
                **source, "input_sha256": hashes, "planned_field_close_at_utc": close.isoformat(),
                "close_tool_sha256": sha(Path(__file__).resolve()),
                "namespace_policy": "original protocol namespaces; no pooling or imputation",
                "seal_method": "root ownership; directories 0550; files 0440"}})
    if assigned != LINEAGES:
        raise CloseError("All four intended lineages require explicit namespace assignments")
    if any(config["backup_parent"].is_relative_to(item["root"]) for item in work):
        raise CloseError("Backup must be outside every raw wave tree")
    verify_no_collector()
    return config, work


def completion_name():
    with open("/dev/tty", "w", encoding="utf-8") as writer:
        writer.write("集計と欠測を確認し、終了記録に署名する氏名（空欄で中止）: ")
        writer.flush()
    with open("/dev/tty", "r", encoding="utf-8") as reader:
        return reader.readline().strip()


def csv_text(header, rows):
    out = io.StringIO(newline="")
    writer = csv.writer(out)
    writer.writerow(header); writer.writerows(rows)
    return out.getvalue()


def seal(root, gid):
    for path in list(root.rglob("*")) + [root]:
        os.chown(path, 0, gid)
        path.chmod(0o550 if path.is_dir() else 0o440)
    if any(path.stat().st_uid != 0 or path.stat().st_mode & 0o222 for path in [root] + list(root.rglob("*"))):
        raise CloseError("Read-only seal verification failed")


def finish(config, work, name):
    if os.geteuid() != 0:
        raise CloseError("Root required for raw-wave ownership seal")
    if not name.strip():
        raise CloseError("Human completion sign-off required; no files changed")
    for item in work:
        if tree_hashes(item["root"]) != item["before"] or any(sha(item["entry"][key]) != value for key, value in item["hashes"].items()):
            raise CloseError("Evidence changed during completion review; no files changed")
        verify_stopped(item["entry"], config)
    verify_no_collector()
    gid = grp.getgrnam("mibo").gr_gid
    signed_at = utc().isoformat()
    for item in work:
        root, entry = item["root"], item["entry"]
        close = root / "closure"
        close.mkdir(mode=0o700)
        write(close / "OBSERVATION_STATUS.csv", csv_text(["initial_attempt_id", "service_lineage_id", "query_form_id", "language", "window_id", "status"], item["cells"]))
        write(close / "COMPLETION_COUNTS.csv", csv_text(["unit", "service_lineage_id", "query_form_id", "language", "window_id", "attempt", "status", "count"], [list(key) + [value] for key, value in sorted(item["counts"].items())]))
        for label in item["hashes"]:
            write(close / ("FROZEN_" + label.upper() + entry[label].suffix), entry[label].read_bytes())
        write(close / "PROVENANCE.json", encoded(item["provenance"]))
        write(close / "COMPLETION_RECORD.json", encoded({"wave_id": config["wave_id"], "site_id": config["site_id"],
            "planned_field_close_at_utc": item["provenance"]["planned_field_close_at_utc"],
            "signed_at_utc": signed_at, "operations_lead": name.strip(),
            "attestation_method": "typed_name_after_completion_summary_review",
            "status": "closed_with_retained_missingness", "summary": item["summary"],
            "capture_is_not_content_analysis_eligibility": True,
            "independent_backup_at_signoff": "not_verified"}))
        sums = tree_hashes(root)
        write(root / "SHA256SUMS.txt", "".join(value + "  " + key + "\n" for key, value in sums.items()))
        seal(root, gid)
        if any(sha(root / key) != value for key, value in sums.items()):
            raise CloseError("Post-seal hash mismatch")
    backup = config["backup_parent"] / (config["wave_id"] + "-close-" + utc().strftime("%Y%m%dT%H%M%S%fZ"))
    backup.mkdir(mode=0o700)
    archive_path = backup / (config["wave_id"] + "-sealed.tar.gz")
    expected = {}
    with tarfile.open(archive_path, "x:gz", dereference=True) as archive:
        for item in work:
            prefix = "v" + item["entry"]["version"] + "/" + config["site_id"] + "/" + config["wave_id"]
            expected.update({prefix + "/" + key: value for key, value in tree_hashes(item["root"]).items()})
            archive.add(item["root"], arcname=prefix)
    checked = set()
    with tarfile.open(archive_path, "r:gz") as archive:
        for member in archive:
            if member.isfile():
                h = hashlib.sha256()
                with archive.extractfile(member) as fh:
                    for block in iter(lambda: fh.read(1048576), b""):
                        h.update(block)
                if member.name in checked or expected.get(member.name) != h.hexdigest():
                    raise CloseError("Archive content verification failed")
                checked.add(member.name)
    if checked != set(expected):
        raise CloseError("Archive is incomplete")
    write(backup / "CLOSE_RECEIPT.json", encoded({"wave_id": config["wave_id"], "site_id": config["site_id"],
        "archive_verified_at_utc": utc().isoformat(), "archive_sha256": sha(archive_path),
        "wave_manifest_sha256": {item["entry"]["version"]: sha(item["root"] / "SHA256SUMS.txt") for item in work},
        "backup_scope": "same_VM_local_export_only; independent_backup_not_verified"}))
    write(backup / "SHA256SUMS.txt", sha(archive_path) + "  " + archive_path.name + "\n" + sha(backup / "CLOSE_RECEIPT.json") + "  CLOSE_RECEIPT.json\n")
    seal(backup, gid)
    os.sync()
    return archive_path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--execute", action="store_true", help="Sign and seal after explicit TTY human review; default is read-only")
    args = parser.parse_args(argv)
    config, work = prepare(args.config)
    print(encoded({"wave_id": config["wave_id"], "site_id": config["site_id"],
        "namespaces": {item["entry"]["version"]: item["summary"] for item in work},
        "content_analysis_eligibility": "not_assessed", "independent_backup": "not_verified"}).strip())
    if not args.execute:
        print("CLOSE_PREFLIGHT=PASS / NO_FILES_CHANGED")
        return 0
    if os.geteuid() != 0:
        raise CloseError("Root required before requesting completion sign-off")
    archive = finish(config, work, completion_name())
    print("RAW_WAVE_SEAL=PASS / ARCHIVE_CONTENT_VERIFY=PASS")
    print("私有保存先:", archive)
    print("INDEPENDENT_BACKUP=NOT_VERIFIED (同VM保存; VM外への保存と復元確認は別工程)")
    return 0


def run_cli(argv=None):
    try:
        return main(argv)
    except CloseError as exc:
        print("終了処理を中断: " + str(exc), file=sys.stderr)
    except Exception as exc:
        print("終了処理を中断 (" + type(exc).__name__ + "): 私有環境で原因を確認してください。", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(run_cli())
