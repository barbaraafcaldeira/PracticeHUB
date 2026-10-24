"""User-confirmed monthly input writes and interactive one-month forecasting."""

import contextlib
import io
import json
import runpy

import pandas as pd
import streamlit as st

from practicehub.monthly_inputs import (
    FIELDS, ROOT, build_live_forecast, planned_calendar, prepare_history,
    correct_input, read_corrections, read_inputs, save_inputs,
)


def mysql_engine():
    with contextlib.redirect_stdout(io.StringIO()):
        connection = runpy.run_path(str(ROOT / "analysis_code" / "01_connect_to_mysql.py"))
    return connection["engine"]


@st.cache_data(ttl=15, show_spinner=False)
def monthly_inputs():
    engine = mysql_engine()
    try:
        return read_inputs(engine)
    finally:
        engine.dispose()


def persist(data, frame, confirmed, source):
    if not confirmed:
        st.error("Confirm that these are complete-month actual demand counts.")
        return
    engine = None
    try:
        engine = mysql_engine()
        count = save_inputs(engine, data["monthly"].kpi_month.max(), frame, source)
    except ValueError as error:
        st.error(str(error))
        return
    except Exception:
        st.error("Save could not be confirmed. Refresh saved inputs before retrying.")
        return
    finally:
        if engine is not None:
            engine.dispose()
    monthly_inputs.clear()
    st.session_state["input_saved_message"] = f"Saved {count} completed month(s) to the separate forecasting-input table."
    st.rerun()


def default_holidays(month):
    path = ROOT / "config" / f"england_bank_holidays_{month.year}.json"
    if not path.exists():
        return []
    return [day for day in json.loads(path.read_text())["dates"] if pd.Timestamp(day).to_period("M") == month.to_period("M")]


def render_correction(data, added):
    if added.empty:
        st.info("Save a completed month before making a correction.")
        return
    month = st.selectbox("Saved month to correct", added.kpi_month.tolist(),
                         format_func=lambda value: pd.Timestamp(value).strftime("%B %Y"))
    original = added.loc[added.kpi_month.eq(month), FIELDS].copy()
    row = original.iloc[0]
    # Include the saved values so refreshed corrections cannot leave stale widget defaults.
    version = "_".join(str(int(row[name])) for name in FIELDS[1:])
    with st.form(f"correct_month_{pd.Timestamp(month):%Y%m}_{version}"):
        values = {}
        for name, label, maximum in [
            ("same_day_gp_requests", "Corrected same-day GP requests", 2_147_483_647),
            ("routine_gp_requests", "Corrected routine GP requests", 2_147_483_647),
            ("opening_days", "Corrected opening days", 31),
            ("bank_holidays", "Corrected bank-holiday closures", 31),
            ("opening_mondays", "Corrected opening Mondays", 5),
        ]:
            values[name] = st.number_input(label, min_value=1 if name == "opening_days" else 0,
                                           max_value=maximum, value=int(row[name]), step=1)
        reason = st.text_input("Reason for correction", max_chars=500)
        confirmed = st.checkbox("I confirm these corrected totals cover the entire completed month")
        submitted = st.form_submit_button("Save correction", icon=":material/save:")
    if submitted:
        if not confirmed:
            st.error("Confirm the corrected complete-month totals before saving.")
            return
        engine = None
        try:
            engine = mysql_engine()
            frame = pd.DataFrame([{"kpi_month": month, **values}])
            correct_input(engine, data["monthly"].kpi_month.max(), frame, original, reason)
        except ValueError as error:
            st.error(str(error))
            return
        except Exception:
            st.error("Correction could not be confirmed. Refresh saved inputs before retrying.")
            return
        finally:
            if engine is not None:
                engine.dispose()
        monthly_inputs.clear()
        st.session_state["input_saved_message"] = "Correction saved with an audit record. Regenerate the forecast using the corrected totals."
        st.rerun()
    with st.expander("Correction history"):
        engine = None
        try:
            engine = mysql_engine()
            audit = read_corrections(engine)
            if audit.empty:
                st.info("No corrections have been saved.")
            else:
                st.dataframe(audit, hide_index=True, width="stretch")
        except Exception:
            st.error("Correction history is currently unavailable.")
        finally:
            if engine is not None:
                engine.dispose()


def render_monthly_inputs(data, saved, source, allow_forecast=True):
    if source != "MySQL":
        st.info("Monthly inputs are stored in MySQL. The selected SQLite copy remains read-only.")
        return None
    try:
        added = monthly_inputs()
        history, _ = prepare_history(data, added)
    except Exception:
        st.error("Monthly forecasting inputs are unavailable or overlap operational history.")
        return None
    base_end = data["monthly"].kpi_month.max()
    next_month = history.index.max() + pd.offsets.MonthBegin(1)
    if "input_saved_message" in st.session_state:
        st.success(st.session_state.pop("input_saved_message"))
    st.caption(f"Operational history through {base_end:%B %Y}  |  Forecast inputs through {history.index.max():%B %Y}")
    tabs = st.tabs(["Enter completed month", "Saved inputs", "Correct saved month"])
    with tabs[0]:
        st.subheader(f"{next_month:%B %Y} actual demand")
        st.caption("Clinically indicated GP requests, including those not accommodated. Not booked-appointment totals.")
        defaults = default_holidays(next_month)
        _, month_calendar = planned_calendar(next_month, defaults, [])
        calendar_row = month_calendar.iloc[0]
        with st.form(f"completed_month_form_{next_month:%Y%m}"):
            left, right = st.columns(2)
            same = left.number_input("Same-day GP requests", min_value=0, max_value=2_147_483_647, value=None, step=1)
            routine = right.number_input("Routine GP requests", min_value=0, max_value=2_147_483_647, value=None, step=1)
            first, second, third = st.columns(3)
            openings = first.number_input("Actual opening days", min_value=1, max_value=31, value=int(calendar_row.opening_days))
            holidays = second.number_input("Actual bank-holiday closures", min_value=0, max_value=31, value=int(calendar_row.bank_holidays))
            mondays = third.number_input("Actual opening Mondays", min_value=0, max_value=5, value=int(calendar_row.opening_mondays))
            confirmed = st.checkbox("Counts cover the entire completed month", key=f"complete_month_confirmed_{next_month:%Y%m}")
            submitted = st.form_submit_button("Save completed month", icon=":material/save:")
        if submitted:
            frame = pd.DataFrame([dict(zip(FIELDS, [next_month, same, routine, openings, holidays, mondays]))])
            persist(data, frame, confirmed, "Manual entry")
    with tabs[1]:
        if added.empty:
            st.info("No additional completed months have been saved.")
        else:
            st.dataframe(added.rename(columns={"kpi_month": "Month", "same_day_gp_requests": "Same-day GP requests", "routine_gp_requests": "Routine GP requests"}), hide_index=True, width="stretch")
            st.download_button("Download saved inputs", added.to_csv(index=False), "saved_monthly_forecast_inputs.csv", "text/csv", icon=":material/download:")
    with tabs[2]:
        render_correction(data, added)
    st.divider()
    st.subheader(f"Generate {next_month:%B %Y} forecast")
    st.caption(f"Training history: {history.index.min():%B %Y} - {history.index.max():%B %Y}. Both appointment types are refitted when generated.")
    dates = pd.date_range(next_month, next_month + pd.offsets.MonthEnd(0), freq="D")
    options = [day.strftime("%Y-%m-%d") for day in dates if day.weekday() < 5]
    with st.form(f"generate_forecast_form_{next_month:%Y%m}"):
        bank_dates = st.multiselect("Planned bank-holiday closures", options, default=default_holidays(next_month), format_func=lambda d: pd.Timestamp(d).strftime("%a %d %b"))
        other_dates = st.multiselect("Other planned weekday closures", options, format_func=lambda d: pd.Timestamp(d).strftime("%a %d %b"))
        plan_confirmed = st.checkbox("Planned opening calendar confirmed", key=f"planned_calendar_confirmed_{next_month:%Y%m}")
        generate = st.form_submit_button("Generate forecast", type="primary", icon=":material/model_training:", disabled=not allow_forecast)
    if not allow_forecast:
        st.warning("The operational history changed since the reference model was saved; refresh the reference analysis before generating a forecast.")
    if generate:
        if not plan_confirmed:
            st.error("Confirm the planned opening calendar before generating the forecast.")
            return None
        try:
            _, plan = planned_calendar(next_month, bank_dates, other_dates)
            with st.spinner("Refitting Model 4 and calculating prediction ranges..."):
                result = build_live_forecast(data, added, saved, plan, bank_dates, other_dates)
        except ValueError as error:
            st.error(str(error))
            return None
        except Exception:
            st.error("Forecast generation failed. Historical records and saved inputs have not been changed.")
            return None
        st.success(f"Generated {next_month:%B %Y} forecast from completed data through {history.index.max():%B %Y}.")
        return result
    return None
