"""Incoming/outgoing telephone workload. Reads records without modifying them."""

import argparse
import contextlib
import io
from pathlib import Path
import runpy
import sqlite3
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from practicehub.dashboard import read_database

OUTPUT = ROOT / "analysis_code" / "outputs" / "charts" / "telephone_workload"
QUERIES = {
    "outcomes": "SELECT call_outcome, COUNT(*) AS attempts FROM outgoing_call_attempts GROUP BY call_outcome",
    "requests": "SELECT COUNT(DISTINCT request_id) AS requests_with_attempts, COUNT(*) AS attempts FROM outgoing_call_attempts",
    "hourly": """SELECT hour_start, SUM(calls_offered) AS offered,
                 SUM(calls_answered) AS answered, SUM(calls_abandoned) AS abandoned
                 FROM incoming_call_volumes GROUP BY hour_start ORDER BY hour_start""",
}


def read_call_details(source):
    if source == "SQLite":
        path = ROOT / "database" / "practicehub_final.sqlite"
        with contextlib.closing(sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)) as db:
            return {name: pd.read_sql_query(query, db) for name, query in QUERIES.items()}
    with contextlib.redirect_stdout(io.StringIO()):
        configured = runpy.run_path(str(ROOT / "analysis_code" / "01_connect_to_mysql.py"))
    engine = configured["engine"]
    try:
        with engine.connect() as db:
            return {name: pd.read_sql(query, db) for name, query in QUERIES.items()}
    finally:
        engine.dispose()


def validate_calls(monthly, calls):
    if not (monthly.incoming_calls_answered + monthly.incoming_calls_abandoned).eq(monthly.incoming_calls_offered).all():
        raise ValueError("Incoming call outcomes do not reconcile with offered calls.")
    if calls["outcomes"].attempts.sum() != monthly.outgoing_call_attempts.sum():
        raise ValueError("Outgoing attempt totals do not reconcile.")
    if calls["outcomes"].set_index("call_outcome").loc["Answered", "attempts"] != monthly.outgoing_calls_answered.sum():
        raise ValueError("Answered outgoing calls do not reconcile.")
    if calls["hourly"].offered.sum() != monthly.incoming_calls_offered.sum():
        raise ValueError("Hourly incoming totals do not reconcile.")
    if not calls["hourly"].offered.eq(calls["hourly"].answered + calls["hourly"].abandoned).all():
        raise ValueError("Hourly incoming outcomes do not reconcile.")


def create_charts(monthly, calls, output):
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    from matplotlib.ticker import StrMethodFormatter
    import seaborn as sns

    output.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid", font_scale=1.05)
    fig, ax = plt.subplots(figsize=(12, 4.9))
    ax.bar(monthly.kpi_month, monthly.incoming_calls_answered, width=23,
           label="Answered", color="#247BA0")
    ax.bar(monthly.kpi_month, monthly.incoming_calls_abandoned, width=23,
           bottom=monthly.incoming_calls_answered, label="Abandoned", color="#C98275")
    ax.set(title="Monthly Incoming Telephone Workload", xlabel="Month",
           ylabel="Incoming call events per month",
           xlim=(monthly.kpi_month.min() - pd.Timedelta(days=20),
                 monthly.kpi_month.max() + pd.Timedelta(days=20)))
    ax.set_ylim(0, monthly.incoming_calls_offered.max() * 1.15)
    ax.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10]))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
    ax.legend(loc="upper right", ncol=2, frameon=False)
    ax.grid(axis="x", visible=False)
    fig.tight_layout(rect=(0, 0.13, 1, 1))
    fig.text(0.055, 0.025,
             "Synthetic data. Total bar height represents offered calls. Calls include repeat contacts and non-appointment enquiries.",
             fontsize=9, color="#53655F")
    fig.savefig(output / "01_monthly_incoming_calls.png", dpi=300, bbox_inches="tight")

    outcomes = calls["outcomes"].set_index("call_outcome").attempts.sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(10, 5.2))
    wedges, _, _ = ax.pie(outcomes, startangle=90, counterclock=False,
                          colors=["#087F6D", "#247BA0", "#C79A25", "#A15762"],
                          wedgeprops={"width": 0.35, "edgecolor": "white", "linewidth": 2},
                          autopct=lambda p: f"{p:.1f}%" if p >= 3 else "",
                          pctdistance=0.83, textprops={"color": "white", "fontsize": 11, "weight": "bold"})
    ax.text(0, 0.06, f"{outcomes.sum():,}", ha="center", va="center", fontsize=21, fontweight="bold")
    ax.text(0, -0.13, "outgoing attempts", ha="center", va="center", fontsize=10, color="#53655F")
    ax.legend(wedges, [f"{name}: {count:,} ({100 * count / outcomes.sum():.1f}%)"
                       for name, count in outcomes.items()],
              loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=False)
    ax.set_title("Outgoing Telephone Attempt Outcomes, 2023-2025", pad=18)
    fig.tight_layout(rect=(0, 0.12, 1, 1))
    fig.text(0.045, 0.025,
             "Synthetic data. Attempts are not unique patients. An answered call does not necessarily result in an appointment.",
             fontsize=9, color="#53655F")
    fig.savefig(output / "02_outgoing_attempt_outcomes.png", dpi=300, bbox_inches="tight")

    hourly = calls["hourly"].copy()
    y = np.arange(len(hourly))
    fig, ax = plt.subplots(figsize=(11, 4.7))
    ax.bar(y, hourly.answered, color="#247BA0", label="Answered")
    ax.bar(y, hourly.abandoned, bottom=hourly.answered, color="#C98275", label="Abandoned")
    ax.set_xticks(y, [f"{int(hour):02d}:00" for hour in hourly.hour_start])
    ax.set(title="Incoming Calls by Hour, 2023-2025", xlabel="Hour starting",
           ylabel="Total incoming call events across three years")
    ax.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    ax.legend(frameon=False)
    ax.grid(axis="x", visible=False)
    fig.tight_layout(rect=(0, 0.12, 1, 1))
    fig.text(0.055, 0.025, "Synthetic data. Hourly totals describe contact workload, not unique patients or GP appointment demand.",
             fontsize=9, color="#53655F")
    fig.savefig(output / "03_incoming_calls_by_hour.png", dpi=300, bbox_inches="tight")
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
    monthly = read_database(source)["monthly"].sort_values("kpi_month")
    calls = read_call_details(source)
    validate_calls(monthly, calls)
    plt = create_charts(monthly, calls, OUTPUT)
    columns = ["incoming_calls_offered", "incoming_calls_answered", "incoming_calls_abandoned",
               "outgoing_call_attempts", "outgoing_calls_answered"]
    annual = monthly.groupby(monthly.kpi_month.dt.year)[columns].sum()
    annual["incoming_answer_pct"] = 100 * annual.incoming_calls_answered / annual.incoming_calls_offered
    annual["outgoing_answer_pct"] = 100 * annual.outgoing_calls_answered / annual.outgoing_call_attempts
    annual.to_csv(OUTPUT / "annual_telephone_summary.csv")
    for name, frame in calls.items():
        frame.to_csv(OUTPUT / f"{name}.csv", index=False)
    print(annual.round(2).to_string())
    print("Requests with attempts:", calls["requests"].to_dict("records"))
    print(f"Charts saved to {OUTPUT}. Database unchanged.")
    if args.no_show:
        plt.close("all")
    else:
        plt.show()


if __name__ == "__main__":
    main()
