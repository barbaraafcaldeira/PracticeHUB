# PracticeHUB

PracticeHUB is a synthetic GP Practice Management Intelligence application for the Coventry University 604IT Big Data assignment.

The project uses fictional NHS-style data to analyse appointment activity, eConsult workload, telephone activity, complaints, and future GP appointment requirements.

## GitHub Setup

The repository excludes local passwords, generated databases/raw datasets,
backups, virtual environments and submission/presentation working copies.
Dataset generation scripts and saved forecasting evidence are included.

Create a Python virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dashboard.txt matplotlib seaborn
```

For MySQL, copy `analysis_code/01_connect_to_mysql.example.py` to
`analysis_code/01_connect_to_mysql.py`. Set your own credentials in the terminal:

```bash
export PRACTICEHUB_DB_USER='your_mysql_user'
read -s PRACTICEHUB_DB_PASSWORD
export PRACTICEHUB_DB_PASSWORD
```

After the `read` command, enter your password and press Enter. The local connection
file is ignored by Git. Never commit credentials. Host, port and database default
to `127.0.0.1`, `3306` and `practicehub`; optional environment variables are
`PRACTICEHUB_DB_HOST`, `PRACTICEHUB_DB_PORT` and `PRACTICEHUB_DB_NAME`.

Use the generation instructions below to recreate the synthetic dataset. SQL
import scripts may contain the original machine's absolute CSV paths: update
these for your machine, or regenerate the dataset to recreate those SQL assets.
Inspect schema/refresh scripts before running: they can replace project tables.

## Presentation Quick Start

See [PRESENTATION_GUIDE.md](PRESENTATION_GUIDE.md) for the main files, final analysis scripts and chosen PowerPoint.

The working interface is `app/PracticeHUB.py`. Start it only if the website is not already running:

```bash
.venv/bin/python -m streamlit run app/PracticeHUB.py --server.address 127.0.0.1 --server.port 8501
```

MySQL is the default live source. SQLite remains a separate read-only development snapshot.
The application uses the final monthly Ridge forecasting workflow (Model 4).
Do not regenerate or refresh the dataset for a normal presentation launch.

## Current Scope

The current v2 dataset contains:

- A working Streamlit application and separate analysis scripts.
- Relational MySQL tables plus a SQLite development snapshot.
- Monthly forecasting, saved evaluation evidence and a session calculator.
- A reproducible request-led synthetic dataset generator with staged validation and backups.
- CSV exports for every generated table.

All generated data is synthetic and must be labelled as synthetic in reports, charts, and application screens.

## Folder Structure

```text
PracticeHUB/
├── app/                    # Streamlit app pages and UI components
├── config/                 # Dataset and modelling configuration
├── data/
│   ├── raw/                # Generated CSV files
│   ├── processed/          # Cleaned/feature-engineered datasets
│   └── exports/            # Assignment-ready extracts
├── database/               # SQLite database and SQL schema
├── docs/                   # Schema notes, data dictionary, project planning
├── models/                 # Saved model outputs and evaluation files
├── notebooks/              # Exploration notebooks
├── scripts/                # Runnable scripts
├── src/practicehub/        # Reusable Python package code
└── tests/                  # Automated tests
```

## Quick Start

Generate the small reproducible dataset:

```bash
python3 scripts/generate_synthetic_data.py --profile small
```

This creates:

- `database/practicehub_small.sqlite`
- CSV files in `data/raw/small/`
- Calculated KPI CSV in `data/processed/small/monthly_kpis.csv`

KPIs are now automatically recalculated during generation. The earlier option is accepted for compatibility:

```bash
python3 scripts/generate_synthetic_data.py --profile small --populate-kpis
```

Generate the final assignment-scale dataset:

```bash
python3 scripts/generate_synthetic_data.py --profile final
```

This creates:

- `database/practicehub_final.sqlite`
- Final raw CSV files in `data/raw/final/`
- Calculated KPI CSV in `data/processed/final/monthly_kpis.csv`

The final profile represents 10,000 registered patients over 36 months. The generated final raw CSV folder is over 100MB.

## V2 Refresh

The v2 source model is in `src/practicehub/dataset_v2.py`; `scripts/rebuild_dataset.py` stages, validates, exports and replaces local files. Previous data and SQL assets are retained under `data/archives/`.

To refresh MySQL using the existing configured Python connection, with a native SQL backup first:

```bash
/usr/local/bin/python3 scripts/refresh_mysql.py
```

This replaces the named PracticeHUB tables, imports the validated CSVs, recalculates KPIs and compares MySQL with SQLite. It requires the existing `analysis_code/01_connect_to_mysql.py` engine and the pandas/SQLAlchemy/PyMySQL environment. Passwords are not displayed. Alternatively, `database/mysql_refresh_final.sql` is a complete terminal import script; back up MySQL before executing it.

Read `docs/final_dataset_assumptions.md`, `docs/kpi_definitions_v2.md`, `docs/data_dictionary.md` and the JSON validation reports before analysis. Final chart scripts are in `analysis_code/`, and final forecasting evidence is in `analysis_code/outputs/RESULTS_MODEL4/`. Earlier experiments and rejected chart variants were moved outside the active project during the presentation cleanup.

## Database Approach

MySQL is the live database used by the website. SQLite provides a portable, read-only development and testing snapshot; it is not automatically synchronised with MySQL. Both use relational keys and datatypes.

For the assignment requirement that the database/CSV dataset should be at least 100MB, the small dataset is intentionally below that size and the final dataset is generated with the `final` profile.
