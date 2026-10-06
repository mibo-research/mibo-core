#!/usr/bin/env python3
"""Controlled VM: freeze Google Priority, probe once, then human-authorize Google.

The global private anchor reuses the same sealed snapshot and bounded recovery
block on subsequent invocations. Existing three-provider services are untouched.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

SOURCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE / "automation"))
import core_v2_admission as admission
import core_v2_bundle as bundle
import core_v2_executor as executor
import core_v2_preflight as preflight
import core_v2_priority as priority
import core_v2_runner as runner
import runtime_health
from provider_adapters import AdapterFailure, call_provider
from retry_policy import decide_retry

spec = importlib.util.spec_from_file_location("priority_scoped", SOURCE / "runtime/prepare-core-v2-scoped.py")
scoped = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scoped)

ANCHOR = Path("/srv/mibo-private/MIBO2-W01-priority-runtime.json")
SERVICE = "mibo-core-v2-google-priority.service"
OLD_COMMIT = "6292406fb91bceb725ed77d9d94695738df26681"


def prepare_configuration(*, protocol_path: Path, old_protocol_path: Path,
                          old_freeze_path: Path, old_report_path: Path,
                          out_dir: Path) -> None:
    protocol, _ = runner.load_protocol(protocol_path)
    old_protocol, _ = runner.load_protocol(old_protocol_path)
    old_freeze, old_sha = runner.load_freeze(old_freeze_path, protocol=old_protocol,
        wave_id="MIBO2-W01", site_id="JP01")
    original = json.loads(old_report_path.read_text())
    if (protocol["protocol_version"] != priority.VERSION or original.get("protocol_version") != "2.0.1"
            or original.get("protocol_file_sha256") != runner.sha256_file(old_protocol_path)
            or original.get("provider_freeze_sha256") != old_sha or original.get("pass") is not False):
        raise ValueError("original readiness identity mismatch")
    for line in (old_report_path.parent / "SHA256SUMS.txt").read_text().splitlines():
        digest, relative = line.split("  ", 1)
        path = (old_report_path.parent / relative).resolve()
        if not path.is_relative_to(old_report_path.parent.resolve()) or runner.sha256_file(path) != digest:
            raise ValueError("original readiness hash/path mismatch")
    checks = original.get("synthetic_smoke_checks", [])
    if (len(checks) != 4 or {c.get("service_lineage_id") for c in checks} != set(old_freeze["core_api"])
            or {c["service_lineage_id"] for c in checks if c.get("pass") is True} != set(admission.INITIAL_SCOPE)):
        raise ValueError("expected the three passing lineages and deferred Google")
    approved = json.loads((SOURCE / "automation/config/core_v2_agent_provider_freeze.draft.json").read_text())
    for sid, cfg in old_freeze["core_api"].items():
        if cfg["model_id"] != approved["core_api"][sid]["model_id"] or cfg["request_profile"] != approved["core_api"][sid]["request_profile"]:
            raise ValueError("prior freeze differs from the approved exact models/profiles")
        terms = cfg["terms_review_source"]
        record = admission.checked(Path(terms["file"]), terms["sha256"])
        if (record.get("official_terms_and_applicable_research_conditions_reviewed_by_human") is not True
                or record.get("literal_ids_and_material_profiles_frozen_by_human") is not True):
            raise ValueError("human Terms review is incomplete")
    out_dir.mkdir(mode=0o750)
    freeze = json.loads(json.dumps(old_freeze))
    freeze.update(schema_version=priority.VERSION, protocol_version=priority.VERSION,
        protocol_registration_id=protocol["protocol_registration_id"], frozen_at_utc=scoped.now(),
        prior_human_profile_frozen_at_utc=old_freeze["frozen_at_utc"],
        priority_configuration_approved_at_utc="2026-10-06T02:16:30Z",
        prior_freeze_file=str(old_freeze_path), prior_freeze_sha256=old_sha)
    freeze["core_api"][admission.GOOGLE_SCOPE[0]]["request_profile"]["service_tier"] = "priority"
    freeze_path = out_dir / "core_v2_provider_freeze.json"
    scoped.write(freeze_path, freeze)
    runner.load_freeze(freeze_path, protocol=protocol, wave_id="MIBO2-W01", site_id="JP01")
    scoped.write(out_dir / "PRIORITY_CONTEXT.json", {"protocol_file": str(protocol_path),
        "protocol_file_sha256": runner.sha256_file(protocol_path),
        "old_protocol_file": str(old_protocol_path), "old_protocol_sha256": runner.sha256_file(old_protocol_path),
        "prior_report_file": str(old_report_path), "prior_report_sha256": runner.sha256_file(old_report_path),
        "prior_freeze_file": str(old_freeze_path), "prior_freeze_sha256": old_sha,
        "created_at_utc": scoped.now(), "gemini_priority_policy": priority.POLICY,
        "service_tier_requested": "priority", "current_account_access_verified": False,
        "human_execution_authorized": False, "three_provider_collector_modified": False})


def probe(*, out_dir: Path, current: datetime | None = None) -> dict:
    if os.environ.get("MIBO_CORE_V2_SMOKE_TEST") != preflight.SMOKE_SENTINEL:
        raise ValueError("Terms-reviewed fixed readiness sentinel is missing")
    context = json.loads((out_dir / "PRIORITY_CONTEXT.json").read_text())
    protocol_path = Path(context["protocol_file"])
    protocol, protocol_sha = runner.load_protocol(protocol_path)
    if protocol_sha != context["protocol_file_sha256"]:
        raise ValueError("Priority protocol hash changed")
    freeze_path = out_dir / "core_v2_provider_freeze.json"
    freeze, freeze_sha = runner.load_freeze(freeze_path, protocol=protocol, wave_id="MIBO2-W01", site_id="JP01")
    original = admission.checked(Path(context["prior_report_file"]), context["prior_report_sha256"])
    admission.checked(Path(context["prior_freeze_file"]), context["prior_freeze_sha256"])
    if runner.sha256_file(Path(context["old_protocol_file"])) != context["old_protocol_sha256"]:
        raise ValueError("old protocol evidence changed")
    current = current or datetime.now(timezone.utc)
    bounds = runner.wave(protocol, "MIBO2-W01")
    close = runner.parse_aware_utc(bounds["close_utc"])
    if not runner.parse_aware_utc(bounds["start_utc"]) <= current < close:
        raise ValueError("original field window is not open")
    block = out_dir / "priority-recovery-block"
    block.mkdir(mode=0o750, exist_ok=True)
    records = sorted(block.glob("probe-*/RESULT.json"))
    if len(records) != len(list(block.glob("probe-*"))):
        raise ValueError("an interrupted or running Priority probe exists; stop and review")
    if records:
        latest = json.loads(records[-1].read_text())
        if latest.get("pass") is True:
            target = records[-1].parent
            report_path = target / "bundle/CORE_V2_BUNDLE_REPORT.json"
            if not report_path.exists():
                raise ValueError("passing evidence exists without a completed bundle; preserve it and review")
            return {"out_dir": target, "bundle": json.loads(report_path.read_text()), "provider_called": False}
        if len(records) >= 3:
            raise ValueError("Priority recovery block exhausted; no fourth probe")
        decision = decide_retry(attempt=len(records), failure_kind=latest["failure_kind"],
            failed_at=runner.parse_aware_utc(latest["recorded_at_utc"]),
            provider_retry_after_seconds=latest.get("retry_after_seconds"), field_close=close)
        if latest.get("http_status") not in {429, 500, 502, 503, 504, None} or not decision.retry:
            raise ValueError("this Priority failure is not retryable; no new probe")
        if current < runner.parse_aware_utc(decision.due_at_utc):
            raise ValueError("Priority retry wait has not elapsed; eligible UTC: " + decision.due_at_utc)
    else:
        old_report = Path(context["prior_report_file"])
        old = next(c for c in original["synthetic_smoke_checks"] if c["service_lineage_id"] == admission.GOOGLE_SCOPE[0])
        failures = [old_report.parent / old["file"]]
        failures.extend(old_report.parents[1].glob("recovery-*/RECOVERY_FAILURE.json"))
        for path in failures:
            value = json.loads(path.read_text())
            if value.get("http_status") != 503:
                raise ValueError("prior Google model/readiness failure requires review")
            due = runner.parse_aware_utc(value["recorded_at_utc"])
            from datetime import timedelta
            due += timedelta(seconds=max(600, value.get("retry_after_seconds") or 0))
            if current < due:
                raise ValueError("prior Google Retry-After has not elapsed; eligible UTC: " + due.isoformat())
        prior_standard = out_dir / "PRIOR_STANDARD_RECOVERY.json"
        if prior_standard.exists():
            from datetime import timedelta
            for entry in json.loads(prior_standard.read_text())["records"]:
                value = admission.checked(Path(entry["file"]), entry["sha256"])
                if value.get("pass") is True: continue
                if value.get("http_status") not in {429, 500, 502, 503, 504, None} or value.get("failure_kind") in {"request_environment_mismatch", "returned_model_or_status_mismatch"}:
                    raise ValueError("prior Standard recovery requires review before a Priority probe")
                due = runner.parse_aware_utc(value["recorded_at_utc"]) + timedelta(seconds=max(600, value.get("retry_after_seconds") or 0))
                if current < due:
                    raise ValueError("prior Standard Retry-After has not elapsed; eligible UTC: " + due.isoformat())
    number = len(records) + 1
    target = block / f"probe-{number}"
    target.mkdir(mode=0o750)
    cfg = freeze["core_api"][admission.GOOGLE_SCOPE[0]]
    scoped.write(target / "PROBE_CONTEXT.json", {"readiness_only": True,
        "registered_mibo_prompt_used": False, "probe_number": number, "model_id": cfg["model_id"],
        "service_tier_requested": "priority", "provider_freeze_sha256": freeze_sha,
        "requested_at_utc": current.isoformat()})
    try:
        result = call_provider(provider="Google", model_id=cfg["model_id"],
            prompt=preflight.SYNTHETIC_PROMPT, profile=cfg["request_profile"], timeout_s=60)
    except AdapterFailure as exc:
        body = exc.response_body
        if body:
            for entry in freeze["core_api"].values():
                token = os.environ.get(entry["request_profile"]["api_key_env"])
                if token: body = body.replace(token, "[REDACTED]")
        scoped.write(target / "RESULT.json", {"pass": False, "readiness_only": True,
            "failure_kind": exc.kind, "http_status": exc.http_status,
            "retry_after_seconds": exc.retry_after_seconds, "response_body": body,
            "response_metadata": exc.response_metadata, "recorded_at_utc": scoped.now(),
            "probe_number": number})
        raise ValueError(f"Google Priority FAIL / HTTP {exc.http_status} / {exc.kind}; private record: {target / 'RESULT.json'}") from None
    metadata = result.response_metadata or {}
    passed = (result.returned_model == cfg["model_id"] and 200 <= result.http_status < 300
        and result.request_payload.get("service_tier") == "priority"
        and metadata.get("service_tier_actual") == "priority"
        and metadata.get("response_headers", {}).get("x-gemini-service-tier") == "priority")
    evidence = target / "SMOKE.json"
    scoped.write(evidence, {"protocol_version": priority.VERSION, "readiness_only": True,
        "requested_model": cfg["model_id"], "returned_model": result.returned_model,
        "http_status": result.http_status, "started_at_utc": result.started_at_utc,
        "completed_at_utc": result.completed_at_utc, "duration_ms": result.duration_ms,
        "request_payload": result.request_payload, "response": result.response_json,
        "raw_response_text": result.raw_response_text, "response_metadata": metadata, "usage": result.usage,
        "synthetic_prompt_sha256": hashlib.sha256(preflight.SYNTHETIC_PROMPT.encode()).hexdigest(),
        "registered_mibo_prompt_used": False, "pass": passed})
    scoped.write(target / "RESULT.json", {"pass": passed, "readiness_only": True,
        "failure_kind": None if passed else "priority_tier_or_model_unconfirmed",
        "http_status": result.http_status, "recorded_at_utc": scoped.now(),
        "service_tier_actual": metadata.get("service_tier_actual"), "probe_number": number,
        "evidence_file": str(evidence), "evidence_sha256": runner.sha256_file(evidence)})
    if not passed:
        raise ValueError("actual Priority tier/model was not confirmed; response preserved, collection remains disabled")
    report = json.loads(json.dumps(original))
    for check in report["synthetic_smoke_checks"]:
        if check["service_lineage_id"] == admission.GOOGLE_SCOPE[0]:
            check.clear()
            check.update(service_lineage_id=admission.GOOGLE_SCOPE[0], provider="Google",
                model_id=cfg["model_id"], file=str(evidence.resolve()), sha256=runner.sha256_file(evidence))
            check["pass"] = True
        else:
            check["file"] = str((Path(context["prior_report_file"]).parent / check["file"]).resolve())
    report.update(schema_version=priority.VERSION, protocol_version=priority.VERSION,
        protocol_registration_id=protocol["protocol_registration_id"], protocol_file_sha256=protocol_sha,
        provider_freeze_sha256=freeze_sha, checked_at_utc=scoped.now(),
        readiness_scope="admitted_lineages_only", admitted_lineages=admission.GOOGLE_SCOPE,
        outside_this_authorization_lineages=admission.INITIAL_SCOPE,
        prior_report_file=context["prior_report_file"], prior_report_sha256=context["prior_report_sha256"],
        prior_freeze_file=context["prior_freeze_file"], prior_freeze_sha256=context["prior_freeze_sha256"],
        gemini_priority_policy=priority.POLICY, priority_access_confirmed_by_response=True,
        google_recovery_probe_number=number, human_google_admission_required=True)
    report.update(prior_errors=original.get("errors", []), errors=[], all_four_ready=True)
    report["pass"] = True
    report_path = target / "PRIORITY_READINESS_REPORT.json"
    scoped.write(report_path, report)
    built = bundle.build_bundle(protocol_path=protocol_path, freeze_path=freeze_path,
        wave_id="MIBO2-W01", site_id="JP01", preflight_report_path=report_path, out_dir=target / "bundle")
    rows = runner.read_csv(target / "bundle" / built["manifest_file"])
    if rows != runner.generate_manifest(protocol_path=protocol_path, freeze_path=freeze_path, wave_id="MIBO2-W01", site_id="JP01"):
        raise ValueError("strict deterministic manifest verification failed")
    old_rows = runner.generate_manifest(protocol_path=Path(context["old_protocol_file"]),
        freeze_path=Path(context["prior_freeze_file"]), wave_id="MIBO2-W01", site_id="JP01")
    fields = ("attempt_id", "query_sha256", "query_form_id", "execution_order", "random_seed", "window_id", "replication")
    if len(old_rows) != len(rows):
        raise ValueError("Priority manifest changed the scientific row count")
    for old, new in zip(old_rows, rows):
        if any(old[key] != new[key] for key in fields):
            raise ValueError("Priority manifest changed a scientific row")
    scoped.write(target / "WAVE_LINEAGE_PROVENANCE.json", {
        "wave_id": "MIBO2-W01", "site_id": "JP01", "full_intended_rows": 1120,
        "google_executable_rows": 280, "google_protocol_version": priority.VERSION,
        "other_lineages_execution_protocol": "2.0.2", "automatic_cross_version_pooling": False,
        "prior_freeze_sha256": context["prior_freeze_sha256"],
        "priority_manifest_sha256": built["manifest_sha256"],
        "logical_attempt_ids_preserved": True, "mapping": [
            {"attempt_id": row["attempt_id"], "service_lineage_id": row["service_lineage_id"],
             "executed_by_priority_scope": row["service_lineage_id"] in admission.GOOGLE_SCOPE} for row in rows]})
    return {"out_dir": target, "bundle": built, "provider_called": True}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args()
    os.umask(0o077)
    try:
        if os.geteuid() != 0 or runtime_health.installed_snapshot_state(SOURCE).get("snapshot_integrity_pass") is not True:
            raise ValueError("controlled VM root and sealed collector required")
        values = scoped.preparation_module(SOURCE).read_environment(Path("/etc/mibo/mibo-core-v2.env"))
        root = Path(values["MIBO_DATA_ROOT"])
        if not root.is_absolute() or not root.is_dir() or shutil.disk_usage(root).free < 2 * 1024**3:
            raise ValueError("configured private data store is not ready")
        if subprocess.check_output(["timedatectl", "show", "-p", "NTPSynchronized", "--value"], text=True).strip() != "yes":
            raise ValueError("VM clock is not synchronized")
        priority.block_prior_google_attempts(root, "JP01", "MIBO2-W01")
        for unit in ("mibo-core-v2.service", "mibo-core-v2-google.service"):
            state = subprocess.run(["systemctl", "is-active", unit], capture_output=True, text=True).stdout.strip()
            if state not in {"inactive", "failed", "unknown"}:
                raise ValueError("another Google collection path is running; preserve it and review")
        if ANCHOR.exists():
            anchor = json.loads(ANCHOR.read_text())
            if Path(anchor["installed_source"]).resolve() != SOURCE or Path(anchor["readiness"]).resolve() != args.out_dir.resolve():
                raise ValueError("use the previously pinned Priority runtime and its single recovery block")
        else:
            reports = list(Path("/srv/mibo-private").glob("agent-ready.*/readiness/preflight/CORE_V2_API_PREFLIGHT_REPORT.json"))
            original = max(reports, key=lambda path: path.stat().st_mtime)
            sources = [path for path in Path("/opt").glob("mibo-core-v2.0.1.*")
                if (path / "INSTALL_PROVENANCE.json").is_file()
                and json.loads((path / "INSTALL_PROVENANCE.json").read_text()).get("source_commit_sha") == OLD_COMMIT]
            old_source = max(sources, key=lambda path: path.stat().st_mtime)
            if runtime_health.installed_snapshot_state(old_source).get("snapshot_integrity_pass") is not True:
                raise ValueError("original sealed source integrity failed")
            old_protocol = old_source / "automation/config/core_v2_agent_protocol.v2.0.1.json"
            prepare_configuration(protocol_path=SOURCE / "automation/config/core_v2_protocol.v2.0.3.json",
                old_protocol_path=old_protocol, old_freeze_path=original.parents[1] / "core_v2_provider_freeze.json",
                old_report_path=original, out_dir=args.out_dir)
            scoped.write(args.out_dir / "OLD_PROTOCOL_LINK.json", {"old_protocol_file": str(old_protocol),
                "old_protocol_sha256": runner.sha256_file(old_protocol)})
            standard = list(Path("/srv/mibo-private").glob("scoped-ready.*/readiness/google-recovery-block/probe-*/RESULT.json"))
            scoped.write(args.out_dir / "PRIOR_STANDARD_RECOVERY.json", {"records": [
                {"file": str(path), "sha256": runner.sha256_file(path)} for path in standard]})
            scoped.write(ANCHOR, {"installed_source": str(SOURCE), "readiness": str(args.out_dir),
                "data_root": str(root), "protocol_version": priority.VERSION,
                "source_commit_sha": json.loads((SOURCE / "INSTALL_PROVENANCE.json").read_text())["source_commit_sha"]})
            os.chown(ANCHOR, 0, scoped.grp.getgrnam("mibo").gr_gid); ANCHOR.chmod(0o640)
        # Prevent a dormant old Google service from starting alongside Priority at boot.
        if Path("/etc/systemd/system/mibo-core-v2-google.service").exists():
            subprocess.run(["systemctl", "disable", "mibo-core-v2-google.service"], check=True)
        authorizations = list((args.out_dir / "priority-recovery-block").glob("probe-*/core_v2_execution_authorization.scoped.json"))
        if authorizations:
            auth_path = authorizations[-1]
            base = auth_path.parent / "bundle"
            executor.preflight(protocol_path=base / "configuration/core_v2_protocol.final.json",
                freeze_path=base / "configuration/core_v2_provider_freeze.json",
                manifest_path=base / "manifests/MIBO2-W01-JP01-API-CORE.csv", authorization_path=auth_path, data_root=root)
            installed_unit = Path("/etc/systemd/system") / SERVICE
            saved_unit = auth_path.parent / SERVICE
            if not installed_unit.exists() or runner.sha256_file(installed_unit) != runner.sha256_file(saved_unit):
                raise ValueError("authorized Priority unit is missing or changed; preserve records and review")
            subprocess.run(["systemctl", "start", SERVICE], check=True)
            print("既存の人間承認を検証し、同じPriorityサービスを実行します。新しい応答テストは行いません。")
            return 0
        freeze = json.loads((args.out_dir / "core_v2_provider_freeze.json").read_text())
        for cfg in freeze["core_api"].values():
            key = cfg["request_profile"]["api_key_env"]
            if values.get(key): os.environ[key] = values[key]
        os.environ.pop("MIBO_CORE_V2_EXECUTION", None)
        os.environ["MIBO_CORE_V2_SMOKE_TEST"] = preflight.SMOKE_SENTINEL
        print("Gemini 3.8 Flash / Priority要求 / 最大4096 / 固定の非観測確認1回。", flush=True)
        print("利用条件: Tier 2・3。料金: Standardの約1.75〜2倍。実処理tierも保存します。", flush=True)
        result = probe(out_dir=args.out_dir.resolve())
        print("Google Priority応答を確認: PASS。次はこのGoogle範囲だけの人間の実行承認です。", flush=True)
        scoped.authorize_and_start(out_dir=result["out_dir"], built=result["bundle"], data_root=root, values=values,
            service=SERVICE, phrase_required="AUTHORIZE_GOOGLE_PRIORITY")
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        print("3社のサービスとコードは変更していません。Googleの開始状態は私有記録とサービス状態で確認してください。", file=sys.stderr)
        return 1
    finally:
        if args.out_dir.exists(): scoped.permissions(args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
