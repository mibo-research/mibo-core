#!/usr/bin/env python3
"""One documented Google technical recovery block; human admission stays separate.

Run manually on the controlled VM. Each invocation sends at most one fixed
synthetic prompt. It never touches the active three-provider collector.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

SOURCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE / "automation"))
import core_v2_admission as admission
import core_v2_bundle as bundle
import core_v2_preflight as preflight
import core_v2_runner as runner
from provider_adapters import AdapterFailure, call_provider
from retry_policy import decide_retry

spec = importlib.util.spec_from_file_location("scoped_preparation", SOURCE / "runtime/prepare-core-v2-scoped.py")
scoped = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scoped)


def probe(*, readiness: Path, current: datetime | None = None) -> dict:
    if os.environ.get("MIBO_CORE_V2_SMOKE_TEST") != preflight.SMOKE_SENTINEL:
        raise ValueError("fixed readiness sentinel is not enabled")
    current = current or datetime.now(timezone.utc)
    base = readiness / "bundle"
    protocol_path = base / "configuration/core_v2_protocol.final.json"
    freeze_path = base / "configuration/core_v2_provider_freeze.json"
    protocol, protocol_sha = runner.load_protocol(protocol_path)
    freeze, freeze_sha = runner.load_freeze(freeze_path, protocol=protocol, wave_id="MIBO2-W01", site_id="JP01")
    auth_path = readiness / "core_v2_execution_authorization.scoped.json"
    auth = json.loads(auth_path.read_text())
    if auth.get("authorized") is not True:
        raise ValueError("initial three-provider human authorization is missing")
    admission.validate_authorization(auth, protocol_path=protocol_path, freeze_path=freeze_path,
                                     protocol=protocol, freeze=freeze)
    if auth["admitted_lineages"] != admission.INITIAL_SCOPE:
        raise ValueError("expected the initial three-provider admission")
    bounds = runner.wave(protocol, "MIBO2-W01")
    close = runner.parse_aware_utc(bounds["close_utc"])
    if not runner.parse_aware_utc(bounds["start_utc"]) <= current < close:
        raise ValueError("original registered field window is not open")
    block = readiness / "google-recovery-block"
    block.mkdir(mode=0o750, exist_ok=True)
    if not (block / "CONTEXT.json").exists():
        scoped.write(block / "CONTEXT.json", {"prospective_amendment": protocol["protocol_registration_id"],
            "created_at_utc": current.isoformat(), "readiness_only": True,
            "maximum_probes": 3, "prior_v2_0_1_evidence_preserved": True,
            "initial_authorization_sha256": runner.sha256_file(auth_path)})
    attempts = sorted(block.glob("probe-*/RESULT.json"))
    reservations = list(block.glob("probe-*"))
    if len(attempts) != len(reservations):
        raise ValueError("an interrupted or running probe exists; preserve it and review")
    if len(attempts) >= 3:
        raise ValueError("Google recovery block exhausted; no fourth probe")
    if attempts:
        latest = json.loads(attempts[-1].read_text())
        if latest.get("pass") is True:
            raise ValueError("Google already passed; use its existing unsigned bundle")
        decision = decide_retry(attempt=len(attempts), failure_kind=latest["failure_kind"],
            failed_at=runner.parse_aware_utc(latest["recorded_at_utc"]),
            provider_retry_after_seconds=latest.get("retry_after_seconds"), field_close=close)
        if latest.get("http_status") not in {429, 500, 502, 503, 504, None} or not decision.retry:
            raise ValueError("latest failure cannot be retried in this block")
        if current < runner.parse_aware_utc(decision.due_at_utc):
            raise ValueError("readiness wait has not elapsed; eligible UTC: " + decision.due_at_utc)
    else:
        initial = json.loads(Path(auth["readiness_report_file"]).read_text())
        original = Path(initial["prior_report_file"])
        failures = [Path(next(c for c in initial["synthetic_smoke_checks"]
                             if c["service_lineage_id"] == admission.GOOGLE_SCOPE[0])["file"])]
        failures.extend(original.parents[1].glob("recovery-*/RECOVERY_FAILURE.json"))
        for failure_path in failures:
            failure = json.loads(failure_path.read_text())
            if failure.get("http_status") != 503:
                raise ValueError("prior Google recovery had a non503 failure; stop and review")
            due = runner.parse_aware_utc(failure["recorded_at_utc"]) + timedelta(seconds=max(600, failure.get("retry_after_seconds") or 0))
            if current < due:
                raise ValueError("prior provider readiness wait has not elapsed; eligible UTC: " + due.isoformat())
    number = len(attempts) + 1
    target = block / f"probe-{number}"
    target.mkdir(mode=0o750)
    cfg = freeze["core_api"][admission.GOOGLE_SCOPE[0]]
    scoped.write(target / "PROBE_CONTEXT.json", {"readiness_only": True, "probe_number": number,
        "requested_at_utc": current.isoformat(), "model_id": cfg["model_id"],
        "provider_freeze_sha256": freeze_sha, "registered_mibo_prompt_used": False})
    try:
        result = call_provider(provider="Google", model_id=cfg["model_id"],
            prompt=preflight.SYNTHETIC_PROMPT, profile=cfg["request_profile"], timeout_s=60)
    except AdapterFailure as exc:
        body = exc.response_body
        if body:
            for entry in freeze["core_api"].values():
                key = os.environ.get(entry["request_profile"]["api_key_env"])
                if key:
                    body = body.replace(key, "[REDACTED]")
        scoped.write(target / "RESULT.json", {"pass": False, "readiness_only": True,
            "failure_kind": exc.kind, "http_status": exc.http_status,
            "retry_after_seconds": exc.retry_after_seconds, "response_body": body,
            "recorded_at_utc": scoped.now(), "probe_number": number})
        raise ValueError(f"Google fixed readiness FAIL / HTTP {exc.http_status}; three-provider service unchanged") from None
    passed = result.returned_model == cfg["model_id"] and 200 <= result.http_status < 300
    evidence = target / "SMOKE.json"
    scoped.write(evidence, {"protocol_version": admission.VERSION, "readiness_only": True,
        "requested_model": cfg["model_id"], "returned_model": result.returned_model,
        "http_status": result.http_status, "started_at_utc": result.started_at_utc,
        "completed_at_utc": result.completed_at_utc, "duration_ms": result.duration_ms,
        "usage": result.usage, "request_payload": result.request_payload,
        "response": result.response_json, "raw_response_text": result.raw_response_text,
        "synthetic_prompt_sha256": hashlib.sha256(preflight.SYNTHETIC_PROMPT.encode()).hexdigest(),
        "registered_mibo_prompt_used": False, "pass": passed})
    scoped.write(target / "RESULT.json", {"pass": passed, "readiness_only": True,
        "recorded_at_utc": scoped.now(), "probe_number": number, "http_status": result.http_status,
        "failure_kind": None if passed else "request_environment_mismatch",
        "evidence_file": str(evidence), "evidence_sha256": runner.sha256_file(evidence)})
    if not passed:
        raise ValueError("Google model/status mismatch; response retained, no retry or admission")
    report = json.loads(Path(auth["readiness_report_file"]).read_text())
    for check in report["synthetic_smoke_checks"]:
        if check["service_lineage_id"] == admission.GOOGLE_SCOPE[0]:
            check.clear()
            check.update(service_lineage_id=admission.GOOGLE_SCOPE[0], provider="Google",
                model_id=cfg["model_id"], file=str(evidence.resolve()), sha256=runner.sha256_file(evidence))
            check["pass"] = True
    report.update(checked_at_utc=scoped.now(), admitted_lineages=admission.GOOGLE_SCOPE,
        deferred_lineages=[], previously_authorized_lineages=admission.INITIAL_SCOPE,
        human_google_admission_required=True,
        all_four_ready=True,
        google_recovery_probe_number=number, prior_initial_report_file=auth["readiness_report_file"],
        prior_initial_report_sha256=auth["readiness_report_sha256"])
    report_path = target / "GOOGLE_READINESS_REPORT.json"
    scoped.write(report_path, report)
    built = bundle.build_bundle(protocol_path=protocol_path, freeze_path=freeze_path,
        wave_id="MIBO2-W01", site_id="JP01", preflight_report_path=report_path,
        out_dir=target / "bundle")
    if built["manifest_sha256"] != auth["manifest_sha256"]:
        raise ValueError("Google admission changed the original manifest")
    return {"out_dir": target, "bundle": built}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--readiness", type=Path, required=True)
    parser.add_argument("--authorize-passed-probe", type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    try:
        values = scoped.preparation_module(SOURCE).read_environment(Path("/etc/mibo/mibo-core-v2.env"))
        root = scoped.checked_runtime(values, first_start=False)
        if args.authorize_passed_probe:
            target = args.authorize_passed_probe.resolve()
            if not target.is_relative_to((args.readiness / "google-recovery-block").resolve()):
                raise ValueError("passed probe must belong to this recovery block")
            result = json.loads((target / "RESULT.json").read_text())
            if result.get("pass") is not True:
                raise ValueError("the selected Google probe did not pass")
            built = json.loads((target / "bundle/CORE_V2_BUNDLE_REPORT.json").read_text())
            scoped.authorize_and_start(out_dir=target, built=built, data_root=root, values=values,
                service="mibo-core-v2-google.service", phrase_required="AUTHORIZE_GOOGLE_JOIN")
        else:
            os.environ.pop("MIBO_CORE_V2_EXECUTION", None)
            for cfg in json.loads((args.readiness / "bundle/configuration/core_v2_provider_freeze.json").read_text())["core_api"].values():
                key = cfg["request_profile"]["api_key_env"]
                if values.get(key):
                    os.environ[key] = values[key]
            os.environ["MIBO_CORE_V2_SMOKE_TEST"] = preflight.SMOKE_SENTINEL
            result = probe(readiness=args.readiness.resolve())
            print(f"Google readiness PASS。まだ観測開始は未承認です。合格記録: {result['out_dir']}")
            print("次に同じコードで --authorize-passed-probe を指定し、ハッシュと参加範囲を人間が確認します。")
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        if (args.readiness / "google-recovery-block").exists():
            scoped.permissions(args.readiness / "google-recovery-block")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
