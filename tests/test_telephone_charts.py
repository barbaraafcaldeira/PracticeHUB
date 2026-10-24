"""Telephone chart reconciliations against the packaged, read-only database."""

from pathlib import Path
import copy
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis_code"))
from telephone_workload import read_call_details, validate_calls
from practicehub.dashboard import read_database


class TelephoneChartTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.monthly = read_database("SQLite")["monthly"]
        cls.calls = read_call_details("SQLite")

    def test_outcomes_and_hourly_rollups_reconcile(self):
        validate_calls(self.monthly, self.calls)
        self.assertEqual(self.calls["outcomes"].attempts.sum(), 183009)
        self.assertEqual(self.calls["requests"].requests_with_attempts.iloc[0], 124495)

    def test_inconsistent_outcome_totals_are_rejected(self):
        invalid = copy.deepcopy(self.calls)
        invalid["outcomes"].loc[0, "attempts"] += 1
        with self.assertRaises(ValueError):
            validate_calls(self.monthly, invalid)


if __name__ == "__main__":
    unittest.main()
