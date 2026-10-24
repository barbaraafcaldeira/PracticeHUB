"""Allocation decisions and access-complaint figures from read-only practice data."""

import argparse
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from practicehub.dashboard import read_database

OUTPUT = ROOT / "analysis_code" / "outputs" / "charts" / "allocation_access"
OUTCOMES = {
    "internal": "Allocated internally",
    "appropriate": "Clinically appropriate signposting",
    "capacity": "Capacity-related signposting",
}


def prepare_outcomes(data):
    routing = data["routing"].copy()
    if not routing[list(OUTCOMES) + ["pending"]].sum(axis=1).eq(routing.received).all():
        raise ValueError("Allocation outcomes do not reconcile with received requests.")
    annual = routing.groupby(routing.kpi_month.dt.year)[
        ["received", *OUTCOMES, "pending"]
    ].sum()
    annual.index.name = "year"
    annual["decided_requests"] = annual[list(OUTCOMES)].sum(axis=1)
    if annual.decided_requests.le(0).any():
        raise ValueError("An annual comparison requires decided requests.")
    for name in OUTCOMES:
        annual[name + "_pct"] = 100 * annual[name] / annual.decided_requests
    annual["access_complaints"] = data["monthly"].groupby(
        data["monthly"].kpi_month.dt.year
    ).access_complaints.sum()
    return annual


def create_charts(data, annual, output):
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    import seaborn as sns

    sns.set_theme(style="whitegrid", font_scale=1.05)
    output.mkdir(parents=True, exist_ok=True)

    # Exclude pending requests from the decision mix, with an explicit disclosure.
    fig, ax = plt.subplots(figsize=(12, 5.5))
    y = np.arange(len(annual))
    left = np.zeros(len(annual))
    for (key, label), color in zip(OUTCOMES.items(), ["#087F6D", "#247BA0", "#C44C44"]):
        percentages = annual[key + "_pct"].to_numpy()
        ax.barh(y, percentages, left=left, color=color, height=0.56, label=label)
        for i, (percentage, count) in enumerate(zip(percentages, annual[key])):
            ax.text(left[i] + percentage / 2, i, f"{percentage:.1f}%\n{count:,.0f}",
                    ha="center", va="center", color="white", fontsize=11, fontweight="bold")
        left += percentages
    ax.set_yticks(y, [f"{year}\n({int(row.decided_requests):,} decisions)"
                     for year, row in annual.iterrows()])
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("Share of requests with a recorded decision (%)")
    ax.grid(axis="y", visible=False)
    fig.suptitle("Annual Appointment-Request Allocation Outcomes", fontsize=16, y=0.99)
    fig.legend(*ax.get_legend_handles_labels(), loc="upper center", ncol=3,
               bbox_to_anchor=(0.5, 0.925), frameon=False, fontsize=10)
    fig.tight_layout(rect=(0, 0.14, 1, 0.85))
    pending = "; ".join(f"{year}: {int(row.pending):,}" for year, row in annual.iterrows())
    fig.text(0.045, 0.045,
             "Synthetic data. All intake routes combined. Counts are request episodes, not unique patients.\n"
             f"Pending requests excluded from the decision percentages ({pending}). Signposting does not confirm external care.",
             fontsize=9, color="#53655F")
    fig.savefig(output / "01_annual_allocation_outcomes.png", dpi=300, bbox_inches="tight")

    # A separate count scale avoids implying that complaints equal unmet requests.
    monthly = data["monthly"].sort_values("kpi_month")
    fig, ax = plt.subplots(figsize=(12, 4.8))
    ax.plot(monthly.kpi_month, monthly.access_complaints, color="#9B4657", linewidth=2.3)
    ax.fill_between(monthly.kpi_month, 0, monthly.access_complaints, color="#9B4657", alpha=0.10)
    ax.set(title="Monthly Appointment-Access Complaints", xlabel="Month",
           ylabel="Complaints received per month", ylim=(0, monthly.access_complaints.max() * 1.2))
    ax.set_xlim(monthly.kpi_month.min(), monthly.kpi_month.max())
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10]))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
    peak = monthly.loc[monthly.access_complaints.idxmax()]
    ax.annotate(f"{int(peak.access_complaints)} complaints\n{peak.kpi_month:%b %Y}",
                (peak.kpi_month, peak.access_complaints), xytext=(12, 8),
                textcoords="offset points", fontsize=10)
    ax.grid(axis="x", visible=False)
    fig.tight_layout(rect=(0, 0.13, 1, 1))
    fig.text(0.055, 0.025,
             "Synthetic data. Complaints are indirect access-pressure indicators, not additional GP requests or proof of causation.",
             fontsize=9, color="#53655F")
    fig.savefig(output / "02_monthly_access_complaints.png", dpi=300, bbox_inches="tight")

    causes = data["complaint_causes"].groupby("complaint_trigger").complaints.sum().sort_values()
    fig, ax = plt.subplots(figsize=(11, 4.6))
    ax.barh(causes.index, causes.values, color="#247BA0", height=0.55)
    for i, count in enumerate(causes):
        ax.text(count + causes.max() * 0.02, i, f"{count:,} ({100 * count / causes.sum():.1f}%)",
                va="center", fontsize=10)
    ax.set(title="Recorded Triggers of Appointment-Access Complaints",
           xlabel="Complaints across January 2023-December 2025", xlim=(0, causes.max() * 1.27))
    ax.grid(axis="y", visible=False)
    fig.tight_layout(rect=(0, 0.13, 1, 1))
    fig.text(0.045, 0.025,
             "Synthetic data. Recorded complaint classifications describe this dataset; they do not establish causal effects.",
             fontsize=9, color="#53655F")
    fig.savefig(output / "03_access_complaint_triggers.png", dpi=300, bbox_inches="tight")
    causes.to_csv(output / "complaint_trigger_totals.csv")
    return plt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sqlite", action="store_true")
    parser.add_argument("--no-show", action="store_true")
    args = parser.parse_args()
    if args.no_show:
        import matplotlib
        matplotlib.use("Agg")
    data = read_database("SQLite" if args.sqlite else "MySQL")
    annual = prepare_outcomes(data)
    plt = create_charts(data, annual, OUTPUT)
    annual.to_csv(OUTPUT / "annual_outcomes_summary.csv")
    print(annual.round(2).to_string())
    print(f"Saved charts and calculations to: {OUTPUT}. Database unchanged.")
    if args.no_show:
        plt.close("all")
    else:
        plt.show()


if __name__ == "__main__":
    main()
