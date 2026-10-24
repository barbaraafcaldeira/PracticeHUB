"""One-month forecasting must not access target-month or later demand."""

from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from practicehub.monthly_forecasting import TARGETS, calendar_features, demand_features, predict_month, walk_forward


class MonthlyForecastTests(unittest.TestCase):
    def setUp(self):
        self.index = pd.date_range("2023-01-01", "2025-12-01", freq="MS")
        self.history = pd.DataFrame({
            TARGETS[0]: 1800 + 200 * np.cos(np.arange(36) * np.pi / 6),
            TARGETS[1]: 800 + 100 * np.sin(np.arange(36) * np.pi / 3),
        }, index=self.index)
        self.calendar = pd.DataFrame({"opening_days": 21, "bank_holidays": 1, "opening_mondays": 4}, index=self.index)

    def test_future_demand_cannot_change_earlier_prediction(self):
        month = pd.Timestamp("2025-01-01")
        first, evidence = predict_month(self.history, self.calendar, month, TARGETS[0])
        changed = self.history.copy()
        changed.loc["2025":] = 999999
        second, _ = predict_month(changed, self.calendar, month, TARGETS[0])
        self.assertAlmostEqual(first, second)
        self.assertEqual(evidence["training_end"], "2024-12-01")

    def test_lags_only_use_completed_months(self):
        features = demand_features(self.history, self.calendar, TARGETS[1])
        month = pd.Timestamp("2024-01-01")
        expected = self.history.loc["2023-10":"2023-12", TARGETS[1]].mean() / 21
        self.assertAlmostEqual(features.loc[month, "previous_three_month_daily_mean"], expected)
        self.assertEqual(features.loc[month, "winter"], 1)

    def test_each_month_retrains_using_newly_completed_observations(self):
        months = pd.date_range("2025-01-01", "2025-02-01", freq="MS")
        predictions = walk_forward(self.history, self.calendar, months)
        ridge = predictions[predictions.Method.eq("Monthly fitted Ridge") & predictions.Target.eq(TARGETS[0])]
        self.assertEqual(ridge.training_end.tolist(), ["2024-12-01", "2025-01-01"])
        self.assertTrue(ridge.horizon_months.eq(1).all())

    def test_forecast_requires_previous_month_and_planned_calendar(self):
        with self.assertRaises(ValueError):
            predict_month(self.history.drop(pd.Timestamp("2024-12-01")), self.calendar,
                          pd.Timestamp("2025-01-01"), TARGETS[0])
        with self.assertRaises(ValueError):
            predict_month(self.history, self.calendar.drop(pd.Timestamp("2025-01-01")),
                          pd.Timestamp("2025-01-01"), TARGETS[0])

    def test_incomplete_daily_calendar_is_rejected(self):
        dates = pd.date_range("2024-01-01", "2024-01-31", freq="D")
        calendar = pd.DataFrame({"calendar_date": dates, "is_open": 1, "closure_reason": None})
        self.assertEqual(calendar_features(calendar).opening_days.iloc[0], 31)
        with self.assertRaises(ValueError):
            calendar_features(calendar.drop(4))


if __name__ == "__main__":
    unittest.main()
