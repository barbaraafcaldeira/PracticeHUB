"""Explore Model 4 features using the initial training period only."""

import argparse
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from practicehub.dashboard import read_database
from practicehub.monthly_forecasting import TARGETS, calendar_features, demand_features

OUTPUT = ROOT / "analysis_code" / "outputs" / "charts" / "forecast_correlations"
LABELS = [
    "Opening\ndays", "Bank\nholidays", "Opening\nMondays",
    "Previous month\nrequests/day", "Two months ago\nrequests/day",
    "Previous 3-month\nmean requests/day", "Winter", "Spring", "Summer",
    "Target\nrequests/day",
]


def training_correlations(history, calendar, target):
    history = history.loc[history.index < "2024-01-01", TARGETS].copy()
    calendar = calendar.loc[calendar.index < "2024-01-01"].copy()
    frame = demand_features(history, calendar, target)
    frame["target_daily_requests"] = history[target] / calendar.opening_days
    frame = frame.dropna()
    if len(frame) < 3 or not np.isfinite(frame.to_numpy()).all():
        raise ValueError("Insufficient finite training observations for correlation.")
    if frame.index.max() >= pd.Timestamp("2024-01-01"):
        raise ValueError("Evaluation data must not enter feature exploration.")
    return frame, frame.corr(method="pearson")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sqlite", action="store_true", help="Use the read-only SQLite snapshot.")
    parser.add_argument("--no-show", action="store_true")
    args = parser.parse_args()
    source = "SQLite" if args.sqlite else "MySQL"
    data = read_database(source)
    history = data["monthly"].set_index("kpi_month")[TARGETS].sort_index()
    calendar = calendar_features(data["calendar"])
    OUTPUT.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="white", font_scale=0.9)
    for target, title in zip(TARGETS, ["Same-day GP", "Routine GP"]):
        frame, corr = training_correlations(history, calendar, target)
        frame.to_csv(OUTPUT / f"{target}_training_features.csv")
        corr.to_csv(OUTPUT / f"{target}_correlations.csv")
        fig, ax = plt.subplots(figsize=(12, 10))
        sns.heatmap(
            corr, ax=ax, annot=True, fmt=".2f", cmap="vlag", center=0,
            vmin=-1, vmax=1, square=True, linewidths=0.6, linecolor="white",
            xticklabels=LABELS, yticklabels=LABELS,
            cbar_kws={"label": "Pearson correlation (r)", "shrink": 0.8},
            annot_kws={"fontsize": 9},
        )
        ax.set_title(f"{title}: Forecast Feature Correlations\nInitial Training Period Only", pad=18)
        ax.tick_params(axis="x", labelrotation=45)
        ax.tick_params(axis="y", labelrotation=0)
        plt.setp(ax.get_xticklabels(), ha="right", rotation_mode="anchor")
        fig.tight_layout(rect=(0, 0.1, 1, 1))
        fig.text(
            0.04, 0.025,
            f"Synthetic data. April-December 2023; n={len(frame)} months after lag creation. "
            "2024-2025 excluded.\nTarget: requests per opening day. Autumn is the reference season. "
            "Small-sample correlations are exploratory, not feature-selection proof.",
            fontsize=9, color="#4B5563",
        )
        path = OUTPUT / f"{target}_heatmap.png"
        fig.savefig(path, dpi=300, bbox_inches="tight")
        print(f"{title}: {len(frame)} training observations; saved {path}")
        print(corr["target_daily_requests"].round(3).to_string())
    if not args.no_show:
        plt.show()
    plt.close("all")


if __name__ == "__main__":
    main()
