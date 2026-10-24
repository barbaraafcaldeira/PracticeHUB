"""Monthly forecast inputs with audited corrections, separate from operational KPIs."""

from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
import copy
import hashlib
import json
import uuid

import numpy as np
import pandas as pd
from sqlalchemy import CheckConstraint, Column, Date, DateTime, Integer, MetaData, String, Table, Text, inspect, select
from sqlalchemy.exc import IntegrityError

from practicehub.monthly_forecasting import TARGETS, calendar_features, predict_month, walk_forward
from practicehub.forecast_uncertainty import future_bands

ROOT = Path(__file__).resolve().parents[2]
FIELDS = ["kpi_month", *TARGETS, "opening_days", "bank_holidays", "opening_mondays"]
METADATA = MetaData()
INPUTS = Table("forecast_month_inputs", METADATA,
    Column("kpi_month", Date, primary_key=True),
    *(Column(name, Integer, nullable=False) for name in FIELDS[1:]),
    Column("input_source", String(100), nullable=False),
    Column("created_at_utc", DateTime, nullable=False),
    CheckConstraint("same_day_gp_requests >= 0 AND routine_gp_requests >= 0"),
    CheckConstraint("opening_days BETWEEN 1 AND 31"),
    CheckConstraint("bank_holidays BETWEEN 0 AND 31"),
    CheckConstraint("opening_mondays BETWEEN 0 AND 5"),
)
CORRECTIONS = Table("forecast_month_input_corrections", METADATA,
    Column("correction_id", String(36), primary_key=True),
    Column("kpi_month", Date, nullable=False),
    Column("before_values", Text, nullable=False),
    Column("after_values", Text, nullable=False),
    Column("reason", String(500), nullable=False),
    Column("corrected_at_utc", DateTime, nullable=False),
)


def empty_inputs():
    return pd.DataFrame(columns=FIELDS + ["input_source", "created_at_utc"])


def read_inputs(engine):
    with engine.connect() as db:
        if not inspect(db).has_table(INPUTS.name):
            return empty_inputs()
        result = pd.read_sql(select(INPUTS).order_by(INPUTS.c.kpi_month), db)
    result["kpi_month"] = pd.to_datetime(result.kpi_month)
    return result


def validate_batch(base_end, existing, incoming, today=None):
    if set(incoming.columns) != set(FIELDS) or incoming.empty or len(incoming) > 24:
        raise ValueError("Provide 1-24 monthly rows with exactly the template columns.")
    rows = incoming[FIELDS].copy()
    try:
        rows["kpi_month"] = pd.to_datetime(rows.kpi_month, errors="raise")
    except (ValueError, TypeError):
        raise ValueError("Month dates must use YYYY-MM-01.") from None
    if (rows.kpi_month.isna().any() or rows.kpi_month.dt.tz is not None
            or not rows.kpi_month.dt.is_month_start.all()
            or not rows.kpi_month.eq(rows.kpi_month.dt.normalize()).all()):
        raise ValueError("Each month must use its first day, for example 2026-01-01.")
    if rows.kpi_month.duplicated().any():
        raise ValueError("Duplicate months are not allowed.")
    for column in FIELDS[1:]:
        try:
            numeric = pd.to_numeric(rows[column], errors="raise")
        except (ValueError, TypeError):
            raise ValueError(f"{column} must contain whole numbers.") from None
        if not np.isfinite(numeric.to_numpy(dtype=float)).all() or (numeric < 0).any() or (numeric % 1 != 0).any() or (numeric > 2_147_483_647).any():
            raise ValueError(f"{column} must contain non-negative whole numbers.")
        rows[column] = numeric.astype(int)
    current = pd.Timestamp(today or datetime.now(ZoneInfo("Europe/London")).date()).to_period("M").to_timestamp()
    if rows.kpi_month.ge(current).any():
        raise ValueError("Only fully completed months may be saved as actual demand.")
    if rows.kpi_month.le(pd.Timestamp(base_end)).any():
        raise ValueError("Existing operational months cannot be overwritten.")
    existing_dates = pd.DatetimeIndex(pd.to_datetime(existing.kpi_month)) if not existing.empty else pd.DatetimeIndex([])
    if rows.kpi_month.isin(existing_dates).any():
        raise ValueError("That month is already saved. Existing input rows are not overwritten.")
    combined = existing_dates.union(pd.DatetimeIndex(rows.kpi_month)).sort_values()
    expected = pd.date_range(pd.Timestamp(base_end) + pd.offsets.MonthBegin(1), combined.max(), freq="MS")
    if not combined.equals(expected):
        raise ValueError("Add consecutive months immediately after the latest completed month; do not skip months.")
    for row in rows.itertuples(index=False):
        dates = pd.date_range(row.kpi_month, row.kpi_month + pd.offsets.MonthEnd(0), freq="D")
        weekdays = int((dates.weekday < 5).sum())
        mondays = int((dates.weekday == 0).sum())
        closed_weekdays = weekdays - row.opening_days
        if not 0 < row.opening_days <= weekdays or not 0 <= row.bank_holidays <= closed_weekdays:
            raise ValueError("Calendar counts must match a Monday-Friday practice: holidays are closed weekdays.")
        if not max(0, mondays - closed_weekdays) <= row.opening_mondays <= min(mondays, row.opening_days):
            raise ValueError("Opening Monday count is inconsistent with this month's calendar.")
    return rows.sort_values("kpi_month").reset_index(drop=True)


def save_inputs(engine, base_end, incoming, input_source="Manual entry", today=None):
    # Validate before even creating a table. Duplicates/races also fail atomically at the primary key.
    validate_batch(base_end, read_inputs(engine), incoming, today)
    METADATA.create_all(engine, tables=[INPUTS])
    try:
        with engine.begin() as db:
            query = select(INPUTS).order_by(INPUTS.c.kpi_month)
            if engine.dialect.name == "mysql":
                query = query.with_for_update()
            existing = pd.read_sql(query, db)
            valid = validate_batch(base_end, existing, incoming, today)
            records = valid.to_dict("records")
            for record in records:
                record["kpi_month"] = record["kpi_month"].date()
                record["input_source"] = input_source[:100]
                record["created_at_utc"] = datetime.now(ZoneInfo("UTC")).replace(tzinfo=None)
            db.execute(INPUTS.insert(), records)
    except IntegrityError:
        raise ValueError("A month was saved by another session. Refresh before trying again.") from None
    return len(records)


def correct_input(engine, base_end, incoming, expected, reason, today=None):
    """Replace one input and record its previous values in the same transaction."""
    if len(incoming) != 1 or len(expected) != 1:
        raise ValueError("Select exactly one saved month to correct.")
    reason = reason.strip()
    if not reason or len(reason) > 500:
        raise ValueError("Provide a correction reason of 1-500 characters.")
    existing = read_inputs(engine)
    month = pd.Timestamp(expected.iloc[0].kpi_month)
    if pd.Timestamp(incoming.iloc[0].kpi_month) != month or not existing.kpi_month.eq(month).any():
        raise ValueError("Select an existing forecasting-input month; its date cannot be changed.")
    validate_batch(base_end, existing.loc[~existing.kpi_month.eq(month)], incoming, today)
    METADATA.create_all(engine, tables=[CORRECTIONS])
    with engine.begin() as db:
        query = select(INPUTS).order_by(INPUTS.c.kpi_month)
        if engine.dialect.name == "mysql":
            query = query.with_for_update()
        current = pd.read_sql(query, db)
        current["kpi_month"] = pd.to_datetime(current.kpi_month)
        selected = current.loc[current.kpi_month.eq(month)]
        if selected.empty:
            raise ValueError("The saved month changed. Refresh before correcting it.")
        before = {name: int(selected.iloc[0][name]) for name in FIELDS[1:]}
        expected_values = {name: int(expected.iloc[0][name]) for name in FIELDS[1:]}
        if before != expected_values:
            raise ValueError("This month was corrected by another session. Refresh before trying again.")
        valid = validate_batch(base_end, current.loc[~current.kpi_month.eq(month)], incoming, today)
        after = {name: int(valid.iloc[0][name]) for name in FIELDS[1:]}
        if before == after:
            raise ValueError("Change at least one value before saving a correction.")
        db.execute(INPUTS.update().where(INPUTS.c.kpi_month == month.date()).values(**after))
        db.execute(CORRECTIONS.insert().values(
            correction_id=str(uuid.uuid4()), kpi_month=month.date(),
            before_values=json.dumps(before), after_values=json.dumps(after), reason=reason,
            corrected_at_utc=datetime.now(ZoneInfo("UTC")).replace(tzinfo=None),
        ))


def read_corrections(engine):
    with engine.connect() as db:
        if not inspect(db).has_table(CORRECTIONS.name):
            return pd.DataFrame(columns=CORRECTIONS.c.keys())
        return pd.read_sql(select(CORRECTIONS).order_by(CORRECTIONS.c.corrected_at_utc.desc()), db)


def prepare_history(data, added):
    history = data["monthly"].set_index("kpi_month")[TARGETS].copy()
    calendar = calendar_features(data["calendar"])
    if not added.empty:
        extra = added[FIELDS].copy()
        extra["kpi_month"] = pd.to_datetime(extra.kpi_month)
        extra = extra.set_index("kpi_month").sort_index()
        if extra.index.intersection(history.index).size:
            raise ValueError("Monthly inputs overlap operational history; resolve the duplicate source before forecasting.")
        history = pd.concat([history, extra[TARGETS]])
        calendar = pd.concat([calendar, extra[["opening_days", "bank_holidays", "opening_mondays"]]])
    history = history.sort_index()
    if not history.index.equals(pd.date_range(history.index.min(), history.index.max(), freq="MS")):
        raise ValueError("Forecast history has missing or duplicate months.")
    return history, calendar.reindex(history.index)


def history_signature(history, calendar):
    snapshot = history.join(calendar).astype(float).rename_axis("kpi_month")
    return hashlib.sha256(snapshot.to_csv(date_format="%Y-%m-%d").encode()).hexdigest()


def planned_calendar(month, bank_dates, other_dates):
    month = pd.Timestamp(month)
    dates = pd.date_range(month, month + pd.offsets.MonthEnd(0), freq="D")
    bank = {pd.Timestamp(day).normalize() for day in bank_dates}
    other = {pd.Timestamp(day).normalize() for day in other_dates}
    if bank & other or any(day not in dates or day.weekday() > 4 for day in bank | other):
        raise ValueError("Choose distinct weekday closures within the forecast month.")
    frame = pd.DataFrame({"calendar_date": dates})
    frame["is_open"] = ((frame.calendar_date.dt.weekday < 5) & ~frame.calendar_date.isin(bank | other)).astype(int)
    frame["closure_reason"] = np.where(frame.calendar_date.isin(bank), "Bank holiday", "Other closure")
    return frame, calendar_features(frame)


def build_live_forecast(data, added, saved, plan, bank_dates, other_dates):
    history, calendar = prepare_history(data, added)
    month = history.index.max() + pd.offsets.MonthBegin(1)
    if not plan.index.equals(pd.DatetimeIndex([month])):
        raise ValueError("Planned calendar must cover the month immediately after completed inputs.")
    extended = pd.concat([calendar, plan])
    forecasts = []
    for target in TARGETS:
        point, evidence = predict_month(history, extended, month, target)
        forecasts.append({"forecast_month": month, "Target": target, "Method": "Monthly fitted Ridge",
                          "predicted_requests": point, "forecast_origin": month - pd.Timedelta(days=1),
                          "horizon_months": 1, **evidence})
    forecast = pd.DataFrame(forecasts)
    # Retrospective one-month-ahead errors, never using a month's actual count as its own predictor.
    calibration_months = history.index[history.index >= pd.Timestamp("2024-01-01")]
    calibration = walk_forward(history, calendar, calibration_months)
    calibration = calibration[calibration.Method.eq("Monthly fitted Ridge")].copy()
    bands = future_bands(calibration, forecast)
    bundle = copy.deepcopy(saved)
    bundle["forecast"], bundle["bands"] = forecast, bands
    bundle["assumptions"].update({
        "forecast_month": month.strftime("%Y-%m-%d"), "approved_leave": [],
        "bank_holiday_dates": [str(pd.Timestamp(d).date()) for d in bank_dates],
        "additional_closure_dates": [str(pd.Timestamp(d).date()) for d in other_dates],
    })
    signature = history_signature(history, calendar)
    run_id = datetime.now(ZoneInfo("UTC")).strftime("%Y%m%dT%H%M%S%f") + "_" + uuid.uuid4().hex[:8]
    folder = ROOT / "data" / "exports" / "live_forecasts" / run_id
    folder.mkdir(parents=True, exist_ok=False)
    forecast.to_csv(folder / "forecast.csv", index=False)
    bands.to_csv(folder / "bands.csv", index=False)
    history.join(calendar).to_csv(folder / "input_snapshot.csv", index_label="kpi_month")
    calibration.to_csv(folder / "retrospective_errors.csv", index=False)
    metadata = {
        "history_signature": signature, "run_id": run_id,
        "generated_at_utc": datetime.now(ZoneInfo("UTC")).isoformat(),
        "latest_completed_month": str(history.index.max().date()),
        "assumptions": bundle["assumptions"], "synthetic_data": True,
        "method": "Model 4 refitted at the button click using all available completed monthly inputs",
        "uncertainty": "Retrospective chronological errors; opening calendars assumed known in advance. No formal time-series coverage guarantee.",
        "evaluation_note": "2024/2025 reference metrics remain unchanged; they are not new metrics for this future month",
    }
    (folder / "run.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    bundle["live_metadata"] = metadata
    return bundle


def latest_live_forecast(data, added, saved):
    history, calendar = prepare_history(data, added)
    signature = history_signature(history, calendar)
    base = ROOT / "data" / "exports" / "live_forecasts"
    for path in sorted(base.glob("*/run.json"), reverse=True):
        meta = json.loads(path.read_text())
        if meta.get("history_signature") != signature:
            continue
        result = copy.deepcopy(saved)
        result["forecast"] = pd.read_csv(path.parent / "forecast.csv", parse_dates=["forecast_month"])
        result["bands"] = pd.read_csv(path.parent / "bands.csv", parse_dates=["forecast_month"])
        result["assumptions"] = meta["assumptions"]
        result["live_metadata"] = meta
        return result
    return None
