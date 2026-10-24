"""Read-only dashboard data and scenario integration tests."""

from pathlib import Path
import copy
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from practicehub.dashboard import calculate_scenario, forecast_matches_database, period_totals, read_artifacts, read_database


class DashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = read_database("SQLite")
        cls.saved = read_artifacts()

    def test_readonly_data_and_artifact_parity(self):
        self.assertEqual(len(self.data["monthly"]), 36)
        self.assertTrue(forecast_matches_database(self.data, self.saved))

    def test_stale_forecast_detected(self):
        changed = copy.deepcopy(self.data)
        changed["monthly"].loc[0, "routine_gp_requests"] += 1
        self.assertFalse(forecast_matches_database(changed, self.saved))

    def test_weighted_rates_not_average_monthly_percentages(self):
        monthly = self.data["monthly"].copy()
        result = period_totals(monthly)
        self.assertAlmostEqual(result["utilisation_pct"], 100 * monthly.gp_slots_booked.sum() / monthly.gp_slots_bookable.sum())

    def test_default_scenario_matches_saved_plan_and_leave_reduces_capacity(self):
        base = calculate_scenario(self.data["clinicians"], self.saved)
        self.assertEqual(base["additional_appointments"], 1235)
        self.assertEqual(base["extra_sessions"], 103)
        day = base["roster"].iloc[0]
        leave = [{"clinician_id": int(day.clinician_id), "absence_date": str(day.calendar_date.date())}]
        changed = calculate_scenario(self.data["clinicians"], self.saved, leave=leave)
        self.assertLess(changed["capacity"].planned_usable_slots.sum(), base["capacity"].planned_usable_slots.sum())

    def test_demand_bands_and_cost_have_expected_order(self):
        low = calculate_scenario(self.data["clinicians"], self.saved, demand_case="Lower band")
        high = calculate_scenario(self.data["clinicians"], self.saved, demand_case="Upper band", cost=100)
        self.assertLessEqual(low["additional_appointments"], high["additional_appointments"])
        self.assertEqual(high["cost"], high["extra_sessions"] * 100)


try:
    from streamlit.testing.v1 import AppTest
except ImportError:
    AppTest = None


@unittest.skipIf(AppTest is None, "Streamlit app tests require the dashboard environment")
class DashboardAppTests(unittest.TestCase):
    def test_all_four_views_render_and_calculator_updates(self):
        path = Path(__file__).resolve().parents[1] / "app" / "PracticeHUB.py"
        with patch.dict(os.environ, {"PRACTICEHUB_SOURCE": "SQLite"}):
            app = AppTest.from_file(str(path), default_timeout=60).run()
            self.assertFalse(app.exception)
            self.assertEqual(app.title[0].value, "Management overview")
            app.radio(key="page").set_value("Historical analysis").run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.tabs), 5)
            app.radio(key="page").set_value("Next-month forecast").run()
            self.assertFalse(app.exception)
            app.radio(key="page").set_value("Session calculator").run()
            self.assertFalse(app.exception)
            self.assertEqual(app.metric[0].value, "1,235")
            blocked = next(slider for slider in app.slider if slider.label == "Blocked slots (%)")
            blocked.set_value(10.0).run()
            self.assertFalse(app.exception)
            self.assertGreater(int(app.metric[0].value.replace(",", "")), 1235)

    def test_leave_slots_and_optional_cost_controls(self):
        path = Path(__file__).resolve().parents[1] / "app" / "PracticeHUB.py"
        with patch.dict(os.environ, {"PRACTICEHUB_SOURCE": "SQLite"}):
            app = AppTest.from_file(str(path), default_timeout=60).run()
            app.radio(key="page").set_value("Session calculator").run()
            app.multiselect(key="leave_1").set_value(["2026-01-02"]).run()
            self.assertFalse(app.exception)
            self.assertGreater(int(app.metric[0].value.replace(",", "")), 1235)
            next(toggle for toggle in app.toggle if toggle.label == "Include a session cost").set_value(True).run()
            next(item for item in app.number_input if item.label == "Cost per added session (GBP)").set_value(100.0).run()
            self.assertFalse(app.exception)
            self.assertTrue(app.metric[2].value.startswith("GBP "))
            next(item for item in app.number_input if item.label == "Slots per GP session").set_value(6).run()
            self.assertFalse(app.exception)


if __name__ == "__main__":
    unittest.main()
