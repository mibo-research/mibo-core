from datetime import datetime, timezone
import hashlib
from pathlib import Path
import tempfile
import unittest
import sys

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import mibo_runner as core
import ui_capture as cap
import ui_operator as op

UI_CONFIG = Path(__file__).with_name("ui_configuration.synthetic.json")


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

    def test_human_capture_is_append_only_and_hash_bound(self):
        row = self.row()
        prompt = next(f["text"] for f in core._forms() if f["query_form_id"] == row["query_form_id"])
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            meta = cap.capture_ui_observation(
                data_root=root, row=row, prompt_text=prompt, output_text="synthetic output",
                ui_configuration_path=UI_CONFIG, operator_id="operator-test",
                operator_confirmed_new_session=True,
                submitted_at_utc="2026-09-01T01:00:00Z", captured_at_utc="2026-09-01T01:01:00Z",
                now=datetime(2026, 9, 1, 1, 1, tzinfo=timezone.utc),
            )
            self.assertEqual(meta["output_sha256"], hashlib.sha256(b"synthetic output").hexdigest())
            self.assertTrue(meta["operator_confirmed_new_session"])
            self.assertFalse(meta["browser_automation"])
            with self.assertRaises(FileExistsError):
                cap.capture_ui_observation(
                    data_root=root, row=row, prompt_text=prompt, output_text="replacement",
                    ui_configuration_path=UI_CONFIG, operator_id="operator-test",
                    operator_confirmed_new_session=True,
                    submitted_at_utc="2026-09-01T01:02:00Z", captured_at_utc="2026-09-01T01:03:00Z",
                    now=datetime(2026, 9, 1, 1, 3, tzinfo=timezone.utc),
                )

    def test_capture_rejects_wrong_prompt_and_no_fresh_session(self):
        row = self.row()
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, "fresh session"):
                cap.capture_ui_observation(
                    data_root=Path(d), row=row, prompt_text="wrong", output_text="x",
                    ui_configuration_path=UI_CONFIG, operator_id="operator-test",
                    operator_confirmed_new_session=False,
                    submitted_at_utc="s", captured_at_utc="c",
                    now=datetime(2026, 9, 1, 1, 0, tzinfo=timezone.utc),
                )
            with self.assertRaisesRegex(ValueError, "prompt text"):
                cap.capture_ui_observation(
                    data_root=Path(d), row=row, prompt_text="wrong", output_text="x",
                    ui_configuration_path=UI_CONFIG, operator_id="operator-test",
                    operator_confirmed_new_session=True,
                    submitted_at_utc="s", captured_at_utc="c",
                    now=datetime(2026, 9, 1, 1, 0, tzinfo=timezone.utc),
                )

    def test_next_task_is_selected_only_when_due(self):
        rows = core.generate_ui_manifest("MIBO-W01")
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            before_open = op.select_next_row(rows, data_root=root, now=datetime(2026, 8, 31, 23, 0, tzinfo=timezone.utc), window_id="WA")
            self.assertIsNone(before_open)
            inside = op.select_next_row(rows, data_root=root, now=datetime(2026, 9, 1, 1, 0, tzinfo=timezone.utc), window_id="WA")
            self.assertIsNotNone(inside)
            self.assertEqual(inside["window_id"], "WA")

    def test_retry_near_window_end_is_not_scheduled_outside_calibration_window(self):
        row = self.row()
        with tempfile.TemporaryDirectory() as d:
            retry = op.schedule_retry(
                data_root=Path(d), row=row, failure_kind="timeout",
                failed_at=datetime(2026, 9, 1, 11, 55, tzinfo=timezone.utc),
            )
            self.assertIsNone(retry)

    def test_operator_source_contains_no_browser_or_http_automation(self):
        source = (HERE / "ui_operator.py").read_text(encoding="utf-8") + (HERE / "ui_capture.py").read_text(encoding="utf-8")
        for forbidden in ("selenium", "playwright", "urlopen(", "requests.get", "requests.post", "webdriver"):
            self.assertNotIn(forbidden, source.lower())


if __name__ == "__main__":
    unittest.main()
