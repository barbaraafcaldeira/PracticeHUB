# PracticeHUB Presentation Guide

## Open These

- Website: http://127.0.0.1:8501/
- Main interface: `app/PracticeHUB.py`
- Monthly input and correction forms: `app/monthly_inputs_ui.py`
- Chosen presentation: `output/presentation/PracticeHUB_Presentation_Ready_For_Rehearsal.pptx`
- Speaking script: `output/presentation/PracticeHUB_Presentation_Rehearsal.txt`

The chosen presentation retains the original nine-month correlation analysis.

## Start the Website

From this project folder, only if it is not already running:

```bash
.venv/bin/python -m streamlit run app/PracticeHUB.py --server.address 127.0.0.1 --server.port 8501
```

## Main Code

| Purpose | File |
|---|---|
| MySQL connection | `analysis_code/01_connect_to_mysql.py` |
| Dashboard data and calculations | `src/practicehub/dashboard.py` |
| Model 4 training and saved evaluation | `analysis_code/FORECASTING_MODEL4.py` |
| Shared monthly Ridge model | `src/practicehub/monthly_forecasting.py` |
| Monthly input validation and corrections | `src/practicehub/monthly_inputs.py` |
| Capacity planning | `src/practicehub/forecast_capacity.py` |
| Prediction ranges | `src/practicehub/forecast_uncertainty.py` |
| Monthly KPI calculations | `database/mysql_kpi_views.sql` |

## Final Analysis and Figures

The scripts remaining in `analysis_code/` generate the final historical demand,
capacity/utilisation, allocation/access, telephone, correlation and evaluation charts.
These figures are organised under `analysis_code/outputs/charts/`.

Keep `RESULTS_MODEL4`, `RESULTS_MODEL4_CAPACITY` and `RESULTS_MODEL4_UNCERTAINTY`:
the website uses saved forecasting evidence from these workflows.
Generating a live forecast through the website is separate from rerunning all scripts.

## Cleanup Recovery

Obsolete experiments, rejected figures and temporary build files were removed from
the active project and retained under `../PracticeHUB cleanup backups/`.
Each recovery folder includes a manifest with original paths and checksums.
The database, selected presentation, report, final figures and working application
were preserved. No MySQL data was deleted or regenerated during cleanup.
