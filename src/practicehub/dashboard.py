"""Read-only dashboard data access and reproducible scenario calculations."""

from contextlib import closing
import contextlib
import io
import json
import math
from pathlib import Path
import runpy
import sqlite3

import numpy as np
import pandas as pd

from practicehub.forecast_capacity import TARGET_TYPES, appointment_gap, capacity_plan
from practicehub.monthly_forecasting import calendar_features


ROOT = Path(__file__).resolve().parents[2]
QUERIES = {
    "monthly": "SELECT * FROM monthly_kpis ORDER BY kpi_month",
    "calendar": "SELECT calendar_date,is_open,closure_reason FROM practice_calendar ORDER BY calendar_date",
    "clinicians": "SELECT * FROM clinicians ORDER BY clinician_id",
    "capacity": """
        SELECT SUBSTR(cs.session_date,1,7) AS kpi_month,s.slot_type,
          SUM(s.is_bookable) AS bookable_slots,COUNT(a.appointment_id) AS allocated_slots,
          SUM(CASE WHEN a.attendance_status='Attended' THEN 1 ELSE 0 END) AS attended,
          SUM(CASE WHEN a.attendance_status='DNA' THEN 1 ELSE 0 END) AS dna,
          SUM(CASE WHEN a.attendance_status='Cancelled by patient' THEN 1 ELSE 0 END) AS patient_cancelled,
          SUM(CASE WHEN a.attendance_status='Cancelled by practice' THEN 1 ELSE 0 END) AS practice_cancelled
        FROM clinic_sessions cs JOIN clinicians c ON c.clinician_id=cs.clinician_id
        JOIN appointment_slots s ON s.session_id=cs.session_id
        LEFT JOIN appointments a ON a.slot_id=s.slot_id
        WHERE c.is_gp=1 AND s.slot_type IN ('Same-day GP','Routine GP')
        GROUP BY SUBSTR(cs.session_date,1,7),s.slot_type ORDER BY kpi_month,s.slot_type
    """,
    "routing": """
        SELECT SUBSTR(requested_datetime,1,7) AS kpi_month,COUNT(*) AS received,
          SUM(CASE WHEN request_outcome='Allocated internally' THEN 1 ELSE 0 END) AS internal,
          SUM(CASE WHEN request_outcome='Appropriate signposting' THEN 1 ELSE 0 END) AS appropriate,
          SUM(CASE WHEN request_outcome='Signposted due to capacity' THEN 1 ELSE 0 END) AS capacity,
          SUM(CASE WHEN request_outcome='Pending' THEN 1 ELSE 0 END) AS pending
        FROM appointment_requests GROUP BY SUBSTR(requested_datetime,1,7) ORDER BY kpi_month
    """,
    "complaint_causes": """
        SELECT SUBSTR(complaint_date,1,7) AS kpi_month,complaint_trigger,COUNT(*) AS complaints
        FROM patient_complaints WHERE complaint_category='Appointment access'
        GROUP BY SUBSTR(complaint_date,1,7),complaint_trigger ORDER BY kpi_month
    """,
}


def read_database(source):
    if source == "SQLite":
        path = ROOT / "database" / "practicehub_final.sqlite"
        with closing(sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)) as db:
            db.execute("BEGIN")
            result = {name: pd.read_sql_query(query, db) for name, query in QUERIES.items()}
    elif source == "MySQL":
        with contextlib.redirect_stdout(io.StringIO()):
            connection = runpy.run_path(str(ROOT / "analysis_code" / "01_connect_to_mysql.py"))
        engine = connection["engine"]
        try:
            with engine.connect().execution_options(isolation_level="REPEATABLE READ") as db:
                with db.begin():
                    result = {name: pd.read_sql(query, db) for name, query in QUERIES.items()}
        finally:
            engine.dispose()
    else:
        raise ValueError("Unsupported data source.")
    for key in ["monthly", "capacity", "routing", "complaint_causes"]:
        result[key]["kpi_month"] = pd.to_datetime(result[key].kpi_month)
    result["calendar"]["calendar_date"] = pd.to_datetime(result["calendar"].calendar_date)
    monthly = result["monthly"]
    if monthly.empty or monthly.kpi_month.duplicated().any():
        raise ValueError("Monthly KPIs are empty or duplicated.")
    if not pd.DatetimeIndex(monthly.kpi_month).equals(pd.date_range(monthly.kpi_month.min(), monthly.kpi_month.max(), freq="MS")):
        raise ValueError("Monthly KPIs contain missing months.")
    routing = result["routing"]
    if not routing[["internal", "appropriate", "capacity", "pending"]].sum(axis=1).eq(routing.received).all():
        raise ValueError("Routing outcomes do not reconcile.")
    capacity = result["capacity"].groupby("kpi_month").allocated_slots.sum()
    if not capacity.reindex(monthly.kpi_month).to_numpy().tolist() == monthly.gp_slots_booked.tolist():
        raise ValueError("Slot allocations do not reconcile with monthly KPIs.")
    return result


def read_artifacts():
    output = ROOT / "analysis_code" / "outputs"
    model = output / "RESULTS_MODEL4"
    uncertainty = output / "RESULTS_MODEL4_UNCERTAINTY"
    result = {
        "forecast": pd.read_csv(model / "next_month_forecast.csv", parse_dates=["forecast_month"]),
        "metrics": pd.read_csv(model / "RESULTS_MODEL4.csv"),
        "evaluation": pd.read_csv(model / "2025_walk_forward_predictions.csv", parse_dates=["kpi_month"]),
        "snapshot": pd.read_csv(model / "model_input_snapshot.csv", parse_dates=["kpi_month"]),
        "bands": pd.read_csv(uncertainty / "next_month_prediction_bands.csv", parse_dates=["forecast_month"]),
        "coverage": pd.read_csv(uncertainty / "2025_observed_coverage.csv"),
        "assumptions": json.loads((ROOT / "config" / "model4_capacity_assumptions.json").read_text()),
    }
    forecast = result["forecast"]
    if len(forecast) != 2 or set(forecast.Target) != set(TARGET_TYPES) or forecast.forecast_month.nunique() != 1:
        raise ValueError("Expected two forecasts for the same month.")
    bands = result["bands"]
    for target, group in bands.groupby("Target"):
        point = forecast.loc[forecast.Target.eq(target)].iloc[0]
        if not np.allclose(group.point_forecast, point.predicted_requests) or not group.forecast_month.eq(point.forecast_month).all():
            raise ValueError("Saved prediction bands do not match saved point forecasts.")
    if set(bands.Target) != set(TARGET_TYPES) or len(bands) != 4:
        raise ValueError("Expected 80% and 90% bands for both appointment types.")
    return result


def forecast_matches_database(data, artifacts):
    historical = data["monthly"].set_index("kpi_month")
    saved = artifacts["snapshot"].set_index("kpi_month")
    if not historical.index.equals(saved.index):
        return False
    for column in TARGET_TYPES:
        if not np.allclose(historical[column], saved[column], equal_nan=False):
            return False
    calendar = calendar_features(data["calendar"])
    for column in ["opening_days", "opening_mondays", "bank_holidays"]:
        if not np.allclose(calendar.reindex(saved.index)[column], saved[column], equal_nan=False):
            return False
    return True


def period_totals(monthly):
    slots = monthly.gp_slots_bookable.sum()
    offered = monthly.incoming_calls_offered.sum()
    return {
        "gp_requests": int(monthly.gp_requests.sum()),
        "utilisation_pct": 100 * monthly.gp_slots_booked.sum() / slots if slots else 0,
        "capacity_diverted": int(monthly.capacity_diverted_requests.sum()),
        "complaints": int(monthly.access_complaints.sum()),
        "incoming_answer_rate_pct": 100 * monthly.incoming_calls_answered.sum() / offered if offered else 0,
    }


def calculate_scenario(clinicians, artifacts, sessions_per_day=2, slots_per_session=12,
                       same_day_slots=7, blocked_pct=1.5, leave=None, demand_case="Point forecast",
                       band_level=90, extra_slots=12, keep_mix=False, extra_same_day=7, cost=None):
    assumptions = dict(artifacts["assumptions"])
    month = artifacts["forecast"].forecast_month.iloc[0]
    if pd.Timestamp(assumptions["forecast_month"]) != month:
        raise ValueError("Capacity calendar and saved forecast months differ.")
    if extra_slots < 1 or (keep_mix and not 0 < extra_same_day < extra_slots):
        raise ValueError("Invalid extra-session slot mix.")
    if cost is not None and (not math.isfinite(cost) or cost < 0):
        raise ValueError("Cost must be finite and non-negative.")
    if slots_per_session > 12:
        raise ValueError("A 210-minute session cannot hold more than twelve 15-minute slots plus 30 non-slot minutes.")
    assumptions.update({
        "sessions_per_working_day": sessions_per_day, "slots_per_session": slots_per_session,
        "same_day_slots_per_session": same_day_slots, "routine_slots_per_session": slots_per_session - same_day_slots,
        "blocked_slot_fraction": blocked_pct / 100, "approved_leave": leave or [],
        "non_slot_minutes_per_session": 210 - 15 * slots_per_session,
    })
    roster, capacity, opening_days, roster_sessions = capacity_plan(clinicians, assumptions)
    forecast = artifacts["forecast"].copy()
    if not forecast.opening_days.eq(opening_days).all():
        raise ValueError("Planned opening calendar differs from the forecast's calendar.")
    if demand_case != "Point forecast":
        column = {"Lower band": "lower_requests", "Upper band": "upper_requests"}.get(demand_case)
        if column is None:
            raise ValueError("Unknown demand scenario.")
        band = artifacts["bands"].loc[artifacts["bands"].nominal_coverage_pct.eq(band_level)].set_index("Target")
        forecast["predicted_requests"] = forecast.Target.map(band[column])
    gaps = appointment_gap(forecast, capacity)
    additional = int(gaps.additional_appointments_rounded_up.sum())
    if keep_mix:
        same = int(gaps.loc[gaps.appointment_type.eq("Same-day GP"), "additional_appointments_rounded_up"].item())
        routine = int(gaps.loc[gaps.appointment_type.eq("Routine GP"), "additional_appointments_rounded_up"].item())
        extra_sessions = max(math.ceil(same / extra_same_day), math.ceil(routine / (extra_slots - extra_same_day)))
    else:
        extra_sessions = math.ceil(additional / extra_slots)
    return {
        "gaps": gaps, "roster": roster, "capacity": capacity, "opening_days": opening_days,
        "roster_sessions": roster_sessions, "additional_appointments": additional,
        "extra_sessions": extra_sessions, "cost": None if cost is None else extra_sessions * cost,
        "assumptions": assumptions,
    }
