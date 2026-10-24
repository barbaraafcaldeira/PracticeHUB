"""Focused tests for booking-protected historical capacity sensitivities."""

from pathlib import Path
import sys
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from practicehub.capacity_analysis import diagnose, scenario


class CapacityTests(unittest.TestCase):
    def request(self, kind="Same-day GP", decision="2024-01-02 08:30", deadline="2024-01-02 18:00"):
        return pd.DataFrame([{
            "request_id": 1, "patient_id": 1,
            "requested_datetime": pd.Timestamp("2024-01-02 08:00"),
            "decision_datetime": pd.Timestamp(decision),
            "required_by_datetime": pd.Timestamp(deadline),
            "required_appointment_type": kind,
            "external_care_status": "Advised; receipt unknown",
        }])

    def slots(self, kind="Same-day GP", at="2024-01-02 09:00", booked=None):
        return pd.DataFrame([{
            "slot_id": 1, "slot_type": kind, "is_bookable": 1,
            "slot_start_datetime": pd.Timestamp(at),
            "booked_datetime": pd.Timestamp(booked) if booked else pd.NaT,
        }])

    def appointments(self):
        return pd.DataFrame(columns=["patient_id", "slot_start_datetime", "booked_datetime"])

    def calendar(self):
        return pd.DataFrame({"calendar_date": pd.to_datetime(["2024-01-02"]), "is_open": [1]})

    def test_booking_after_decision_is_free_in_replay_but_protected_in_scenario(self):
        slots = self.slots(booked="2024-01-02 08:45")
        diagnosis = diagnose(self.request(), slots, self.appointments())
        self.assertEqual(diagnosis.suitable_free_slots_at_decision.iloc[0], 1)
        summary, _ = scenario(self.request(), slots, self.appointments(), self.calendar())
        self.assertEqual(summary["could_allocate_internally"], 0)

    def test_retyping_is_explicit_and_cannot_double_book(self):
        requests = pd.concat([self.request(), self.request().assign(request_id=2, patient_id=2)])
        slots = self.slots(kind="Routine GP")
        baseline, _ = scenario(requests, slots, self.appointments(), self.calendar())
        changed, _ = scenario(requests, slots, self.appointments(), self.calendar(), redistribute=True)
        self.assertEqual(baseline["could_allocate_internally"], 0)
        self.assertEqual(changed["could_allocate_internally"], 1)
        self.assertEqual(changed["retyped_existing_slots_used"], 1)

    def test_routine_cannot_use_same_date_slot(self):
        requests = self.request(kind="Routine GP", deadline="2024-01-16 18:00")
        diagnosis = diagnose(requests, self.slots(kind="Routine GP"), self.appointments())
        self.assertEqual(diagnosis.eligible_matching_slots.iloc[0], 0)

    def test_lead_time_and_deadline_enforced(self):
        requests = self.request(decision="2024-01-02 08:50")
        summary, _ = scenario(requests, self.slots(), self.appointments(), self.calendar())
        self.assertEqual(summary["could_allocate_internally"], 0)
        requests = self.request(deadline="2024-01-02 08:59")
        summary, _ = scenario(requests, self.slots(), self.appointments(), self.calendar())
        self.assertEqual(summary["could_allocate_internally"], 0)

    def test_patient_conflict_blocks_existing_and_extra_slots(self):
        appointments = pd.DataFrame([{
            "patient_id": 1, "slot_start_datetime": pd.Timestamp("2024-01-02 09:00"),
            "booked_datetime": pd.Timestamp("2024-01-02 08:00"),
        }])
        summary, _ = scenario(self.request(), self.slots(), appointments, self.calendar())
        self.assertEqual(summary["could_allocate_internally"], 0)

    def test_extra_sessions_supply_twelve_slots_without_retyping(self):
        requests = pd.concat([self.request().assign(request_id=i, patient_id=i) for i in range(1, 10)])
        summary, details = scenario(requests, self.slots(booked="2024-01-02 08:00"),
                                    self.appointments(), self.calendar(), extra_sessions=1)
        self.assertEqual(summary["extra_bookable_slots"], 12)
        self.assertEqual(summary["could_allocate_internally"], 7)
        self.assertEqual(details.loc[details.could_allocate_internally, "scenario_slot_id"].nunique(), 7)


if __name__ == "__main__":
    unittest.main()
