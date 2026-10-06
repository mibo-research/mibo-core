#!/usr/bin/env python3
"""Private VM: reuse verified three-provider readiness, then ask a human to start.

No live provider call, no automatic human signature, no change to old evidence.
Google admission is a separate action on the same sealed collector.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import grp
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
import core_v2_runner as runner
import runtime_health

OLD_COMMIT = "6292406fb91bceb725ed77d9d94695738df26681"
SERVICE = "mibo-core-v2-ready-three.service"
PHRASE = "AUTHORIZE_READY_THREE"
UNIT_DIR = Path("/etc/systemd/system")


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as fh:
        json.dump(value, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")


def preparation_module(source: Path):
    spec = importlib.util.spec_from_file_location("private_preparation", source / "runtime/prepare-core-v2-agent.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def checked_runtime(values: dict, *, first_start: bool) -> Path:
    if os.geteuid() != 0:
        raise ValueError("controlled VM root execution required")
    if runtime_health.installed_snapshot_state(SOURCE).get("snapshot_integrity_pass") is not True:
        raise ValueError("sealed installed collector integrity failed")
    if subprocess.check_output(["timedatectl", "show", "-p", "NTPSynchronized", "--value"], text=True).strip() != "yes":
        raise ValueError("VM clock is not synchronized")
    root = Path(values["MIBO_DATA_ROOT"])
    if not root.is_absolute() or not root.is_dir() or any(c.isspace() for c in str(root)):
        raise ValueError("invalid configured data root")
    versions = ["v2.0", "v2.0.1"] + (["v2.0.2"] if first_start else [])
    for version in versions:
        wave = root / version / "JP01" / "MIBO2-W01"
        if any(next((wave / folder).glob("*.json"), None) for folder in ("api_raw", "failures")):
            raise ValueError("prior confirmatory attempts exist; do not migrate or repeat first start")
    if shutil.disk_usage(root).free < 2 * 1024**3:
        raise ValueError("less than 2 GiB free")
    for name in (["mibo-core-v2.service", SERVICE] if first_start else ["mibo-core-v2.service"]):
        state = subprocess.run(["systemctl", "is-active", name], capture_output=True, text=True).stdout.strip()
        if state not in {"inactive", "failed", "unknown"}:
            raise ValueError("an incompatible collection service is running")
    subprocess.run(["runuser", "-u", "mibo", "--", "python3", "-c",
        "import tempfile,sys; f=tempfile.TemporaryFile(dir=sys.argv[1]); f.write(b'probe'); f.close()",
        str(root)], check=True)
    return root


def build_scoped(*, old_report_path: Path, old_freeze_path: Path,
                 protocol_path: Path, out_dir: Path) -> dict:
    protocol, protocol_sha = runner.load_protocol(protocol_path)
    if protocol["protocol_version"] != admission.VERSION:
        raise ValueError("scoped preparation requires v2.0.2")
    old = json.loads(old_report_path.read_text())
    old_freeze = json.loads(old_freeze_path.read_text())
    if (old.get("protocol_version") != "2.0.1" or old.get("pass") is not False
            or old.get("provider_freeze_sha256") != runner.sha256_file(old_freeze_path)):
        raise ValueError("original readiness identity/freeze mismatch")
    for line in (old_report_path.parent / "SHA256SUMS.txt").read_text().splitlines():
        digest, relative = line.split("  ", 1)
        path = (old_report_path.parent / relative).resolve()
        if not path.is_relative_to(old_report_path.parent.resolve()) or runner.sha256_file(path) != digest:
            raise ValueError("original readiness evidence integrity failed")
    models = old.get("model_checks", [])
    if len(models) != 4 or not all(c.get("exact_metadata_verified") is True for c in models):
        raise ValueError("all original model metadata checks must pass")
    approved = json.loads((SOURCE / "automation/config/core_v2_agent_provider_freeze.draft.json").read_text())
    for sid, cfg in old_freeze["core_api"].items():
        if (cfg["model_id"] != approved["core_api"][sid]["model_id"]
                or cfg["request_profile"] != approved["core_api"][sid]["request_profile"]):
            raise ValueError("frozen model/profile differs from approved configuration")
        terms = cfg["terms_review_source"]
        record = admission.checked(Path(terms["file"]), terms["sha256"])
        if (record.get("official_terms_and_applicable_research_conditions_reviewed_by_human") is not True
                or record.get("literal_ids_and_material_profiles_frozen_by_human") is not True):
            raise ValueError("original human Terms/profile review is incomplete")
    if datetime.now(timezone.utc) < runner.parse_aware_utc(protocol["prospectively_registered_at_utc"]):
        raise ValueError("public registration timestamp is in the future")
    out_dir.mkdir(mode=0o750)
    freeze = json.loads(json.dumps(old_freeze))
    freeze.update(schema_version=admission.VERSION, protocol_version=admission.VERSION,
        protocol_registration_id=protocol["protocol_registration_id"], frozen_at_utc=now(),
        prior_human_profile_frozen_at_utc=old_freeze["frozen_at_utc"],
        unchanged_profiles_carried_forward_under_approved_amendment=True,
        prior_freeze_file=str(old_freeze_path), prior_freeze_sha256=runner.sha256_file(old_freeze_path))
    freeze_path = out_dir / "core_v2_provider_freeze.json"
    write(freeze_path, freeze)
    report = json.loads(json.dumps(old))
    for check in report["synthetic_smoke_checks"]:
        check["file"] = str((old_report_path.parent / check["file"]).resolve())
    report.update(schema_version=admission.VERSION, protocol_version=admission.VERSION,
        protocol_registration_id=protocol["protocol_registration_id"],
        protocol_file_sha256=protocol_sha, provider_freeze_sha256=runner.sha256_file(freeze_path),
        checked_at_utc=now(), readiness_scope="admitted_lineages_only",
        admitted_lineages=admission.INITIAL_SCOPE, deferred_lineages=admission.GOOGLE_SCOPE,
        all_four_ready=False, reused_evidence=True, new_live_provider_calls=0,
        prior_report_file=str(old_report_path), prior_report_sha256=runner.sha256_file(old_report_path),
        prior_freeze_file=str(old_freeze_path), prior_freeze_sha256=runner.sha256_file(old_freeze_path))
    report["pass"] = True
    report_path = out_dir / "SCOPED_READINESS_REPORT.json"
    write(report_path, report)
    built = bundle.build_bundle(protocol_path=protocol_path, wave_id="MIBO2-W01", site_id="JP01",
        freeze_path=freeze_path, preflight_report_path=report_path, out_dir=out_dir / "bundle")
    rows = runner.read_csv(out_dir / "bundle" / built["manifest_file"])
    if rows != runner.generate_manifest(protocol_path=protocol_path, freeze_path=freeze_path,
                                       wave_id="MIBO2-W01", site_id="JP01"):
        raise ValueError("strict deterministic manifest comparison failed")
    write(out_dir / "READINESS_STATUS.json", {"technical_readiness_completed_at_utc": now(),
        "planned_preparation_completed_at_utc": "2026-10-06T00:00:00Z",
        "planned_observation_start_at_utc": "2026-10-06T00:00:00Z",
        "actual_preparation_completed_at_utc": None, "actual_observation_start_at_utc": None,
        "full_manifest_rows": len(rows), "admitted_rows": built["admitted_request_count"],
        "all_four_ready": False, "collection_enabled": False})
    return built


def permissions(root: Path) -> None:
    gid = grp.getgrnam("mibo").gr_gid
    for path in [root, *root.rglob("*")]:
        os.chown(path, 0, gid)
        path.chmod(0o750 if path.is_dir() else 0o640)


def authorize_and_start(*, out_dir: Path, built: dict, data_root: Path, values: dict,
                        service: str = SERVICE, phrase_required: str = PHRASE) -> None:
    base = out_dir / "bundle"
    built = dict(built)
    built["bundle_report_sha256"] = runner.sha256_file(base / "CORE_V2_BUNDLE_REPORT.json")
    template = base / "core_v2_execution_authorization.template.json"
    authorization_path = out_dir / "core_v2_execution_authorization.scoped.json"
    admitted = admission.scope(built["admitted_lineages"])
    print("\n指定した系統の技術準備 PASS。全4社の一括承認ではありません。", flush=True)
    print("実行対象: " + ", ".join(admitted), flush=True)
    print(f"予定1,120件 / 今回の許可範囲 {built['admitted_request_count']}件", flush=True)
    for key in ("protocol_file_sha256", "provider_freeze_sha256", "manifest_sha256", "bundle_report_sha256"):
        print(f"{key}: {built[key]}", flush=True)
    print(f"具体的な実行バンドル: {base}", flush=True)
    with open("/dev/tty", "r", encoding="utf-8") as reader, open("/dev/tty", "w", encoding="utf-8", buffering=1) as tty:
        print("上記ハッシュ・指定した系統の範囲・元の時間帯を確認し、このVMで自動観測を開始する場合だけ入力してください。", file=tty)
        print("Operations Lead 氏名: ", end="", flush=True, file=tty)
        name = reader.readline().strip()
        print(f"実行承認語 {phrase_required}: ", end="", flush=True, file=tty)
        phrase = reader.readline().strip()
    if not name or phrase != phrase_required:
        raise ValueError("explicit private human execution authorization not completed")
    auth = json.loads(template.read_text())
    auth.update(authorized=True, authorized_at_utc=now(), operations_lead=name,
        terms_review_complete=True, authorize_confirmatory_api_core=True,
        prospective_agent_amendment_reviewed=True,
        late_activation_with_original_windows_approved=True,
        prospective_lineage_admission_amendment_reviewed=True,
        explicit_human_phrase=phrase)
    if auth["protocol_version"] == runner.PRIORITY_PROTOCOL_VERSION:
        auth["prospective_gemini_priority_amendment_reviewed"] = True
    write(authorization_path, auth)
    protocol = base / built["protocol_file"]
    freeze = base / built["provider_freeze_file"]
    manifest = base / built["manifest_file"]
    permissions(out_dir)
    executor.preflight(protocol_path=protocol, manifest_path=manifest, freeze_path=freeze,
        authorization_path=authorization_path, data_root=data_root)
    # Root's dry preflight creates the new namespace. The service runs as mibo.
    import pwd
    user = pwd.getpwnam("mibo")
    namespace = "v" + auth["protocol_version"]
    for path in (data_root / namespace, data_root / namespace / "JP01", data_root / namespace / "JP01/MIBO2-W01"):
        os.chown(path, user.pw_uid, user.pw_gid)
        path.chmod(0o750)
    paths = [SOURCE, out_dir, data_root]
    if any(any(c.isspace() for c in str(p)) for p in paths):
        raise ValueError("runtime paths with whitespace are unsupported")
    env_path = out_dir / "ready-three.env"
    frozen = json.loads(freeze.read_text())
    env = {frozen["core_api"][sid]["request_profile"]["api_key_env"]:
           values[frozen["core_api"][sid]["request_profile"]["api_key_env"]] for sid in admitted}
    env["MIBO_CORE_V2_EXECUTION"] = executor.EXECUTION_SENTINEL
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    with env_path.open("x") as fh:
        for key, value in env.items():
            if any(c in value for c in "\n\r\x00"):
                raise ValueError("invalid credential/environment value")
            fh.write(key + "=" + json.dumps(value, ensure_ascii=False) + "\n")
    os.chown(env_path, 0, grp.getgrnam("mibo").gr_gid)
    env_path.chmod(0o640)
    unit_path = UNIT_DIR / service
    if unit_path.exists():
        raise ValueError("scoped service already exists; do not overwrite")
    command = f"/usr/bin/python3 -B {SOURCE}/automation/core_v2_waiter.py --protocol {protocol} --wave MIBO2-W01 --manifest {manifest} --freeze {freeze} --authorization {authorization_path} --data-root {data_root}"
    unit = f"[Unit]\nDescription=MIBO Core authorized scope\nAfter=network-online.target time-sync.target\nWants=network-online.target time-sync.target\n[Service]\nType=simple\nUser=mibo\nGroup=mibo\nWorkingDirectory={SOURCE}\nEnvironmentFile={env_path}\nExecStart={command}\nRestart=no\nTimeoutStartSec=infinity\nNoNewPrivileges=true\nPrivateTmp=true\nProtectSystem=strict\nProtectHome=true\nReadWritePaths={data_root} /srv/mibo-private\nUMask=0077\n[Install]\nWantedBy=multi-user.target\n"
    # Preserve the exact new service definition alongside the private hashes.
    with (out_dir / service).open("x") as fh:
        fh.write(unit)
    with unit_path.open("x") as fh:
        fh.write(unit)
    write(out_dir / "EXECUTION_AUTHORIZATION_STATUS.json", {
        "actual_preparation_completed_at_utc": now(),
        "actual_observation_start_at_utc": None, "admitted_lineages": admitted,
        "authorization_file_sha256": runner.sha256_file(authorization_path),
        "service": service, "source_commit_sha": json.loads((SOURCE / "INSTALL_PROVENANCE.json").read_text())["source_commit_sha"]})
    write(out_dir / "RUNTIME_LINK.json", {"installed_source": str(SOURCE),
        "data_root": str(data_root), "readiness": str(out_dir), "service": service,
        "admitted_lineages": admitted, "authorization_file": str(authorization_path),
        "source_commit_sha": json.loads((SOURCE / "INSTALL_PROVENANCE.json").read_text())["source_commit_sha"]})
    permissions(out_dir)
    subprocess.run(["systemctl", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "enable", "--now", service], check=True)
    state = subprocess.check_output(["systemctl", "show", service, "-p", "ActiveState", "-p", "SubState"], text=True)
    write(out_dir / "SERVICE_ACTIVATION_STATUS.json", {"recorded_at_utc": now(),
        "service_state": state, "actual_observation_start_at_utc": None,
        "note": "Actual request times are recorded by the private observation archive; service activation alone does not prove submission."})
    print(state, flush=True)
    print(f"指定した系統のサービスを起動しました。私有記録: {out_dir}", flush=True)
    print(f"状態確認: sudo systemctl status {service} --no-pager", flush=True)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args()
    os.umask(0o077)
    try:
        module = preparation_module(SOURCE)
        values = module.read_environment(Path("/etc/mibo/mibo-core-v2.env"))
        data_root = checked_runtime(values, first_start=True)
        reports = list(Path("/srv/mibo-private").glob("agent-ready.*/readiness/preflight/CORE_V2_API_PREFLIGHT_REPORT.json"))
        report = max(reports, key=lambda path: path.stat().st_mtime)
        old_sources = [path for path in Path("/opt").glob("mibo-core-v2.0.1.*")
            if (path / "INSTALL_PROVENANCE.json").is_file()
            and json.loads((path / "INSTALL_PROVENANCE.json").read_text()).get("source_commit_sha") == OLD_COMMIT]
        old_source = max(old_sources, key=lambda path: path.stat().st_mtime)
        if runtime_health.installed_snapshot_state(old_source).get("snapshot_integrity_pass") is not True:
            raise ValueError("old collector integrity failed")
        old_protocol = old_source / "automation/config/core_v2_agent_protocol.v2.0.1.json"
        if json.loads(report.read_text())["protocol_file_sha256"] != runner.sha256_file(old_protocol):
            raise ValueError("original readiness protocol mismatch")
        built = build_scoped(old_report_path=report,
            old_freeze_path=report.parents[1] / "core_v2_provider_freeze.json",
            protocol_path=SOURCE / "automation/config/core_v2_protocol.v2.0.2.json", out_dir=args.out_dir)
        authorize_and_start(out_dir=args.out_dir, built=built, data_root=data_root, values=values)
    except Exception as exc:
        if args.out_dir.is_dir():
            # Local/operational exceptions only; this helper never calls a provider.
            write(args.out_dir / "SCOPED_PREPARATION_FAILURE.json", {
                "recorded_at_utc": now(), "kind": type(exc).__name__, "message": str(exc),
                "service_may_have_started": (args.out_dir / "EXECUTION_AUTHORIZATION_STATUS.json").exists()})
            permissions(args.out_dir)
        print(f"停止: {type(exc).__name__}。私有記録とサービス状態を確認してください。", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
