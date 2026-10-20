#!/usr/bin/env python3
"""Controlled VM: restore Google Standard, probe once, then human-authorize Google.

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
import core_v2_standard as standard
import core_v2_runner as runner
import runtime_health
from provider_adapters import AdapterFailure, call_provider
from retry_policy import decide_retry

spec = importlib.util.spec_from_file_location("standard_scoped", SOURCE / "runtime/prepare-core-v2-scoped.py")
scoped = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scoped)

ANCHOR = Path("/srv/mibo-private/MIBO2-W01-standard-runtime.json")
SERVICE = "mibo-core-v2-google-standard.service"
OLD_COMMIT = "6292406fb91bceb725ed77d9d94695738df26681"


PRIORITY_ANCHOR = Path("/srv/mibo-private/MIBO2-W01-priority-runtime.json")


def history_paths(old_report: Path) -> list[Path]:
    paths = list(old_report.parents[1].rglob("*.json"))
    for candidate in Path("/srv/mibo-private").glob("scoped-ready.*/readiness/google-recovery-block"):
        if len(list(candidate.glob("probe-*"))) != len(list(candidate.glob("probe-*/RESULT.json"))):
            raise ValueError("interrupted prior Standard probe; preserve and review")
        paths.extend(candidate.rglob("*.json"))
    if not PRIORITY_ANCHOR.is_file():
        raise ValueError("prior Priority anchor required for this eligibility correction")
    prior = json.loads(PRIORITY_ANCHOR.read_text())
    root = Path(prior["readiness"])
    prior_source = Path(prior["installed_source"])
    if runtime_health.installed_snapshot_state(prior_source).get("snapshot_integrity_pass") is not True:
        raise ValueError("prior sealed Priority source integrity failed")
    block = root / "priority-recovery-block"
    if len(list(block.glob("probe-*"))) != len(list(block.glob("probe-*/RESULT.json"))):
        raise ValueError("interrupted prior Priority probe; preserve and review")
    if not list(block.glob("probe-*/RESULT.json")):
        raise ValueError("prior Priority readiness history is missing")
    paths.extend([PRIORITY_ANCHOR, *root.rglob("*.json")])
    return paths


def honor_prior_waits(*, out_dir: Path, current: datetime, model_id: str) -> None:
    from datetime import timedelta
    context = json.loads((out_dir / "STANDARD_CONTEXT.json").read_text())
    history = admission.checked(Path(context["prior_readiness_history_file"]), context["prior_readiness_history_sha256"])
    for entry in history["files"]:
        path = Path(entry["file"])
        value = admission.checked(path, entry["sha256"])
        if path.name == "SMOKE.json" and value.get("request_payload", {}).get("service_tier") == "priority":
            # The retained result below identifies why this response did not pass.
            result = json.loads((path.parent / "RESULT.json").read_text())
            if result.get("failure_kind") == "priority_tier_or_model_unconfirmed":
                continue
        if value.get("failure_kind") == "priority_tier_or_model_unconfirmed":
            smoke = admission.checked(path.parent / "SMOKE.json", value["evidence_sha256"])
            if (not 200 <= smoke.get("http_status", 0) < 300 or
                    smoke.get("requested_model") != model_id or smoke.get("returned_model") != model_id or
                    smoke.get("request_payload", {}).get("service_tier") != "priority" or
                    ((smoke.get("response") or {}).get("modelVersion") is not None and
                     not standard.model_matches(smoke["response"]["modelVersion"], model_id))):
                raise ValueError("prior Priority failure is not an eligibility-only mismatch; review required")
            continue
        is_failure = (value.get("readiness_only") and
                      (value.get("pass") is False or bool(value.get("failure_kind")))) or path.name == "RECOVERY_FAILURE.json"
        if not is_failure:
            continue
        status = value.get("http_status")
        if status not in {429, 500, 502, 503, 504, None} or value.get("failure_kind") in {
                "request_environment_mismatch", "returned_model_or_status_mismatch"}:
            raise ValueError("prior readiness has an unresolved nontechnical failure")
        stamp = value.get("recorded_at_utc") or value.get("completed_at_utc")
        if not stamp:
            raise ValueError("prior failed readiness has no timestamp")
        due = runner.parse_aware_utc(stamp) + timedelta(seconds=max(600, value.get("retry_after_seconds") or 0))
        if current < due:
            raise ValueError("prior Retry-After has not elapsed; eligible UTC: " + due.isoformat())


def prior_manifest_hash(context: dict, target: Path) -> str:
    rows = runner.generate_manifest(protocol_path=Path(context["old_protocol_file"]),
        freeze_path=Path(context["prior_freeze_file"]), wave_id="MIBO2-W01", site_id="JP01")
    path = target / "PRIOR_LOGICAL_MANIFEST.csv"
    runner.write_csv(rows, path)
    return runner.sha256_file(path)


def prepare_configuration(*, protocol_path: Path, old_protocol_path: Path,
                          old_freeze_path: Path, old_report_path: Path,
                          out_dir: Path, history_files: list[Path] | None = None) -> None:
    protocol, _ = runner.load_protocol(protocol_path)
    old_protocol, _ = runner.load_protocol(old_protocol_path)
    old_freeze, old_sha = runner.load_freeze(old_freeze_path, protocol=old_protocol,
        wave_id="MIBO2-W01", site_id="JP01")
    original = json.loads(old_report_path.read_text())
    if (protocol["protocol_version"] != standard.VERSION or original.get("protocol_version") != "2.0.1"
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
    paths = history_files if history_files is not None else history_paths(old_report_path)
    history = out_dir / "PRIOR_READINESS_HISTORY.json"
    scoped.write(history, {"created_at_utc": scoped.now(), "files": [
        {"file": str(path.resolve()), "sha256": runner.sha256_file(path)} for path in sorted(set(paths))]})
    scoped.write(out_dir / "ELIGIBILITY_CORRECTION.json", {
        "approved_at_utc": "2026-10-06T03:35:46Z", "recorded_at_utc": scoped.now(),
        "reason": "Tier 1 account cannot establish Priority eligibility; prospectively restore Standard",
        "protocol_registration_id": protocol["protocol_registration_id"],
        "prior_readiness_history_sha256": runner.sha256_file(history),
        "old_blocks_reset": False, "prior_priority_response_reused": False,
        "three_provider_collector_modified": False})
    freeze = json.loads(json.dumps(old_freeze))
    freeze.update(schema_version=standard.VERSION, protocol_version=standard.VERSION,
        protocol_registration_id=protocol["protocol_registration_id"], frozen_at_utc=scoped.now(),
        prior_human_profile_frozen_at_utc=old_freeze["frozen_at_utc"],
        standard_configuration_approved_at_utc="2026-10-06T03:35:46Z",
        prior_freeze_file=str(old_freeze_path), prior_freeze_sha256=old_sha)
    freeze_path = out_dir / "core_v2_provider_freeze.json"
    scoped.write(freeze_path, freeze)
    runner.load_freeze(freeze_path, protocol=protocol, wave_id="MIBO2-W01", site_id="JP01")
    scoped.write(out_dir / "STANDARD_CONTEXT.json", {"protocol_file": str(protocol_path),
        "protocol_file_sha256": runner.sha256_file(protocol_path),
        "old_protocol_file": str(old_protocol_path), "old_protocol_sha256": runner.sha256_file(old_protocol_path),
        "prior_report_file": str(old_report_path), "prior_report_sha256": runner.sha256_file(old_report_path),
        "prior_freeze_file": str(old_freeze_path), "prior_freeze_sha256": old_sha,
        "prior_readiness_history_file": str(history), "prior_readiness_history_sha256": runner.sha256_file(history),
        "created_at_utc": scoped.now(), "gemini_standard_policy": standard.POLICY,
        "service_tier_requested": "standard_default", "eligibility_correction": "restore_standard_after_priority_tier1_review",
        "human_execution_authorized": False, "three_provider_collector_modified": False})


def probe(*, out_dir: Path, current: datetime | None = None) -> dict:
    if os.environ.get("MIBO_CORE_V2_SMOKE_TEST") != preflight.SMOKE_SENTINEL:
        raise ValueError("Terms-reviewed fixed readiness sentinel is missing")
    context = json.loads((out_dir / "STANDARD_CONTEXT.json").read_text())
    protocol_path = Path(context["protocol_file"])
    protocol, protocol_sha = runner.load_protocol(protocol_path)
    if protocol_sha != context["protocol_file_sha256"]:
        raise ValueError("Standard protocol hash changed")
    freeze_path = out_dir / "core_v2_provider_freeze.json"
    freeze, freeze_sha = runner.load_freeze(freeze_path, protocol=protocol, wave_id="MIBO2-W01", site_id="JP01")
    original = admission.checked(Path(context["prior_report_file"]), context["prior_report_sha256"])
    history = admission.checked(Path(context["prior_readiness_history_file"]), context["prior_readiness_history_sha256"])
    for entry in history["files"]:
        admission.checked(Path(entry["file"]), entry["sha256"])
    admission.checked(Path(context["prior_freeze_file"]), context["prior_freeze_sha256"])
    if runner.sha256_file(Path(context["old_protocol_file"])) != context["old_protocol_sha256"]:
        raise ValueError("old protocol evidence changed")
    current = current or datetime.now(timezone.utc)
    if current < runner.parse_aware_utc(freeze["frozen_at_utc"]):
        raise ValueError("Standard readiness cannot precede its prospective freeze")
    bounds = runner.wave(protocol, "MIBO2-W01")
    close = runner.parse_aware_utc(bounds["close_utc"])
    if not runner.parse_aware_utc(bounds["start_utc"]) <= current < close:
        raise ValueError("original field window is not open")
    block = out_dir / "standard-recovery-block"
    block.mkdir(mode=0o750, exist_ok=True)
    records = sorted(block.glob("probe-*/RESULT.json"))
    if len(records) != len(list(block.glob("probe-*"))):
        raise ValueError("an interrupted or running Standard probe exists; stop and review")
    if records:
        latest = json.loads(records[-1].read_text())
        if latest.get("pass") is True:
            target = records[-1].parent
            report_path = target / "bundle/CORE_V2_BUNDLE_REPORT.json"
            if not report_path.exists():
                raise ValueError("passing evidence exists without a completed bundle; preserve it and review")
            return {"out_dir": target, "bundle": json.loads(report_path.read_text()), "provider_called": False}
        if len(records) >= 3:
            raise ValueError("Standard recovery block exhausted; no fourth probe")
        decision = decide_retry(attempt=len(records), failure_kind=latest["failure_kind"],
            failed_at=runner.parse_aware_utc(latest["recorded_at_utc"]),
            provider_retry_after_seconds=latest.get("retry_after_seconds"), field_close=close)
        if latest.get("http_status") not in {429, 500, 502, 503, 504, None} or not decision.retry:
            raise ValueError("this Standard failure is not retryable; no new probe")
        if current < runner.parse_aware_utc(decision.due_at_utc):
            raise ValueError("Standard retry wait has not elapsed; eligible UTC: " + decision.due_at_utc)
    else:
        honor_prior_waits(out_dir=out_dir, current=current, model_id=freeze["core_api"][admission.GOOGLE_SCOPE[0]]["model_id"])
    number = len(records) + 1
    target = block / f"probe-{number}"
    target.mkdir(mode=0o750)
    cfg = freeze["core_api"][admission.GOOGLE_SCOPE[0]]
    scoped.write(target / "PROBE_CONTEXT.json", {"readiness_only": True,
        "registered_mibo_prompt_used": False, "probe_number": number, "model_id": cfg["model_id"],
        "service_tier_requested": "standard_default", "provider_freeze_sha256": freeze_sha,
        "requested_at_utc": current.isoformat()})
    try:
        result = call_provider(provider="Google", model_id=cfg["model_id"],
            prompt=preflight.SYNTHETIC_PROMPT, profile=cfg["request_profile"], timeout_s=60, capture_response_metadata=True)
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
        raise ValueError(f"Google Standard FAIL / HTTP {exc.http_status} / {exc.kind}; private record: {target / 'RESULT.json'}") from None
    metadata = result.response_metadata or {}
    passed = (result.returned_model == cfg["model_id"] and 200 <= result.http_status < 300
        and "service_tier" not in result.request_payload
        and metadata.get("service_tier_actual") != "priority"
        and (result.response_json.get("modelVersion") is None or
             (isinstance(result.response_json["modelVersion"], str) and
              standard.model_matches(result.response_json["modelVersion"], cfg["model_id"]))))
    evidence = target / "SMOKE.json"
    scoped.write(evidence, {"protocol_version": standard.VERSION, "readiness_only": True,
        "requested_model": cfg["model_id"], "returned_model": result.returned_model,
        "http_status": result.http_status, "started_at_utc": result.started_at_utc,
        "completed_at_utc": result.completed_at_utc, "duration_ms": result.duration_ms,
        "request_payload": result.request_payload, "response": result.response_json,
        "raw_response_text": result.raw_response_text, "response_metadata": metadata, "usage": result.usage,
        "synthetic_prompt_sha256": hashlib.sha256(preflight.SYNTHETIC_PROMPT.encode()).hexdigest(),
        "registered_mibo_prompt_used": False, "pass": passed})
    scoped.write(target / "RESULT.json", {"pass": passed, "readiness_only": True,
        "failure_kind": None if passed else "request_environment_mismatch",
        "http_status": result.http_status, "recorded_at_utc": scoped.now(),
        "service_tier_actual": metadata.get("service_tier_actual"), "probe_number": number,
        "evidence_file": str(evidence), "evidence_sha256": runner.sha256_file(evidence)})
    if not passed:
        raise ValueError("Standard request/model was not confirmed; response preserved, collection remains disabled")
    report = json.loads(json.dumps(original))
    for check in report["synthetic_smoke_checks"]:
        if check["service_lineage_id"] == admission.GOOGLE_SCOPE[0]:
            check.clear()
            check.update(service_lineage_id=admission.GOOGLE_SCOPE[0], provider="Google",
                model_id=cfg["model_id"], file=str(evidence.resolve()), sha256=runner.sha256_file(evidence))
            check["pass"] = True
        else:
            check["file"] = str((Path(context["prior_report_file"]).parent / check["file"]).resolve())
    report.update(schema_version=standard.VERSION, protocol_version=standard.VERSION,
        protocol_registration_id=protocol["protocol_registration_id"], protocol_file_sha256=protocol_sha,
        provider_freeze_sha256=freeze_sha, checked_at_utc=scoped.now(),
        readiness_scope="admitted_lineages_only", admitted_lineages=admission.GOOGLE_SCOPE,
        outside_this_authorization_lineages=admission.INITIAL_SCOPE,
        prior_report_file=context["prior_report_file"], prior_report_sha256=context["prior_report_sha256"],
        prior_freeze_file=context["prior_freeze_file"], prior_freeze_sha256=context["prior_freeze_sha256"],
        prior_readiness_history_file=context["prior_readiness_history_file"],
        prior_readiness_history_sha256=context["prior_readiness_history_sha256"],
        gemini_standard_policy=standard.POLICY, new_standard_readiness_confirmed=True,
        google_recovery_probe_number=number, human_google_admission_required=True)
    report.update(prior_errors=original.get("errors", []), errors=[], all_four_ready=True)
    report["pass"] = True
    report_path = target / "STANDARD_READINESS_REPORT.json"
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
        raise ValueError("Standard manifest changed the scientific row count")
    for old, new in zip(old_rows, rows):
        if any(old[key] != new[key] for key in fields):
            raise ValueError("Standard manifest changed a scientific row")
    scoped.write(target / "WAVE_LINEAGE_PROVENANCE.json", {
        "wave_id": "MIBO2-W01", "site_id": "JP01", "full_intended_rows": 1120,
        "google_executable_rows": 280, "google_protocol_version": standard.VERSION,
        "other_lineages_execution_protocol": "2.0.2", "automatic_cross_version_pooling": False,
        "prior_freeze_sha256": context["prior_freeze_sha256"],
        "prior_manifest_sha256": prior_manifest_hash(context, target),
        "standard_manifest_sha256": built["manifest_sha256"],
        "logical_attempt_ids_preserved": True, "mapping": [
            {"attempt_id": row["attempt_id"], "service_lineage_id": row["service_lineage_id"],
             "executed_by_standard_scope": row["service_lineage_id"] in admission.GOOGLE_SCOPE} for row in rows]})
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
        standard.block_prior_google_attempts(root, "JP01", "MIBO2-W01")
        if Path("/etc/systemd/system", SERVICE).exists() and not ANCHOR.exists():
            raise ValueError("Standard service exists without its private anchor; preserve and review")
        for unit in ("mibo-core-v2.service", "mibo-core-v2-google.service", "mibo-core-v2-google-priority.service"):
            state = subprocess.run(["systemctl", "is-active", unit], capture_output=True, text=True).stdout.strip()
            if state not in {"inactive", "failed", "unknown"}:
                raise ValueError("another Google collection path is running; preserve it and review")
        if ANCHOR.exists():
            anchor = json.loads(ANCHOR.read_text())
            if Path(anchor["installed_source"]).resolve() != SOURCE or Path(anchor["readiness"]).resolve() != args.out_dir.resolve():
                raise ValueError("use the previously pinned Standard runtime and its single recovery block")
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
            prepare_configuration(protocol_path=SOURCE / "automation/config/core_v2_protocol.v2.0.4.json",
                old_protocol_path=old_protocol, old_freeze_path=original.parents[1] / "core_v2_provider_freeze.json",
                old_report_path=original, out_dir=args.out_dir)
            scoped.write(args.out_dir / "OLD_PROTOCOL_LINK.json", {"old_protocol_file": str(old_protocol),
                "old_protocol_sha256": runner.sha256_file(old_protocol)})
            scoped.write(ANCHOR, {"installed_source": str(SOURCE), "readiness": str(args.out_dir),
                "data_root": str(root), "protocol_version": standard.VERSION,
                "source_commit_sha": json.loads((SOURCE / "INSTALL_PROVENANCE.json").read_text())["source_commit_sha"]})
            os.chown(ANCHOR, 0, scoped.grp.getgrnam("mibo").gr_gid); ANCHOR.chmod(0o640)
        # Disable only dormant alternative Google units, never the three-provider collector.
        for unit in ("mibo-core-v2-google.service", "mibo-core-v2-google-priority.service"):
            if Path("/etc/systemd/system", unit).exists():
                subprocess.run(["systemctl", "disable", unit], check=True)
        authorizations = list((args.out_dir / "standard-recovery-block").glob("probe-*/core_v2_execution_authorization.scoped.json"))
        if authorizations:
            auth_path = authorizations[-1]
            base = auth_path.parent / "bundle"
            executor.preflight(protocol_path=base / "configuration/core_v2_protocol.final.json",
                freeze_path=base / "configuration/core_v2_provider_freeze.json",
                manifest_path=base / "manifests/MIBO2-W01-JP01-API-CORE.csv", authorization_path=auth_path, data_root=root)
            installed_unit = Path("/etc/systemd/system") / SERVICE
            saved_unit = auth_path.parent / SERVICE
            if not installed_unit.exists() or runner.sha256_file(installed_unit) != runner.sha256_file(saved_unit):
                raise ValueError("authorized Standard unit is missing or changed; preserve records and review")
            subprocess.run(["systemctl", "start", SERVICE], check=True)
            print("既存の人間承認を検証し、同じStandardサービスを実行します。新しい応答テストは行いません。")
            return 0
        freeze = json.loads((args.out_dir / "core_v2_provider_freeze.json").read_text())
        for cfg in freeze["core_api"].values():
            key = cfg["request_profile"]["api_key_env"]
            if values.get(key): os.environ[key] = values[key]
        os.environ.pop("MIBO_CORE_V2_EXECUTION", None)
        os.environ["MIBO_CORE_V2_SMOKE_TEST"] = preflight.SMOKE_SENTINEL
        print("Gemini 3.8 Flash / Standard要求 / 最大4096 / 固定の非観測確認1回。", flush=True)
        print("Standard設定を復元。追加クレジット購入は行いません。以前のPriority応答は流用しません。", flush=True)
        result = probe(out_dir=args.out_dir.resolve())
        print("Google Standard応答を確認: PASS。次はこのGoogle範囲だけの人間の実行承認です。", flush=True)
        scoped.authorize_and_start(out_dir=result["out_dir"], built=result["bundle"], data_root=root, values=values,
            service=SERVICE, phrase_required="AUTHORIZE_GOOGLE_STANDARD")
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        print("3社のサービスとコードは変更していません。Googleの開始状態は私有記録とサービス状態で確認してください。", file=sys.stderr)
        return 1
    finally:
        if args.out_dir.exists(): scoped.permissions(args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
