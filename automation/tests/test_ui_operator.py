from datetime import datetime, timezone
import hashlib
from pathlib import Path
import tempfile
import unittest
import sys

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import mibo_runner as core
import operator_roster as roster_lib
import ui_capture as cap
import ui_operator as op

UI_CONFIG = Path(__file__).with_name("ui_configuration.synthetic.json")
ROSTER = Path(__file__).with_name("operator_roster.synthetic.json")


class EcologicalLiveCaptureTests(unittest.TestCase):
    def row(self):
        return next(
            r for r in core.generate_ui_manifest("MIBO-W01")
            if r["service_lineage_id"] == "MIBO-SL-001" and r["window_id"] == "WA"
        )

    def test_calibration_window_bounds_are_frozen(self):
        wa_start, wa_end = cap.window_bounds("MIBO-W01", "WA")
        wb_start, wb_end = cap.window_bounds("MIBO-W01", "WB")
        self.assertEqual(wa_start, datetime(2026, 9, 1, 0, 0, tzinfo=timezone.utc))
        self.assertEqual(wa_end, datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc))
        self.assertEqual(wb_start, datetime(2026, 9, 2, 0, 0, tzinfo=timezone.utc))
        self.assertEqual(wb_end, datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc))

    def test_operator_roster_is_frozen_and_service_specific(self):
        roster, digest = roster_lib.load_roster(ROSTER, wave_id="MIBO-W01", site_id="JP01")
        self.assertEqual(len(digest), 64)
        roster_lib.assert_operator_assigned(roster, service_lineage_id="MIBO-SL-001", operator_id="operator-openai")
        with self.assertRaises(ValueError):
            roster_lib.assert_operator_assigned(roster, service_lineage_id="MIBO-SL-002", operator_id="operator-openai")

    def test_human_capture_is_append_only_hash_bound_and_captures_sources(self):
        row = self.row()
        prompt = next(f["text"] for f in core._forms() if f["query_form_id"] == row["query_form_id"])
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            meta = cap.capture_ui_observation(
                data_root=root, row=row, prompt_text=prompt, output_text="synthetic output",
                ui_configuration_path=UI_CONFIG, operator_roster_path=ROSTER,
                operator_id="operator-openai", operator_confirmed_new_session=True,
                submitted_at_utc="2026-09-01T01:00:00Z", captured_at_utc="2026-09-01T01:01:00Z",
                sources_displayed=True, sources_text="Source card: https://example.org/source",
                now=datetime(2026, 9, 1, 1, 1, tzinfo=timezone.utc),
            )
            self.assertEqual(meta["output_sha256"], hashlib.sha256(b"synthetic output").hexdigest())
            self.assertEqual(meta["sources_capture_state"], "captured")
            self.assertEqual(len(meta["sources_sha256"]), 64)
            self.assertEqual(len(meta["operator_roster_sha256"]), 64)
            self.assertTrue(meta["operator_confirmed_new_session"])
            self.assertFalse(meta["browser_automation"])
            with self.assertRaises(FileExistsError):
                cap.capture_ui_observation(
                    data_root=root, row=row, prompt_text=prompt, output_text="replacement",
                    ui_configuration_path=UI_CONFIG, operator_roster_path=ROSTER,
                    operator_id="operator-openai", operator_confirmed_new_session=True,
                    submitted_at_utc="2026-09-01T01:02:00Z", captured_at_utc="2026-09-01T01:03:00Z",
                    sources_displayed=False, sources_text=None,
                    now=datetime(2026, 9, 1, 1, 3, tzinfo=timezone.utc),
                )

    def test_no_displayed_sources_is_recorded_explicitly(self):
        row = self.row()
        prompt = next(f["text"] for f in core._forms() if f["query_form_id"] == row["query_form_id"])
        with tempfile.TemporaryDirectory() as d:
            meta = cap.capture_ui_observation(
                data_root=Path(d), row=row, prompt_text=prompt, output_text="synthetic output",
                ui_configuration_path=UI_CONFIG, operator_roster_path=ROSTER,
                operator_id="operator-openai", operator_confirmed_new_session=True,
                submitted_at_utc="2026-09-01T01:00:00Z", captured_at_utc="2026-09-01T01:01:00Z",
                sources_displayed=False, sources_text=None,
                now=datetime(2026, 9, 1, 1, 1, tzinfo=timezone.utc),
            )
            self.assertEqual(meta["sources_capture_state"], "none_displayed")
            self.assertIsNone(meta["sources_file"])

    def test_capture_rejects_wrong_prompt_wrong_operator_and_no_fresh_session(self):
        row = self.row()
        with tempfile.TemporaryDirectory() as d:
            kwargs = dict(
                data_root=Path(d), row=row, output_text="x",
                ui_configuration_path=UI_CONFIG, operator_roster_path=ROSTER,
                submitted_at_utc="s", captured_at_utc="c",
                sources_displayed=False, sources_text=None,
                now=datetime(2026, 9, 1, 1, 0, tzinfo=timezone.utc),
            )
            with self.assertRaisesRegex(ValueError, "fresh session"):
                cap.capture_ui_observation(
                    prompt_text="wrong", operator_id="operator-openai",
                    operator_confirmed_new_session=False, **kwargs,
                )
            with self.assertRaisesRegex(ValueError, "not assigned"):
                cap.capture_ui_observation(
                    prompt_text=next(f["text"] for f in core._forms() if f["query_form_id"] == row["query_form_id"]),
                    operator_id="operator-anthropic", operator_confirmed_new_session=True, **kwargs,
                )
            with self.assertRaisesRegex(ValueError, "prompt text"):
                cap.capture_ui_observation(
                    prompt_text="wrong", operator_id="operator-openai",
                    operator_confirmed_new_session=True, **kwargs,
                )

    def test_next_task_is_selected_only_when_due_and_operator_assigned(self):
        rows = core.generate_ui_manifest("MIBO-W01")
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            before_open = op.select_next_row(rows, data_root=root, now=datetime(2026, 8, 31, 23, 0, tzinfo=timezone.utc), window_id="WA")
            self.assertIsNone(before_open)
            inside = op.select_next_row(
                rows, data_root=root, now=datetime(2026, 9, 1, 1, 0, tzinfo=timezone.utc),
                window_id="WA", allowed_lineages={"MIBO-SL-002"},
            )
            self.assertIsNotNone(inside)
            self.assertEqual(inside["window_id"], "WA")
            self.assertEqual(inside["service_lineage_id"], "MIBO-SL-002")

    def test_retry_near_window_end_is_not_scheduled_outside_calibration_window(self):
        row = self.row()
        with tempfile.TemporaryDirectory() as d:
            retry = op.schedule_retry(
                data_root=Path(d), row=row, failure_kind="timeout",
                failed_at=datetime(2026, 9, 1, 11, 55, tzinfo=timezone.utc),
            )
            self.assertIsNone(retry)

    def test_outage_recovery_requires_minimum_delay_and_stays_in_window(self):
        row = self.row()
        failed = datetime(2026, 9, 1, 2, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            with self.assertRaisesRegex(ValueError, "minimum retry delay"):
                op.schedule_outage_recovery(
                    data_root=root, row=row, failed_at=failed,
                    recovery_at_utc="2026-09-01T02:05:00Z",
                )
            task = op.schedule_outage_recovery(
                data_root=root, row=row, failed_at=failed,
                recovery_at_utc="2026-09-01T03:00:00Z",
            )
            self.assertEqual(task["status"], "scheduled_outage_recovery_retry")
            self.assertEqual(task["row"]["attempt"], 2)
            self.assertEqual(task["row"]["retry_of_attempt_id"], row["attempt_id"])

    def test_operator_source_contains_no_browser_or_http_automation(self):
        source = (HERE / "ui_operator.py").read_text(encoding="utf-8") + (HERE / "ui_capture.py").read_text(encoding="utf-8")
        for forbidden in ("selenium", "playwright", "urlopen(", "requests.get", "requests.post", "webdriver"):
            self.assertNotIn(forbidden, source.lower())


if __name__ == "__main__":
    unittest.main()
