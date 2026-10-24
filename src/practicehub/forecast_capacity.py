"""Explicit monthly capacity scenarios, not exact deadline-level allocation."""

import math

import pandas as pd

WEEKDAYS = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6}
TARGET_TYPES = {"same_day_gp_requests": "Same-day GP", "routine_gp_requests": "Routine GP"}


def capacity_plan(clinicians, assumptions):
    month = pd.Timestamp(assumptions["forecast_month"])
    if month.day != 1:
        raise ValueError("forecast_month must be the first day of a month.")
    fraction = assumptions["blocked_slot_fraction"]
    if not 0 <= fraction < 1:
        raise ValueError("Blocked fraction must be between zero and one.")
    same = assumptions["same_day_slots_per_session"]
    routine = assumptions["routine_slots_per_session"]
    slots = assumptions["slots_per_session"]
    sessions_per_day = assumptions["sessions_per_working_day"]
    if any(not isinstance(value, int) or isinstance(value, bool) or value <= 0
           for value in [same, routine, slots, sessions_per_day]):
        raise ValueError("Session and slot assumptions must be positive integers.")
    if same + routine != slots:
        raise ValueError("Same-day plus routine slots must equal slots per session.")
    holidays = {pd.Timestamp(day).normalize() for day in
                assumptions["bank_holiday_dates"] + assumptions.get("additional_closure_dates", [])}
    if any(day.to_period("M") != month.to_period("M") for day in holidays):
        raise ValueError("Holiday dates must belong to the forecast month.")
    leave = {(int(item["clinician_id"]), pd.Timestamp(item["absence_date"]).normalize())
             for item in assumptions["approved_leave"]}
    daily = []
    opening_days = [day for day in pd.date_range(month, month + pd.offsets.MonthEnd(0), freq="D")
                    if day.weekday() < 5 and day not in holidays]
    for doctor in clinicians.itertuples(index=False):
        if not doctor.is_gp:
            continue
        pattern = doctor.working_pattern.split()
        if not pattern or any(day not in WEEKDAYS for day in pattern):
            raise ValueError("Unrecognised clinician working pattern.")
        if doctor.usual_session_minutes != slots * assumptions["appointment_minutes"] + assumptions["non_slot_minutes_per_session"]:
            raise ValueError("Session length does not reconcile with slots and non-slot time.")
        weekdays = {WEEKDAYS[day] for day in pattern}
        for day in opening_days:
            active_to = pd.to_datetime(doctor.active_to)
            if (day.weekday() not in weekdays or day < pd.Timestamp(doctor.active_from)
                    or (not pd.isna(active_to) and day > active_to)):
                continue
            absent = (doctor.clinician_id, day) in leave
            sessions = 0 if absent else sessions_per_day
            daily.append({
                "calendar_date": day, "clinician_id": doctor.clinician_id,
                "planned_leave": absent, "sessions": sessions,
                "same_day_slots": sessions * same, "routine_slots": sessions * routine,
            })
    daily = pd.DataFrame(daily)
    if daily.empty:
        raise ValueError("No clinician working days found for this month.")
    sessions = int(daily.sessions.sum())
    raw = {"Same-day GP": int(daily.same_day_slots.sum()), "Routine GP": int(daily.routine_slots.sum())}
    summary = pd.DataFrame([{
        "appointment_type": kind, "nominal_slots": count,
        "assumed_blocked_slots": count - math.floor(count * (1 - fraction)),
        "planned_usable_slots": math.floor(count * (1 - fraction)),
    } for kind, count in raw.items()])
    return daily, summary, len(opening_days), sessions


def appointment_gap(forecasts, capacity):
    if forecasts.Target.duplicated().any() or set(forecasts.Target) != set(TARGET_TYPES):
        raise ValueError("Expected one next-month forecast for each appointment type.")
    rows = []
    for forecast in forecasts.itertuples(index=False):
        if not math.isfinite(forecast.predicted_requests) or forecast.predicted_requests < 0:
            raise ValueError("Forecast values must be finite and non-negative.")
        kind = TARGET_TYPES[forecast.Target]
        available = int(capacity.loc[capacity.appointment_type.eq(kind), "planned_usable_slots"].item())
        rows.append({
            "forecast_month": forecast.forecast_month, "appointment_type": kind,
            "predicted_requests": forecast.predicted_requests,
            "planned_usable_slots": available,
            "positive_gap_unrounded": max(0.0, forecast.predicted_requests - available),
            "additional_appointments_rounded_up": math.ceil(max(0.0, forecast.predicted_requests - available)),
        })
    return pd.DataFrame(rows)
