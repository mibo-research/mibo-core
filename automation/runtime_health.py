#!/usr/bin/env python3
"""Runtime health and provenance checks for the controlled MIBO Japan site.

The report never prints credential values. It supports both a clean Git checkout
and the commit/hash-bound installed snapshot used by the production runtime.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import stat
import subprocess
import sys
from typing import Any


def _run(args: list[str]) -> tuple[int, str]:
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=10, check=False)
        return p.returncode, p.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return 127, ""


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def installed_snapshot_state(repo_root: Path) -> dict[str, Any] | None:
    """Verify the complete sealed tree without following untrusted paths.

    Only an entirely absent seal is reported as None. A partial or damaged seal
    fails closed, including extra files that the checksum manifest did not bind.
    Installed runtimes must disable bytecode writes before this check runs.
    """
    provenance_path = repo_root / "INSTALL_PROVENANCE.json"
    sums_path = repo_root / "INSTALL_SHA256SUMS.txt"
    if not any(p.exists() or p.is_symlink() for p in (provenance_path, sums_path)):
        return None
    errors: list[str] = []
    provenance: dict[str, Any] = {}
    installed_files: set[str] = set()
    if repo_root.is_symlink() or not repo_root.is_dir():
        errors.append("installed root must be a real directory")
    else:
        def walk_error(exc: OSError) -> None:
            errors.append("cannot enumerate installed tree")

        for current, dirs, files in os.walk(repo_root, followlinks=False, onerror=walk_error):
            current_path = Path(current)
            for name in list(dirs):
                path = current_path / name
                if path.is_symlink():
                    errors.append(f"installed symlink is forbidden: {path.relative_to(repo_root).as_posix()}")
                    dirs.remove(name)
            for name in files:
                path = current_path / name
                rel = path.relative_to(repo_root).as_posix()
                try:
                    mode = path.lstat().st_mode
                except OSError:
                    errors.append(f"cannot inspect installed file: {rel}")
                    continue
                if stat.S_ISLNK(mode):
                    errors.append(f"installed symlink is forbidden: {rel}")
                elif not stat.S_ISREG(mode):
                    errors.append(f"installed special file is forbidden: {rel}")
                elif rel != "INSTALL_SHA256SUMS.txt":
                    installed_files.add(rel)

    try:
        if "INSTALL_PROVENANCE.json" not in installed_files:
            raise ValueError("missing or unsafe provenance")
        loaded = json.loads(provenance_path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError("provenance must be an object")
        provenance = loaded
    except (OSError, ValueError, UnicodeError):
        errors.append("invalid or missing INSTALL_PROVENANCE.json")
    try:
        if repo_root.is_symlink() or sums_path.is_symlink() or not sums_path.is_file():
            raise ValueError("missing or unsafe checksum manifest")
        lines = sums_path.read_text(encoding="utf-8").splitlines()
    except (OSError, ValueError, UnicodeError):
        errors.append("invalid or missing INSTALL_SHA256SUMS.txt")
        lines = []
    declared: set[str] = set()
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            expected, rel = line.split("  ", 1)
        except ValueError:
            errors.append(f"malformed checksum line {number}")
            continue
        if not re.fullmatch(r"[0-9a-f]{64}", expected):
            errors.append(f"invalid checksum digest on line {number}")
            continue
        relative = Path(rel)
        if (not rel or relative.is_absolute() or relative.as_posix() != rel
                or any(part in {".", ".."} for part in rel.split("/"))
                or "\\" in rel or any(ord(char) < 32 for char in rel)
                or rel == "INSTALL_SHA256SUMS.txt"):
            errors.append(f"unsafe checksum path on line {number}")
            continue
        if rel in declared:
            errors.append(f"duplicate checksum path: {rel}")
            continue
        declared.add(rel)
        path = repo_root / rel
        if rel not in installed_files:
            errors.append(f"missing or unsafe installed file: {rel}")
        else:
            try:
                if _sha256(path) != expected:
                    errors.append(f"installed file hash mismatch: {rel}")
            except OSError:
                errors.append(f"cannot hash installed file: {rel}")
    if not declared:
        errors.append("empty installed checksum manifest")
    for rel in sorted(installed_files - declared):
        errors.append(f"installed file absent from checksum manifest: {rel}")
    if not (installed_files - {"INSTALL_PROVENANCE.json"}):
        errors.append("installed snapshot has no payload files")
    commit = provenance.get("source_commit_sha")
    commit_resolved = isinstance(commit, str) and re.fullmatch(r"[0-9a-f]{40}", commit) is not None
    if not commit_resolved:
        errors.append("source commit must be a full lowercase 40-hex Git SHA")
    if provenance.get("source_worktree_clean") is not True:
        errors.append("source worktree was not recorded as clean")
    return {
        "commit_sha": commit,
        "commit_resolved": commit_resolved,
        "working_tree_clean": not errors,
        "provenance_mode": "installed_snapshot",
        "snapshot_integrity_pass": not errors,
        "snapshot_errors": errors,
        "installed_at_utc": provenance.get("installed_at_utc"),
        "collection_enabled_by_provisioner": provenance.get("collection_enabled_by_provisioner"),
    }


def provenance_state(repo_root: Path) -> dict[str, Any]:
    # An installed seal is authoritative even if a parent directory has .git.
    # A damaged seal must not fall back to an unrelated clean checkout.
    snapshot = installed_snapshot_state(repo_root)
    if snapshot is not None:
        return snapshot
    code, sha = _run(["git", "-C", str(repo_root), "rev-parse", "HEAD"])
    status_code, status = _run(["git", "-C", str(repo_root), "status", "--porcelain"])
    if code == 0:
        return {
            "commit_sha": sha,
            "commit_resolved": True,
            "working_tree_clean": status_code == 0 and status == "",
            "provenance_mode": "git_checkout",
        }
    return {
        "commit_sha": None,
        "commit_resolved": False,
        "working_tree_clean": False,
        "provenance_mode": "unresolved",
    }


def ntp_state() -> dict[str, Any]:
    code, synchronized = _run(["timedatectl", "show", "-p", "NTPSynchronized", "--value"])
    if code == 0:
        value = synchronized.lower() == "yes"
        return {"check_available": True, "ntp_synchronized": value, "raw": synchronized}
    return {"check_available": False, "ntp_synchronized": None, "raw": None}


def credential_presence(env_names: list[str]) -> dict[str, bool]:
    return {name: bool(os.environ.get(name)) for name in sorted(set(env_names))}


def paired_credential_envs(provider_freeze: Path) -> list[str]:
    data = json.loads(provider_freeze.read_text(encoding="utf-8"))
    envs: list[str] = []
    for cfg in (data.get("paired_api") or {}).values():
        if not isinstance(cfg, dict) or cfg.get("status") != "eligible":
            continue
        profile = cfg.get("request_profile") or {}
        env_name = profile.get("api_key_env")
        if not isinstance(env_name, str) or not env_name:
            raise ValueError("eligible paired provider is missing request_profile.api_key_env")
        envs.append(env_name)
    return sorted(set(envs))


# Backward-compatible public helper used by existing tests and callers.
def eligible_credential_envs(provider_freeze: Path) -> list[str]:
    return paired_credential_envs(provider_freeze)


def shadow_credential_envs(shadow_freeze: Path) -> list[str]:
    data = json.loads(shadow_freeze.read_text(encoding="utf-8"))
    envs: list[str] = []
    for cfg in (data.get("shadow_api") or {}).values():
        if not isinstance(cfg, dict) or cfg.get("status") != "eligible":
            continue
        profile = cfg.get("request_profile") or {}
        env_name = profile.get("api_key_env")
        if not isinstance(env_name, str) or not env_name:
            raise ValueError("eligible API Shadow provider is missing request_profile.api_key_env")
        envs.append(env_name)
    return sorted(set(envs))


def build_report(*, repo_root: Path, data_root: Path, credential_envs: list[str]) -> dict[str, Any]:
    usage = shutil.disk_usage(data_root if data_root.exists() else data_root.parent)
    provenance = provenance_state(repo_root)
    ntp = ntp_state()
    creds = credential_presence(credential_envs)
    report = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "platform": platform.platform(),
        "python_version": sys.version.split()[0],
        "repo_root": str(repo_root.resolve()),
        "data_root": str(data_root.resolve()),
        "provenance": provenance,
        "clock": ntp,
        "disk": {
            "free_bytes": usage.free,
            "free_gib": round(usage.free / (1024 ** 3), 3),
        },
        "required_credential_envs": sorted(set(credential_envs)),
        "credentials_present": creds,
        "credentials_values_recorded": False,
    }
    report["pass"] = bool(
        provenance["commit_resolved"]
        and provenance["working_tree_clean"]
        and usage.free >= 1024 ** 3
        and (ntp["ntp_synchronized"] is not False)
        and all(creds.values())
    )
    report["manual_clock_verification_required"] = not ntp["check_available"]
    return report


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument("--data-root", type=Path, required=True)
    p.add_argument("--provider-freeze", type=Path)
    p.add_argument("--shadow-freeze", type=Path)
    p.add_argument("--credential-env", action="append", default=[])
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    args.data_root.mkdir(parents=True, exist_ok=True)
    envs = list(args.credential_env)
    if args.provider_freeze:
        envs.extend(paired_credential_envs(args.provider_freeze))
    if args.shadow_freeze:
        envs.extend(shadow_credential_envs(args.shadow_freeze))
    report = build_report(
        repo_root=args.repo_root,
        data_root=args.data_root,
        credential_envs=envs,
    )
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("x", encoding="utf-8") as fh:
            fh.write(text)
    print(text, end="")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
