#!/usr/bin/env python3
"""Seal a clean installed runtime tree with commit and file-hash provenance."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re


def seal(root: Path, source_commit: str) -> dict[str, object]:
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"runtime root is not a directory: {root}")
    if not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise ValueError("source commit must be a full lowercase 40-hex Git SHA")
    provenance_path = root / "INSTALL_PROVENANCE.json"
    sums_path = root / "INSTALL_SHA256SUMS.txt"
    if provenance_path.exists() or sums_path.exists():
        raise FileExistsError("installed snapshot is already sealed")
    provenance = {
        "schema_version": "2.0",
        "source_commit_sha": source_commit,
        "installed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_worktree_clean": True,
        "collection_enabled_by_provisioner": False,
        "installed_services": [
            "mibo-paired.service", "mibo-shadow.service", "mibo-core-v2.service",
        ],
    }
    with provenance_path.open("x", encoding="utf-8") as fh:
        json.dump(provenance, fh, indent=2, sort_keys=True)
        fh.write("\n")
    entries: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path == sums_path:
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        entries.append(f"{digest}  {path.relative_to(root).as_posix()}")
    with sums_path.open("x", encoding="utf-8") as fh:
        fh.write("\n".join(entries) + "\n")
    return {
        **provenance,
        "hashed_file_count": len(entries),
        "sha256s_sha256": hashlib.sha256(sums_path.read_bytes()).hexdigest(),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", required=True, type=Path)
    p.add_argument("--source-commit", required=True)
    args = p.parse_args()
    print(json.dumps(seal(args.root, args.source_commit), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
