import calendar
import contextlib
import io
import runpy
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

# Reuse existing MySQL connection.
FOLDER = Path(__file__).resolve().parent
OUTPUT = FOLDER / "outputs" / "charts" / "historical_demand"
OUTPUT.mkdir(parents=True, exist_ok=True)

with contextlib.redirect_stdout(io.StringIO()):
    connection = runpy.run_path(
        str(FOLDER / "01_connect_to_mysql.py")
    )

engine = connection["engine"]

try:
    with engine.connect() as database:
        demand = pd.read_sql(
            """
            SELECT kpi_month,
                   same_day_gp_requests,
                   routine_gp_requests
            FROM monthly_kpis
            ORDER BY kpi_month
            """,
            database,
        )

        opening_calendar = pd.read_sql(
            """
            SELECT calendar_date, is_open
            FROM practice_calendar
            ORDER BY calendar_date
            """,
            database,
        )
finally:
    engine.dispose()

# Prepare dates and monthly opening-day counts.
demand["kpi_month"] = pd.to_datetime(demand["kpi_month"])
opening_calendar["calendar_date"] = pd.to_datetime(
    opening_calendar["calendar_date"]
)

opening_calendar["kpi_month"] = (
    opening_calendar["calendar_date"]
    .dt.to_period("M")
    .dt.to_timestamp()
)

opening_days = (
    opening_calendar.groupby("kpi_month", as_index=False)["is_open"]
    .sum()
    .rename(columns={"is_open": "opening_days"})
)

demand = demand.merge(
    opening_days,
    on="kpi_month",
    how="left",
    validate="one_to_one",
)

if demand["opening_days"].isna().any() or (
    demand["opening_days"] <= 0
).any():
    raise ValueError("Missing or invalid monthly opening-day counts.")

labels = {
    "same_day_gp_requests": "Same-day GP",
    "routine_gp_requests": "Routine GP",
}

long = demand.melt(
    id_vars=["kpi_month", "opening_days"],
    value_vars=list(labels),
    var_name="appointment_type",
    value_name="requests",
)

long["appointment_type"] = long["appointment_type"].map(labels)
long["year"] = long["kpi_month"].dt.year.astype(str)
long["month"] = long["kpi_month"].dt.month
long["requests_per_opening_day"] = (
    long["requests"] / long["opening_days"]
)

sns.set_theme(style="whitegrid", font_scale=1.05)

# Chart 1: the full monthly demand series.
fig, ax = plt.subplots(figsize=(12, 5))

sns.lineplot(
    data=long,
    x="kpi_month",
    y="requests",
    hue="appointment_type",
    palette={"Same-day GP": "#087F6D", "Routine GP": "#247BA0"},
    marker="o",
    ax=ax,
)

ax.set(
    title="Monthly GP Appointment Requests",
    xlabel="Month",
    ylabel="Requests per month",
)
ax.legend(title="Appointment type")
fig.autofmt_xdate()
fig.tight_layout()
fig.savefig(OUTPUT / "01_monthly_gp_requests.png", dpi=300)

# Charts 2 and 3: compare the same months across years.
years = sorted(long["year"].unique())
year_colours = dict(
    zip(years, sns.color_palette("colorblind", n_colors=len(years)))
)

for measure, heading, ylabel, filename in [
    (
        "requests",
        "Year-on-Year Monthly GP Demand",
        "Requests per month",
        "02_year_on_year_monthly_requests.png",
    ),
    (
        "requests_per_opening_day",
        "Year-on-Year GP Demand per Opening Day",
        "Requests per opening day",
        "03_year_on_year_daily_requests.png",
    ),
]:
    fig, axes = plt.subplots(2, 1, figsize=(11, 8), sharex=True)

    for ax, appointment_type in zip(
        axes, ["Same-day GP", "Routine GP"]
    ):
        subset = long[
            long["appointment_type"] == appointment_type
        ]

        sns.lineplot(
            data=subset,
            x="month",
            y=measure,
            hue="year",
            hue_order=years,
            palette=year_colours,
            marker="o",
            ax=ax,
        )

        ax.set_title(appointment_type)
        ax.set_ylabel(ylabel)
        ax.set_xlabel("Month")
        ax.set_xticks(range(1, 13))
        ax.set_xticklabels(list(calendar.month_abbr)[1:])
        ax.legend(title="Year")

    fig.suptitle(heading, fontsize=15)
    fig.tight_layout()
    fig.savefig(OUTPUT / filename, dpi=300)

print(f"Charts saved in: {OUTPUT}")
plt.show()