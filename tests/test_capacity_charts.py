"""Validate chart inputs without changing the source databases."""

from pathlib import Path
import sys
import unittest
import copy

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis_code"))
from appointment_capacity_utilisation import prepare_capacity_data
from practicehub.dashboard import read_database


class CapacityChartTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = read_database("SQLite")

    def test_monthly_totals_reconcile_and_source_is_unchanged(self):
        original = self.data["monthly"].copy(deep=True)
        totals, detail = prepare_capacity_data(self.data)
        self.assertEqual(len(totals), 36)
        self.assertEqual(len(detail), 72)
        self.assertTrue(detail.utilisation_pct.between(0, 100).all())
        self.assertEqual(totals.requests.sum(), original.gp_requests.sum())
        pd.testing.assert_frame_equal(original, self.data["monthly"])

    def test_duplicate_or_missing_capacity_is_rejected(self):
        duplicate = copy.deepcopy(self.data)
        duplicate["capacity"] = pd.concat([duplicate["capacity"], duplicate["capacity"].iloc[[0]]])
        with self.assertRaises(pd.errors.MergeError):
            prepare_capacity_data(duplicate)
        missing = copy.deepcopy(self.data)
        missing["capacity"] = missing["capacity"].iloc[1:]
        with self.assertRaises(ValueError):
            prepare_capacity_data(missing)

    def test_overallocation_or_missing_month_is_rejected(self):
        invalid = copy.deepcopy(self.data)
        invalid["capacity"].loc[0, "allocated_slots"] = invalid["capacity"].loc[0, "bookable_slots"] + 1
        with self.assertRaises(ValueError):
            prepare_capacity_data(invalid)
        invalid = copy.deepcopy(self.data)
        invalid["monthly"] = invalid["monthly"].drop(index=1)
        with self.assertRaises(ValueError):
            prepare_capacity_data(invalid)


if __name__ == "__main__":
    unittest.main()
