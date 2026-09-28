"""Guard the prospective v2.1 schedule draft without enabling its execution."""
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import core_v2_runner as runner


class V21ProspectiveDraftTests(unittest.TestCase):
    def test_only_w01_schedule_changes_and_registration_is_pending(self):
        old = json.loads((HERE / "config/core_v2_protocol.v2.0.json").read_text())
        new = json.loads((HERE / "config/core_v21_protocol.draft.json").read_text())
        self.assertEqual(new["protocol_version"], "2.1")
        self.assertEqual(new["protocol_status"], "draft_pending_version_specific_registration")
        self.assertEqual(new["protocol_registration_id"], "PENDING_ZENODO_VERSION_DOI")
        self.assertEqual(new["predecessor_protocol_registration_id"], old["protocol_registration_id"])
        self.assertEqual(new["waves"][0]["start_utc"], "2026-10-01T00:00:00Z")
        self.assertEqual(new["waves"][0]["close_utc"], "2026-10-03T00:00:00Z")
        self.assertEqual(new["waves"][0]["window_a"], old["waves"][0]["window_a"])
        self.assertEqual(new["waves"][0]["window_b"], old["waves"][0]["window_b"])
        self.assertEqual(new["waves"][1:], old["waves"][1:])
        for key in old.keys() - {"schema_version", "protocol_version", "protocol_status", "protocol_registration_id", "waves"}:
            self.assertEqual(new[key], old[key], key)
        with self.assertRaises(ValueError):
            runner.load_protocol(HERE / "config/core_v21_protocol.draft.json")


if __name__ == "__main__":
    unittest.main()
