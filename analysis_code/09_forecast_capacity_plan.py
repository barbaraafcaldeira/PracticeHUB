"""Compare Model 4's next-month forecast with an explicit five-GP roster scenario."""

from pathlib import Path
import contextlib
import hashlib
import io
import json
import math
import runpy
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from practicehub.forecast_capacity import appointment_gap, capacity_plan


def main():
    assumptions_path = ROOT / "config" / "model4_capacity_assumptions.json"
    assumptions = json.loads(assumptions_path.read_text())
    forecast_path = ROOT / "analysis_code" / "outputs" / "RESULTS_MODEL4" / "next_month_forecast.csv"
    forecasts = pd.read_csv(forecast_path)
    if set(forecasts.forecast_month) != {assumptions["forecast_month"]}:
        raise ValueError("Forecast and capacity-assumption months do not match.")
    with contextlib.redirect_stdout(io.StringIO()):
        connection = runpy.run_path(str(Path(__file__).with_name("01_connect_to_mysql.py")))
    engine = connection["engine"]
    try:
        clinicians = pd.read_sql(
            "SELECT clinician_id,working_pattern,usual_session_minutes,is_gp,active_from,active_to "
            "FROM clinicians ORDER BY clinician_id", engine)
    finally:
        engine.dispose()
    daily, capacity, opening_days, sessions = capacity_plan(clinicians, assumptions)
    if not forecasts.opening_days.eq(opening_days).all():
        raise ValueError("Capacity calendar differs from the calendar used in Model 4's forecast.")
    gaps = appointment_gap(forecasts, capacity)
    total_gap = int(gaps.additional_appointments_rounded_up.sum())
    flexible_equivalent = math.ceil(total_gap / assumptions["slots_per_session"])
    same_gap = int(gaps.loc[gaps.appointment_type.eq("Same-day GP"), "additional_appointments_rounded_up"].item())
    routine_gap = int(gaps.loc[gaps.appointment_type.eq("Routine GP"), "additional_appointments_rounded_up"].item())
    fixed_mix_sessions = max(
        math.ceil(same_gap / assumptions["same_day_slots_per_session"]),
        math.ceil(routine_gap / assumptions["routine_slots_per_session"]),
    )
    notes = {
        "synthetic_data": True, "forecast_month": assumptions["forecast_month"],
        "opening_days": opening_days, "existing_roster_sessions": sessions,
        "additional_appointments": total_gap,
        "flexible_mix_session_equivalents_lower_bound": flexible_equivalent,
        "fixed_7_same_day_5_routine_session_equivalents": fixed_mix_sessions,
        "forecast_sha256": hashlib.sha256(forecast_path.read_bytes()).hexdigest(),
        "assumptions": assumptions,
        "limitations": [
            "No future leave supplied: existing roster is a provisional no-leave upper scenario, not confirmed capacity",
            "Blocked-slot count is an assumption, not an observed future count",
            "Flexible session equivalents require tailoring the appointment mix, not keeping a seven/five split",
            "Extra sessions assume twelve usable slots; extra clinician and room resources have not been established",
            "Monthly request intake and scheduled slots are not identical cohorts, especially for routine requests",
            "No carry-in backlog, routine carry-out, within-month timing or patient-level allocation is modelled",
            "This is a point-forecast planning estimate, not proof these sessions meet every request deadline",
            "No uncertainty interval, session cost or optimal purchasing decision is provided",
            "January 2026 follows the historical dataset cutoff; this is not the current live practice position",
        ],
    }
    output = ROOT / "analysis_code" / "outputs" / "RESULTS_MODEL4_CAPACITY"
    output.mkdir(parents=True, exist_ok=True)
    daily.to_csv(output / "planned_gp_roster.csv", index=False)
    capacity.to_csv(output / "planned_slot_capacity.csv", index=False)
    gaps.to_csv(output / "forecast_vs_capacity.csv", index=False)
    (output / "capacity_assumptions_and_estimates.json").write_text(json.dumps(notes, indent=2) + "\n")
    report = [
        "# Next-Month Forecast and Capacity Scenario", "", "All practice data and forecasts are synthetic.", "",
        f"Forecast month: {pd.Timestamp(assumptions['forecast_month']):%B %Y}.",
        f"Same five GP working patterns: {opening_days} opening days and {sessions} rostered sessions before future leave.",
        "No future leave was supplied. This is an optimistic roster scenario, not a confirmed staffing plan.", "",
        "| Appointment type | Forecast requests | Assumed usable slots | Additional appointments, rounded up |",
        "|---|---:|---:|---:|",
    ]
    for row in gaps.itertuples(index=False):
        report.append(f"| {row.appointment_type} | {row.predicted_requests:,.2f} | "
                      f"{row.planned_usable_slots:,} | {row.additional_appointments_rounded_up:,} |")
    report += ["", f"Total positive gap by type: **{total_gap:,} appointments**.",
               f"With a flexible appointment mix, this equals at least **{flexible_equivalent:,} extra 12-slot session-equivalents** over the month.",
               f"Keeping a seven same-day/five routine split requires **{fixed_mix_sessions:,} session-equivalents** in this monthly arithmetic scenario.",
               "These are capacity equivalents, not an optimal staffing recommendation or a guarantee of access.",
               "", "## Assumptions and Limitations", ""]
    report += [f"- {note}." for note in notes["limitations"]]
    report += ["", "Holiday date source: [GOV.UK bank holidays](https://www.gov.uk/bank-holidays).", ""]
    (output / "forecast_capacity_summary.md").write_text("\n".join(report), encoding="utf-8")
    x = np.arange(len(gaps))
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(x - .2, gaps.predicted_requests, width=.4, label="Forecast GP requests", color="#087eaa")
    ax.bar_label(bars, fmt="%.0f", padding=4)
    bars = ax.bar(x + .2, gaps.planned_usable_slots, width=.4, label="Assumed usable capacity", color="#d79b00")
    ax.bar_label(bars, fmt="%.0f", padding=4)
    ax.set_xticks(x, gaps.appointment_type)
    ax.set_ylabel("Requests / appointment slots")
    ax.set_title(f"{pd.Timestamp(assumptions['forecast_month']):%B %Y}: forecast and capacity\nSynthetic PracticeHUB planning scenario")
    ax.set_ylim(0, max(gaps.predicted_requests.max(), gaps.planned_usable_slots.max()) * 1.25)
    ax.legend()
    ax.grid(axis="y", alpha=.2)
    ax.set_axisbelow(True)
    fig.text(.02, .02, "No future leave supplied; 1.5% blocking assumed. Monthly comparison, not a deadline-level guarantee.", fontsize=9)
    fig.tight_layout(rect=[0, .07, 1, 1])
    fig.savefig(output / "next_month_demand_vs_capacity.png", dpi=160)
    plt.close(fig)
    print("SYNTHETIC NEXT-MONTH CAPACITY SCENARIO")
    print(gaps.round(2).to_string(index=False))
    print(f"Flexible-mix session-equivalent lower bound: {flexible_equivalent}")
    print(f"Fixed seven/five split session-equivalents: {fixed_mix_sessions}")
    print("No future leave supplied: provisional scenario only. No database changes made.")
    print("Saved to:", output)


if __name__ == "__main__":
    main()
