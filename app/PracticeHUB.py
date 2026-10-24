"""Local PracticeHUB dashboard; operational data stays read-only."""

from pathlib import Path
import copy
import os
import sys

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "app"))
from practicehub.dashboard import calculate_scenario, forecast_matches_database, period_totals, read_artifacts, read_database
from practicehub.forecast_capacity import capacity_plan
from practicehub.monthly_inputs import latest_live_forecast, prepare_history
from monthly_inputs_ui import monthly_inputs, render_monthly_inputs

st.set_page_config(page_title="PracticeHUB | Practice intelligence", page_icon=":material/monitoring:", layout="wide")
COLORS = {"Same-day GP": "#087F6D", "Routine GP": "#247BA0", "Capacity": "#C44C44", "Slots": "#C79A25"}
LABELS = {"same_day_gp_requests": "Same-day GP", "routine_gp_requests": "Routine GP"}
PAGES = ["Overview", "Historical analysis", "Next-month forecast", "Session calculator", "Monthly inputs"]
st.markdown("""<style>
html,body,[class*="css"] {letter-spacing:0!important;}
.block-container {padding-top:4rem; max-width:1450px; padding-bottom:3rem;}
h1 {font-size:1.9rem!important; font-weight:650!important;}
h2 {font-size:1.25rem!important; margin-top:1rem!important;}
h3 {font-size:1.05rem!important;}
[data-testid="stMetricValue"] {font-size:1.8rem!important; line-height:1.3;}
[data-testid="stMetricLabel"] p {font-size:.85rem!important; white-space:normal!important;}
[data-testid="stMetric"] {border-left:2px solid #DDE6E2;padding-left:14px;min-height:86px;}
[data-testid="stSidebar"] {border-right:1px solid #DFE7E3;}
.brand {font-size:1.65rem;font-weight:750;color:#172329;line-height:1.3;}
.brand span {color:#087F6D;}
.eyebrow {font-size:.74rem;font-weight:650;text-transform:uppercase;color:#62736D;margin:0 0 4px;}
.status-line {font-size:.85rem;color:#52645D;padding:8px 0 16px;}
.mobile-brand {display:none;}
button {border-radius:6px!important;}
@media(max-width:640px){.block-container{padding-top:3.8rem;}h1{font-size:1.55rem!important;}.mobile-brand{display:block;font-size:1.55rem;font-weight:750;margin-bottom:10px;}.mobile-brand span{color:#087F6D;}.eyebrow{display:none;}}
</style>""", unsafe_allow_html=True)


@st.cache_data(ttl=60, show_spinner=False)
def database(source):
    return read_database(source)


@st.cache_data(ttl=60, show_spinner=False)
def artifacts():
    return read_artifacts()


def chart(fig, height=350):
    fig.update_layout(
        template="plotly_white", height=height, margin=dict(l=5, r=15, t=25, b=5),
        font=dict(family="Arial, sans-serif", size=12, color="#24342E"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        hovermode="x unified", paper_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#E8EEEB", rangemode="tozero")
    st.plotly_chart(fig, width="stretch", config={"displaylogo": False, "displayModeBar": False})


def metric_row(items):
    for column, (label, value, help_text) in zip(st.columns(len(items)), items):
        column.metric(label, value, help=help_text)


def date_filter(frame, start, end):
    return frame[frame.kpi_month.between(start, end)].copy()


def demand_chart(monthly, per_day=False, calendar=None):
    frame = monthly[["kpi_month", "same_day_gp_requests", "routine_gp_requests"]].copy()
    if per_day:
        days = calendar.groupby(calendar.calendar_date.dt.to_period("M")).is_open.sum()
        for target in LABELS:
            frame[target] = frame[target] / frame.kpi_month.dt.to_period("M").map(days)
    frame = frame.rename(columns=LABELS).melt("kpi_month", var_name="Appointment type", value_name="Requests")
    fig = px.line(frame, x="kpi_month", y="Requests", color="Appointment type", markers=True, color_discrete_map=COLORS)
    fig.update_xaxes(title=None, tickformat="%b %Y")
    fig.update_yaxes(title="Requests per opening day" if per_day else "GP requests per month")
    chart(fig)


def overview(data, selected):
    totals = period_totals(selected)
    metric_row([
        ("GP requests (period total)", f"{totals['gp_requests']:,}", "Clinically indicated request episodes across the selected months, not all eConsults or calls."),
        ("Booked-slot utilisation (period)", f"{totals['utilisation_pct']:.1f}%", "Total booked slots / total bookable slots across the selected months. Includes DNAs and late cancellations."),
        ("Capacity signposting (period total)", f"{totals['capacity_diverted']:,}", "Total across the selected months. Includes confirmed external bookings; not all are unresolved need."),
        ("Access complaints (period total)", f"{totals['complaints']:,}", "Complaints received in the selected months; not additional appointment requests."),
    ])
    st.subheader("GP appointment requests")
    demand_chart(selected)
    left, right = st.columns(2)
    with left:
        st.subheader("Demand and scheduled capacity")
        fig = go.Figure()
        fig.add_scatter(x=selected.kpi_month, y=selected.gp_requests, name="GP requests", line_color="#087F6D")
        fig.add_scatter(x=selected.kpi_month, y=selected.gp_slots_bookable, name="Bookable slots", line_color="#C79A25")
        fig.update_yaxes(title="Requests / slots per month")
        chart(fig, 300)
        st.caption("Request month and appointment month differ for some routine bookings; the difference is not a direct unmet-demand count.")
    with right:
        st.subheader("Capacity-related signposting")
        frame = selected[["kpi_month", "same_day_capacity_diverted", "routine_capacity_diverted"]].rename(
            columns={"same_day_capacity_diverted": "Same-day GP", "routine_capacity_diverted": "Routine GP"})
        fig = px.bar(frame.melt("kpi_month", var_name="Appointment type", value_name="Requests"),
                     x="kpi_month", y="Requests", color="Appointment type", color_discrete_map=COLORS)
        fig.update_yaxes(title="Signposted requests per month")
        chart(fig, 300)
    st.download_button("Download monthly KPIs", selected.to_csv(index=False), "practicehub_monthly_kpis.csv",
                       "text/csv", icon=":material/download:")


def history(data, selected, start, end):
    tabs = st.tabs(["GP demand", "Slot utilisation", "eConsult routing", "Telephone", "Complaints"])
    with tabs[0]:
        per_day = st.toggle("Requests per opening day", value=False)
        demand_chart(selected, per_day, data["calendar"])
        seasonal = selected.assign(year=selected.kpi_month.dt.year.astype(str), month=selected.kpi_month.dt.month)
        melted = seasonal.melt(["kpi_month", "year", "month"], value_vars=list(LABELS), var_name="Target", value_name="Requests")
        melted["Appointment type"] = melted.Target.map(LABELS)
        chart(px.line(melted, x="month", y="Requests", color="year", facet_row="Appointment type", markers=True,
                      labels={"month": "Month of year", "Requests": "Requests per month", "year": "Year"}), 490)
    with tabs[1]:
        capacity = date_filter(data["capacity"], start, end)
        capacity["Utilisation (%)"] = 100 * capacity.allocated_slots / capacity.bookable_slots.replace(0, np.nan)
        chart(px.line(capacity, x="kpi_month", y="Utilisation (%)", color="slot_type", markers=True,
                      color_discrete_map=COLORS, labels={"Utilisation (%)": "Monthly utilisation (%)"}))
        st.caption("Booking utilisation is not attendance. Late cancellations and DNAs still occupied an allocated slot.")
        status = capacity.groupby("kpi_month")[["attended", "dna", "patient_cancelled", "practice_cancelled"]].sum().reset_index()
        status = status.rename(columns={"attended": "Attended", "dna": "DNA", "patient_cancelled": "Patient cancellation", "practice_cancelled": "Practice cancellation"})
        chart(px.bar(status.melt("kpi_month", var_name="Outcome", value_name="Appointments"),
                     x="kpi_month", y="Appointments", color="Outcome", labels={"Appointments": "Appointments per month"}))
    with tabs[2]:
        routing = date_filter(data["routing"], start, end)
        frame = routing.rename(columns={"internal": "Internal GP booking", "appropriate": "Appropriate signposting", "capacity": "Capacity-related signposting"})
        frame = frame.melt("kpi_month", value_vars=["Internal GP booking", "Appropriate signposting", "Capacity-related signposting"], var_name="Routing", value_name="Requests")
        chart(px.area(frame, x="kpi_month", y="Requests", color="Routing",
                      color_discrete_sequence=["#247BA0", "#087F6D", "#C44C44"], labels={"Requests": "Requests per month"}))
        st.caption(f"All intake routes combined. {int(routing.pending.sum()):,} pending requests excluded from the areas. Signposting is not proof of an external appointment.")
    with tabs[3]:
        total = period_totals(selected)
        metric_row([
            ("Incoming calls (period total)", f"{selected.incoming_calls_offered.sum():,.0f}", "Call events across the selected months, including repeat contacts and non-appointment enquiries."),
            ("Answer rate (period)", f"{total['incoming_answer_rate_pct']:.1f}%", "Total answered / total offered calls across the selected months, not the mean of monthly rates."),
            ("Outgoing attempts (period total)", f"{selected.outgoing_call_attempts.sum():,.0f}", "Total across the selected months. Multiple attempts may relate to one request."),
        ])
        frame = selected.rename(columns={"incoming_calls_offered": "Incoming offered", "incoming_calls_answered": "Incoming answered", "outgoing_call_attempts": "Outgoing attempts"})
        chart(px.line(frame.melt("kpi_month", value_vars=["Incoming offered", "Incoming answered", "Outgoing attempts"], var_name="Activity", value_name="Calls"),
                      x="kpi_month", y="Calls", color="Activity", markers=True, labels={"Calls": "Calls / attempts per month"}))
        st.caption("Telephone activity is workload, not a direct measure of appointment demand.")
    with tabs[4]:
        causes = date_filter(data["complaint_causes"], start, end)
        if causes.empty:
            st.info("No appointment-access complaints in this period.")
        else:
            chart(px.bar(causes, x="kpi_month", y="complaints", color="complaint_trigger", labels={"complaints": "Complaints per month"}))
        chart(px.line(selected, x="kpi_month", y="patients_without_appointment", markers=True,
                      labels={"patients_without_appointment": "Monthly distinct patients with unmet requests"}))
        st.caption("Monthly patient counts are deduplicated across intake routes; do not sum them into annual unique patients. Complaints are an indirect indicator, not extra appointment demand.")
    with st.expander("Monthly data"):
        st.dataframe(selected.drop(columns=["synthetic_data_label"], errors="ignore"), hide_index=True, width="stretch")


def forecasts_view(saved):
    month = saved["forecast"].forecast_month.iloc[0]
    st.subheader(f"Monthly demand forecast: {month:%B %Y}")
    st.caption(f"Forecast origin: {(month - pd.Timedelta(days=1)):%d %B %Y}  |  Horizon: one month  |  Fitted Ridge for both appointment types")
    if "live_metadata" in saved:
        latest = pd.Timestamp(saved["live_metadata"]["latest_completed_month"])
        st.success(f"Forecast generated from completed monthly inputs through {latest:%B %Y}.", icon=":material/model_training:")
    else:
        st.info(f"{month:%B %Y} follows the historical dataset cutoff, not the current live practice position.", icon=":material/calendar_month:")
    level = st.segmented_control("Prediction band", [80, 90], default=90, format_func=lambda x: f"{x}% nominal", required=True)
    bands = saved["bands"][saved["bands"].nominal_coverage_pct.eq(level)].copy()
    items = []
    for target, label in LABELS.items():
        row = bands[bands.Target.eq(target)].iloc[0]
        items.append((label + " requests (month)", f"{row.point_forecast:,.0f}", f"Total for {month:%B %Y}. Empirical prediction range: {row.lower_requests:,.0f} to {row.upper_requests:,.0f}."))
    metric_row(items)
    fig = go.Figure()
    fig.add_scatter(x=bands.point_forecast, y=bands.Target.map(LABELS), mode="markers",
                    marker=dict(size=12, color="#087F6D"), name="Point forecast",
                    error_x=dict(type="data", symmetric=False, array=bands.upper_requests-bands.point_forecast,
                                 arrayminus=bands.point_forecast-bands.lower_requests, color="#247BA0", thickness=6))
    fig.update_xaxes(title=f"Total GP requests for {month:%B %Y}")
    chart(fig, 260)
    table = bands.assign(**{"Appointment type": bands.Target.map(LABELS)}).rename(
        columns={"point_forecast": "Point forecast", "lower_requests": "Lower range", "upper_requests": "Upper range"})
    st.dataframe(table[["Appointment type", "Point forecast", "Lower range", "Upper range"]].round(2), hide_index=True, width="stretch")
    st.caption("Empirical ranges use earlier forecasting errors. Nominal coverage is not accuracy or a guarantee, and the two ranges are not a jointly calibrated total.")
    st.subheader("Historical model evaluation")
    if "live_metadata" in saved:
        st.caption("Reference 2024/2025 evaluation is unchanged. Future-month accuracy is only measurable once actual demand is recorded.")
    year = st.selectbox("Evaluation period", [2025, 2024], format_func=lambda y: f"{y} - previously inspected evaluation" if y == 2025 else "2024 - development")
    metrics = saved["metrics"]
    metrics = metrics[metrics.Method.eq("Monthly fitted Ridge") & metrics.evaluation_stage.str.startswith(str(year))].copy()
    metrics["Appointment type"] = metrics.Target.map(LABELS)
    st.caption(f"January-December {year}: 12 one-month-ahead predictions per appointment type. Errors refer to monthly demand, not an annual demand total.")
    columns = {"MAE": "MAE (requests/month)", "RMSE": "RMSE (requests/month)", "WAPE_pct": "WAPE (%)", "R_squared": "R-squared", "Bias_requests": "Bias (requests/month)"}
    st.dataframe(metrics[["Appointment type", *columns]].rename(columns=columns).round(2), hide_index=True, width="stretch")
    st.caption("Chronological one-month-ahead evaluation with monthly retraining. Negative bias means underforecasting. R-squared is not accuracy. The 2025 period is not a fresh independent test.")
    with st.expander("All metrics and prediction-band coverage"):
        st.dataframe(metrics.round(3), hide_index=True, width="stretch")
        coverage = saved["coverage"][saved["coverage"].nominal_coverage_pct.eq(level)]
        st.dataframe(coverage.round(2), hide_index=True, width="stretch")
        st.caption("Band coverage was checked across the 12 monthly predictions in 2025 per appointment type, regardless of the evaluation year selected above.")
    evaluation = saved["evaluation"]
    if year == 2025:
        target = st.selectbox("Appointment type", list(LABELS), format_func=lambda x: LABELS[x])
        frame = evaluation[evaluation.Method.eq("Monthly fitted Ridge") & evaluation.Target.eq(target)]
        frame = frame.rename(columns={"actual_requests": "Actual", "predicted_requests": "Forecast"})
        chart(px.line(frame.melt("kpi_month", value_vars=["Actual", "Forecast"], var_name="Series", value_name="Requests"),
                      x="kpi_month", y="Requests", color="Series", markers=True, labels={"Requests": "Requests per month"}))
    st.download_button("Download forecast and ranges", bands.to_csv(index=False), "practicehub_forecast_ranges.csv", "text/csv", icon=":material/download:")


def calculator(data, saved):
    month = saved["forecast"].forecast_month.iloc[0]
    st.caption(f"Monthly planning scenario: {month:%B %Y}  |  Existing GP working patterns  |  No database records are changed")
    inputs, result_column = st.columns([1, 1.65], gap="large")
    with inputs:
        st.subheader("Demand scenario")
        case = st.segmented_control("Demand", ["Point forecast", "Lower band", "Upper band"], default="Point forecast", required=True)
        level = st.selectbox("Nominal band coverage", [90, 80], disabled=case == "Point forecast", format_func=lambda x: f"{x}%")
        st.subheader("Existing capacity")
        daily_sessions = st.number_input("GP sessions per working day", min_value=1, max_value=2, value=2)
        slots = st.number_input("Slots per GP session", min_value=4, max_value=12, value=12, help="15-minute appointments in a 210-minute session; remaining time is non-slot work.")
        same = st.number_input("Same-day slots per session", min_value=1, max_value=int(slots)-1, value=min(7, int(slots)-1))
        st.caption(f"Routine slots per session: {int(slots)-int(same)}")
        blocked = st.slider("Blocked slots (%)", min_value=0.0, max_value=20.0, value=1.5, step=0.5)
        leave = []
        with st.expander("GP roster and planned leave"):
            clinicians = data["clinicians"][data["clinicians"].is_gp.eq(1)]
            st.dataframe(clinicians[["clinician_name", "fte", "working_pattern"]].rename(columns={"clinician_name": "GP", "fte": "FTE", "working_pattern": "Working days"}), hide_index=True, width="stretch")
            base = copy.deepcopy(saved["assumptions"])
            base["approved_leave"] = []
            roster, _, _, _ = capacity_plan(clinicians, base)
            for doctor in clinicians.itertuples(index=False):
                dates = roster.loc[roster.clinician_id.eq(doctor.clinician_id), "calendar_date"].dt.strftime("%Y-%m-%d").tolist()
                leave_key = f"leave_{doctor.clinician_id}"
                if leave_key in st.session_state:
                    st.session_state[leave_key] = [day for day in st.session_state[leave_key] if day in dates]
                chosen = st.multiselect(doctor.clinician_name + " leave", dates, key=leave_key,
                                        format_func=lambda d: pd.Timestamp(d).strftime("%a %d %b"))
                leave.extend({"clinician_id": int(doctor.clinician_id), "absence_date": date} for date in chosen)
        st.subheader("Additional sessions")
        extra_slots = st.number_input("Usable appointments per added session", min_value=1, max_value=12, value=12)
        keep_mix = st.toggle("Fixed appointment mix in added sessions", value=False, disabled=extra_slots == 1)
        if extra_slots == 1:
            keep_mix = False
        extra_same = st.number_input("Added-session same-day slots", min_value=1, max_value=max(1, int(extra_slots)-1), value=min(7, max(1, int(extra_slots)-1)), disabled=not keep_mix or extra_slots == 1)
        include_cost = st.toggle("Include a session cost", value=False)
        cost = st.number_input("Cost per added session (GBP)", min_value=0.0, value=0.0, step=25.0, disabled=not include_cost)
    with result_column:
        try:
            scenario = calculate_scenario(data["clinicians"], saved, int(daily_sessions), int(slots), int(same), blocked,
                                          leave, case, level, int(extra_slots), keep_mix and extra_slots > 1, int(extra_same),
                                          cost if include_cost and cost > 0 else None)
        except ValueError:
            st.error("The selected capacity assumptions are inconsistent with the saved forecast calendar.")
            return
        st.subheader("Estimated monthly shortfall")
        metric_row([
            ("Additional appointments (month)", f"{scenario['additional_appointments']:,}", f"Positive gap for {month:%B %Y} by appointment type, rounded up."),
            ("Session-equivalents (month)" if keep_mix else "Session lower bound (month)", f"{scenario['extra_sessions']:,}", "Monthly arithmetic, not a guarantee of meeting individual deadlines."),
        ])
        gaps = scenario["gaps"]
        fig = go.Figure()
        fig.add_bar(x=gaps.appointment_type, y=gaps.predicted_requests, name="Demand scenario", marker_color="#247BA0")
        fig.add_bar(x=gaps.appointment_type, y=gaps.planned_usable_slots, name="Assumed usable slots", marker_color="#C79A25")
        fig.update_yaxes(title=f"Requests / slots for {month:%B %Y}")
        chart(fig, 330)
        st.dataframe(gaps[["appointment_type", "predicted_requests", "planned_usable_slots", "additional_appointments_rounded_up"]].rename(
            columns={"appointment_type": "Type", "predicted_requests": "Demand", "planned_usable_slots": "Usable slots", "additional_appointments_rounded_up": "Additional appointments"}).round(2), hide_index=True, width="stretch")
        cost_value = "Not supplied" if scenario["cost"] is None else f"GBP {scenario['cost']:,.0f}"
        st.metric("Estimated added-session cost (month)", cost_value)
        if not leave:
            st.warning("No future leave supplied. This is a provisional no-leave roster, not confirmed staffing capacity.", icon=":material/event_busy:")
        else:
            st.caption(f"Planned leave included: {len(leave)} GP-days. Sickness and locum cover are not modelled.")
        st.caption(f"{scenario['opening_days']} opening days; {scenario['roster_sessions']} existing roster sessions. Added appointments require additional resources.")
        st.caption("Routine carry-in/carry-out and within-month timing are excluded. Flexible appointment mix is assumed unless fixed mix is selected. Band endpoints are scenarios, not a joint total-demand interval.")
        export = gaps.assign(demand_scenario=case, nominal_band_pct=level if case != "Point forecast" else np.nan,
                             extra_sessions=scenario["extra_sessions"], appointments_per_added_session=extra_slots,
                             fixed_mix=keep_mix, estimated_cost_gbp=scenario["cost"], planned_leave_gp_days=len(leave),
                             blocked_pct=blocked, synthetic_data=True)
        st.download_button("Download capacity scenario", export.to_csv(index=False), "practicehub_capacity_scenario.csv", "text/csv", icon=":material/download:")


def main():
    with st.sidebar:
        st.markdown('<div class="brand">Practice<span>HUB</span></div>', unsafe_allow_html=True)
        st.caption("GP practice management intelligence")
        page = st.radio("Workspace", PAGES, label_visibility="collapsed", key="page")
        st.divider()
        initial_source = os.environ.get("PRACTICEHUB_SOURCE", "MySQL")
        source = st.selectbox("Database", ["MySQL", "SQLite"], index=0 if initial_source == "MySQL" else 1)
        if st.button("Refresh data", icon=":material/refresh:", help="Reload database records and saved results. Does not retrain the model.", width="stretch"):
            database.clear()
            artifacts.clear()
            monthly_inputs.clear()
        st.caption("Operational tables are read-only. Monthly input saves use a separate table." if source == "MySQL" else "Read-only SQLite copy")
    try:
        with st.spinner("Loading practice records..."):
            data = database(source)
    except Exception:
        st.error(f"{source} records are unavailable or failed validation.")
        st.caption("MySQL and the local SQLite copy are separate selectable sources.")
        st.stop()
    monthly = data["monthly"]
    with st.sidebar:
        st.caption(f"{int(data['clinicians'].is_gp.sum())} GPs  |  {int(monthly.registered_patients.iloc[-1]):,} registered patients")
        st.caption(f"History: {monthly.kpi_month.min():%b %Y} - {monthly.kpi_month.max():%b %Y}")
    st.markdown('<div class="eyebrow">Practice intelligence / English GP practice</div>', unsafe_allow_html=True)
    st.markdown('<div class="mobile-brand">Practice<span>HUB</span></div>', unsafe_allow_html=True)
    st.title({"Overview": "Management overview", "Historical analysis": "Historical analysis", "Next-month forecast": "Next-month forecast", "Session calculator": "Additional-session calculator", "Monthly inputs": "Monthly forecasting inputs"}[page])
    st.caption(f"{source}  |  Historical reporting cutoff: {(monthly.kpi_month.max() + pd.offsets.MonthEnd(0)):%d %B %Y}")
    if page in ["Overview", "Historical analysis"]:
        months = monthly.kpi_month.tolist()
        with st.sidebar:
            start, end = st.select_slider("Historical period", options=months, value=(months[max(0, len(months)-12)], months[-1]), format_func=lambda d: d.strftime("%b %Y"))
        selected = date_filter(monthly, start, end)
        period_kind = "Annual totals" if start.month == 1 and end.month == 12 and start.year == end.year else "Selected-period totals"
        st.caption(f"{period_kind}: {start:%B %Y} - {end:%B %Y} ({len(selected)} months). Charts show monthly values; rates apply across the selected period.")
        overview(data, selected) if page == "Overview" else history(data, selected, start, end)
    else:
        try:
            saved = artifacts()
        except Exception:
            st.error("Saved Model 4 forecast results are unavailable or inconsistent.")
            st.stop()
        reference_matches = forecast_matches_database(data, saved)
        if page == "Monthly inputs":
            generated = render_monthly_inputs(data, saved, source, reference_matches)
            if generated is not None:
                st.divider()
                forecasts_view(generated)
            return
        if not reference_matches:
            st.warning("Saved forecasts do not match this database's current demand history or calendar. Forecast refresh is required.")
            if page == "Session calculator":
                st.stop()
        if source == "MySQL" and reference_matches:
            try:
                added = monthly_inputs()
                live = latest_live_forecast(data, added, saved)
                forecast_history, _ = prepare_history(data, added)
            except Exception:
                st.error("Monthly inputs or generated forecasts are unavailable. Refresh before using forecast results.")
                st.stop()
            if live is not None:
                saved = live
            elif not added.empty:
                st.warning(f"Completed inputs now reach {forecast_history.index.max():%B %Y}; the next-month forecast has not been generated for this updated history.")
                if page == "Session calculator":
                    st.stop()
        forecasts_view(saved) if page == "Next-month forecast" else calculator(data, saved)


main()
