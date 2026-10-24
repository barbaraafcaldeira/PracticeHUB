"""Historical, booking-protected capacity diagnostics for synthetic requests."""

from bisect import bisect_left, bisect_right
from collections import defaultdict
from datetime import timedelta

import pandas as pd


KINDS = ("Same-day GP", "Routine GP")


def request_window(request):
    day = request.requested_datetime.normalize()
    first = day if request.required_appointment_type == KINDS[0] else day + timedelta(days=1)
    last = request.required_by_datetime
    earliest = max(first, request.decision_datetime + timedelta(minutes=15))
    return earliest, last


def slot_index(slots):
    result = {}
    for kind in KINDS:
        rows = list(slots[slots.slot_type.eq(kind)].sort_values(
            ["slot_start_datetime", "slot_id"]).itertuples(index=False))
        result[kind] = ([s.slot_start_datetime for s in rows], rows)
    return result


def in_window(index, kind, first, last):
    times, rows = index[kind]
    return rows[bisect_left(times, first):bisect_right(times, last)]


def patient_bookings(appointments):
    result = defaultdict(dict)
    for row in appointments.itertuples(index=False):
        result[row.patient_id][row.slot_start_datetime] = row.booked_datetime
    return result


def diagnose(diverted, slots, appointments):
    """Replay actual availability, including slots booked after the decision."""
    index = slot_index(slots[slots.is_bookable.eq(1)])
    patient_times = patient_bookings(appointments)
    details = []
    for request in diverted.itertuples(index=False):
        first, last = request_window(request)
        kind = request.required_appointment_type
        other = KINDS[1] if kind == KINDS[0] else KINDS[0]
        matching = in_window(index, kind, first, last)
        opposite = in_window(index, other, first, last)

        def free_at_decision(slot):
            return pd.isna(slot.booked_datetime) or slot.booked_datetime > request.decision_datetime

        def no_conflict(slot):
            booked = patient_times[request.patient_id].get(slot.slot_start_datetime)
            return booked is None or booked > request.decision_datetime

        free = [s for s in matching if free_at_decision(s)]
        suitable = [s for s in free if no_conflict(s)]
        wrong_type = [s for s in opposite if free_at_decision(s) and no_conflict(s)]
        if suitable:
            reason = "Suitable capacity found - investigate data"
        elif free:
            reason = "Free matching slots conflict with patient bookings"
        elif wrong_type:
            reason = "Free opposite-type slots in window - retyping sensitivity only"
        elif not matching:
            reason = "No matching bookable slots in remaining eligible window"
        else:
            reason = "Matching eligible slots already booked"
        details.append({
            "request_id": request.request_id,
            "patient_id": request.patient_id,
            "requested_datetime": request.requested_datetime,
            "decision_datetime": request.decision_datetime,
            "required_by_datetime": last,
            "appointment_type": kind,
            "external_care_status": request.external_care_status,
            "eligible_matching_slots": len(matching),
            "free_matching_slots_at_decision": len(free),
            "suitable_free_slots_at_decision": len(suitable),
            "free_opposite_type_slots_at_decision": len(wrong_type),
            "diagnosis": reason,
        })
    return pd.DataFrame(details)


def scenario(diverted, slots, appointments, calendar, extra_sessions=0, redistribute=False):
    """Conservative sensitivity analysis: never displace a historical booking.

    Future realised bookings are protected too. This uses hindsight and is not a
    prospective scheduling algorithm. Only never-booked bookable slots can change
    type. Hypothetical extra GPs provide 12 slots per 210-minute session at 14:00,
    split seven same-day and five routine, on every recorded opening day.
    """
    free = slots[slots.is_bookable.eq(1) & slots.booked_datetime.isna()].copy()
    extra = []
    for day in calendar.loc[calendar.is_open.eq(1), "calendar_date"]:
        for session in range(extra_sessions):
            for position in range(12):
                extra.append({
                    "slot_id": -(len(extra) + 1),
                    "slot_start_datetime": day + timedelta(hours=14, minutes=15 * position),
                    "slot_type": KINDS[0] if position < 7 else KINDS[1],
                    "is_bookable": 1,
                    "booked_datetime": pd.NaT,
                })
    if extra:
        free = pd.concat([free, pd.DataFrame(extra)], ignore_index=True)
    index = slot_index(free)
    reserved = {patient: set(times) for patient, times in patient_bookings(appointments).items()}
    used = set()
    results = []
    for request in diverted.sort_values(["decision_datetime", "request_id"]).itertuples(index=False):
        first, last = request_window(request)
        kind = request.required_appointment_type
        candidates = in_window(index, kind, first, last)
        if redistribute:
            other = KINDS[1] if kind == KINDS[0] else KINDS[0]
            # Extra-session templates are not retyped; existing spare slots may be.
            candidates += [s for s in in_window(index, other, first, last) if s.slot_id > 0]
        candidates.sort(key=lambda s: (s.slot_start_datetime, s.slot_type != kind, s.slot_id))
        patient_times = reserved.setdefault(request.patient_id, set())
        selected = next((s for s in candidates if s.slot_id not in used
                         and s.slot_start_datetime not in patient_times), None)
        if selected is not None:
            used.add(selected.slot_id)
            patient_times.add(selected.slot_start_datetime)
        results.append({
            "request_id": request.request_id,
            "patient_id": request.patient_id,
            "requested_datetime": request.requested_datetime,
            "appointment_type": kind,
            "external_care_status": request.external_care_status,
            "could_allocate_internally": selected is not None,
            "scenario_slot_id": selected.slot_id if selected is not None else None,
            "scenario_slot_datetime": selected.slot_start_datetime if selected is not None else pd.NaT,
            "used_extra_slot": selected is not None and selected.slot_id < 0,
            "retyped_existing_slot": selected is not None and selected.slot_type != kind,
        })
    details = pd.DataFrame(results)
    allocated = int(details.could_allocate_internally.sum())
    extra_used = int(details.used_extra_slot.sum())
    sessions = int(calendar.is_open.sum()) * extra_sessions
    summary = {
        "original_diverted_requests": len(details),
        "could_allocate_internally": allocated,
        "remaining_diverted_requests": len(details) - allocated,
        "distinct_patients_reallocated": int(details.loc[details.could_allocate_internally, "patient_id"].nunique()),
        "retyped_existing_slots_used": int(details.retyped_existing_slot.sum()),
        "reallocated_previously_confirmed_external": int((details.could_allocate_internally
            & details.external_care_status.eq("Confirmed external booking")).sum()),
        "reallocated_external_receipt_unknown": int((details.could_allocate_internally
            & ~details.external_care_status.eq("Confirmed external booking")).sum()),
        "extra_sessions_per_opening_day": extra_sessions,
        "extra_sessions_total": sessions,
        "extra_bookable_slots": sessions * 12,
        "extra_slots_used": extra_used,
        "extra_slot_use_pct": 100 * extra_used / (sessions * 12) if sessions else None,
        "redistribution_allowed": redistribute,
    }
    return summary, details
