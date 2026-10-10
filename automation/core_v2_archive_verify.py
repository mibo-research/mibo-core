#!/usr/bin/env python3
"""Read-only verification of a sealed Core archive against a trusted receipt.

The receipt SHA-256 must be retained independently of the archive. A digest read
from the same untrusted export does not establish independent authenticity.
Raw observations are streamed as bytes; this tool never parses or displays them.
It performs no extraction, writes, provider calls, or backup existence checks.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import sys
import tarfile
import unicodedata


MAX_RECEIPT_BYTES = 1024 * 1024
MAX_MANIFEST_BYTES = 8 * 1024 * 1024
MAX_MEMBERS = 200_000
MAX_COMPONENTS = 64
MAX_EXTENSION_BYTES = 64 * 1024
CHUNK_BYTES = 1024 * 1024
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
VERSION_RE = re.compile(r"v[0-9]+(?:\.[0-9]+)+\Z")


class ArchiveVerificationError(ValueError):
    """A generic, disclosure-safe verification failure."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ArchiveVerificationError(message)


def _digest(value: object) -> str:
    _require(isinstance(value, str) and SHA256_RE.fullmatch(value) is not None,
             "Invalid SHA-256 digest")
    return value


def _canonical_name(name: str, *, directory: bool = False) -> str:
    _require(isinstance(name, str) and 0 < len(name) <= 4096,
             "Invalid archive path")
    if directory and name.endswith("/"):
        name = name[:-1]
    _require(bool(name) and not name.startswith("/") and "\\" not in name
             and not any(unicodedata.category(c).startswith("C") for c in name),
             "Unsafe archive path")
    parts = name.split("/")
    _require(len(parts) <= MAX_COMPONENTS and
             all(p not in {"", ".", ".."} and len(p) <= 255 for p in parts),
             "Noncanonical archive path")
    return name


def _signature(info: os.stat_result) -> tuple:
    return (info.st_dev, info.st_ino, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


def _open_directory(path: Path) -> int:
    """Open each ancestor without following symlinks, including the root."""
    parts = Path(os.path.abspath(path)).parts
    fd = os.open(parts[0], os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts[1:]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=fd)
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


@contextmanager
def _regular_file(path: Path):
    parent = _open_directory(path.parent)
    fd = None
    try:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                     dir_fd=parent)
        _require(stat.S_ISREG(os.fstat(fd).st_mode),
                 "Verification input is not a regular file")
        with os.fdopen(fd, "rb") as stream:
            fd = None
            yield stream
    finally:
        if fd is not None:
            os.close(fd)
        os.close(parent)


def _hash(stream) -> str:
    hasher = hashlib.sha256()
    while True:
        chunk = stream.read(CHUNK_BYTES)
        if not chunk:
            break
        hasher.update(chunk)
    return hasher.hexdigest()


def _json_pairs(pairs: list) -> dict:
    result = {}
    for key, value in pairs:
        _require(key not in result, "Duplicate receipt JSON key")
        result[key] = value
    return result


def _read_receipt(path: Path, expected_digest: str, wave: str) -> tuple[dict, str]:
    with _regular_file(path) as stream:
        before = _signature(os.fstat(stream.fileno()))
        data = stream.read(MAX_RECEIPT_BYTES + 1)
        _require(len(data) <= MAX_RECEIPT_BYTES, "Receipt exceeds size limit")
        digest = hashlib.sha256(data).hexdigest()
        _require(digest == expected_digest, "Receipt hash mismatch")
        _require(before == _signature(os.fstat(stream.fileno())),
                 "Receipt changed during verification")
    try:
        receipt = json.loads(data.decode("utf-8"), object_pairs_hook=_json_pairs)
    except ArchiveVerificationError:
        raise
    except (UnicodeError, ValueError, RecursionError):
        raise ArchiveVerificationError("Invalid receipt JSON") from None
    _require(isinstance(receipt, dict) and receipt.get("wave_id") == wave,
             "Receipt wave mismatch")
    _digest(receipt.get("archive_sha256"))
    manifests = receipt.get("wave_manifest_sha256")
    _require(isinstance(manifests, dict) and 0 < len(manifests) <= 32,
             "Receipt has no declared wave manifests")
    for version, manifest_digest in manifests.items():
        _require(isinstance(version, str) and VERSION_RE.fullmatch(version) is not None,
                 "Invalid declared namespace")
        _digest(manifest_digest)
    return receipt, digest


def _manifest_entries(data: bytes) -> dict[str, str]:
    try:
        text = data.decode("utf-8")
    except UnicodeError:
        raise ArchiveVerificationError("Invalid manifest encoding") from None
    _require(bool(text) and text.endswith("\n"), "Empty or incomplete wave manifest")
    entries = {}
    for line in text[:-1].split("\n"):
        _require(len(entries) < MAX_MEMBERS and len(line) >= 67 and line[64:66] == "  ",
                 "Invalid wave manifest record")
        digest = _digest(line[:64])
        name = _canonical_name(line[66:])
        _require(name != "SHA256SUMS.txt" and name not in entries,
                 "Duplicate or self-referential manifest record")
        entries[name] = digest
    _require(bool(entries), "Empty wave manifest")
    return entries


def _ancestors(names: set[str]) -> set[str]:
    result = set()
    for name in names:
        parts = name.split("/")
        result.update("/".join(parts[:i]) for i in range(1, len(parts)))
    return result


def _pax_records(data: bytes) -> dict[str, str]:
    """Parse bounded local PAX records without accepting hidden extensions."""
    records = {}
    position = 0
    allowed = {"path", "size", "mtime", "atime", "ctime", "uid", "gid", "uname", "gname"}
    while position < len(data):
        space = data.find(b" ", position, position + 9)
        _require(space > position and data[position:space].isdigit(), "Invalid local PAX record")
        length = int(data[position:space])
        end = position + length
        _require(end <= len(data) and end > space + 3 and data[end - 1:end] == b"\n",
                 "Invalid local PAX record")
        pair = data[space + 1:end - 1].split(b"=", 1)
        _require(len(pair) == 2, "Invalid local PAX record")
        try:
            key, value = (part.decode("utf-8") for part in pair)
        except UnicodeError:
            raise ArchiveVerificationError("Invalid local PAX encoding") from None
        _require(key in allowed and key not in records, "Unsupported or duplicate local PAX key")
        if key == "path":
            _canonical_name(value, directory=True)
        elif key in {"size", "uid", "gid"}:
            _require(bool(re.fullmatch(r"[0-9]{1,20}", value)) and int(value) < 2 ** 63,
                     "Invalid local PAX numeric value")
        elif key in {"mtime", "atime", "ctime"}:
            try:
                _require(0 < len(value) <= 64 and math.isfinite(float(value)),
                         "Invalid local PAX timestamp")
            except ValueError:
                raise ArchiveVerificationError("Invalid local PAX timestamp") from None
        else:
            _require(len(value) <= 255 and
                     not any(unicodedata.category(c).startswith("C") for c in value),
                     "Invalid local PAX owner name")
        records[key] = value
        position = end
    return records


def _physical_tar_preflight(stream) -> None:
    """Bound/check extension headers before tarfile can consume hidden bodies."""
    magic = stream.read(6)
    stream.seek(0)
    _require(not magic.startswith((b"BZh", b"\xfd7zXZ\x00")),
             "Unsupported archive compression")
    compressed = magic.startswith(b"\x1f\x8b")
    source = gzip.GzipFile(fileobj=stream, mode="rb") if compressed else stream
    headers, pending_pax = 0, None
    try:
        while True:
            header = source.read(512)
            _require(len(header) == 512, "Archive has an incomplete tar header")
            if header == b"\0" * 512:
                _require(pending_pax is None, "Orphan local PAX header")
                padding_bytes = 512
                while True:
                    padding = source.read(CHUNK_BYTES)
                    if not padding:
                        break
                    _require(not padding.strip(b"\0"), "Archive contains trailing nonzero data")
                    padding_bytes += len(padding)
                _require(padding_bytes >= 1024 and padding_bytes % 512 == 0,
                         "Archive has an incomplete tar terminator")
                break
            headers += 1
            _require(headers <= 2 * MAX_MEMBERS, "Archive exceeds physical header limit")
            info = tarfile.TarInfo.frombuf(header, "utf-8", "surrogateescape")
            _require(info.type in {tarfile.REGTYPE, tarfile.AREGTYPE, tarfile.DIRTYPE, tarfile.XHDTYPE},
                     "Archive contains an unsupported extension or special file")
            # This exact synthetic name is generated by Python's default PAX
            # writer. All other physical header names must be canonical too.
            if not (info.type == tarfile.XHDTYPE and info.name == "././@PaxHeader"):
                _canonical_name(info.name, directory=info.type == tarfile.DIRTYPE)
            size = info.size
            _require(size >= 0, "Invalid physical tar size")
            if info.type == tarfile.XHDTYPE:
                _require(pending_pax is None and size <= MAX_EXTENSION_BYTES,
                         "Local PAX header exceeds limit or is repeated")
                payload = source.read(size)
                _require(len(payload) == size, "Incomplete local PAX header")
                pending_pax = _pax_records(payload)
            else:
                if pending_pax is not None:
                    size = int(pending_pax.get("size", size))
                    pending_pax = None
                if info.type == tarfile.DIRTYPE:
                    _require(size == 0, "Directory contains unexpected data")
                remaining = size
                while remaining:
                    data = source.read(min(CHUNK_BYTES, remaining))
                    _require(bool(data), "Incomplete physical tar member")
                    remaining -= len(data)
            padding_size = (-size) % 512
            padding = source.read(padding_size)
            _require(len(padding) == padding_size and not padding.strip(b"\0"),
                     "Invalid physical tar member padding")
    finally:
        if compressed:
            source.close()
        stream.seek(0)


def _tar_contents(stream, prefixes: dict[str, str]) -> tuple[dict, dict]:
    _physical_tar_preflight(stream)
    files, directories, manifests, seen = {}, set(), {}, set()
    allowed_top = set(prefixes) | _ancestors(set(prefixes))
    with tarfile.open(fileobj=stream, mode="r:*") as archive:
        for member in archive:
            _require(len(seen) < MAX_MEMBERS, "Archive exceeds member limit")
            _require(member.type in {tarfile.REGTYPE, tarfile.AREGTYPE, tarfile.DIRTYPE}
                     and member.sparse is None and
                     not any(k.startswith("GNU.sparse") for k in member.pax_headers),
                     "Archive contains a link, sparse entry, or special file")
            is_directory = member.type == tarfile.DIRTYPE
            name = _canonical_name(member.name, directory=is_directory)
            _require(name not in seen, "Duplicate archive member")
            seen.add(name)
            under_wave = any(name.startswith(prefix + "/") for prefix in prefixes)
            _require(under_wave or (is_directory and name in allowed_top),
                     "Archive contains an undeclared namespace or wave")
            if is_directory:
                _require(member.size == 0, "Directory contains unexpected data")
                directories.add(name)
                continue
            _require(member.size >= 0, "Invalid archive member size")
            extracted = archive.extractfile(member)
            _require(extracted is not None, "Archive member is unreadable")
            with extracted:
                if name in {prefix + "/SHA256SUMS.txt" for prefix in prefixes}:
                    _require(member.size <= MAX_MANIFEST_BYTES,
                             "Wave manifest exceeds size limit")
                    data = extracted.read(MAX_MANIFEST_BYTES + 1)
                    _require(len(data) == member.size, "Incomplete wave manifest")
                    digest = hashlib.sha256(data).hexdigest()
                    manifests[name] = data
                else:
                    digest = _hash(extracted)
            files[name] = digest
        # tarfile stops at the first zero block and otherwise ignores appended
        # members. Only a complete zero-block terminator/padding is permitted.
        # This also detects a concatenated gzip stream containing another tar.
        archive.fileobj.seek(archive.offset)
        padding_bytes = 0
        while True:
            padding = archive.fileobj.read(CHUNK_BYTES)
            if not padding:
                break
            _require(not padding.strip(b"\0"), "Archive contains trailing nonzero data")
            padding_bytes += len(padding)
        _require(padding_bytes >= 1024 and padding_bytes % 512 == 0,
                 "Archive has an incomplete tar terminator")
    expected = {}
    for prefix, manifest_digest in prefixes.items():
        manifest_path = prefix + "/SHA256SUMS.txt"
        _require(manifest_path in manifests, "Missing wave manifest")
        _require(files[manifest_path] == manifest_digest, "Wave manifest hash mismatch")
        expected[manifest_path] = manifest_digest
        for name, digest in _manifest_entries(manifests[manifest_path]).items():
            expected[prefix + "/" + name] = digest
    _require(set(files) == set(expected), "Archive file coverage mismatch")
    _require(all(files[name] == digest for name, digest in expected.items()),
             "Archive file hash mismatch")
    allowed_directories = _ancestors(set(expected))
    _require(directories <= allowed_directories and not (set(files) & allowed_directories),
             "Archive directory coverage or file hierarchy mismatch")
    return expected, {prefix.split("/")[0]: sum(
        name.startswith(prefix + "/") for name in expected) for prefix in prefixes}


def _verify_restored(root: Path, expected: dict[str, str]) -> None:
    """Compare bytes/coverage only on a filesystem verified as read-only."""
    root_fd = _open_directory(root)
    allowed_directories = _ancestors(set(expected))
    def walk(directory_fd, relative, baseline=None):
        signatures, seen_files = {}, set()
        before = _signature(os.fstat(directory_fd))
        if baseline is not None:
            _require(baseline.get(relative) == before, "Restored directory changed")
        signatures[relative] = before
        for child in sorted(os.listdir(directory_fd)):
            name = _canonical_name(relative + "/" + child if relative else child)
            info = os.stat(child, dir_fd=directory_fd, follow_symlinks=False)
            signature = _signature(info)
            if baseline is not None:
                _require(baseline.get(name) == signature, "Restored tree changed")
            signatures[name] = signature
            if stat.S_ISDIR(info.st_mode):
                _require(name in allowed_directories, "Restored directory coverage mismatch")
                fd = os.open(child, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                             dir_fd=directory_fd)
                try:
                    _require(signature == _signature(os.fstat(fd)), "Restored directory changed")
                    descendants, files = walk(fd, name, baseline)
                    signatures.update(descendants)
                    seen_files.update(files)
                finally:
                    os.close(fd)
            else:
                _require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
                         "Restored tree contains a link or special file")
                _require(name in expected, "Restored file coverage mismatch")
                fd = os.open(child, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                             dir_fd=directory_fd)
                with os.fdopen(fd, "rb") as stream:
                    _require(signature == _signature(os.fstat(stream.fileno())), "Restored file changed")
                    if baseline is None:
                        _require(_hash(stream) == expected[name], "Restored file hash mismatch")
                    _require(signature == _signature(os.fstat(stream.fileno())), "Restored file changed")
                seen_files.add(name)
        # Hold each ancestor until all descendants are checked, so an extra
        # entry added to the root during child traversal cannot evade coverage.
        _require(before == _signature(os.fstat(directory_fd)), "Restored directory changed")
        return signatures, seen_files
    try:
        _require(bool(os.fstatvfs(root_fd).f_flag & os.ST_RDONLY),
                 "Restored tree must be on a read-only filesystem")
        baseline, seen = walk(root_fd, "")
        _require(seen == set(expected), "Restored file coverage mismatch")
        final, seen = walk(root_fd, "", baseline)
        _require(final == baseline and seen == set(expected), "Restored tree changed")
    finally:
        os.close(root_fd)


def verify_tar_content(archive: Path, expected_files: dict[str, str]) -> None:
    """Verify an export against a caller's trusted complete file/hash mapping.

    This is intended for validating a staged closure export before writing or
    sealing the original wave. Unlike ``verify_archive``, it does not establish
    a receipt binding. All keys include the namespace/site/wave prefix, and the
    mapping must include the wave-level SHA256SUMS.txt files themselves.
    """
    try:
        _require(isinstance(expected_files, dict) and 0 < len(expected_files) <= MAX_MEMBERS,
                 "Invalid expected archive file mapping")
        prefixes = {}
        for name, digest in expected_files.items():
            _canonical_name(name)
            _digest(digest)
            parts = name.split("/")
            _require(len(parts) >= 4 and VERSION_RE.fullmatch(parts[0]) is not None,
                     "Invalid expected archive namespace")
            if len(parts) == 4 and parts[3] == "SHA256SUMS.txt":
                prefixes["/".join(parts[:3])] = digest
        _require(bool(prefixes), "Expected mapping has no wave manifests")
        with _regular_file(Path(archive)) as stream:
            before = _signature(os.fstat(stream.fileno()))
            actual, _ = _tar_contents(stream, prefixes)
            _require(actual == expected_files, "Staged archive file mapping mismatch")
            _require(before == _signature(os.fstat(stream.fileno())),
                     "Archive changed during verification")
    except ArchiveVerificationError:
        raise
    except (OSError, EOFError, tarfile.TarError, UnicodeError, RecursionError):
        raise ArchiveVerificationError("Staged archive could not be verified") from None


def verify_archive(*, archive: Path, receipt: Path, expected_receipt_sha256: str,
                   wave: str, site: str, restored_data_root: Path | None = None) -> dict:
    """Validate a complete export; raise ArchiveVerificationError on any failure.

    ``restored_data_root`` must be a dedicated restoration root containing only
    the archive's namespace/site/wave trees. Its files are opened read-only.
    The restored tree must be on a read-only filesystem; writable mounts fail
    closed. Use an isolated read-only snapshot with no active writers. This
    verifies the mount and observed bytes, not underlying block immutability
    or the independent existence of a cloud snapshot.
    No file is extracted, created, rewritten, signed, or chmodded by this tool.
    """
    try:
        _require(_canonical_name(wave) == wave and "/" not in wave,
                 "Invalid requested wave")
        _require(_canonical_name(site) == site and "/" not in site,
                 "Invalid requested site")
        trusted_digest = _digest(expected_receipt_sha256)
        record, receipt_digest = _read_receipt(Path(receipt), trusted_digest, wave)
        prefixes = {version + "/" + site + "/" + wave: digest
                    for version, digest in record["wave_manifest_sha256"].items()}
        with _regular_file(Path(archive)) as stream:
            before = _signature(os.fstat(stream.fileno()))
            archive_digest = _hash(stream)
            _require(archive_digest == record["archive_sha256"], "Archive hash mismatch")
            stream.seek(0)
            expected, counts = _tar_contents(stream, prefixes)
            _require(before == _signature(os.fstat(stream.fileno())),
                     "Archive changed during verification")
        if restored_data_root is not None:
            _verify_restored(Path(restored_data_root), expected)
        return {
            "status": "PASS", "wave_id": wave, "site_id": site,
            "receipt_sha256": receipt_digest, "archive_sha256": archive_digest,
            "wave_manifest_sha256": record["wave_manifest_sha256"],
            "file_count": len(expected), "namespace_file_counts": counts,
            "restoration_check": "PASS" if restored_data_root is not None else "NOT_REQUESTED",
            "restoration_filesystem_read_only": True if restored_data_root is not None else None,
            "restoration_atomic_snapshot_verified": False,
            "independent_backup_assessed": False,
        }
    except ArchiveVerificationError:
        raise
    except (OSError, EOFError, tarfile.TarError, UnicodeError, RecursionError):
        raise ArchiveVerificationError("Archive or restored tree could not be verified") from None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--expected-receipt-sha256", required=True,
                        help="Receipt SHA-256 retained independently of this export")
    parser.add_argument("--wave", required=True)
    parser.add_argument("--site", required=True)
    parser.add_argument("--restored-data-root", type=Path,
                        help="Dedicated restored tree on a required read-only filesystem. "
                             "Use an isolated snapshot with no writers. "
                             "Comparison only, not atomic snapshot proof; never extraction")
    args = parser.parse_args(argv)
    try:
        summary = verify_archive(archive=args.archive, receipt=args.receipt,
                                 expected_receipt_sha256=args.expected_receipt_sha256,
                                 wave=args.wave, site=args.site,
                                 restored_data_root=args.restored_data_root)
    except ArchiveVerificationError as exc:
        print(json.dumps({"status": "FAIL", "reason": str(exc),
                          "independent_backup_assessed": False}), file=sys.stderr)
        return 1
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
