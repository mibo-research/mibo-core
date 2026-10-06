#!/usr/bin/env python3
"""One failed synthetic readiness probe; retain prior passing evidence unchanged.

This standalone VM helper does not modify the sealed collector, freeze,
original report, original failure, authorization, or service configuration.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as fh:
        json.dump(value, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")


def checked_file(root: Path, relative: str, expected_sha: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or sha(path) != expected_sha:
        raise ValueError("previous readiness evidence hash/path mismatch")
    return path


def recover(*, protocol_path: Path, freeze_path: Path, report_path: Path,
            out_dir: Path, current: datetime | None = None) -> dict:
    import core_v2_bundle as bundle
    import core_v2_preflight as preflight
    import core_v2_runner as runner
    from provider_adapters import AdapterFailure, call_provider
    import api_preflight as api
    if os.environ.get("MIBO_CORE_V2_SMOKE_TEST") != preflight.SMOKE_SENTINEL:
        raise ValueError("synthetic readiness sentinel is not enabled after Terms review")
    protocol, protocol_sha = runner.load_protocol(protocol_path)
    original = json.loads(report_path.read_text())
    wave_id, site_id = original["wave_id"], original["site_id"]
    freeze, freeze_sha = runner.load_freeze(freeze_path, protocol=protocol, wave_id=wave_id, site_id=site_id)
    for key, expected in {
        "protocol_version": protocol["protocol_version"],
        "protocol_registration_id": protocol["protocol_registration_id"],
        "protocol_file_sha256": protocol_sha, "provider_freeze_sha256": freeze_sha,
        "synthetic_smoke_requested": True, "pass": False,
    }.items():
        if original.get(key) != expected:
            raise ValueError("original readiness identity/status mismatch")
    checks = original["synthetic_smoke_checks"]
    if len(checks) != 4 or {c["service_lineage_id"] for c in checks} != set(freeze["core_api"]):
        raise ValueError("previous readiness must cover exactly four frozen lineages")
    failed = [c for c in checks if c.get("pass") is not True]
    if len(failed) != 1 or len(original.get("errors", [])) != 1:
        raise ValueError("recovery requires exactly one technical smoke failure")
    target = failed[0]
    if target.get("failure_kind") != "provider_error" or target.get("http_status") != 503:
        raise ValueError("this recovery is limited to a prior HTTP 503")
    if len(original["model_checks"]) != 4 or not all(c.get("exact_metadata_verified") is True for c in original["model_checks"]):
        raise ValueError("all four original model metadata checks must have passed")
    root = report_path.parent
    for line in (root / "SHA256SUMS.txt").read_text().splitlines():
        digest, relative = line.split("  ", 1)
        checked_file(root, relative, digest)
    expected_prompt = hashlib.sha256(preflight.SYNTHETIC_PROMPT.encode()).hexdigest()
    for check in checks:
        cfg = freeze["core_api"][check["service_lineage_id"]]
        if check["model_id"] != cfg["model_id"]:
            raise ValueError("previous smoke model does not match unchanged freeze")
        path = checked_file(root, check["file"], check["sha256"])
        evidence = json.loads(path.read_text())
        if check["pass"]:
            if (evidence.get("pass") is not True or evidence.get("readiness_only") is not True
                    or evidence.get("requested_model") != cfg["model_id"]
                    or evidence.get("returned_model") != cfg["model_id"]
                    or evidence.get("synthetic_prompt_sha256") != expected_prompt):
                raise ValueError("prior passing smoke evidence is not reusable")
    failure_path = checked_file(root, target["file"], target["sha256"])
    failure = json.loads(failure_path.read_text())
    if failure.get("failure_kind") != "provider_error" or failure.get("http_status") != 503:
        raise ValueError("retained original failure is not HTTP 503")
    attempts = sorted(report_path.parents[1].glob("recovery-*/RECOVERY_FAILURE.json"))
    if len(attempts) >= 2:
        raise ValueError("two readiness recovery attempts already failed; stop and review")
    if attempts:
        failure = json.loads(max(attempts, key=lambda p: p.stat().st_mtime).read_text())
        if failure.get("http_status") != 503:
            raise ValueError("latest recovery failure is not HTTP 503; stop and review")
    delay = max(60 * (2 ** len(attempts)), failure.get("retry_after_seconds") or 0)
    due = runner.parse_aware_utc(failure["recorded_at_utc"]) + timedelta(seconds=delay)
    current = current or datetime.now(timezone.utc)
    bounds = runner.wave(protocol, wave_id)
    if not runner.parse_aware_utc(bounds["start_utc"]) <= current < runner.parse_aware_utc(bounds["close_utc"]):
        raise ValueError("original registered field window is not open")
    if current < due:
        raise ValueError("readiness recovery wait has not elapsed; eligible UTC: " + due.isoformat())
    out_dir.mkdir(mode=0o700)
    with (out_dir / "OPERATIONAL_HELPER.py").open("xb") as fh:
        fh.write(Path(__file__).read_bytes())
    write(out_dir / "RECOVERY_CONTEXT.json", {
        "readiness_only": True, "registered_mibo_prompt_used": False,
        "prior_report_file": str(report_path), "prior_report_sha256": sha(report_path),
        "original_failure_file": str(failure_path), "original_failure_sha256": sha(failure_path),
        "helper_file_sha256": sha(Path(__file__)), "attempt": len(attempts) + 1,
        "unchanged_freeze_sha256": freeze_sha, "collector_or_profile_modified": False})
    model = target["model_id"]
    label = target["provider"]
    cfg = freeze["core_api"][target["service_lineage_id"]]
    try:
        result = call_provider(provider=label, model_id=model, prompt=preflight.SYNTHETIC_PROMPT,
                               profile=cfg["request_profile"], timeout_s=60)
    except AdapterFailure as exc:
        body = exc.response_body
        if body:
            for entry in freeze["core_api"].values():
                token = os.environ.get(entry["request_profile"]["api_key_env"])
                if token:
                    body = body.replace(token, "[REDACTED]")
        write(out_dir / "RECOVERY_FAILURE.json", {
            "readiness_only": True, "provider": label, "model_id": model,
            "failure_kind": exc.kind, "http_status": exc.http_status,
            "retry_after_seconds": exc.retry_after_seconds,
            "recorded_at_utc": api.utc_now(), "response_body": body})
        print(f"応答テスト FAIL: {label} / HTTP {exc.http_status} / {exc.kind}", flush=True)
        raise ValueError("readiness recovery failed; no collection authorized") from None
    passed = result.returned_model == model and 200 <= result.http_status < 300
    path = out_dir / "RECOVERED_SMOKE.json"
    write(path, {"protocol_version": protocol["protocol_version"],
        "readiness_only": True, "service_lineage_id": target["service_lineage_id"],
        "provider": label, "requested_model": model, "returned_model": result.returned_model,
        "http_status": result.http_status, "started_at_utc": result.started_at_utc,
        "completed_at_utc": result.completed_at_utc, "duration_ms": result.duration_ms,
        "usage": result.usage, "request_payload": result.request_payload,
        "response": result.response_json, "raw_response_text": result.raw_response_text,
        "synthetic_prompt_sha256": expected_prompt, "registered_mibo_prompt_used": False,
        "returned_model_matches_requested": result.returned_model == model, "pass": passed})
    if not passed:
        write(out_dir / "RECOVERY_FAILURE.json", {
            "readiness_only": True, "provider": label, "model_id": model,
            "failure_kind": "returned_model_or_status_mismatch", "http_status": result.http_status,
            "recorded_at_utc": api.utc_now(), "retained_response_file": str(path),
            "retained_response_sha256": sha(path)})
        raise ValueError("recovered response model/status mismatch; stop and review")
    combined = json.loads(json.dumps(original))
    for check in combined["synthetic_smoke_checks"]:
        check["file"] = str((root / check["file"]).resolve())
        if check["service_lineage_id"] == target["service_lineage_id"]:
            check.clear()
            check.update(service_lineage_id=target["service_lineage_id"], provider=label,
                         model_id=model, **{"pass": True}, file=str(path), sha256=sha(path))
    for catalog in combined["catalogs"].values():
        catalog["file"] = str((root / catalog["file"]).resolve())
    for check in combined["model_checks"]:
        if check.get("metadata_file"):
            check["metadata_file"] = str((root / check["metadata_file"]).resolve())
    combined.update(checked_at_utc=api.utc_now(), errors=[], **{"pass": True},
        prior_report_file=str(report_path), prior_report_sha256=sha(report_path),
        technical_recovery_only=True, original_failure_retained=True)
    combined_path = out_dir / "CORE_V2_API_PREFLIGHT_REPORT.json"
    write(combined_path, combined)
    built = bundle.build_bundle(protocol_path=protocol_path, wave_id=wave_id, site_id=site_id,
        freeze_path=freeze_path, preflight_report_path=combined_path, out_dir=out_dir / "bundle")
    rows = runner.read_csv(out_dir / "bundle" / built["manifest_file"])
    if rows != runner.generate_manifest(protocol_path=protocol_path, freeze_path=freeze_path, wave_id=wave_id, site_id=site_id):
        raise ValueError("strict deterministic manifest comparison failed")
    write(out_dir / "READINESS_STATUS.json", {"status": "READY_FOR_HUMAN_EXECUTION_AUTHORIZATION",
        "technical_readiness_completed_at_utc": api.utc_now(), "actual_preparation_completed_at_utc": None,
        "actual_observation_start_at_utc": None, "planned_observation_start_at_utc": bounds["start_utc"],
        "bundle": built, "collection_enabled": False, "strict_manifest_pass": True})
    print(f"応答テスト PASS: {label} / {model}", flush=True)
    print("他の3社: 元のPASS記録をハッシュ検証して使用", flush=True)
    print(f"準備 PASS / マニフェスト {len(rows)}件", flush=True)
    print(f"実行バンドル: {out_dir / 'bundle'}", flush=True)
    for key in ("protocol_file_sha256", "provider_freeze_sha256", "manifest_sha256", "bundle_report_sha256"):
        print(f"{key}: {built[key]}", flush=True)
    return built


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()
    os.umask(0o077)
    if os.geteuid() != 0:
        raise SystemExit("controlled VM root execution required")
    reports = list(Path("/srv/mibo-private").glob("agent-ready.*/readiness/preflight/CORE_V2_API_PREFLIGHT_REPORT.json"))
    report = max(reports, key=lambda p: p.stat().st_mtime)
    source_options = [p for p in Path("/opt").glob("mibo-core-v2.0.1.*")
        if (p / "INSTALL_PROVENANCE.json").is_file()
        and json.loads((p / "INSTALL_PROVENANCE.json").read_text()).get("source_commit_sha") == args.source_commit]
    source = max(source_options, key=lambda p: p.stat().st_mtime)
    sys.path.insert(0, str(source / "automation"))
    import runtime_health
    if runtime_health.installed_snapshot_state(source).get("snapshot_integrity_pass") is not True:
        raise SystemExit("sealed collector integrity check failed")
    spec = importlib.util.spec_from_file_location("installed_preparation", source / "runtime/prepare-core-v2-agent.py")
    preparation = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(preparation)
    values = preparation.read_environment(Path("/etc/mibo/mibo-core-v2.env"))
    data_root = Path(values["MIBO_DATA_ROOT"])
    if subprocess.run(["systemctl", "is-active", "mibo-core-v2.service"], capture_output=True, text=True).stdout.strip() not in {"inactive", "failed"}:
        raise SystemExit("collection service must remain stopped")
    if subprocess.check_output(["timedatectl", "show", "-p", "NTPSynchronized", "--value"], text=True).strip() != "yes":
        raise SystemExit("clock is not synchronized")
    for version in ("v2.0", "v2.0.1"):
        root = data_root / version / "JP01" / "MIBO2-W01"
        if any(next((root / folder).glob("*.json"), None) for folder in ("api_raw", "failures")):
            raise SystemExit("retained confirmatory attempts exist; stop and review")
    freeze = report.parents[1] / "core_v2_provider_freeze.json"
    raw = json.loads(freeze.read_text())
    for entry in raw["core_api"].values():
        record = entry["terms_review_source"]
        if sha(Path(record["file"])) != record["sha256"]:
            raise SystemExit("private human Terms/profile record hash mismatch")
        key = entry["request_profile"]["api_key_env"]
        if not values.get(key):
            raise SystemExit("a frozen credential is missing")
        os.environ[key] = values[key]
    os.environ.pop("MIBO_CORE_V2_EXECUTION", None)
    os.environ["MIBO_CORE_V2_SMOKE_TEST"] = preparation.preflight.SMOKE_SENTINEL
    parent = report.parents[1]
    if any(parent.glob("recovery-*/READINESS_STATUS.json")):
        raise SystemExit("recovered readiness already exists; do not repeat provider calls")
    destination = Path(tempfile.mkdtemp(prefix="recovery-", dir=parent))
    destination.rmdir()  # Reserved random name; recover creates it exclusively before its one call.
    try:
        recover(protocol_path=source / "automation/config/core_v2_agent_protocol.v2.0.1.json",
                freeze_path=freeze, report_path=report, out_dir=destination)
        status = json.loads((destination / "READINESS_STATUS.json").read_text())
        status.update(installed_source=str(source), source_commit_sha=args.source_commit, data_root=str(data_root))
        write(destination / "RUNTIME_LINK.json", status)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        print("観測は開始していません。", file=sys.stderr)
        return 1
    finally:
        if destination.exists():
            import grp
            gid = grp.getgrnam("mibo").gr_gid
            for path in [destination, *destination.rglob("*")]:
                os.chown(path, 0, gid)
                path.chmod(0o750 if path.is_dir() else 0o640)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
