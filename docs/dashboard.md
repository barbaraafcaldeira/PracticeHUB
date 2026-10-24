# PracticeHUB Dashboard

## Start Locally

From the project directory:

```bash
.venv/bin/python -m streamlit run app/PracticeHUB.py --server.address 127.0.0.1 --server.port 8501
```

If another process is using that port, select another port, for example 8502. The app is local-only and is not deployed publicly. Operational tables are read-only; user-confirmed monthly forecast inputs use a separate MySQL table.

The project `.venv` was created with access to the installed Python packages. To recreate it:

```bash
/usr/local/bin/python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install -r requirements-dashboard.txt
```

## Data and Saved Forecasts

- MySQL is the default source, using the existing connection script without copying its credentials into the app.
- SQLite is an explicit selectable local copy, opened in read-only mode. It is not a live MySQL mirror.
- Database reads are cached for up to 60 seconds. Refresh data reloads records and saved artifacts; it does not refit a model or modify the database.
- Historical date filters apply to Overview and Historical analysis only. The saved Model 4 forecast has its own reporting period and provenance.
- Saved forecast demand and opening calendar are compared with the selected database. If they differ, a stale-results warning appears and the calculator is disabled.
- Missing, inconsistent or inaccessible data produces a visible status rather than invented values or silent substitution of another source.

## Sections

Monthly inputs adds completed-month totals to the separate MySQL forecasting-input table and refits Model 4 on demand. See [the live forecasting guide](live_forecasting.md). Existing operational KPI history is not rewritten by these analytical inputs.

Overview contains clinically indicated demand, weighted booking utilisation, capacity-related signposting and access complaints. Historical analysis includes demand, utilisation/attendance, eConsult routing, incoming/outgoing calls and complaints, all with monthly filters. Monthly distinct patients are not summed across months. Signposting is not described as confirmed external care.

Next-month forecast displays Model 4's fitted same-day/routine predictions, nominal 80%/90% empirical ranges, every evaluation metric including weak R-squared, and actual sequential coverage. January 2026 is the month after the dataset cutoff, not the current calendar month. Neither band coverage nor R-squared is labelled accuracy.

The session calculator is an in-memory scenario. It supports planned leave dates for each GP, sessions per working day, usable slot count and same-day/routine split, blocked slots, point/lower/upper demand scenarios, extra-session slot count and mix, and an optional user-supplied session cost. Defaults match the saved provisional capacity estimate. Changes do not overwrite previous results; downloads include scenario values.

## Capacity Limitations

No future leave is assumed unless entered. Staff recruitment, room availability, sickness, locum cover, routine carry-in/carry-out and within-month deadline matching are not modelled. Flexible-mix session counts are monthly arithmetic lower bounds, not guaranteed staffing requirements. Type-specific band endpoints do not create a calibrated joint total-demand interval. Costs are scenario inputs, not sourced NHS rates. Only recorded clinically indicated demand is forecast.

Application logic is in `app/PracticeHUB.py` and `src/practicehub/dashboard.py`. The unused `app/Home.py` starter page and superseded analysis experiments were removed from the active workspace during presentation cleanup. Saved Model 4 results and the synthetic database remain unchanged; see `PRESENTATION_GUIDE.md` at the project root.

## Verification

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Streamlit AppTest checks all four views, including calculator updates. The same test file can run without Streamlit installed; app-specific tests are then explicitly skipped.
