from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from practicehub.forecast_uncertainty import coverage_summary, future_bands, residual_band, sequential_bands


class UncertaintyTests(unittest.TestCase):
    def predictions(self):
        dates = pd.date_range("2024-01-01", "2025-12-01", freq="MS")
        return pd.DataFrame({"kpi_month": dates, "Target": "routine_gp_requests",
                             "actual_requests": np.arange(24) + 100,
                             "predicted_requests": 100., "opening_days": 20.})

    def test_finite_sample_quantile_and_outward_rounding(self):
        band = residual_band(100.5, 2, np.arange(1, 13), .8)
        self.assertEqual(band["order_statistic_rank"], 11)
        self.assertEqual((band["lower_requests"], band["upper_requests"]), (78, 123))

    def test_rejects_small_pools_and_unattainable_finite_levels(self):
        with self.assertRaises(ValueError):
            residual_band(100, 20, [1] * 11, .8)
        with self.assertRaises(ValueError):
            residual_band(100, 20, [1] * 12, .95)
        with self.assertRaises(ValueError):
            residual_band(100, 20, [np.nan] * 12, .8)

    def test_current_and_future_errors_do_not_change_current_band(self):
        history = self.predictions()
        original = sequential_bands(history, "2025-01-01")
        history.loc[history.kpi_month.ge("2025-01-01"), "actual_requests"] = 999999
        changed = sequential_bands(history, "2025-01-01")
        cols = ["lower_requests", "upper_requests", "calibration_observations"]
        pd.testing.assert_frame_equal(original.iloc[:2][cols], changed.iloc[:2][cols])
        self.assertTrue(original.calibration_end.lt(original.kpi_month).all())

    def test_width_increases_with_coverage_and_nonnegative_lower_bound(self):
        small = residual_band(1, 20, np.arange(1, 25), .8)
        large = residual_band(1, 20, np.arange(1, 25), .9)
        self.assertEqual(small["lower_requests"], 0)
        self.assertGreaterEqual(large["upper_requests"], small["upper_requests"])

    def test_future_uses_only_completed_errors_and_summary_counts(self):
        predictions = self.predictions()
        future = pd.DataFrame({"forecast_month": [pd.Timestamp("2026-01-01")],
                               "Target": ["routine_gp_requests"], "predicted_requests": [110.], "opening_days": [21.]})
        bands = future_bands(predictions, future)
        self.assertTrue(bands.calibration_observations.eq(24).all())
        summary = coverage_summary(sequential_bands(predictions, "2025-01-01"))
        self.assertTrue(summary.evaluated_months.eq(12).all())
        self.assertTrue(summary.observed_coverage_pct.between(0, 100).all())

    def test_rejects_duplicate_observations(self):
        history = self.predictions()
        with self.assertRaises(ValueError):
            sequential_bands(pd.concat([history, history.iloc[:1]]), "2025-01-01")


if __name__ == "__main__":
    unittest.main()
