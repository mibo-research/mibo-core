"""Operational monitoring is content-blind and never resumes a collector."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import core_v2_monitor as monitor


class MonitorTests(unittest.TestCase):
    def assess(self, status="COLLECTING", complete=False, active="active", before_close=True,
               clock=True, free=3 * 1024 ** 3, integrity=True):
        return monitor.assess(completion={"status": status, "scientific_collection_complete": complete,
            "integrity_pass": integrity}, services={"synthetic.service": {
            "available": True, "ActiveState": active, "MainPID": "10" if active == "active" else "0",
            "Result": "success"}}, before_close=before_close, free_bytes=free,
            clock={"check_available": clock is not None, "ntp_synchronized": clock})

    def test_active_collection_with_missing_cells_is_expected(self):
        self.assertEqual(self.assess()["monitor_status"], "OK")

    def test_inactive_success_with_missing_cells_requires_attention(self):
        report = self.assess(active="inactive")
        self.assertIn("collector_not_running_with_missing_cells", report["attention_reasons"])

    def test_suspension_is_visible_even_while_process_runs(self):
        report = self.assess(status="SUSPENDED")
        self.assertEqual(report["monitor_status"], "ATTENTION_REQUIRED")
        self.assertFalse(report["automatic_recovery_performed"])
        self.assertEqual(report["provider_calls_made"], 0)

    def test_completed_inactive_service_is_expected(self):
        self.assertEqual(self.assess(status="COMPLETE", complete=True, active="inactive")["monitor_status"], "OK")

    def test_close_with_missing_cells_and_failed_service_remains_incomplete(self):
        report = self.assess(status="INCOMPLETE", active="failed", before_close=False)
        self.assertIn("registered_window_closed_with_missing_cells", report["attention_reasons"])

    def test_corrupt_state_unknown_clock_or_low_disk_requires_attention(self):
        for kwargs in ({"integrity": False}, {"clock": None}, {"clock": False}, {"free": 1024}):
            with self.subTest(kwargs=kwargs):
                self.assertEqual(self.assess(**kwargs)["monitor_status"], "ATTENTION_REQUIRED")


if __name__ == "__main__":
    unittest.main()
