"""Plot saved Model 4 evaluation predictions without retraining."""

import argparse
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.ticker import StrMethodFormatter
import numpy as np
import pandas as pd
import seaborn as sns

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "analysis_code/outputs/RESULTS_MODEL4/2025_walk_forward_predictions.csv"
OUTPUT = ROOT / "analysis_code/outputs/charts/forecast_evaluation"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-show", action="store_true")
    args = parser.parse_args()
    saved = pd.read_csv(SOURCE, parse_dates=["kpi_month", "forecast_origin"])
    selected = saved.loc[saved.Method.eq("Monthly fitted Ridge")].copy()
    sns.set_theme(style="whitegrid", font_scale=1.05)
    fig, axes = plt.subplots(2, 1, figsize=(11, 8), sharex=True)
    for ax, target, title in zip(
        axes, ["same_day_gp_requests", "routine_gp_requests"],
        ["Same-day GP requests", "Routine GP requests"],
    ):
        group = selected.loc[selected.Target.eq(target)].sort_values("kpi_month")
        expected = pd.date_range("2025-01-01", "2025-12-01", freq="MS")
        if not pd.DatetimeIndex(group.kpi_month).equals(expected):
            raise ValueError(f"Expected exactly 12 consecutive 2025 predictions for {target}.")
        if not np.isfinite(group[["actual_requests", "predicted_requests"]].to_numpy()).all():
            raise ValueError("Predictions and actual observations must be finite.")
        if not group.forecast_origin.lt(group.kpi_month).all():
            raise ValueError("Forecast origins must precede predicted months.")
        ax.plot(group.kpi_month, group.actual_requests, color="#087F6D",
                marker="o", markersize=5, linewidth=2, label="Actual requests")
        ax.plot(group.kpi_month, group.predicted_requests, color="#B45A32",
                marker="s", markersize=4, linewidth=2, linestyle="--",
                label="Predicted requests")
        ax.set_title(title, loc="left", fontsize=12, fontweight="bold")
        ax.set_ylabel("Requests per month")
        ax.set_ylim(0, group[["actual_requests", "predicted_requests"]].max().max() * 1.14)
        ax.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
        ax.legend(loc="upper right", frameon=False, ncol=2, fontsize=10)
        ax.grid(axis="x", visible=False)
    axes[-1].xaxis.set_major_locator(mdates.MonthLocator())
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    axes[-1].set_xlabel("Forecast month (2025)")
    fig.suptitle("Actual versus Predicted Monthly GP Demand", fontsize=16, y=0.98)
    fig.tight_layout(rect=(0, 0.10, 1, 0.95), h_pad=2)
    fig.text(0.07, 0.025,
             "Synthetic data. Saved Model 4 rolling one-month-ahead forecasts; 12 months per appointment type.\n"
             "2025 was previously inspected and is not an untouched final test. Panel scales differ.",
             fontsize=9, color="#4B5563")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / "2025_actual_vs_predicted.png"
    fig.savefig(path, dpi=300, bbox_inches="tight")
    print(f"Saved {path}. Existing model results unchanged.")
    if not args.no_show:
        plt.show()
    plt.close(fig)


if __name__ == "__main__":
    main()
