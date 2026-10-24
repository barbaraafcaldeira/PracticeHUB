"""All input writes use an isolated in-memory database, never presentation data."""

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
from sqlalchemy import create_engine, event, inspect

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from practicehub.monthly_inputs import (
    FIELDS, build_live_forecast, empty_inputs, latest_live_forecast, planned_calendar,
    correct_input, prepare_history, read_corrections, read_inputs, save_inputs, validate_batch,
)
from practicehub.dashboard import read_artifacts, read_database, calculate_scenario


class MonthlyInputTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        self.row = pd.DataFrame([dict(zip(FIELDS, ["2026-01-01", 2400, 850, 21, 1, 4]))])
        self.today = "2026-10-16"

    def tearDown(self):
        self.engine.dispose()

    def test_create_separate_table_and_round_trip(self):
        self.assertTrue(read_inputs(self.engine).empty)
        self.assertEqual(save_inputs(self.engine, "2025-12-01", self.row, today=self.today), 1)
        saved = read_inputs(self.engine)
        self.assertEqual(saved.same_day_gp_requests.iloc[0], 2400)
        self.assertEqual(inspect(self.engine).get_table_names(), ["forecast_month_inputs"])

    def test_duplicates_gaps_and_operational_months_rejected(self):
        save_inputs(self.engine, "2025-12-01", self.row, today=self.today)
        with self.assertRaises(ValueError):
            save_inputs(self.engine, "2025-12-01", self.row, today=self.today)
        for month in ["2025-12-01", "2026-03-01"]:
            with self.assertRaises(ValueError):
                validate_batch("2025-12-01", read_inputs(self.engine), self.row.assign(kpi_month=month), self.today)
        self.assertEqual(len(read_inputs(self.engine)), 1)

    def test_future_partial_fractional_and_bad_calendars_rejected_before_writing(self):
        variants = [self.row.assign(kpi_month="2026-10-01"), self.row.assign(kpi_month="2026-01-02"),
                    self.row.assign(same_day_gp_requests=2.5), self.row.assign(routine_gp_requests=-1),
                    self.row.assign(opening_days=31), self.row.assign(opening_mondays=5),
                    self.row.assign(bank_holidays=2), self.row.assign(same_day_gp_requests=None)]
        for frame in variants:
            with self.assertRaises(ValueError):
                save_inputs(self.engine, "2025-12-01", frame, today=self.today)
        self.assertEqual(inspect(self.engine).get_table_names(), [])

    def test_csv_batch_rejected_atomically(self):
        bad = pd.concat([self.row, self.row.assign(kpi_month="2026-02-01", opening_days=20, opening_mondays=4, bank_holidays=0, routine_gp_requests=-1)])
        with self.assertRaises(ValueError):
            save_inputs(self.engine, "2025-12-01", bad, today=self.today)
        self.assertTrue(read_inputs(self.engine).empty)

    def test_valid_consecutive_csv_batch(self):
        batch = pd.concat([self.row, self.row.assign(kpi_month="2026-02-01", opening_days=20, bank_holidays=0)])
        self.assertEqual(save_inputs(self.engine, "2025-12-01", batch, "CSV upload", self.today), 2)
        self.assertTrue(read_inputs(self.engine).input_source.eq("CSV upload").all())

    def test_other_planned_closures_affect_days_not_holiday_count(self):
        _, calendar = planned_calendar("2026-02-01", [], ["2026-02-02"])
        self.assertEqual(calendar.opening_days.iloc[0], 19)
        self.assertEqual(calendar.opening_mondays.iloc[0], 3)
        self.assertEqual(calendar.bank_holidays.iloc[0], 0)

    def test_correction_audits_old_and_new_values_and_rejects_stale_edit(self):
        save_inputs(self.engine, "2025-12-01", self.row, today=self.today)
        original = read_inputs(self.engine)[FIELDS]
        revised = original.assign(routine_gp_requests=900)
        correct_input(self.engine, "2025-12-01", revised, original, "Transcription error", self.today)
        self.assertEqual(read_inputs(self.engine).routine_gp_requests.iloc[0], 900)
        audit = read_corrections(self.engine)
        self.assertEqual(len(audit), 1)
        self.assertIn('"routine_gp_requests": 850', audit.before_values.iloc[0])
        self.assertIn('"routine_gp_requests": 900', audit.after_values.iloc[0])
        for frame, expected, reason in [
            (revised.assign(routine_gp_requests=910), original, "Stale edit"),
            (revised.assign(routine_gp_requests=-1), revised, "Invalid"),
            (revised, revised, "Unchanged"),
            (revised.assign(routine_gp_requests=910), revised, ""),
            (revised.assign(kpi_month="2025-12-01"), revised, "Wrong month"),
        ]:
            with self.assertRaises(ValueError):
                correct_input(self.engine, "2025-12-01", frame, expected, reason, self.today)
        self.assertEqual(len(read_corrections(self.engine)), 1)
        self.assertEqual(read_inputs(self.engine).routine_gp_requests.iloc[0], 900)

    def test_audit_failure_rolls_back_correction(self):
        save_inputs(self.engine, "2025-12-01", self.row, today=self.today)
        original = read_inputs(self.engine)[FIELDS]
        def fail_audit(connection, cursor, statement, parameters, context, executemany):
            if statement.startswith("INSERT INTO forecast_month_input_corrections"):
                raise RuntimeError("Simulated audit failure")
        event.listen(self.engine, "before_cursor_execute", fail_audit)
        try:
            with self.assertRaises(RuntimeError):
                correct_input(self.engine, "2025-12-01", original.assign(routine_gp_requests=900),
                              original, "Fix count", self.today)
        finally:
            event.remove(self.engine, "before_cursor_execute", fail_audit)
        self.assertEqual(read_inputs(self.engine).routine_gp_requests.iloc[0], 850)
        self.assertTrue(read_corrections(self.engine).empty)

    def test_live_forecast_uses_added_month_and_is_saved_separately(self):
        data, saved = read_database("SQLite"), read_artifacts()
        added = validate_batch("2025-12-01", empty_inputs(), self.row, self.today)
        history, calendar = prepare_history(data, added)
        self.assertEqual(len(history), 37)
        self.assertEqual(history.index.max(), pd.Timestamp("2026-01-01"))
        _, plan = planned_calendar("2026-02-01", [], [])
        with tempfile.TemporaryDirectory() as folder:
            with patch("practicehub.monthly_inputs.ROOT", Path(folder)):
                result = build_live_forecast(data, added, saved, plan, [], [])
                self.assertTrue(result["forecast"].forecast_month.eq(pd.Timestamp("2026-02-01")).all())
                self.assertTrue(result["forecast"].training_end.eq("2026-01-01").all())
                self.assertEqual(len(result["bands"]), 4)
                restored = latest_live_forecast(data, added, saved)
                pd.testing.assert_series_equal(restored["forecast"].predicted_requests, result["forecast"].predicted_requests)
                self.assertIsNone(latest_live_forecast(data, empty_inputs(), saved))
                scenario = calculate_scenario(data["clinicians"], restored)
                self.assertEqual(scenario["opening_days"], 20)
                save_inputs(self.engine, "2025-12-01", self.row, today=self.today)
                original = read_inputs(self.engine)[FIELDS]
                correct_input(self.engine, "2025-12-01", original.assign(routine_gp_requests=900),
                              original, "Fix count", self.today)
                self.assertIsNone(latest_live_forecast(data, read_inputs(self.engine), saved))
        self.assertTrue(saved["forecast"].forecast_month.eq(pd.Timestamp("2026-01-01")).all())


if __name__ == "__main__":
    unittest.main()
