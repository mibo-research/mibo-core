#!/usr/bin/env python3
"""Offline MIBO2-W01 close. Never dispatches API requests or reads answer content."""
import csv
import grp
import hashlib
import io
import json
import os
import shlex
import subprocess
import tarfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

WAVE = "MIBO2-W01"
FIELD_CLOSE = "2026-10-08T00:00:00+00:00"
LABELS = {"MIBO-SL-001": "OpenAI", "MIBO-SL-002": "Anthropic",
          "MIBO-SL-003": "Google", "MIBO-SL-004": "Perplexity"}

def utc():
    return datetime.now(timezone.utc).isoformat()

def read(p):
    return json.loads(Path(p).read_text())

def sha(p):
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda: f.read(1048576), b""):
            h.update(b)
    return h.hexdigest()

def write(p, content):
    with Path(p).open("xb") as f:
        f.write(content.encode() if isinstance(content, str) else content)
        f.flush()
        os.fsync(f.fileno())

def encoded(v):
    return json.dumps(v, ensure_ascii=False, sort_keys=True, indent=2) + "\n"

def original(aid, parents, planned):
    seen = set()
    for depth in range(3):
        if aid in seen:
            raise ValueError("Retry cycle detected")
        seen.add(aid)
        if aid in planned:
            return aid, depth + 1
        aid = parents.get(aid)
        if not aid:
            break
    raise ValueError("Attempt cannot be linked to a registered initial row")

def inspect(root, manifest, admitted, version, input_hashes):
    with manifest.open(newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["service_lineage_id"] in admitted]
    planned = {r["attempt_id"]: r for r in rows}
    if any(r.get("wave_id") != WAVE or r.get("site_id") != "JP01" or r.get("protocol_version") != version or int(r.get("attempt", 0)) != 1 or r.get("protocol_file_sha256") != input_hashes["protocol"] or r.get("provider_freeze_sha256") != input_hashes["freeze"] for r in rows):
        raise ValueError("Frozen manifest, protocol, or provider identity mismatch")
    if len(planned) != len(rows) or len(rows) != 280 * len(admitted):
        raise ValueError("Manifest count or identity mismatch")
    for sid in admitted:
        if Counter(r["window_id"] for r in rows if r["service_lineage_id"] == sid) != {"WA": 40, "STD": 200, "WB": 40}:
            raise ValueError("Registered window counts mismatch")
    items = [root] + list(root.rglob("*"))
    if any(p.is_symlink() or not (p.is_file() or p.is_dir()) for p in items):
        raise ValueError("Unexpected symlink or special file in raw wave")
    records, parents, counts, captured, failed, referenced = [], {}, Counter(), set(), set(), set()
    for folder, kind in (("metadata", "capture"), ("failures", "failure")):
        for p in (root / folder).glob("*.json"):
            v = read(p)
            if p.name.startswith("retry-link-"):
                child, parent = v["retry_attempt_id"], v["original_attempt_id"]
            elif v.get("attempt_id"):
                child, parent = v["attempt_id"], v.get("retry_of_attempt_id")
                records.append((v, kind))
            else:
                continue
            if child in parents and parents[child] != parent:
                raise ValueError("Conflicting retry links")
            parents[child] = parent
    seen_attempts = set()
    for v, kind in records:
        aid, attempt = original(v["attempt_id"], parents, planned)
        row = planned[aid]
        if v["attempt_id"] in seen_attempts or v.get("protocol_version") != version or v.get("service_lineage_id") != row["service_lineage_id"] or v.get("window_id") != row["window_id"]:
            raise ValueError("Stored attempt identity mismatch")
        seen_attempts.add(v["attempt_id"])
        if kind == "capture":
            raw = (root / v["raw_file"]).resolve()
            if not raw.is_relative_to(root) or sha(raw) != v["raw_file_sha256"] or v.get("status") != "valid_confirmatory_api_capture" or aid in captured:
                raise ValueError("Capture hash, status, path, or duplicate mismatch")
            referenced.add(raw)
            captured.add(aid)
            status = "captured"
        else:
            if int(v["attempt"]) != attempt:
                raise ValueError("Stored retry number mismatch")
            failed.add(aid)
            status = "failure:" + str(v.get("failure_kind")) + ":" + str(v.get("http_status"))
        key = ("attempt", row["service_lineage_id"], row["query_form_id"], row["language"], row["window_id"], str(attempt), status)
        counts[key] += 1
    if referenced != {p.resolve() for p in (root / "api_raw").glob("*.json")}:
        raise ValueError("Unlinked raw capture found")
    suspended = {v.get("service_lineage_id") for p in (root / "deviations").glob("*.json") for v in [read(p)] if "suspend" in str(v.get("type", ""))}
    cells, summary = [], {}
    for row in rows:
        aid, sid = row["attempt_id"], row["service_lineage_id"]
        status = "captured" if aid in captured else "failed_no_capture" if aid in failed else "missing_after_lineage_suspension" if sid in suspended else "missing_without_capture"
        cells.append([aid, sid, row["query_form_id"], row["language"], row["window_id"], status])
        counts[("planned_cell", sid, row["query_form_id"], row["language"], row["window_id"], "", status)] += 1
    for sid in admitted:
        subset = [r for r in cells if r[1] == sid]
        summary[LABELS[sid]] = {"planned": len(subset), "captured": sum(r[-1] == "captured" for r in subset), "without_capture": sum(r[-1] != "captured" for r in subset)}
    return cells, counts, summary

def csv_text(header, rows):
    out = io.StringIO(newline="")
    w = csv.writer(out)
    w.writerow(header)
    w.writerows(rows)
    return out.getvalue()

def seal(root, gid):
    for p in list(root.rglob("*")) + [root]:
        os.chown(p, 0, gid)
        p.chmod(0o550 if p.is_dir() else 0o440)
    if any(p.stat().st_uid != 0 or p.stat().st_mode & 0o222 for p in [root] + list(root.rglob("*"))):
        raise ValueError("Read-only seal verification failed")

def completion_name():
    # Buffered update mode (r+) requires seeking and cannot open a real TTY.
    with open("/dev/tty", "w", encoding="utf-8") as writer:
        writer.write("集計を確認し、欠測を保持した終了記録に署名する氏名（空欄で中止）: ")
        writer.flush()
    with open("/dev/tty", "r", encoding="utf-8") as reader:
        return reader.readline().strip()

def main():
    if os.geteuid() != 0 or datetime.now(timezone.utc) < datetime.fromisoformat(FIELD_CLOSE):
        raise ValueError("Root and completed registered field window required")
    configs = [("2.0.2", "mibo-core-v2-ready-three.service", set(LABELS) - {"MIBO-SL-003"}),
               ("2.0.4", "mibo-core-v2-google-standard.service", {"MIBO-SL-003"})]
    work = []
    for version, unit, admitted in configs:
        output = subprocess.check_output(["systemctl", "show", unit, "-p", "ActiveState", "-p", "MainPID", "-p", "UnitFileState", "-p", "ControlGroup", "-p", "Result", "-p", "InactiveEnterTimestamp"], text=True)
        state = dict(line.split("=", 1) for line in output.splitlines() if "=" in line)
        if state.get("ActiveState") != "inactive" or state.get("MainPID") != "0" or state.get("UnitFileState") != "disabled":
            raise ValueError("Collector is not stopped and disabled: " + unit)
        cg = state.get("ControlGroup", "")
        if cg and (Path("/sys/fs/cgroup") / cg.lstrip("/")).exists():
            if any(p.read_text().strip() for p in (Path("/sys/fs/cgroup") / cg.lstrip("/")).rglob("cgroup.procs")):
                raise ValueError("Collector child process remains active")
        line = next(l for l in Path("/etc/systemd/system", unit).read_text().splitlines() if l.startswith("ExecStart="))
        args = shlex.split(line.split("=", 1)[1])
        get = lambda key: Path(args[args.index(key) + 1]).resolve()
        root, manifest = get("--data-root") / ("v" + version) / "JP01" / WAVE, get("--manifest")
        if not root.is_dir() or (root / "closure").exists() or (root / "SHA256SUMS.txt").exists():
            raise ValueError("Missing wave or existing closure; inspect before rerunning")
        inputs = {name: get("--" + name) for name in ("manifest", "protocol", "freeze")}
        input_hashes = {name: sha(p) for name, p in inputs.items()}
        cells, counts, summary = inspect(root, manifest, admitted, version, input_hashes)
        source = next(Path(a).parent.parent for a in args if a.endswith("/automation/core_v2_waiter.py"))
        provenance = {"protocol_version": version, "unit": unit, "unit_state": state, "installed_source": str(source), "source_commit_sha": read(source / "INSTALL_PROVENANCE.json")["source_commit_sha"], "close_tool_sha256": sha(Path(__file__).resolve()), "input_sha256": input_hashes, "planned_field_close_at_utc": FIELD_CLOSE, "namespace_policy": "Separate original protocol namespaces; no pooling or imputation", "seal_method": "root ownership; directories 0550; files 0440"}
        work.append((root, cells, counts, summary, inputs, provenance))
        print(version, encoded(summary).strip())
    for p in Path("/proc").glob("[0-9]*/cmdline"):
        try:
            tokens = p.read_bytes().split(b"\0")
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        if any(t.rsplit(b"/", 1)[-1] in {b"core_v2_waiter.py", b"core_v2_executor.py"} for t in tokens):
            raise ValueError("Active collector process found; closure aborted")
    name = completion_name()
    if not name:
        raise ValueError("Human completion sign-off not supplied; no files changed")
    signed_at = utc()
    for root, cells, counts, summary, inputs, provenance in work:
        close = root / "closure"
        close.mkdir(mode=0o700)
        write(close / "OBSERVATION_STATUS.csv", csv_text(["initial_attempt_id", "service_lineage_id", "query_form_id", "language", "window_id", "status"], cells))
        write(close / "COMPLETION_COUNTS.csv", csv_text(["unit", "service_lineage_id", "query_form_id", "language", "window_id", "attempt", "status", "count"], [list(k) + [n] for k, n in sorted(counts.items())]))
        for label, p in inputs.items():
            write(close / ("FROZEN_" + label.upper() + p.suffix), p.read_bytes())
        write(close / "PROVENANCE.json", encoded(provenance))
        write(close / "COMPLETION_RECORD.json", encoded({"wave_id": WAVE, "planned_field_close_at_utc": FIELD_CLOSE, "signed_at_utc": signed_at, "operations_lead": name, "attestation_method": "typed_name_after_completion_summary_review", "status": "closed_with_retained_missingness", "summary": summary, "independent_backup_at_signoff": "not_yet_verified"}))
        entries = {str(p.relative_to(root)): sha(p) for p in sorted(root.rglob("*")) if p.is_file()}
        write(root / "SHA256SUMS.txt", "".join(h + "  " + p + "\n" for p, h in entries.items()))
        seal(root, grp.getgrnam("mibo").gr_gid)
        if any(sha(root / p) != h for p, h in entries.items()):
            raise ValueError("Post-seal hash mismatch")
    sealed_at = utc()
    backup = Path("/srv/mibo-private") / (WAVE + "-close-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    backup.mkdir(mode=0o700)
    archive = backup / (WAVE + "-sealed.tar.gz")
    expected = {}
    with tarfile.open(archive, "x:gz", dereference=True) as t:
        for root, *_ in work:
            prefix = root.parent.parent.name + "/JP01/" + WAVE
            expected.update({prefix + "/" + str(p.relative_to(root)): sha(p) for p in root.rglob("*") if p.is_file()})
            t.add(root, arcname=prefix)
    checked = set()
    with tarfile.open(archive, "r:gz") as t:
        for member in t:
            if member.isfile():
                h = hashlib.sha256()
                with t.extractfile(member) as f:
                    for b in iter(lambda: f.read(1048576), b""):
                        h.update(b)
                if member.name in checked or expected.get(member.name) != h.hexdigest():
                    raise ValueError("Archive content verification failed")
                checked.add(member.name)
    if checked != set(expected):
        raise ValueError("Archive is incomplete")
    receipt = {"wave_id": WAVE, "sealed_at_utc": sealed_at, "archive_verified_at_utc": utc(), "archive_sha256": sha(archive), "wave_manifest_sha256": {root.parent.parent.name: sha(root / "SHA256SUMS.txt") for root, *_ in work}, "backup_scope": "same_VM_local_export_only; independent_backup_pending"}
    write(backup / "CLOSE_RECEIPT.json", encoded(receipt))
    write(backup / "SHA256SUMS.txt", sha(archive) + "  " + archive.name + "\n" + sha(backup / "CLOSE_RECEIPT.json") + "  CLOSE_RECEIPT.json\n")
    seal(backup, grp.getgrnam("mibo").gr_gid)
    os.sync()
    print("RAW_WAVE_SEAL=PASS / ARCHIVE_CONTENT_VERIFY=PASS")
    print("実際の封印時刻UTC:", sealed_at)
    print("私有保存先:", archive)
    print("INDEPENDENT_BACKUP=PENDING (VM外への保存は次の工程)")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        raise SystemExit("終了処理を中断: " + str(exc))
