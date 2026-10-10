"""Synthetic, offline archive/restore verification security regressions."""
import hashlib
import gzip
import io
import json
import os
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import core_v2_archive_verify as verify


PRIVATE = b"SYNTHETIC_PRIVATE_ANSWER_DO_NOT_PRINT\x00\xff"


def sha(data):
    return hashlib.sha256(data).hexdigest()


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.archive = self.base / "sealed.tar.gz"
        self.receipt = self.base / "CLOSE_RECEIPT.json"
        self.wave = "MIBO2-W01"
        self.site = "JP01"
        self.files = {}
        self.manifests = {}
        for version in ("v2.0.2", "v2.0.4"):
            prefix = "/".join((version, self.site, self.wave))
            contents = {
                "api_raw/SYNTHETIC.json": PRIVATE,
                "metadata/SYNTHETIC.json": b'{"synthetic":true}',
                "closure/COMPLETION_RECORD.json": b'{"status":"synthetic"}',
            }
            manifest = "".join(sha(data) + "  " + name + "\n"
                               for name, data in sorted(contents.items())).encode()
            self.manifests[version] = sha(manifest)
            contents["SHA256SUMS.txt"] = manifest
            self.files.update({prefix + "/" + name: data for name, data in contents.items()})
        self.members = [(name, tarfile.REGTYPE, data, "")
                        for name, data in self.files.items()]
        self.write_archive()
        # Synthetic temporary fixtures use a writable local filesystem. Mock
        # only its mount flag; the verifier still opens and hashes real bytes.
        readonly_mount = patch.object(verify.os, "fstatvfs",
                                      return_value=SimpleNamespace(f_flag=os.ST_RDONLY))
        readonly_mount.start()
        self.addCleanup(readonly_mount.stop)

    def tearDown(self):
        self.tmp.cleanup()

    def write_archive(self):
        with tarfile.open(self.archive, "w:gz") as archive:
            for name, kind, data, linkname in self.members:
                member = tarfile.TarInfo(name)
                member.type = kind
                member.linkname = linkname
                member.size = len(data)
                archive.addfile(member, io.BytesIO(data) if data else None)
        self.bind_receipt()

    def bind_receipt(self, **updates):
        receipt = {
            "wave_id": self.wave,
            "sealed_at_utc": "2026-10-08T05:33:58Z",
            "archive_verified_at_utc": "2026-10-08T05:34:00Z",
            "archive_sha256": sha(self.archive.read_bytes()),
            "wave_manifest_sha256": self.manifests,
            "backup_scope": "synthetic_local_export_only",
        }
        receipt.update(updates)
        self.receipt.write_bytes(json.dumps(receipt, sort_keys=True).encode())
        self.receipt_digest = sha(self.receipt.read_bytes())

    def check(self, **kwargs):
        return verify.verify_archive(archive=self.archive, receipt=self.receipt,
                                     expected_receipt_sha256=self.receipt_digest,
                                     wave=self.wave, site=self.site, **kwargs)

    def restore(self):
        root = self.base / "restored"
        for name, data in self.files.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        return root

    def test_w01_valid_bound_export(self):
        result = self.check()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["file_count"], 8)
        self.assertEqual(result["namespace_file_counts"], {"v2.0.2": 4, "v2.0.4": 4})
        self.assertEqual(result["restoration_check"], "NOT_REQUESTED")
        self.assertIsNone(result["restoration_filesystem_read_only"])
        self.assertIs(result["restoration_atomic_snapshot_verified"], False)
        self.assertIs(result["independent_backup_assessed"], False)

    def test_w02_valid_without_w01_count_or_version_assumptions(self):
        self.wave = "MIBO2-W02"
        self.members = [(name.replace("MIBO2-W01", self.wave), kind, data, link)
                        for name, kind, data, link in self.members]
        self.write_archive()
        self.assertEqual(self.check()["wave_id"], "MIBO2-W02")

    def test_stage_verification_against_trusted_mapping(self):
        expected = {name: sha(data) for name, data in self.files.items()}
        verify.verify_tar_content(self.archive, expected)
        expected[next(iter(expected))] = "0" * 64
        with self.assertRaisesRegex(verify.ArchiveVerificationError, "mapping mismatch"):
            verify.verify_tar_content(self.archive, expected)

    def test_receipt_digest_is_mandatory_and_checked_before_json(self):
        self.receipt.write_bytes(b"not JSON " + PRIVATE)
        with self.assertRaisesRegex(verify.ArchiveVerificationError, "Receipt hash mismatch"):
            self.check()
        with self.assertRaisesRegex(verify.ArchiveVerificationError, "Invalid SHA"):
            verify.verify_archive(archive=self.archive, receipt=self.receipt,
                                 expected_receipt_sha256="", wave=self.wave, site=self.site)

    def test_receipt_wrong_wave(self):
        self.bind_receipt(wave_id="MIBO2-W02")
        with self.assertRaisesRegex(verify.ArchiveVerificationError, "Receipt wave mismatch"):
            self.check()

    def test_duplicate_receipt_key(self):
        data = self.receipt.read_bytes()
        self.receipt.write_bytes(b'{"wave_id":"MIBO2-W01",' + data[1:])
        self.receipt_digest = sha(self.receipt.read_bytes())
        with self.assertRaisesRegex(verify.ArchiveVerificationError, "Duplicate receipt JSON key"):
            self.check()

    def test_receipt_size_limit(self):
        data = b"x" * (verify.MAX_RECEIPT_BYTES + 1)
        self.receipt.write_bytes(data)
        self.receipt_digest = sha(data)
        with self.assertRaisesRegex(verify.ArchiveVerificationError, "Receipt exceeds"):
            self.check()

    def test_empty_or_invalid_namespace_mapping(self):
        for mapping in ({}, {"../../escape": "0" * 64}, {"v2.0.2": "bad"}):
            with self.subTest(mapping=mapping):
                self.bind_receipt(wave_manifest_sha256=mapping)
                with self.assertRaises(verify.ArchiveVerificationError):
                    self.check()

    def test_archive_hash_mismatch(self):
        with self.archive.open("ab") as stream:
            stream.write(b"modified")
        with self.assertRaisesRegex(verify.ArchiveVerificationError, "Archive hash mismatch"):
            self.check()

    def test_hidden_members_after_zero_terminator_rejected(self):
        valid = self.archive.read_bytes()
        other = io.BytesIO()
        with tarfile.open(fileobj=other, mode="w") as archive:
            member = tarfile.TarInfo("../../HIDDEN")
            member.size = len(PRIVATE)
            archive.addfile(member, io.BytesIO(PRIVATE))
        variants = (gzip.compress(gzip.decompress(valid) + other.getvalue()),
                    valid + gzip.compress(other.getvalue()))
        for data in variants:
            with self.subTest(concatenated_gzip=data.startswith(valid)):
                self.archive.write_bytes(data)
                self.bind_receipt()
                with self.assertRaisesRegex(verify.ArchiveVerificationError, "trailing nonzero"):
                    self.check()

    def test_truncated_zero_terminator_rejected(self):
        plain = gzip.decompress(self.archive.read_bytes())
        with tarfile.open(fileobj=io.BytesIO(plain), mode="r:") as archive:
            list(archive)
            offset = archive.offset
        self.archive.write_bytes(gzip.compress(plain[:offset + 512]))
        self.bind_receipt()
        with self.assertRaisesRegex(verify.ArchiveVerificationError, "incomplete tar terminator"):
            self.check()

    def test_manifest_tampering_even_if_archive_digest_is_rebound(self):
        self.members = [(name, kind, data + b"extra" if name.endswith("SHA256SUMS.txt") else data, link)
                        for name, kind, data, link in self.members]
        self.write_archive()
        with self.assertRaisesRegex(verify.ArchiveVerificationError, "manifest hash mismatch"):
            self.check()

    def test_raw_hash_tampering_even_if_archive_digest_is_rebound(self):
        self.members[0] = (self.members[0][0], tarfile.REGTYPE, b"modified raw", "")
        self.write_archive()
        with self.assertRaisesRegex(verify.ArchiveVerificationError, "file hash mismatch"):
            self.check()

    def test_missing_and_extra_archive_files(self):
        initial = list(self.members)
        for members in (initial[1:], initial + [("v2.0.2/JP01/MIBO2-W01/extra", tarfile.REGTYPE, b"extra", "")]):
            self.members = members
            self.write_archive()
            with self.assertRaisesRegex(verify.ArchiveVerificationError, "file coverage mismatch"):
                self.check()

    def test_missing_wave_manifest(self):
        self.members = [m for m in self.members if not m[0].startswith("v2.0.2/") or
                        not m[0].endswith("SHA256SUMS.txt")]
        self.write_archive()
        with self.assertRaisesRegex(verify.ArchiveVerificationError, "Missing wave manifest"):
            self.check()

    def test_duplicate_files_and_directories(self):
        initial = list(self.members)
        cases = [initial + [initial[0]], initial + [
            ("v2.0.2/JP01/MIBO2-W01/api_raw", tarfile.DIRTYPE, b"", ""),
            ("v2.0.2/JP01/MIBO2-W01/api_raw/", tarfile.DIRTYPE, b"", "")]]
        for members in cases:
            self.members = members
            self.write_archive()
            with self.assertRaisesRegex(verify.ArchiveVerificationError, "Duplicate archive member"):
                self.check()

    def test_valid_explicit_directories(self):
        self.members += [(name, tarfile.DIRTYPE, b"", "") for name in (
            "v2.0.2", "v2.0.2/JP01", "v2.0.2/JP01/MIBO2-W01/",
            "v2.0.2/JP01/MIBO2-W01/api_raw")]
        self.write_archive()
        self.assertEqual(self.check()["status"], "PASS")

    def test_python_default_recursive_filesystem_export(self):
        root = self.restore()
        with tarfile.open(self.archive, "w:gz", dereference=True) as archive:
            for version in self.manifests:
                prefix = "/".join((version, self.site, self.wave))
                archive.add(root / prefix, arcname=prefix)
        self.bind_receipt()
        self.assertEqual(self.check()["status"], "PASS")

    def test_unsafe_member_paths(self):
        initial = list(self.members)
        for name in ("/absolute", "../outside", "v2.0.2/JP01/MIBO2-W01/../escape",
                     "v2.0.2/JP01/MIBO2-W01/./x", "v2.0.2/JP01/MIBO2-W01//x",
                     "v2.0.2/JP01/MIBO2-W01/\\outside", "v2.0.2/JP01/MIBO2-W01/control\nname",
                     "v2.0.2/JP01/MIBO2-W01/control\x1bname", "v2.0.2/JP01/MIBO2-W01/format\u202ename"):
            with self.subTest(name=repr(name)):
                self.members = initial + [(name, tarfile.REGTYPE, PRIVATE, "")]
                self.write_archive()
                with self.assertRaises(verify.ArchiveVerificationError):
                    self.check()

    def test_undeclared_namespace_site_wave_and_directory(self):
        initial = list(self.members)
        for name, kind in (("v2.1.0/JP01/MIBO2-W01/extra", tarfile.REGTYPE),
                           ("v2.0.2/JP02/MIBO2-W01/extra", tarfile.REGTYPE),
                           ("v2.0.2/JP01/MIBO2-W02/extra", tarfile.REGTYPE),
                           ("v9.9.9", tarfile.DIRTYPE),
                           ("v2.0.2/JP01/MIBO2-W01/unused", tarfile.DIRTYPE)):
            self.members = initial + [(name, kind, b"", "")]
            self.write_archive()
            with self.assertRaises(verify.ArchiveVerificationError):
                self.check()

    def test_links_devices_fifo_and_sparse_rejected(self):
        initial = list(self.members)
        for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.CHRTYPE,
                     tarfile.BLKTYPE, tarfile.FIFOTYPE, tarfile.GNUTYPE_SPARSE):
            with self.subTest(kind=kind):
                self.members = initial + [("v2.0.2/JP01/MIBO2-W01/unsafe", kind, b"", "../../outside")]
                self.write_archive()
                with self.assertRaisesRegex(verify.ArchiveVerificationError, "special file"):
                    self.check()

    def test_invalid_duplicate_self_reference_and_escape_manifest_records(self):
        manifest_path = "v2.0.2/JP01/MIBO2-W01/SHA256SUMS.txt"
        initial = list(self.members)
        valid = self.files[manifest_path]
        for content in (b"", b"invalid\n", valid + valid,
                        ("0" * 64 + "  ../outside\n").encode(),
                        ("0" * 64 + "  SHA256SUMS.txt\n").encode()):
            with self.subTest(content=content[:10]):
                self.members = [(name, kind, content if name == manifest_path else data, link)
                                for name, kind, data, link in initial]
                self.manifests["v2.0.2"] = sha(content)
                self.write_archive()
                with self.assertRaises(verify.ArchiveVerificationError):
                    self.check()

    def test_manifest_size_limit(self):
        with patch.object(verify, "MAX_MANIFEST_BYTES", 16):
            with self.assertRaisesRegex(verify.ArchiveVerificationError, "manifest exceeds"):
                self.check()

    def test_member_count_limit(self):
        with patch.object(verify, "MAX_MEMBERS", 1):
            with self.assertRaisesRegex(verify.ArchiveVerificationError, "limit"):
                self.check()

    def test_hidden_global_pax_header_rejected(self):
        plain = gzip.decompress(self.archive.read_bytes())
        value = b"comment=SYNTHETIC_PRIVATE_HIDDEN_METADATA\n"
        length = len(value) + 3
        while length != len(value) + len(str(length)) + 1:
            length = len(value) + len(str(length)) + 1
        payload = str(length).encode() + b" " + value
        header = tarfile.TarInfo("../../HIDDEN_METADATA")
        header.type = tarfile.XGLTYPE
        header.size = len(payload)
        extension = header.tobuf(format=tarfile.USTAR_FORMAT) + payload
        extension += b"\0" * ((-len(payload)) % 512)
        self.archive.write_bytes(gzip.compress(extension + plain))
        self.bind_receipt()
        with self.assertRaisesRegex(verify.ArchiveVerificationError, "unsupported extension"):
            self.check()
        with self.assertRaisesRegex(verify.ArchiveVerificationError, "unsupported extension"):
            verify.verify_tar_content(self.archive, {name: sha(data) for name, data in self.files.items()})

    def test_local_pax_default_mtime_is_supported_but_unknown_keys_rejected(self):
        for headers, succeeds in (({"mtime": "1791437638.160523"}, True),
                                  ({"comment": "SYNTHETIC_PRIVATE_HIDDEN_METADATA"}, False),
                                  ({"GNU.sparse.size": "10"}, False)):
            with tarfile.open(self.archive, "w:gz", format=tarfile.PAX_FORMAT) as archive:
                for name, data in self.files.items():
                    info = tarfile.TarInfo(name)
                    info.size = len(data)
                    info.pax_headers = headers
                    archive.addfile(info, io.BytesIO(data))
            self.bind_receipt()
            if succeeds:
                self.assertEqual(self.check()["status"], "PASS")
            else:
                with self.assertRaisesRegex(verify.ArchiveVerificationError, "PAX key"):
                    self.check()

    def test_oversize_pax_body_rejected_before_tarfile_expansion(self):
        with tarfile.open(self.archive, "w:gz", format=tarfile.PAX_FORMAT) as archive:
            for name, data in self.files.items():
                info = tarfile.TarInfo(name)
                info.size = len(data)
                info.pax_headers = {"comment": "x" * (verify.MAX_EXTENSION_BYTES + 1)}
                archive.addfile(info, io.BytesIO(data))
        self.bind_receipt()
        with self.assertRaisesRegex(verify.ArchiveVerificationError, "Local PAX header exceeds"):
            self.check()

    def test_restored_exact_copy_passes_without_modification(self):
        root = self.restore()
        before = {name: (root / name).stat().st_mtime_ns for name in self.files}
        result = self.check(restored_data_root=root)
        self.assertEqual(result["restoration_check"], "PASS")
        self.assertIs(result["restoration_filesystem_read_only"], True)
        self.assertIs(result["restoration_atomic_snapshot_verified"], False)
        self.assertEqual(before, {name: (root / name).stat().st_mtime_ns for name in self.files})

    def test_restored_hash_mismatch(self):
        root = self.restore()
        (root / next(iter(self.files))).write_bytes(PRIVATE + b"changed")
        with self.assertRaisesRegex(verify.ArchiveVerificationError, "Restored file hash mismatch"):
            self.check(restored_data_root=root)

    def test_writable_restored_filesystem_rejected_even_with_matching_bytes(self):
        root = self.restore()
        with patch.object(verify.os, "fstatvfs", return_value=SimpleNamespace(f_flag=0)):
            with self.assertRaisesRegex(verify.ArchiveVerificationError, "read-only filesystem"):
                self.check(restored_data_root=root)

    def test_root_entry_added_during_descendant_scan_rejected(self):
        root = self.restore()
        native_listdir = os.listdir
        calls = 0
        def mutated_listdir(fd):
            nonlocal calls
            calls += 1
            if calls == 2:
                (root / "UNSCANNED_EXTRA").write_bytes(PRIVATE)
            return native_listdir(fd)
        with patch.object(verify.os, "listdir", side_effect=mutated_listdir):
            with self.assertRaisesRegex(verify.ArchiveVerificationError, "directory changed"):
                self.check(restored_data_root=root)

    def test_previously_hashed_file_modified_during_scan_rejected(self):
        root = self.restore()
        victim = root / sorted(self.files)[0]
        native_hash = verify._hash
        file_calls = 0
        def mutated_hash(stream):
            nonlocal file_calls
            digest = native_hash(stream)
            try:
                in_restore = os.readlink("/proc/self/fd/" + str(stream.fileno())).startswith(str(root) + "/")
            except (OSError, io.UnsupportedOperation, AttributeError):
                in_restore = False
            # Mutate the first restored file during the second file's hash,
            # after its own initial post-hash fstat has already succeeded.
            if in_restore:
                file_calls += 1
                if file_calls == 2:
                    victim.write_bytes(PRIVATE + b"changed-after-read")
            return digest
        with patch.object(verify, "_hash", side_effect=mutated_hash):
            with self.assertRaises(verify.ArchiveVerificationError):
                self.check(restored_data_root=root)

    def test_restored_missing_extra_files_and_directories(self):
        root = self.restore()
        victim = root / next(iter(self.files))
        data = victim.read_bytes()
        victim.unlink()
        with self.assertRaisesRegex(verify.ArchiveVerificationError, "coverage mismatch"):
            self.check(restored_data_root=root)
        victim.write_bytes(data)
        extra = root / "extra"
        extra.write_bytes(PRIVATE)
        with self.assertRaisesRegex(verify.ArchiveVerificationError, "coverage mismatch"):
            self.check(restored_data_root=root)
        extra.unlink()
        extra.mkdir()
        with self.assertRaisesRegex(verify.ArchiveVerificationError, "coverage mismatch"):
            self.check(restored_data_root=root)

    def test_restored_symlink_hardlink_fifo(self):
        root = self.restore()
        victim = root / next(iter(self.files))
        original = victim.read_bytes()
        target = self.base / "outside"
        target.write_bytes(original)
        for kind in ("symlink", "hardlink", "fifo"):
            victim.unlink()
            if kind == "symlink":
                victim.symlink_to(target)
            elif kind == "hardlink":
                os.link(target, victim)
            else:
                os.mkfifo(victim)
            with self.assertRaisesRegex(verify.ArchiveVerificationError, "link or special file"):
                self.check(restored_data_root=root)
            victim.unlink()
            victim.write_bytes(original)

    def test_input_and_restored_ancestor_symlinks_rejected(self):
        linked_archive = self.base / "linked.tar.gz"
        linked_archive.symlink_to(self.archive)
        with self.assertRaises(verify.ArchiveVerificationError):
            verify.verify_archive(archive=linked_archive, receipt=self.receipt,
                                  expected_receipt_sha256=self.receipt_digest, wave=self.wave, site=self.site)
        root = self.restore()
        link = self.base / "linked-tree"
        link.symlink_to(root, target_is_directory=True)
        with self.assertRaises(verify.ArchiveVerificationError):
            self.check(restored_data_root=link)

    def test_only_receipt_is_json_parsed_and_no_extraction_or_writes(self):
        native_loads, native_open = json.loads, os.open
        def readonly_open(path, flags, *args, **kwargs):
            self.assertFalse(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC))
            return native_open(path, flags, *args, **kwargs)
        with patch.object(verify.json, "loads", wraps=native_loads) as loads, \
             patch.object(verify.os, "open", side_effect=readonly_open), \
             patch.object(tarfile.TarFile, "extract", side_effect=AssertionError("extraction")), \
             patch.object(tarfile.TarFile, "extractall", side_effect=AssertionError("extraction")):
            self.assertEqual(self.check()["status"], "PASS")
            self.assertEqual(loads.call_count, 1)

    def test_cli_success_and_failure_never_leak_raw_bytes(self):
        args = ["--archive", str(self.archive), "--receipt", str(self.receipt),
                "--expected-receipt-sha256", self.receipt_digest,
                "--wave", self.wave, "--site", self.site]
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            self.assertEqual(verify.main(args), 0)
        self.assertEqual(json.loads(out.getvalue())["status"], "PASS")
        self.assertEqual(err.getvalue(), "")
        self.members[0] = (self.members[0][0], tarfile.REGTYPE, PRIVATE + b"changed", "")
        self.write_archive()
        args[args.index("--expected-receipt-sha256") + 1] = self.receipt_digest
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            self.assertEqual(verify.main(args), 1)
        self.assertEqual(out.getvalue(), "")
        self.assertEqual(json.loads(err.getvalue())["status"], "FAIL")
        self.assertNotIn("SYNTHETIC_PRIVATE", out.getvalue() + err.getvalue())


if __name__ == "__main__":
    unittest.main()
