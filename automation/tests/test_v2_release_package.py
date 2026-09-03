import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[2]
AUTOMATION = ROOT / "automation"
sys.path.insert(0, str(AUTOMATION))
sys.path.insert(0, str(ROOT / "release"))

import build_v2_package as builder


class V2ReleasePackageTests(unittest.TestCase):
    def test_builds_disclosure_safe_hash_manifested_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            protocol = json.loads(
                (AUTOMATION / "config" / "core_v2_protocol.draft.json").read_text(encoding="utf-8")
            )
            protocol["protocol_status"] = "finalized_and_prospectively_registered"
            protocol["protocol_registration_id"] = "10.5281/zenodo.99999999"
            protocol_path = tmp_path / "protocol.json"
            protocol_path.write_text(json.dumps(protocol), encoding="utf-8")
            result = builder.build(
                protocol_path=protocol_path,
                version_doi="10.5281/zenodo.99999999",
                release_date="2026-09-03",
                out_dir=tmp_path / "out",
            )
            archive = Path(result["archive"])
            self.assertTrue(archive.is_file())
            self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), result["archive_sha256"])
            with zipfile.ZipFile(archive) as zf:
                names = set(zf.namelist())
                self.assertIn(
                    "MIBO_Core_Protocol_Package_v2.0/configuration/core_v2_protocol.final.json",
                    names,
                )
                self.assertIn("MIBO_Core_Protocol_Package_v2.0/SHA256SUMS.txt", names)
                joined = "\n".join(names).lower()
                self.assertNotIn("api_key", joined)
                self.assertNotIn("authorization.final", joined)


if __name__ == "__main__":
    unittest.main()
