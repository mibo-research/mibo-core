"""Read immutable local Git source bytes. No network, credentials or runtime activation."""
from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath
import re
import subprocess


def git(root: Path, *arguments: str) -> bytes:
    return subprocess.check_output(["git", "--no-pager", *arguments], cwd=root)


def safe_relative(name: str) -> None:
    path = PurePosixPath(name)
    if (not name or "\\" in name or "\n" in name or "\r" in name or "\0" in name
            or path.is_absolute() or path.as_posix() != name
            or re.match(r"^[A-Za-z]:", name) or any(p in {"", ".", ".."} for p in path.parts)
            or path.name.startswith(".env") or path.suffix.lower() in {".pem", ".ppk", ".key"}
            or any(p.lower() in {"private", "credentials", "api_raw"} for p in path.parts)):
        raise ValueError("unsafe or private Git source path")


def clean_commit(root: Path, commit: str) -> dict:
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("reviewed source pin must be an explicit full 40-hex commit")
    if git(root, "rev-parse", "HEAD").decode().strip() != commit:
        raise ValueError("reviewed source pin must equal the current HEAD")
    if git(root, "status", "--porcelain=v1", "--untracked-files=all", "--ignore-submodules=none"):
        raise ValueError("reviewed source pin requires a clean index and working tree")
    parents = git(root, "show", "-s", "--format=%P", commit).decode().strip().split()
    tree = git(root, "rev-parse", commit + "^{tree}").decode().strip()
    if not re.fullmatch(r"[0-9a-f]{40}", tree):
        raise ValueError("source tree identity unresolved")
    return {"reviewed_candidate_commit": commit, "source_tree_sha1": tree,
        "parent_commit": parents[0] if len(parents) == 1 else None,
        "parent_commits": parents, "source_worktree_git_clean": True}


def tree_files(root: Path, tree: str) -> dict[str, bytes]:
    if not re.fullmatch(r"[0-9a-f]{40}", tree):
        raise ValueError("source tree requires a full object identifier")
    entries = {}
    for record in git(root, "ls-tree", "-rz", "--full-tree", tree).split(b"\0"):
        if not record:
            continue
        header, raw_name = record.split(b"\t", 1)
        mode, kind, oid = header.decode("ascii").split()
        name = raw_name.decode("utf-8")
        safe_relative(name)
        if mode not in {"100644", "100755"} or kind != "blob" or name in entries:
            raise ValueError("source tree contains a link, submodule or duplicate path")
        entries[name] = oid
    if not entries:
        raise ValueError("empty source tree")
    # cat-file reads raw object bytes: checkout/export filters cannot transform
    # EOLs, omit a member or expand a placeholder in a pinned source snapshot.
    result = subprocess.run(["git", "cat-file", "--batch"], cwd=root,
        input=("".join(oid + "\n" for oid in entries.values())).encode("ascii"),
        stdout=subprocess.PIPE, check=True).stdout
    files, offset = {}, 0
    for name, oid in entries.items():
        end = result.find(b"\n", offset)
        header = result[offset:end].decode("ascii") if end >= offset else ""
        match = re.fullmatch(r"([0-9a-f]{40}) blob ([0-9]+)", header)
        if match is None or match[1] != oid:
            raise ValueError("Git source blob header/identity mismatch")
        size = int(match[2])
        start = end + 1
        payload = result[start:start + size]
        if len(payload) != size or result[start + size:start + size + 1] != b"\n":
            raise ValueError("Git source blob length mismatch")
        git_oid = hashlib.sha1(b"blob " + str(size).encode() + b"\0" + payload).hexdigest()
        if git_oid != oid:
            raise ValueError("Git source blob digest mismatch")
        files[name] = payload
        offset = start + size + 1
    if offset != len(result):
        raise ValueError("Unexpected trailing Git blob data")
    return files


def committed_snapshot(root: Path, commit: str) -> tuple[dict, dict[str, bytes]]:
    identity = clean_commit(root, commit)
    files = tree_files(root, identity["source_tree_sha1"])
    if clean_commit(root, commit) != identity:
        raise ValueError("source commit changed during immutable snapshot")
    return identity, files


def staged_snapshot(root: Path) -> tuple[dict, dict[str, bytes]]:
    if git(root, "diff", "--name-only", "--") or git(root, "ls-files", "--others", "--exclude-standard", "-z"):
        raise ValueError("stage only the reviewed candidate and leave no unstaged or untracked files")
    head = git(root, "rev-parse", "HEAD").decode().strip()
    tree = git(root, "write-tree").decode().strip()
    files = tree_files(root, tree)
    if (git(root, "write-tree").decode().strip() != tree
            or git(root, "rev-parse", "HEAD").decode().strip() != head):
        raise ValueError("index or HEAD changed during staged snapshot")
    return {"source_parent_commit": head, "source_tree_sha1": tree,
        "source_mode": "git_index_blobs"}, files


def write_snapshot(destination: Path, files: dict[str, bytes]) -> None:
    if any(destination.iterdir()):
        raise ValueError("source snapshot destination must be empty")
    for name, payload in sorted(files.items()):
        safe_relative(name)
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as handle:
            handle.write(payload)
