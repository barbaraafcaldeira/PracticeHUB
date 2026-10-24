# PracticeHUB Project Plan

## Phase 1: Foundation

1. Finalise relational schema.
2. Generate a small reproducible synthetic dataset.
3. Validate key relationships and analytical rules.
4. Load data into SQLite and export CSV files.

## Phase 2: Scale Data

1. Expand from the small profile to 36 months.
2. Scale to 10,000 registered patients and 5 GPs.
3. Ensure exported CSV/database size exceeds 100MB.
4. Add controlled seasonal effects, weekday effects, access pressure, and unmet demand indicators.

## Phase 3: Analysis

1. Build historical appointment summaries.
2. Calculate slot utilisation.
3. Analyse eConsult triage outcomes.
4. Analyse incoming and outgoing telephone workload.
5. Monitor appointment-access complaints.

## Phase 4: Forecasting

1. Create monthly GP appointment demand series.
2. Split historical observations into training and hold-out periods.
3. Train baseline and scikit-learn forecasting models.
4. Calculate MAE and WAPE from hold-out observations only.
5. Store forecasts and model evaluation results in the database.

## Phase 5: Streamlit Application

1. Management overview dashboard.
2. Appointment and utilisation pages.
3. eConsult page.
4. Telephone workload page.
5. Forecasting and evaluation page.
6. Additional GP session calculator.
7. Complaints monitoring page.

