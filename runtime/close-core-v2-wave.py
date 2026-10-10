#!/usr/bin/env python3
"""Offline, human-signed Core v2 wave closure; no provider calls or answer parsing.

Default is a read-only inspection. ``--close`` requires root, disabled collectors,
the registered close time, lineage/namespace locks and a real terminal sign-off.
A complete candidate archive is checked before any raw-wave file is changed.
W01 remains owned by its preserved, pinned closure helper.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import ExitStack
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
import shutil
import stat
import subprocess
import sys
import tarfile
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "automation"))
import core_v2_executor as executor
import core_v2_execution_state as execution_state
import core_v2_runner as runner
import runtime_health

UNIT_DIRECTORY = Path("/etc/systemd/system")
PROC_DIRECTORY = Path("/proc")
ENV_KEYS = {
    "MIBO_CORE_V2_PROTOCOL", "MIBO_CORE_V2_MANIFEST", "MIBO_CORE_V2_FREEZE",
    "MIBO_CORE_V2_AUTHORIZATION", "MIBO_DATA_ROOT", "MIBO_CORE_V2_SOURCE_COMMIT",
    "MIBO_CORE_V2_WAVE", "MIBO_RUNTIME_HOST",
    "MIBO_CORE_V2_EXPECTED_HOST", "MIBO_EXPECTED_HOST", "MIBO_SOURCE_COMMIT",
}


class CloseError(ValueError):
    """A disclosure-safe operational reason for stopping closure."""


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha(path: Path) -> str:
    return runner.sha256_file(path)


def encoded(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def read_record(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CloseError("Technical record must be an object")
    return value


def safe_tree(root: Path) -> dict[str, str]:
    if root.is_symlink() or not root.is_dir():
        raise CloseError("Wave root must be a real directory")
    files = {}
    for path in [root, *sorted(root.rglob("*"))]:
        info = path.lstat()
        relative = path.relative_to(root).as_posix()
        if (path.is_symlink() or not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode))
                or any(ord(c) < 32 or c == "\\" for c in relative)):
            raise CloseError("Wave contains an unsafe path, symlink, or special file")
        if stat.S_ISREG(info.st_mode):
            if info.st_nlink != 1:
                raise CloseError("Wave contains a hard-linked file")
            files[relative] = sha(path)
    return files


def collector_state(unit: str) -> dict[str, str]:
    if not re.fullmatch(r"mibo-[a-zA-Z0-9_.-]+\.service", unit):
        raise CloseError("Expected an explicit MIBO systemd service name")
    properties = ("ActiveState", "MainPID", "UnitFileState", "ControlGroup", "Result",
                  "InactiveEnterTimestamp", "FragmentPath", "DropInPaths")
    output = subprocess.check_output(["systemctl", "show", unit,
        *[arg for name in properties for arg in ("-p", name)]], text=True)
    state = dict(line.split("=", 1) for line in output.splitlines() if "=" in line)
    if (state.get("ActiveState") not in {"inactive", "failed"} or state.get("MainPID") != "0"
            or state.get("UnitFileState") != "disabled"):
        raise CloseError("Collector must be stopped and disabled: " + unit)
    if state.get("DropInPaths"):
        raise CloseError("Collector has unsupported systemd drop-ins; review effective configuration")
    group = state.get("ControlGroup", "")
    if group:
        if ".." in Path(group).parts:
            raise CloseError("Unexpected collector cgroup path")
        directory = Path("/sys/fs/cgroup") / group.lstrip("/")
        if directory.exists() and any(p.read_text().strip() for p in directory.rglob("cgroup.procs")):
            raise CloseError("Collector child process is still active")
    return state


def no_active_collectors() -> None:
    for path in PROC_DIRECTORY.glob("[0-9]*/cmdline"):
        try:
            tokens = path.read_bytes().split(b"\0")
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
        if any(t.rsplit(b"/", 1)[-1] in {b"core_v2_waiter.py", b"core_v2_executor.py"} for t in tokens):
            raise CloseError("An active Core v2 collector remains; closure aborted")


def unit_arguments(unit: str, state: dict[str, str]) -> tuple[list[str], dict[Path, str]]:
    path = UNIT_DIRECTORY / unit
    if path.is_symlink() or not path.is_file():
        raise CloseError("Collector unit must be a regular reviewed file")
    if state.get("FragmentPath") != str(path):
        raise CloseError("Collector unit differs from the loaded systemd fragment")
    text = path.read_text(encoding="utf-8")
    service_lines, section = [], ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", ";")):
            continue
        if line.startswith("["):
            section = line
        elif section == "[Service]":
            if line.endswith("\\"):
                raise CloseError("Multiline systemd commands require manual configuration review")
            service_lines.append(line)
    commands = [line.split("=", 1)[1] for line in service_lines if line.startswith("ExecStart=")]
    if len(commands) != 1:
        raise CloseError("Collector requires exactly one explicit ExecStart")
    environment: dict[str, str] = {}
    bound_files = {path: sha(path)}
    for line in service_lines:
        if line.startswith("Environment="):
            for item in shlex.split(line.split("=", 1)[1]):
                key, separator, value = item.partition("=")
                if separator and key in ENV_KEYS:
                    environment[key] = value
    # systemd EnvironmentFile values override Environment values. Only the
    # reviewed path/provenance keys are parsed; credential values are ignored.
    for line in service_lines:
        if not line.startswith("EnvironmentFile="):
            continue
        filenames = shlex.split(line.split("=", 1)[1])
        if len(filenames) != 1 or any(c in filenames[0] for c in "*?[]%$"):
            raise CloseError("Unsupported systemd EnvironmentFile form")
        optional = filenames[0].startswith("-")
        env_path = Path(filenames[0].lstrip("-"))
        if not env_path.is_absolute() or env_path.is_symlink():
            raise CloseError("EnvironmentFile must be an absolute regular private file")
        if optional and not env_path.exists():
            continue
        bound_files[env_path] = sha(env_path)
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            key, separator, value = raw.partition("=")
            if not separator or key not in ENV_KEYS:
                continue
            parts = shlex.split(value)
            if len(parts) != 1:
                raise CloseError("Runtime path environment value must be a single token")
            environment[key] = parts[0]
    arguments = []
    for argument in shlex.split(commands[0]):
        if argument.startswith("${") and argument.endswith("}"):
            key = argument[2:-1]
            if key not in ENV_KEYS or not environment.get(key):
                raise CloseError("Unresolved reviewed runtime environment argument")
            argument = environment[key]
        if any(c in argument for c in ("$", "%", "\x00", "\n", "\r")):
            raise CloseError("Unsupported systemd argument expansion")
        arguments.append(argument)
    return arguments, bound_files


def load_unit(unit: str, wave: str, site: str, now: datetime) -> dict[str, Any]:
    state = collector_state(unit)
    arguments, bound_files = unit_arguments(unit, state)
    def argument(name: str) -> str:
        if arguments.count(name) != 1 or arguments.index(name) + 1 >= len(arguments):
            raise CloseError("Missing or repeated bound collector argument: " + name)
        return arguments[arguments.index(name) + 1]
    if argument("--wave") != wave:
        raise CloseError("Collector unit is bound to a different wave")
    inputs = {}
    for name in ("protocol", "manifest", "freeze", "authorization"):
        path = Path(argument("--" + name))
        if not path.is_absolute() or path.is_symlink() or not path.is_file():
            raise CloseError("Bound input must be an absolute regular file")
        inputs[name] = path.resolve()
    hashes = {name: sha(path) for name, path in inputs.items()}
    protocol, _ = runner.load_protocol(inputs["protocol"])
    bounds = runner.wave(protocol, wave)
    if now.tzinfo is None or now.astimezone(timezone.utc) < runner.parse_aware_utc(bounds["close_utc"]):
        raise CloseError("Registered field window has not closed")
    rows = runner.read_csv(inputs["manifest"])
    if any(row.get("wave_id") != wave or row.get("site_id") != site for row in rows):
        raise CloseError("Manifest wave/site identity mismatch")
    errors = runner.validate_manifest(rows, protocol_path=inputs["protocol"], freeze_path=inputs["freeze"])
    if errors or rows != runner.generate_manifest(protocol_path=inputs["protocol"],
            freeze_path=inputs["freeze"], wave_id=wave, site_id=site):
        raise CloseError("Bound manifest failed structural or deterministic integrity validation")
    authorization = executor.load_authorization(inputs["authorization"],
        protocol_path=inputs["protocol"], manifest_path=inputs["manifest"],
        freeze_path=inputs["freeze"], protocol=protocol, wave_id=wave, site_id=site)
    admitted = authorization.get("admitted_lineages") if protocol["protocol_version"] in runner.SCOPED_PROTOCOL_VERSIONS else protocol["required_service_lineages"]
    rows = [row for row in rows if row["service_lineage_id"] in admitted]
    if not rows:
        raise CloseError("Authorization has no admitted manifest rows")
    data_root = Path(argument("--data-root"))
    if not data_root.is_absolute():
        raise CloseError("Collector data root must be absolute")
    root = data_root.resolve() / ("v" + protocol["protocol_version"]) / site / wave
    if not root.is_dir() or root.is_symlink() or (root / "closure").exists() or (root / "SHA256SUMS.txt").exists():
        raise CloseError("Missing wave or existing closure; preserve it and review before recovery")
    sources = [Path(arg).resolve().parents[1] for arg in arguments if arg.endswith("/automation/core_v2_waiter.py")]
    if len(sources) != 1:
        raise CloseError("Collector source cannot be resolved from the reviewed waiter command")
    source = sources[0]
    provenance = runtime_health.provenance_state(source)
    if not provenance.get("commit_resolved") or not provenance.get("working_tree_clean"):
        raise CloseError("Installed collector source provenance/integrity failed")
    if "--expected-source-commit" in arguments and argument("--expected-source-commit") != provenance["commit_sha"]:
        raise CloseError("Collector source differs from the prospectively bound commit")
    if "--expected-host" in arguments:
        import socket
        if argument("--expected-host") != socket.gethostname().split(".", 1)[0]:
            raise CloseError("Collector unit is bound to a different runtime host")
    authorization_hash_fields = {"protocol": "protocol_file_sha256",
        "manifest": "manifest_sha256", "freeze": "provider_freeze_sha256"}
    if (any(sha(path) != hashes[name] for name, path in inputs.items())
            or any(authorization.get(field) != hashes[label]
                   for label, field in authorization_hash_fields.items())):
        raise CloseError("Bound inputs changed during closure configuration validation")
    return dict(unit=unit, state=state, root=root, data_root=data_root.resolve(), rows=rows, admitted=list(admitted),
        inputs=inputs, hashes=hashes, bounds=bounds, protocol=protocol,
        source=source, source_commit=provenance["commit_sha"], bound_files=bound_files,
        inspection_clock=now.astimezone(timezone.utc))


def inspect(config: dict[str, Any]) -> dict[str, Any]:
    root, rows = config["root"], config["rows"]
    original_rows = {row["attempt_id"]: row for row in rows}
    row_map, initial_ids = {}, {}
    for row in rows:
        initial = row["attempt_id"]
        variants = [row]
        for number in (2, 3):
            variants.append(executor._clone_retry_row(variants[-1], number))
        for variant in variants:
            row_map[variant["attempt_id"]] = variant
            initial_ids[variant["attempt_id"]] = initial
    hashes = safe_tree(root)
    restored_state = execution_state.restore(root=root, initial_rows=rows,
        clone_retry=executor._clone_retry_row,
        row_bounds=lambda row: executor._row_bounds(config["protocol"], row),
        data_root=root.parents[2], authorization_sha256=config["hashes"]["authorization"],
        persist=False, current=config["inspection_clock"])
    captured, failed, uncertain, seen, raw_references = set(), set(), set(), set(), set()
    counts = Counter()
    for folder, kind in (("metadata", "capture"), ("failures", "failure"), ("dispatch", "dispatch")):
        for path in sorted((root / folder).glob("*.json")):
            record = read_record(path)
            if path.name.startswith("first-dispatch-") and folder == "metadata":
                if (record.get("initial_attempt_id") not in original_rows
                        or record.get("service_lineage_id") not in config["admitted"]):
                    raise CloseError("First-dispatch identity mismatch")
                continue
            if path.name.startswith("retry-link-") and folder == "metadata":
                aid = record.get("retry_attempt_id")
                if (aid not in row_map or row_map[aid]["attempt"] == 1
                        or path.stem != "retry-link-" + aid
                        or record.get("original_attempt_id") != row_map[aid].get("retry_of_attempt_id")
                        or record.get("protocol_version") != config["protocol"]["protocol_version"]):
                    raise CloseError("Stored retry link differs from the registered Attempt ID")
                continue
            aid = record.get("attempt_id")
            if aid not in row_map or path.stem != aid:
                raise CloseError("Unregistered retained attempt identity")
            row = row_map[aid]
            execution_state._bind(record, row, claim=kind == "dispatch")
            if "attempt" in record and int(record["attempt"]) != row["attempt"]:
                raise CloseError("Stored attempt number differs from the registered retry")
            for field in ("site_id", "wave_id", "query_form_id", "language", "query_sha256"):
                if field in record and record[field] != row[field]:
                    raise CloseError("Stored attempt frozen identity mismatch")
            if kind == "dispatch":
                if (record.get("type") != "attempt_dispatch_claim"
                        or record.get("authorization_sha256") != config["hashes"]["authorization"]):
                    raise CloseError("Retained dispatch authorization mismatch")
                uncertain.add(aid)
                continue
            if aid in seen:
                raise CloseError("Attempt has duplicate or conflicting terminal records")
            seen.add(aid)
            if kind == "capture":
                relative = "api_raw/" + aid + ".json"
                if (record.get("raw_file") != relative or hashes.get(relative) != record.get("raw_file_sha256")
                        or record.get("status") != "valid_confirmatory_api_capture"
                        or initial_ids[aid] in captured):
                    raise CloseError("Capture hash, status, path, or duplicate mismatch")
                raw_references.add(aid)
                captured.add(initial_ids[aid])
                status = "captured"
            else:
                if not isinstance(record.get("failure_kind"), str):
                    raise CloseError("Failure has no registered technical classification")
                failed.add(initial_ids[aid])
                status = "failure:" + record["failure_kind"] + ":" + str(record.get("http_status"))
            counts[("attempt", row["service_lineage_id"], row["query_form_id"], row["language"], row["window_id"], str(row["attempt"]), status)] += 1
    # A crash can retain raw bytes before their terminal metadata is written.
    # Preserve those bytes as unresolved, never promote them to a valid capture.
    for path in (root / "api_raw").iterdir() if (root / "api_raw").exists() else []:
        if path.suffix != ".json" or path.stem not in row_map:
            raise CloseError("Unregistered or unexpected raw capture file")
        if path.stem not in raw_references:
            if path.stem in seen:
                raise CloseError("Raw-only bytes conflict with a terminal failure")
            uncertain.add(path.stem)
    uncertain -= seen
    uncertain_cells = {initial_ids[aid] for aid in uncertain}
    for aid in sorted(uncertain):
        row = row_map[aid]
        counts[("retained_unresolved_attempt", row["service_lineage_id"], row["query_form_id"], row["language"], row["window_id"], str(row["attempt"]), "outcome_unknown_without_terminal_metadata")] += 1
    suspended = set(restored_state.suspended)
    for path in (root / "deviations").glob("*.json"):
        record = read_record(path)
        if "suspend" in str(record.get("type", "")):
            sid = record.get("service_lineage_id")
            if sid not in config["admitted"]:
                raise CloseError("Suspension refers to an unauthorized lineage")
            suspended.add(sid)
    cells, summary = [], {}
    for row in rows:
        initial, sid = row["attempt_id"], row["service_lineage_id"]
        status = ("captured" if initial in captured else "outcome_unknown_without_terminal_metadata" if initial in uncertain_cells
            else "failed_no_capture" if initial in failed else "missing_after_lineage_suspension" if sid in suspended else "missing_without_capture")
        cells.append([initial, sid, row["query_form_id"], row["language"], row["window_id"], status])
        counts[("planned_cell", sid, row["query_form_id"], row["language"], row["window_id"], "", status)] += 1
    for sid in config["admitted"]:
        subset = [row for row in cells if row[1] == sid]
        summary[sid] = dict(planned=len(subset), captured=sum(row[-1] == "captured" for row in subset),
            without_capture=sum(row[-1] != "captured" for row in subset),
            unresolved=sum(row[-1] == "outcome_unknown_without_terminal_metadata" for row in subset))
    return dict(cells=cells, counts=counts, summary=summary, original_hashes=hashes)


def csv_bytes(header: list[str], rows: Any) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(header)
    writer.writerows(rows)
    return stream.getvalue().encode()


def completion_name() -> str:
    with open("/dev/tty", "w", encoding="utf-8") as writer:
        writer.write("集計・欠測・未確定結果を確認し、終了記録に署名する氏名（空欄で中止）: ")
        writer.flush()
    with open("/dev/tty", "r", encoding="utf-8") as reader:
        return reader.readline().strip()


def write_exclusive(path: Path, data: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def seal(root: Path, gid: int) -> None:
    safe_tree(root)
    for path in [*root.rglob("*"), root]:
        os.chown(path, 0, gid)
        path.chmod(0o550 if path.is_dir() else 0o440)
    if any(path.stat().st_uid != 0 or path.stat().st_mode & 0o222 for path in [root, *root.rglob("*")]):
        raise CloseError("Read-only seal verification failed")


def closure_bytes(config: dict[str, Any], inspection: dict[str, Any], name: str, signed_at: str) -> dict[str, bytes]:
    files = {
        "closure/OBSERVATION_STATUS.csv": csv_bytes(["initial_attempt_id", "service_lineage_id", "query_form_id", "language", "window_id", "status"], inspection["cells"]),
        "closure/COMPLETION_COUNTS.csv": csv_bytes(["unit", "service_lineage_id", "query_form_id", "language", "window_id", "attempt", "status", "count"],
            [list(key) + [value] for key, value in sorted(inspection["counts"].items())]),
    }
    for label, path in config["inputs"].items():
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != config["hashes"][label]:
            raise CloseError("Bound input changed while preparing its frozen closure copy")
        files["closure/FROZEN_" + label.upper() + path.suffix] = data
    files["closure/PROVENANCE.json"] = encoded(dict(protocol_version=config["protocol"]["protocol_version"],
        unit=config["unit"], unit_state=config["state"], installed_source=str(config["source"]),
        source_commit_sha=config["source_commit"], close_tool_sha256=sha(Path(__file__).resolve()),
        input_sha256=config["hashes"], admitted_lineages=config["admitted"],
        planned_field_close_at_utc=config["bounds"]["close_utc"],
        namespace_policy="Original protocol namespaces and authorized scopes; no pooling or imputation",
        seal_method="root ownership; directories 0550; files 0440"))
    files["closure/COMPLETION_RECORD.json"] = encoded(dict(wave_id=config["rows"][0]["wave_id"],
        site_id=config["rows"][0]["site_id"], planned_field_close_at_utc=config["bounds"]["close_utc"],
        signed_at_utc=signed_at, operations_lead=name, attestation_method="typed_name_after_completion_summary_review",
        status="closed_with_retained_missingness", summary=inspection["summary"],
        scientific_capture_complete=all(value["without_capture"] == 0 for value in inspection["summary"].values()),
        independent_backup_at_signoff="not_yet_verified", imputation_performed=False))
    hashes = {**inspection["original_hashes"], **{path: hashlib.sha256(data).hexdigest() for path, data in files.items()}}
    files["SHA256SUMS.txt"] = "".join(digest + "  " + path + "\n" for path, digest in sorted(hashes.items())).encode()
    return files


def recheck(config: dict[str, Any], inspection: dict[str, Any]) -> None:
    """Revalidate the exact reviewed runtime and bytes before any raw mutation."""
    state = collector_state(config["unit"])
    provenance = runtime_health.provenance_state(config["source"])
    if (state != config["state"] or not provenance.get("commit_resolved")
            or not provenance.get("working_tree_clean")
            or provenance.get("commit_sha") != config["source_commit"]
            or safe_tree(config["root"]) != inspection["original_hashes"]
            or any(sha(path) != digest for path, digest in config["bound_files"].items())
            or any(sha(path) != config["hashes"][label] for label, path in config["inputs"].items())):
        raise CloseError("Runtime, bound inputs or retained wave changed during completion review")


def close_wave(*, units: list[str], wave: str, site: str = "JP01", private_root: Path = Path("/srv/mibo-private"),
               perform_close: bool = False, now: datetime | None = None) -> dict[str, Any]:
    if not re.fullmatch(r"MIBO2-W(?:0[1-9]|1[0-2])", wave) or not re.fullmatch(r"[A-Z0-9_-]+", site):
        raise CloseError("Expected a registered Core v2 wave and safe site identifier")
    if not units or len(units) != len(set(units)):
        raise CloseError("Supply an explicit, unique collector unit list")
    if perform_close and (os.geteuid() != 0 or wave == "MIBO2-W01"):
        raise CloseError("Closure requires root; W01 must remain under its preserved helper")
    current = now or datetime.now(timezone.utc)
    configs = [load_unit(unit, wave, site, current) for unit in units]
    roots, scopes = set(), set()
    for config in configs:
        if config["root"] in roots or scopes.intersection(config["admitted"]):
            raise CloseError("Collector namespaces or authorized lineage scopes overlap")
        roots.add(config["root"])
        scopes.update(config["admitted"])
    no_active_collectors()
    with ExitStack() as stack:
        if perform_close:
            by_data_root: dict[Path, set[str]] = {}
            for config in configs:
                by_data_root.setdefault(config["data_root"], set()).update(config["admitted"])
            # Match the executor's lock order: cross-version lineage locks first,
            # then namespace locks. Hold both through sign-off, archive and seal.
            for data_root, lineages in sorted(by_data_root.items()):
                stack.enter_context(execution_state.lineage_locks(data_root, site, wave, lineages))
            for root in sorted(roots):
                stack.enter_context(execution_state.wave_lock(root))
            no_active_collectors()
        inspections = [inspect(config) for config in configs]
        report = dict(wave_id=wave, site_id=site, registered_panel_fully_included=scopes == set(configs[0]["protocol"]["required_service_lineages"]),
            namespaces={"v" + config["protocol"]["protocol_version"]: item["summary"] for config, item in zip(configs, inspections)},
            closure_performed=False, independent_backup_verified=False)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2), flush=True)
        if not perform_close:
            return report
        name = completion_name()
        if not name:
            raise CloseError("Human completion sign-off not supplied; raw wave unchanged")
        no_active_collectors()
        for config, item in zip(configs, inspections):
            recheck(config, item)
        signed_at = utc()
        staged = [closure_bytes(config, item, name, signed_at) for config, item in zip(configs, inspections)]
        if private_root.is_symlink() or not private_root.is_dir():
            raise CloseError("Private export root must already exist as a real directory")
        raw_bytes = sum((config["root"] / relative).stat().st_size for config, item in zip(configs, inspections) for relative in item["original_hashes"])
        needed = raw_bytes * 2 + sum(len(data) for files in staged for data in files.values()) + 64 * 1024 * 1024
        if shutil.disk_usage(private_root).free < needed:
            raise CloseError("Private export disk lacks the verified archive reserve")
        for config, files in zip(configs, staged):
            if shutil.disk_usage(config["root"]).free < 2 * sum(map(len, files.values())) + 4 * 1024 * 1024:
                raise CloseError("Wave disk lacks the closure-record reserve")
        gid = grp.getgrnam("mibo").gr_gid
        backup = private_root / (wave + "-close-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
        backup.mkdir(mode=0o700)
        archive_path = backup / (wave + "-sealed.tar.gz")
        expected = {}
        def archive_filter(member: tarfile.TarInfo) -> tarfile.TarInfo:
            if not (member.isdir() or member.isfile()):
                raise CloseError("Unsafe candidate archive member")
            member.uid, member.gid = 0, gid
            member.mode = 0o550 if member.isdir() else 0o440
            return member
        with tarfile.open(archive_path, "x:gz", dereference=False) as archive:
            for config, item, files in zip(configs, inspections, staged):
                prefix = "v" + config["protocol"]["protocol_version"] + "/" + site + "/" + wave
                archive.add(config["root"], arcname=prefix, filter=archive_filter)
                directory = tarfile.TarInfo(prefix + "/closure")
                directory.type, directory.mode, directory.uid, directory.gid = tarfile.DIRTYPE, 0o550, 0, gid
                archive.addfile(directory)
                expected.update({prefix + "/" + path: digest for path, digest in item["original_hashes"].items()})
                for path, data in sorted(files.items()):
                    member = tarfile.TarInfo(prefix + "/" + path)
                    member.size, member.mode, member.uid, member.gid = len(data), 0o440, 0, gid
                    archive.addfile(member, io.BytesIO(data))
                    expected[member.name] = hashlib.sha256(data).hexdigest()
        with archive_path.open("rb") as handle:
            os.fsync(handle.fileno())
        import core_v2_archive_verify as verifier
        verifier.verify_tar_content(archive_path, expected)
        no_active_collectors()
        for config, item in zip(configs, inspections):
            recheck(config, item)
        # Only this point begins raw-wave mutation. No archive/receipt failure
        # before this point can create a partial original-wave closure.
        for config, item, files in zip(configs, inspections, staged):
            if safe_tree(config["root"]) != item["original_hashes"]:
                raise CloseError("Retained wave changed before final seal")
            (config["root"] / "closure").mkdir(mode=0o700)
            for path, data in sorted(files.items()):
                write_exclusive(config["root"] / path, data)
            seal(config["root"], gid)
            prefix = "v" + config["protocol"]["protocol_version"] + "/" + site + "/" + wave
            if safe_tree(config["root"]) != {key[len(prefix) + 1:]: value for key, value in expected.items() if key.startswith(prefix + "/")}:
                raise CloseError("Post-seal wave hash mismatch; preserve records for recovery")
        sealed_at = utc()
        receipt = dict(wave_id=wave, site_id=site, sealed_at_utc=sealed_at,
            archive_verified_at_utc=utc(), archive_sha256=sha(archive_path),
            wave_manifest_sha256={"v" + config["protocol"]["protocol_version"]: sha(config["root"] / "SHA256SUMS.txt") for config in configs},
            backup_scope="same_VM_local_export_only; independent_backup_pending")
        receipt_path = backup / "CLOSE_RECEIPT.json"
        write_exclusive(receipt_path, encoded(receipt))
        receipt_hash = sha(receipt_path)
        verification = verifier.verify_archive(archive=archive_path, receipt=receipt_path,
            expected_receipt_sha256=receipt_hash, wave=wave, site=site)
        write_exclusive(backup / "SHA256SUMS.txt", (sha(archive_path) + "  " + archive_path.name + "\n" + receipt_hash + "  CLOSE_RECEIPT.json\n").encode())
        seal(backup, gid)
        os.sync()
        report.update(closure_performed=True, raw_wave_seal="PASS", archive_content_verify="PASS",
            archive_path=str(archive_path), receipt_path=str(receipt_path), receipt_sha256=receipt_hash,
            sealed_at_utc=sealed_at, independent_backup_verified=False, archive_verification=verification)
        print("RAW_WAVE_SEAL=PASS / ARCHIVE_CONTENT_VERIFY=PASS", flush=True)
        print("INDEPENDENT_BACKUP=PENDING; retain this receipt SHA-256 outside the VM:", receipt_hash, flush=True)
        return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--unit", required=True, action="append")
    parser.add_argument("--wave", required=True)
    parser.add_argument("--site", default="JP01")
    parser.add_argument("--private-root", default=Path("/srv/mibo-private"), type=Path)
    parser.add_argument("--close", action="store_true", help="Seal only after real terminal completion sign-off")
    args = parser.parse_args()
    result = close_wave(units=args.unit, wave=args.wave, site=args.site,
        private_root=args.private_root, perform_close=args.close)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CloseError as exc:
        raise SystemExit("Offline wave close stopped: " + str(exc))
    except (ValueError, RuntimeError, OSError, subprocess.CalledProcessError):
        # Never echo provider error bodies, authorization JSON or credentials.
        raise SystemExit("Offline wave close failed; preserve existing data and review the technical state")
