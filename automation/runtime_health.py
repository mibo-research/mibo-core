#!/usr/bin/env python3
"""Runtime health and provenance checks for the controlled MIBO Japan site.

The report never prints credential values. It is intended to be stored in the
private Pre-Wave execution record before W01.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from typing import Any


def _run(args: list[str]) -> tuple[int, str]:
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=10, check=False)
        return p.returncode, p.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return 127, ""


def git_state(repo_root: Path) -> dict[str, Any]:
    code, sha = _run(["git", "-C", str(repo_root), "rev-parse", "HEAD"])
    status_code, status = _run(["git", "-C", str(repo_root), "status", "--porcelain"])
    return {
        "commit_sha": sha if code == 0 else None,
        "commit_resolved": code == 0,
        "working_tree_clean": status_code == 0 and status == "",
    }


def ntp_state() -> dict[str, Any]:
    code, synchronized = _run(["timedatectl", "show", "-p", "NTPSynchronized", "--value"])
    if code == 0:
        value = synchronized.lower() == "yes"
        return {"check_available": True, "ntp_synchronized": value, "raw": synchronized}
    return {"check_available": False, "ntp_synchronized": None, "raw": None}


def credential_presence(env_names: list[str]) -> dict[str, bool]:
    return {name: bool(os.environ.get(name)) for name in env_names}


def build_report(*, repo_root: Path, data_root: Path, credential_envs: list[str]) -> dict[str, Any]:
    usage = shutil.disk_usage(data_root if data_root.exists() else data_root.parent)
    git = git_state(repo_root)
    ntp = ntp_state()
    creds = credential_presence(credential_envs)
    report = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "platform": platform.platform(),
        "python_version": sys.version.split()[0],
        "repo_root": str(repo_root.resolve()),
        "data_root": str(data_root.resolve()),
        "git": git,
        "clock": ntp,
        "disk": {
            "free_bytes": usage.free,
            "free_gib": round(usage.free / (1024 ** 3), 3),
        },
        "credentials_present": creds,
        "credentials_values_recorded": False,
    }
    report["pass"] = bool(
        git["commit_resolved"]
        and git["working_tree_clean"]
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
    p.add_argument("--credential-env", action="append", default=[])
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    args.data_root.mkdir(parents=True, exist_ok=True)
    report = build_report(
        repo_root=args.repo_root,
        data_root=args.data_root,
        credential_envs=args.credential_env,
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
