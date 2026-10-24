"""Fit both GP request types and forecast the next month, updating monthly.

New experiment: one-month-ahead, not the fixed-origin annual Model 1/2 task.
Reads MySQL without modifying it; saves only into RESULTS_MODEL4.
"""

from pathlib import Path
import contextlib
from datetime import datetime, timezone
import hashlib
import io
import json
import runpy
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from practicehub.monthly_forecasting import ALPHA, TARGETS, calendar_features, evaluate, predict_month, walk_forward


def main():
    with contextlib.redirect_stdout(io.StringIO()):
        connection = runpy.run_path(str(Path(__file__).with_name("01_connect_to_mysql.py")))
    engine = connection["engine"]
    try:
        with engine.connect().execution_options(isolation_level="REPEATABLE READ") as db:
            with db.begin():
                monthly = pd.read_sql(
                    "SELECT kpi_month,same_day_gp_requests,routine_gp_requests "
                    "FROM monthly_kpis ORDER BY kpi_month", db)
                daily_calendar = pd.read_sql(
                    "SELECT calendar_date,is_open,closure_reason FROM practice_calendar ORDER BY calendar_date", db)
    finally:
        engine.dispose()
    monthly["kpi_month"] = pd.to_datetime(monthly.kpi_month)
    monthly = monthly.set_index("kpi_month").sort_index()
    expected = pd.date_range(monthly.index.min(), monthly.index.max(), freq="MS")
    if not monthly.index.equals(expected) or len(monthly) < 24:
        raise ValueError("Need at least 24 consecutive completed monthly observations.")
    if not np.isfinite(monthly.to_numpy()).all() or monthly.lt(0).any().any():
        raise ValueError("Demand values must be complete, finite and non-negative.")
    calendar = calendar_features(daily_calendar)
    if not monthly.index.isin(calendar.index).all():
        raise ValueError("Missing historical calendar months.")

    # Fixed alpha and feature set; no search for favourable 2025 results.
    validation_months = monthly.loc["2024"].index
    evaluation_months = monthly.loc["2025"].index
    validation = walk_forward(monthly, calendar, validation_months)
    evaluation = walk_forward(monthly, calendar, evaluation_months)
    validation["evaluation_stage"] = "2024 monthly walk-forward development"
    evaluation["evaluation_stage"] = "2025 previously inspected monthly walk-forward evaluation"
    validation_metrics, evaluation_metrics = evaluate(validation), evaluate(evaluation)
    validation_metrics["evaluation_stage"] = "2024 monthly walk-forward development"
    evaluation_metrics["evaluation_stage"] = "2025 previously inspected monthly walk-forward evaluation"

    next_month = monthly.index.max() + pd.offsets.MonthBegin(1)
    plan_path = ROOT / "config" / "model4_next_month_calendar.csv"
    plan = pd.read_csv(plan_path, parse_dates=["kpi_month"]).set_index("kpi_month")
    if plan.index.duplicated().any() or next_month not in plan.index:
        raise ValueError(f"Update {plan_path.name} with the planned calendar for {next_month:%B %Y}.")
    planned = plan.loc[[next_month], ["opening_days", "bank_holidays", "opening_mondays"]]
    if not np.isfinite(planned.to_numpy()).all() or (planned.to_numpy() % 1 != 0).any():
        raise ValueError("Planned calendar counts must be finite integers.")
    if (planned.opening_days.le(0).any() or planned.opening_days.gt(next_month.days_in_month).any()
            or planned.bank_holidays.lt(0).any() or planned.bank_holidays.gt(next_month.days_in_month).any()
            or planned.opening_mondays.lt(0).any() or planned.opening_mondays.gt(5).any()
            or planned.opening_mondays.gt(planned.opening_days).any()):
        raise ValueError("Invalid planned opening-day, holiday or Monday counts.")
    extended_calendar = pd.concat([calendar.loc[calendar.index <= monthly.index.max()], planned])
    forecasts = []
    for target in TARGETS:
        predicted, evidence = predict_month(monthly, extended_calendar, next_month, target)
        forecasts.append({
            "forecast_month": next_month, "Target": target, "Method": "Monthly fitted Ridge",
            "forecast_origin": next_month - pd.Timedelta(days=1), "horizon_months": 1,
            "predicted_requests": predicted, **evidence,
        })
    forecasts = pd.DataFrame(forecasts)

    output = Path(__file__).resolve().parent / "outputs" / "RESULTS_MODEL4"
    output.mkdir(parents=True, exist_ok=True)
    metrics = pd.concat([validation_metrics, evaluation_metrics], ignore_index=True)
    metrics.to_csv(output / "RESULTS_MODEL4.csv", index=False)
    validation.to_csv(output / "2024_walk_forward_predictions.csv", index=False)
    evaluation.to_csv(output / "2025_walk_forward_predictions.csv", index=False)
    forecasts.to_csv(output / "next_month_forecast.csv", index=False)
    snapshot = monthly.join(calendar)
    snapshot.to_csv(output / "model_input_snapshot.csv", index_label="kpi_month")
    planned.to_csv(output / "next_month_calendar_snapshot.csv", index_label="kpi_month")
    feature_example = {key: value for key, value in forecasts.iloc[0].to_dict().items()
                       if key in ["opening_days", "bank_holidays", "opening_mondays", "winter", "spring", "summer",
                                  "previous_month_daily_requests", "two_months_ago_daily_requests", "previous_three_month_daily_mean"]}
    metadata = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(), "synthetic_data": True,
        "protocol": "Expanding-window one-month-ahead; refit after each newly completed month",
        "method": "StandardScaler fitted on training rows only, then Ridge", "ridge_alpha": ALPHA,
        "features": list(feature_example), "season_reference": "Autumn",
        "training_target": "Recorded clinically indicated requests per opening day, separately for each appointment type",
        "monthly_output": "Predicted daily rate multiplied by the target month's planned opening days",
        "input_sha256": hashlib.sha256(snapshot.to_csv().encode()).hexdigest(),
        "next_month_calendar": planned.reset_index().astype(str).to_dict("records"),
        "calendar_source": "https://www.gov.uk/bank-holidays",
        "calendar_assumption": "Monday-Friday practice; closed on England bank holidays; no unexpected closures",
        "limitations": [
            "Only 36 original monthly observations; seasonal effects learned from few annual cycles",
            "2025 has already been inspected during earlier experiments: not a fresh independent test",
            "New one-month horizon: do not compare directly with fixed-origin annual Model 1/2 scores",
            "Calendar is treated as known ahead; past target-period demand is never used in its own forecast",
            "Latest observed month must be complete; do not add partial monthly KPI rows",
            "January 2026 is next after the historical data cutoff, not the current real-world next month",
            "No prediction intervals, appointment-capacity recommendations or session costs generated",
            "Within +/-10% is an illustrative tolerance, not classification accuracy or an NHS standard",
        ],
    }
    (output / "run_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    for ax, target in zip(axes, TARGETS):
        subset = evaluation[evaluation.Target.eq(target) & evaluation.Method.eq("Monthly fitted Ridge")]
        ax.plot(subset.kpi_month, subset.actual_requests, marker="o", label="Actual requests")
        ax.plot(subset.kpi_month, subset.predicted_requests, marker="o", linestyle="--", label="One-month-ahead Ridge")
        ax.set_title("Same-day GP requests" if target == TARGETS[0] else "Routine GP requests")
        ax.set_ylabel("Requests")
        ax.set_ylim(bottom=0)
        ax.grid(alpha=.25)
        ax.legend()
    axes[-1].xaxis.set_major_locator(mdates.MonthLocator())
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    axes[-1].set_xlabel("2025 - previously inspected evaluation period")
    fig.suptitle("Monthly-updating machine-learning forecasts - Synthetic PracticeHUB data")
    fig.tight_layout(rect=[0, 0, 1, .95])
    fig.savefig(output / "2025_actual_vs_predicted.png", dpi=160)
    plt.close(fig)
    print("MODEL 4 - SYNTHETIC DATA - ONE-MONTH-AHEAD")
    print("\n2024 expanding-window development:")
    print(validation_metrics.round(2).to_string(index=False))
    print("\n2025 previously inspected expanding-window evaluation:")
    print(evaluation_metrics.round(2).to_string(index=False))
    print(f"\nForecast for {next_month:%B %Y}, immediately after the dataset cutoff:")
    print(forecasts[["Target", "predicted_requests"]].round(2).to_string(index=False))
    print("\nResults saved to:", output)
    print("Original scripts, prior results and database records are unchanged.")


if __name__ == "__main__":
    main()
