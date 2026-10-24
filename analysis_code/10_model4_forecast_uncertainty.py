"""Add empirical prediction bands without changing Model 4's saved point forecasts."""

from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from practicehub.forecast_uncertainty import LEVELS, MIN_CALIBRATION, coverage_summary, future_bands, sequential_bands
from practicehub.monthly_forecasting import TARGETS


def main():
    source = ROOT / "analysis_code" / "outputs" / "RESULTS_MODEL4"
    names = ["2024_walk_forward_predictions.csv", "2025_walk_forward_predictions.csv",
             "next_month_forecast.csv", "model_input_snapshot.csv"]
    fingerprints = {name: hashlib.sha256((source / name).read_bytes()).hexdigest() for name in names}
    frames = [pd.read_csv(source / name, parse_dates=["kpi_month", "forecast_origin", "training_end"])
              for name in names[:2]]
    predictions = pd.concat(frames, ignore_index=True)
    predictions = predictions[predictions.Method.eq("Monthly fitted Ridge")].copy()
    if set(predictions.Target) != set(TARGETS):
        raise ValueError("Expected both fitted Model 4 appointment types.")
    for target, group in predictions.groupby("Target"):
        dates = pd.DatetimeIndex(group.kpi_month.sort_values())
        if not dates.equals(pd.date_range("2024-01-01", "2025-12-01", freq="MS")):
            raise ValueError(f"Expected consecutive 2024-2025 calibration/evaluation predictions for {target}.")
    if (not predictions.horizon_months.eq(1).all()
            or not predictions.training_end.lt(predictions.kpi_month).all()
            or not predictions.forecast_origin.eq(predictions.kpi_month - pd.Timedelta(days=1)).all()):
        raise ValueError("Saved predictions do not follow the one-month historical-only protocol.")
    inputs = pd.read_csv(source / "model_input_snapshot.csv", parse_dates=["kpi_month"]).set_index("kpi_month")
    for target, group in predictions.groupby("Target"):
        expected = inputs.reindex(group.kpi_month)
        if (not np.allclose(group.actual_requests, expected[target])
                or not np.allclose(group.opening_days, expected.opening_days)):
            raise ValueError("Prediction actuals/calendar do not match Model 4's input snapshot.")
    next_forecast = pd.read_csv(source / "next_month_forecast.csv", parse_dates=["forecast_month", "training_end"])
    if not next_forecast.training_end.lt(next_forecast.forecast_month).all():
        raise ValueError("Next-month forecast training extends into its forecast period.")

    bands = sequential_bands(predictions, "2025-01-01")
    summary = coverage_summary(bands)
    upcoming = future_bands(predictions, next_forecast)
    output = ROOT / "analysis_code" / "outputs" / "RESULTS_MODEL4_UNCERTAINTY"
    output.mkdir(parents=True, exist_ok=True)
    bands.to_csv(output / "2025_sequential_prediction_bands.csv", index=False)
    summary.to_csv(output / "2025_observed_coverage.csv", index=False)
    upcoming.to_csv(output / "next_month_prediction_bands.csv", index=False)
    calibration = predictions[["kpi_month", "Target", "actual_requests", "predicted_requests", "opening_days"]].copy()
    calibration["absolute_daily_error"] = (calibration.actual_requests - calibration.predicted_requests).abs() / calibration.opening_days
    calibration.to_csv(output / "historical_calibration_errors.csv", index=False)

    # Carry the demand range into the existing provisional capacity scenario, if available.
    capacity_path = ROOT / "analysis_code" / "outputs" / "RESULTS_MODEL4_CAPACITY" / "forecast_vs_capacity.csv"
    assumptions_path = ROOT / "analysis_code" / "outputs" / "RESULTS_MODEL4_CAPACITY" / "capacity_assumptions_and_estimates.json"
    capacity_ranges = None
    if capacity_path.exists() and assumptions_path.exists():
        capacity = pd.read_csv(capacity_path, parse_dates=["forecast_month"])
        evidence = json.loads(assumptions_path.read_text())
        if evidence["forecast_sha256"] != fingerprints["next_month_forecast.csv"]:
            raise ValueError("Capacity estimate uses an older forecast: rerun 09_forecast_capacity_plan.py.")
        types = {TARGETS[0]: "Same-day GP", TARGETS[1]: "Routine GP"}
        capacity_ranges = upcoming.assign(appointment_type=upcoming.Target.map(types)).merge(
            capacity[["forecast_month", "appointment_type", "planned_usable_slots"]],
            on=["forecast_month", "appointment_type"], validate="many_to_one")
        if len(capacity_ranges) != len(upcoming):
            raise ValueError("Capacity and uncertainty months/types do not reconcile.")
        for name, column in [("lower", "lower_requests"), ("point", "point_forecast"), ("upper", "upper_requests")]:
            capacity_ranges[f"{name}_additional_appointments"] = np.ceil(
                (capacity_ranges[column] - capacity_ranges.planned_usable_slots).clip(lower=0)).astype(int)
        capacity_ranges.to_csv(output / "provisional_capacity_gap_ranges.csv", index=False)

    limitations = [
        "Empirical, conformal-style prediction bands, not confidence intervals for an average",
        "Temporal dependence and refitted models mean no formal exchangeable split-conformal coverage guarantee is claimed",
        "Coverage percentages are nominal targets, not forecast accuracy or promises for a particular month",
        "Only 12 historical months evaluate each band; one month changes coverage by 8.33 percentage points",
        "2025 was previously inspected; this is exploratory sequential calibration/evaluation, not a fresh independent test",
        "24 completed errors calibrate January 2026; no independent season-specific calibration is possible at this size",
        "Bands are separate for each appointment type, not a joint simultaneous interval for total demand",
        "Summing type-specific endpoints gives scenarios, not a calibrated combined coverage level",
        "Normalising errors by opening days assumes error size scales approximately with the opening calendar",
        "January 2026 follows the dataset cutoff; it is not the next month relative to today's date",
        "Any capacity gaps retain the earlier no-future-leave and blocked-slot assumptions, not staffing guarantees",
    ]
    notes = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(), "synthetic_data": True,
        "point_model_changed": False, "source_files_sha256": fingerprints,
        "nominal_coverage_levels": list(LEVELS), "minimum_calibration_errors": MIN_CALIBRATION,
        "calibration_score": "abs(actual - prediction) / opening_days, using completed one-month-ahead forecast errors",
        "quantile_rule": "Sorted absolute daily errors at rank ceil((n+1)*coverage), one-based; reject rank > n",
        "interval_rule": "point +/- daily-error quantile * target opening days; lower floored at zero; integer endpoints rounded outward",
        "sequential_protocol": "Build interval from earlier errors, evaluate current month, then append its error",
        "next_month_protocol": "Use completed January 2024-December 2025 forecast errors, separately for each target",
        "references": ["https://arxiv.org/abs/2106.00170",
                       "https://scikit-learn.org/stable/auto_examples/applications/plot_time_series_lagged_features.html"],
        "limitations": limitations,
    }
    (output / "uncertainty_method.json").write_text(json.dumps(notes, indent=2) + "\n", encoding="utf-8")
    report = ["# Model 4 Forecast Uncertainty", "", "All data and forecasts are synthetic. Model 4's point predictions are unchanged.",
              "", "## Next-Month Demand Ranges", "",
              "| Target | Point forecast | Nominal coverage target | Lower requests | Upper requests | Earlier errors used |",
              "|---|---:|---:|---:|---:|---:|"]
    labels = {TARGETS[0]: "Same-day GP", TARGETS[1]: "Routine GP"}
    for row in upcoming.itertuples(index=False):
        report.append(f"| {labels[row.Target]} | {row.point_forecast:,.2f} | {row.nominal_coverage_pct:.0f}% | "
                      f"{row.lower_requests:,} | {row.upper_requests:,} | {row.calibration_observations} |")
    report += ["", "## Actual Sequential Coverage in 2025", "",
               "These bands were formed using earlier errors only; the current month's actual was not used to construct its band.", "",
               "| Target | Nominal target | Months covered | Observed coverage | Mean interval width |",
               "|---|---:|---:|---:|---:|"]
    for row in summary.itertuples(index=False):
        report.append(f"| {labels[row.Target]} | {row.nominal_coverage_pct:.0f}% | "
                      f"{row.covered_months}/{row.evaluated_months} | {row.observed_coverage_pct:.1f}% | {row.average_band_width_requests:,.1f} |")
    report += ["", "## Interpretation", "",
               "A prediction band describes a plausible range for a future observed count based on historical forecast errors. "
               "It is not an accuracy score, a guarantee, or evidence that an upper-end staffing purchase is optimal.",
               "", "## Limitations", ""]
    report += [f"- {item}." for item in limitations]
    report += ["", "## References", "",
               "- [Adaptive Conformal Inference Under Distribution Shift](https://arxiv.org/abs/2106.00170). "
               "This motivates caution about distribution changes; the script does not implement adaptive conformal inference.",
               "- [Scikit-learn time-series forecasting and uncertainty example](https://scikit-learn.org/stable/auto_examples/applications/plot_time_series_lagged_features.html).", ""]
    (output / "uncertainty_summary.md").write_text("\n".join(report), encoding="utf-8")

    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    for ax, target in zip(axes, TARGETS):
        subset = bands[bands.Target.eq(target)].sort_values("kpi_month")
        for level, color, alpha in [(90, "#168aad", .15), (80, "#168aad", .28)]:
            selected = subset[subset.nominal_coverage_pct.eq(level)]
            ax.fill_between(selected.kpi_month, selected.lower_requests, selected.upper_requests,
                            color=color, alpha=alpha, label=f"Nominal {level}% empirical band")
        selected = subset[subset.nominal_coverage_pct.eq(80)]
        ax.plot(selected.kpi_month, selected.actual_requests, marker="o", color="#252525", label="Actual requests")
        ax.plot(selected.kpi_month, selected.point_forecast, linestyle="--", color="#d97706", label="Model 4 point forecast")
        ax.set_title(labels[target])
        ax.set_ylabel("Requests")
        ax.set_ylim(bottom=0)
        ax.legend(fontsize=8, ncol=2)
        ax.grid(alpha=.2)
    axes[-1].xaxis.set_major_locator(mdates.MonthLocator())
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    axes[-1].set_xlabel("2025 - previously inspected sequential evaluation")
    fig.suptitle("Prediction ranges based on earlier forecast errors - Synthetic PracticeHUB data")
    fig.tight_layout(rect=[0, 0, 1, .95])
    fig.savefig(output / "2025_prediction_bands.png", dpi=160)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(11, 5))
    for position, target in enumerate(TARGETS):
        selected = upcoming[upcoming.Target.eq(target)]
        for level, color, width in [(90, "#8ac6d1", 5), (80, "#087eaa", 10)]:
            band = selected[selected.nominal_coverage_pct.eq(level)].iloc[0]
            ax.hlines(position, band.lower_requests, band.upper_requests,
                      color=color, linewidth=width,
                      label=f"Nominal {level}% empirical band" if position == 0 else None)
            if level == 90:
                ax.text(band.lower_requests, position + .17, f"{band.lower_requests:,.0f}", ha="center", fontsize=9)
                ax.text(band.upper_requests, position + .17, f"{band.upper_requests:,.0f}", ha="center", fontsize=9)
        point = selected.point_forecast.iloc[0]
        ax.plot(point, position, "o", color="#252525", markersize=7,
                label="Unchanged point forecast" if position == 0 else None)
        ax.text(point, position - .2, f"Point: {point:,.0f}", ha="center", fontsize=9)
    ax.set_yticks(range(len(TARGETS)), [labels[target] for target in TARGETS])
    ax.set_ylim(-.55, 1.55)
    ax.set_xlim(left=0)
    ax.set_xlabel("GP appointment requests")
    month_label = upcoming.forecast_month.iloc[0].strftime("%B %Y")
    ax.set_title(f"{month_label}: forecast and empirical prediction ranges\nSynthetic PracticeHUB data")
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(axis="x", alpha=.2)
    ax.set_axisbelow(True)
    fig.text(.02, .015, "Coverage targets are not guarantees. Separate bands by appointment type; no joint total-demand coverage claim.", fontsize=8)
    fig.tight_layout(rect=[0, .06, 1, 1])
    fig.savefig(output / "next_month_prediction_ranges.png", dpi=160)
    plt.close(fig)
    # Ensure no previous experiment outputs were changed by this analysis.
    for name, digest in fingerprints.items():
        if hashlib.sha256((source / name).read_bytes()).hexdigest() != digest:
            raise RuntimeError("A source file changed during the uncertainty analysis; rerun for consistency.")
    print("MODEL 4 - EMPIRICAL FORECAST UNCERTAINTY - SYNTHETIC DATA")
    print("\n2025 observed coverage (not accuracy):")
    print(summary.round(2).to_string(index=False))
    print("\nNext-month bands:")
    print(upcoming[["forecast_month", "Target", "point_forecast", "nominal_coverage_pct", "lower_requests", "upper_requests"]].to_string(index=False))
    print("\nPoint forecasts and previous files unchanged. Results saved to:", output)


if __name__ == "__main__":
    main()
