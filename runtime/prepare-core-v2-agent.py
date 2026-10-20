#!/usr/bin/env python3
"""Private VM readiness only; never sign authorization or launch collection.

Exact IDs/settings come from the approved configuration template. Eligibility
is an explicit terminal attestation, never inferred from discovery results.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

SOURCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE / "automation"))
import api_preflight as api
import core_v2_bundle as bundle
import core_v2_preflight as preflight
import core_v2_runner as runner
import mibo_runner as instrument

TERMS_URLS = {
    "OpenAI": "https://openai.com/policies/services-agreement/",
    "Anthropic": "https://www.anthropic.com/legal/commercial-terms",
    "Google": "https://ai.google.dev/gemini-api/terms",
    "Perplexity AI": "https://www.perplexity.ai/en-GB/hub/legal/perplexity-api-terms-of-service",
}
ATTESTATION = "TERMS_AND_PROFILE_REVIEWED"


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write(path: Path, value: object) -> str:
    data = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(data)
    return hashlib.sha256(data).hexdigest()


def read_environment(path: Path) -> dict[str, str]:
    """Read literal single-value entries without executing/expanding shell text."""
    values = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, raw = line.partition("=")
        if not sep or not key.isidentifier() or key in values:
            raise ValueError("invalid or duplicate environment entry")
        parts = shlex.split(raw, comments=False)
        if len(parts) != 1:
            raise ValueError("environment entries require one literal value")
        values[key] = parts[0]
    return values


def attest(reader, tty, freeze: dict) -> str:
    print("\n規約レビューの公開資料:", file=tty)
    print((SOURCE / "docs/v2.0.1/API_TERMS_REVIEW_NOTES_20261006_DRAFT.md").read_text(), file=tty)
    print("\n承認済みのモデルと設定:", file=tty)
    for entry in freeze["core_api"].values():
        print(entry["model_id"], json.dumps(entry["request_profile"], ensure_ascii=False), file=tty)
    print("\nこれは観測開始の承認ではありません。", file=tty)
    print("4社の公式規約・利用地域・研究利用条件、実際のアカウントの課金状態と利用枠を確認済みで、", file=tty)
    print("上記IDと設定を人間の判断で固定する場合だけ、氏名と確認語を入力してください。", file=tty)
    print("未確認ならEnterで停止します。APIキーは入力しないでください。", file=tty)
    print("確認者氏名: ", end="", flush=True, file=tty)
    reviewer = reader.readline().strip()
    print(f"確認語 {ATTESTATION}: ", end="", flush=True, file=tty)
    decision = reader.readline().strip()
    if not reviewer or decision != ATTESTATION:
        raise ValueError("private Terms/profile attestation not completed")
    return reviewer


def prepare(*, env_path: Path, out_dir: Path, protocol_path: Path) -> None:
    if os.geteuid() != 0:
        raise ValueError("run only as root on the controlled private VM")
    protocol, _ = runner.load_protocol(protocol_path)
    values = read_environment(env_path)
    data_root = Path(values["MIBO_DATA_ROOT"])
    if not data_root.is_absolute() or not data_root.is_dir():
        raise ValueError("configured data root must be an existing absolute directory")
    wave_id, site_id = "MIBO2-W01", "JP01"
    bounds = runner.wave(protocol, wave_id)
    if not (runner.parse_aware_utc(bounds["start_utc"]) <= datetime.now(timezone.utc)
            < runner.parse_aware_utc(bounds["close_utc"])):
        raise ValueError("original field window is not open")
    state = subprocess.run(["systemctl", "is-active", "mibo-core-v2.service"],
                           capture_output=True, text=True).stdout.strip()
    if state not in {"inactive", "failed"}:
        raise ValueError("collection service must be stopped before preparation")
    ntp = subprocess.check_output(["timedatectl", "show", "-p", "NTPSynchronized", "--value"], text=True).strip()
    if ntp != "yes":
        raise ValueError("VM UTC clock is not synchronized")
    for version in ("v2.0", "v2.0.1"):
        root = data_root / version / site_id / wave_id
        if any(next((root / folder).glob("*.json"), None) is not None
               for folder in ("api_raw", "failures")):
            raise ValueError("retained wave attempts exist; stop and review before preparation")
    subprocess.run(["runuser", "-u", "mibo", "--", "python3", "-c",
                    "import tempfile,sys; from pathlib import Path; "
                    "f=tempfile.NamedTemporaryFile(dir=sys.argv[1],prefix='mibo-readiness-',delete=True); "
                    "f.write(b'write probe'); f.flush(); f.close()", str(data_root)], check=True)
    if shutil.disk_usage(data_root).free < 2 * 1024**3:
        raise ValueError("less than 2 GiB free in configured data store")
    freeze = json.loads((SOURCE / "automation/config/core_v2_agent_provider_freeze.draft.json").read_text())
    for entry in freeze["core_api"].values():
        key = entry["request_profile"]["api_key_env"]
        if not values.get(key):
            raise ValueError(f"missing credential variable: {key}")
        os.environ[key] = values[key]
    # The env file's collection sentinel is deliberately never imported.
    os.environ.pop("MIBO_CORE_V2_EXECUTION", None)
    if out_dir.exists():
        raise FileExistsError("private readiness directory already exists")
    out_dir.mkdir(parents=True, mode=0o700)
    print(f"私有記録: {out_dir}", flush=True)
    evidence = {}
    for service in instrument._services():
        sid, label = service["service_lineage_id"], service["provider"]
        provider = preflight._api_provider(label)
        model_id = freeze["core_api"][sid]["model_id"]
        catalog, ids = api.fetch_catalog(provider)
        exact = api.fetch_exact_model(provider, model_id)
        verified = (api.returned_metadata_model_id(provider, exact.data) == model_id
                    if exact is not None else model_id in ids)
        if not verified:
            raise ValueError(f"catalog/metadata verification failed: {label}")
        path = out_dir / "discovery" / f"{sid}.json"
        sha = write(path, {"provider": label, "model_id": model_id,
            "catalog": catalog.__dict__, "exact_metadata": exact.__dict__ if exact else None,
            "verified": True, "automatic_eligibility_decision": False})
        evidence[sid] = {"file": str(path), "sha256": sha, "verified_at_utc": now()}
        print(f"モデル確認 PASS: {label} / {model_id}", flush=True)
    with open("/dev/tty", "r", encoding="utf-8") as reader, \
            open("/dev/tty", "w", encoding="utf-8", buffering=1) as tty:
        reviewer = attest(reader, tty, freeze)
    attested_at = now()
    terms_notes = SOURCE / "docs/v2.0.1/API_TERMS_REVIEW_NOTES_20261006_DRAFT.md"
    private_notes = out_dir / "TERMS_SOURCE_NOTES.md"
    with private_notes.open("xb") as handle:
        handle.write(terms_notes.read_bytes())
    terms_path = out_dir / "TERMS_AND_PROFILE_HUMAN_REVIEW.json"
    terms_sha = write(terms_path, {"reviewer": reviewer, "attested_at_utc": attested_at,
        "source_notes_file": str(private_notes), "source_notes_acquired_at_utc": attested_at,
        "source_notes_sha256": runner.sha256_file(private_notes),
        "source_notes_are_direct_terms_page_captures": False,
        "official_terms_urls": TERMS_URLS,
        "official_terms_and_applicable_research_conditions_reviewed_by_human": True,
        "actual_accounts_regions_billing_and_sufficient_rate_limits_attested_by_human": True,
        "literal_ids_and_material_profiles_frozen_by_human": True,
        "identifier_lock_does_not_claim_frozen_provider_weights": True,
        "perplexity_agent_zero_retention_claimed": False,
        "profiles": freeze["core_api"], "wave_execution_authorized": False})
    freeze.update(protocol_registration_id=protocol["protocol_registration_id"],
                  frozen_at_utc=attested_at, human_reviewer=reviewer)
    for sid, entry in freeze["core_api"].items():
        entry.update(status="eligible", model_version_locked=True,
            selection_rationale="Operations Lead selected exact identifier and approved material profile; explicit private human Terms/profile attestation",
            provider_evidence=evidence[sid], verified_at_utc=evidence[sid]["verified_at_utc"],
            terms_review_date=attested_at[:10],
            terms_review_source={"file": str(terms_path), "sha256": terms_sha})
    freeze_path = out_dir / "core_v2_provider_freeze.json"
    write(freeze_path, freeze)
    runner.load_freeze(freeze_path, protocol=protocol, wave_id=wave_id, site_id=site_id)
    os.environ["MIBO_CORE_V2_SMOKE_TEST"] = preflight.SMOKE_SENTINEL
    print("固定の非観測テストを各モデル1回実行します。", flush=True)
    report = preflight.run_preflight(protocol_path=protocol_path, freeze_path=freeze_path,
                                   out_dir=out_dir / "preflight", smoke=True)
    for check in report["synthetic_smoke_checks"]:
        print(f"応答テスト {'PASS' if check['pass'] else 'FAIL'}: {check['provider']} / {check['model_id']}"
              f" {check.get('failure_kind', '')}", flush=True)
    if report["pass"] is not True:
        raise ValueError("readiness failed; no bundle or collection authorized")
    result = bundle.build_bundle(protocol_path=protocol_path, wave_id=wave_id, site_id=site_id,
        freeze_path=freeze_path, preflight_report_path=out_dir / "preflight/CORE_V2_API_PREFLIGHT_REPORT.json",
        out_dir=out_dir / "bundle")
    manifest_path = out_dir / "bundle" / result["manifest_file"]
    rows = runner.read_csv(manifest_path)
    expected_rows = runner.generate_manifest(protocol_path=protocol_path, freeze_path=freeze_path,
                                            wave_id=wave_id, site_id=site_id)
    if rows != expected_rows:
        raise ValueError("strict deterministic manifest comparison failed")
    status = {"status": "READY_FOR_HUMAN_EXECUTION_AUTHORIZATION", "technical_readiness_completed_at_utc": now(),
        "actual_preparation_completed_at_utc": None,
        "planned_preparation_completed_at_utc": bounds["start_utc"],
        "planned_observation_start_at_utc": bounds["start_utc"],
        "actual_observation_start_at_utc": None,
        "data_root": str(data_root), "installed_source": str(SOURCE), "bundle": result,
        "strict_deterministic_manifest_comparison_passed": True,
        "collection_enabled": False, "human_execution_authorization_completed": False}
    write(out_dir / "READINESS_STATUS.json", status)
    print(f"準備 PASS / マニフェスト {result['initial_request_count']}件", flush=True)
    print(f"技術テスト完了 UTC: {status['technical_readiness_completed_at_utc']}", flush=True)
    for field in ("protocol_file_sha256", "provider_freeze_sha256", "manifest_sha256", "bundle_report_sha256"):
        print(f"{field}: {result[field]}", flush=True)
    print(f"実行承認テンプレート: {out_dir / 'bundle/core_v2_execution_authorization.template.json'}", flush=True)
    print("実際の観測開始は未実施。次はハッシュを確認した人間の実行承認です。", flush=True)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--env", type=Path, default=Path("/etc/mibo/mibo-core-v2.env"))
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--protocol", type=Path, default=SOURCE / "automation/config/core_v2_agent_protocol.v2.0.1.json")
    args = p.parse_args()
    os.umask(0o077)
    try:
        prepare(env_path=args.env, out_dir=args.out_dir, protocol_path=args.protocol)
    except Exception as exc:
        # No raw provider error, response content, credential, or traceback in terminal.
        if args.out_dir.is_dir():
            message = str(exc)
            try:
                values = read_environment(args.env)
                for name in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "PERPLEXITY_API_KEY"):
                    if values.get(name):
                        message = message.replace(values[name], "[REDACTED]")
                write(args.out_dir / "PREPARATION_FAILURE.json", {
                    "failure_at_utc": now(), "kind": type(exc).__name__,
                    "message": message, "collection_started": False})
                print(f"私有エラー記録: {args.out_dir / 'PREPARATION_FAILURE.json'}", file=sys.stderr)
            except Exception:
                pass
        print(f"準備停止: {type(exc).__name__}。観測は開始していません。", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
