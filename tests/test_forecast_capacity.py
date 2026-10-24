from pathlib import Path
import sys
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from practicehub.forecast_capacity import appointment_gap, capacity_plan


class ForecastCapacityTests(unittest.TestCase):
    def setUp(self):
        self.clinicians = pd.DataFrame([{
            "clinician_id": 1, "working_pattern": "Mon Tue Wed Thu Fri", "is_gp": 1,
            "usual_session_minutes": 210, "active_from": "2020-01-01", "active_to": None,
        }])
        self.assumptions = {
            "forecast_month": "2026-01-01", "blocked_slot_fraction": 0,
            "bank_holiday_dates": ["2026-01-01"], "approved_leave": [],
            "sessions_per_working_day": 2, "slots_per_session": 12,
            "same_day_slots_per_session": 7, "routine_slots_per_session": 5,
            "appointment_minutes": 15, "non_slot_minutes_per_session": 30,
        }

    def test_weekends_and_holiday_excluded(self):
        daily, slots, opening_days, sessions = capacity_plan(self.clinicians, self.assumptions)
        self.assertEqual(opening_days, 21)
        self.assertEqual(sessions, 42)
        self.assertEqual(slots.nominal_slots.sum(), 504)
        self.assertFalse(daily.calendar_date.eq(pd.Timestamp("2026-01-01")).any())

    def test_approved_leave_reduces_rostered_sessions(self):
        self.assumptions["approved_leave"] = [{"clinician_id": 1, "absence_date": "2026-01-02"}]
        _, _, _, sessions = capacity_plan(self.clinicians, self.assumptions)
        self.assertEqual(sessions, 40)

    def test_blocked_slots_and_session_lengths(self):
        self.assumptions["blocked_slot_fraction"] = .015
        _, slots, _, _ = capacity_plan(self.clinicians, self.assumptions)
        self.assertTrue(slots.planned_usable_slots.le(slots.nominal_slots).all())
        self.assumptions["slots_per_session"] = 13
        with self.assertRaises(ValueError):
            capacity_plan(self.clinicians, self.assumptions)

    def test_positive_gaps_by_type_not_cancelled_by_spare_other_type(self):
        forecasts = pd.DataFrame({"Target": ["same_day_gp_requests", "routine_gp_requests"],
                                  "forecast_month": ["2026-01-01"] * 2, "predicted_requests": [101.1, 50]})
        slots = pd.DataFrame({"appointment_type": ["Same-day GP", "Routine GP"], "planned_usable_slots": [100, 80]})
        gaps = appointment_gap(forecasts, slots)
        self.assertEqual(gaps.additional_appointments_rounded_up.tolist(), [2, 0])


if __name__ == "__main__":
    unittest.main()
