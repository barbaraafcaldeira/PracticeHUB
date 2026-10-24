"""Check allocation shares and pending-request treatment using read-only data."""

from pathlib import Path
import copy
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis_code"))
from allocation_outcomes_access_pressures import prepare_outcomes
from practicehub.dashboard import read_database


class AllocationChartTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = read_database("SQLite")

    def test_shares_use_decided_requests_and_preserve_counts(self):
        annual = prepare_outcomes(self.data)
        self.assertEqual(int(annual.loc[2025, "pending"]), 259)
        self.assertEqual(int(annual.loc[2025, "decided_requests"]), 42059)
        self.assertAlmostEqual(annual.loc[2025, "capacity_pct"], 100 * 12093 / 42059)
        self.assertTrue(annual[["internal_pct", "appropriate_pct", "capacity_pct"]].sum(axis=1).round(8).eq(100).all())
        self.assertEqual(int(annual.access_complaints.sum()), 1745)

    def test_unreconciled_outcomes_are_rejected(self):
        invalid = copy.deepcopy(self.data)
        invalid["routing"].loc[0, "received"] += 1
        with self.assertRaises(ValueError):
            prepare_outcomes(invalid)


if __name__ == "__main__":
    unittest.main()
