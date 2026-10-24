"""Read-only appointment-capacity analysis and report figures.

Run with --no-show to save images without opening plot windows.
Use --sqlite to analyse the packaged database instead of MySQL.
"""

import argparse
import calendar
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from practicehub.dashboard import read_database

OUTPUT = ROOT / "analysis_code" / "outputs" / "charts" / "appointment_capacity"
TYPES = {"same_day_gp_requests": "Same-day GP", "routine_gp_requests": "Routine GP"}


def prepare_capacity_data(data):
    """Join separately aggregated demand/capacity, avoiding contact multiplication."""
    monthly = data["monthly"].copy()
    capacity = data["capacity"].copy()
    monthly["kpi_month"] = pd.to_datetime(monthly["kpi_month"])
    capacity["kpi_month"] = pd.to_datetime(capacity["kpi_month"])
    if monthly.empty or not pd.DatetimeIndex(monthly.kpi_month).equals(
        pd.date_range(monthly.kpi_month.min(), monthly.kpi_month.max(), freq="MS")
    ):
        raise ValueError("Expected consecutive, unique monthly observations.")
    demand = monthly.melt(
        id_vars="kpi_month", value_vars=list(TYPES),
        var_name="target", value_name="requests",
    )
    demand["slot_type"] = demand.target.map(TYPES)
    detail = demand.merge(
        capacity, on=["kpi_month", "slot_type"], how="left", validate="one_to_one",
    )
    if detail[["requests", "bookable_slots", "allocated_slots"]].isna().any().any():
        raise ValueError("Missing demand or capacity for a month/appointment type.")
    if (detail[["requests", "bookable_slots", "allocated_slots"]] < 0).any().any():
        raise ValueError("Demand and slot counts must be non-negative.")
    if (detail.allocated_slots > detail.bookable_slots).any():
        raise ValueError("Booked slots exceed bookable slots; investigate before plotting.")
    detail["utilisation_pct"] = (
        100 * detail.allocated_slots / detail.bookable_slots.replace(0, np.nan)
    )
    detail["year"] = detail.kpi_month.dt.year
    detail["month"] = detail.kpi_month.dt.month
    totals = detail.groupby("kpi_month", as_index=False)[
        ["requests", "bookable_slots", "allocated_slots"]
    ].sum()
    totals["year"] = totals.kpi_month.dt.year
    totals["month"] = totals.kpi_month.dt.month
    reference = monthly.set_index("kpi_month").sort_index()
    for actual, expected in [("requests", "gp_requests"),
                             ("bookable_slots", "gp_slots_bookable"),
                             ("allocated_slots", "gp_slots_booked")]:
        if not np.array_equal(totals[actual], reference[expected]):
            raise ValueError(f"Aggregated {actual} does not match monthly KPIs.")
    return totals, detail


def create_charts(totals, detail, output):
    import matplotlib.pyplot as plt
    from matplotlib.ticker import StrMethodFormatter
    import seaborn as sns

    sns.set_theme(style="whitegrid", font_scale=1.05)
    output.mkdir(parents=True, exist_ok=True)
    years = sorted(totals.year.unique())
    month_labels = list(calendar.month_abbr)[1:]

    def save(fig, name, note):
        fig.text(0.065, 0.018, note, fontsize=9, color="#53655F")
        fig.savefig(output / name, dpi=300, bbox_inches="tight", facecolor="white")

    # Compare requests and slots with the same vertical scale across all years.
    fig, axes = plt.subplots(len(years), 1, figsize=(12, 3.2 * len(years) + 1),
                             sharex=True, sharey=True, squeeze=False)
    upper_limit = totals[["requests", "bookable_slots"]].to_numpy().max() * 1.12
    for ax, year in zip(axes[:, 0], years):
        frame = totals[totals.year.eq(year)]
        x = frame.month.to_numpy()
        ax.bar(x - 0.19, frame.requests, width=0.38,
               label="GP requests received", color="#247BA0")
        ax.bar(x + 0.19, frame.bookable_slots, width=0.38,
               label="Bookable GP slots", color="#C79A25")
        ax.set_title(str(year), loc="left", fontsize=12, fontweight="bold")
        ax.set_ylabel("Requests / slots per month")
        ax.set_ylim(0, upper_limit)
        ax.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
        ax.set_xticks(range(1, 13), month_labels)
        ax.grid(axis="x", visible=False)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.955),
               ncol=2, frameon=False)
    fig.suptitle("Monthly GP Demand and Bookable Capacity", fontsize=16, y=0.99)
    axes[-1, 0].set_xlabel("Month")
    fig.tight_layout(rect=(0, 0.055, 1, 0.92))
    save(fig, "01_monthly_demand_vs_capacity.png",
         "Synthetic data. Request month and slot month can differ for routine bookings. The gap is not a direct unmet-demand count.")

    # A common 0-100% scale makes the heatmaps comparable across both slot types.
    fig, axes = plt.subplots(2, 1, figsize=(12, 6.6))
    cmap = sns.light_palette("#087F6D", as_cmap=True)
    for ax, kind in zip(axes, TYPES.values()):
        matrix = detail[detail.slot_type.eq(kind)].pivot(
            index="year", columns="month", values="utilisation_pct",
        ).reindex(index=years, columns=range(1, 13))
        annotations = matrix.map(lambda value: "" if pd.isna(value) else f"{value:.1f}%")
        sns.heatmap(matrix, ax=ax, cmap=cmap, vmin=0, vmax=100,
                    annot=annotations, fmt="", annot_kws={"fontsize": 9},
                    linewidths=2, linecolor="white", mask=matrix.isna(),
                    cbar_kws={"label": "Booked-slot utilisation (%)"})
        ax.set_title(kind, loc="left", fontsize=12, fontweight="bold")
        ax.set_xticklabels(month_labels, rotation=0)
        ax.set_yticklabels([str(y) for y in years], rotation=0)
        ax.set(xlabel="Month", ylabel="Year")
    fig.suptitle("Monthly GP Slot Utilisation", fontsize=16, y=0.995)
    fig.tight_layout(rect=(0, 0.07, 1, 0.96))
    save(fig, "02_utilisation_heatmaps.png",
         "Synthetic data. Utilisation = allocated slots / bookable slots. Booking utilisation is not attendance; DNAs and late cancellations remain allocated.")

    # Average monthly counts within each year, keeping the two slot types separate.
    annual = detail.groupby(["year", "slot_type"], as_index=False).agg(
        average_monthly_requests=("requests", "mean"),
        average_monthly_bookable_slots=("bookable_slots", "mean"),
        months_observed=("kpi_month", "nunique"),
    )
    annual.to_csv(output / "annual_monthly_averages.csv", index=False)
    fig, axes = plt.subplots(2, 1, figsize=(12, 7.2), sharex=True)
    limit = annual[["average_monthly_requests", "average_monthly_bookable_slots"]].to_numpy().max() * 1.12
    for ax, kind in zip(axes, TYPES.values()):
        frame = annual[annual.slot_type.eq(kind)].sort_values("year")
        y = np.arange(len(frame))
        ax.hlines(y, frame.average_monthly_bookable_slots, frame.average_monthly_requests,
                  color="#B1BFBA", linewidth=5, zorder=1)
        ax.scatter(frame.average_monthly_bookable_slots, y, s=105,
                   color="#C79A25", label="Bookable slots", zorder=3)
        ax.scatter(frame.average_monthly_requests, y, s=105,
                   color="#247BA0", label="GP requests", zorder=3)
        for position, row in enumerate(frame.itertuples(index=False)):
            ax.annotate(f"{row.average_monthly_bookable_slots:,.0f}",
                        (row.average_monthly_bookable_slots, position), xytext=(0, -20),
                        textcoords="offset points", ha="center", fontsize=11, color="#7C5C00")
            ax.annotate(f"{row.average_monthly_requests:,.0f}",
                        (row.average_monthly_requests, position), xytext=(0, 12),
                        textcoords="offset points", ha="center", fontsize=11, color="#175B7A")
        ax.set_yticks(y, [f"{row.year} ({row.months_observed} months)"
                          for row in frame.itertuples(index=False)])
        ax.set_ylim(len(frame) - 0.4, -0.6)
        ax.set_title(kind, loc="left", fontsize=12, fontweight="bold")
        ax.set_xlim(0, limit)
        ax.xaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
        ax.grid(axis="y", visible=False)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.945),
               ncol=2, frameon=False)
    axes[-1].set_xlabel("Average requests / bookable slots per month")
    fig.suptitle("Average Monthly GP Demand and Capacity by Year", fontsize=16, y=0.995)
    fig.tight_layout(rect=(0, 0.10, 1, 0.89))
    save(fig, "03_demand_capacity_dumbbell.png",
         "Synthetic data. Values are annual averages of monthly counts, rounded for display, not annual totals.\n"
         "Connecting lines show the difference between averages, not a direct count of unmet requests.")
    return plt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-show", action="store_true")
    parser.add_argument("--sqlite", action="store_true")
    args = parser.parse_args()
    if args.no_show:
        import matplotlib
        matplotlib.use("Agg")
    source = "SQLite" if args.sqlite else "MySQL"
    totals, detail = prepare_capacity_data(read_database(source))
    plt = create_charts(totals, detail, OUTPUT)
    totals.to_csv(OUTPUT / "monthly_capacity_comparison.csv", index=False)
    detail.drop(columns="target").to_csv(OUTPUT / "monthly_capacity_by_type.csv", index=False)
    summary = detail.groupby("slot_type")[["requests", "bookable_slots", "allocated_slots"]].sum()
    summary["weighted_utilisation_pct"] = 100 * summary.allocated_slots / summary.bookable_slots
    summary.to_csv(OUTPUT / "period_summary.csv")
    print(f"Source: {source}. No database records were changed.")
    print(summary.round(2).to_string())
    print(f"Saved 3 charts and supporting calculations in: {OUTPUT}")
    if args.no_show:
        plt.close("all")
    else:
        plt.show()


if __name__ == "__main__":
    main()
