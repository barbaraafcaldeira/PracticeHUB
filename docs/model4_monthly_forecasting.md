# Model 4: Monthly-Updating GP Request Forecasts

## Purpose

Predict the next completed calendar month's clinically indicated same-day and routine GP requests using a fitted machine-learning model for each target. Appropriate signposting is not GP demand. Neither historical bookings nor all contacts are substituted for request demand.

The new script is `analysis_code/FORECASTING_MODEL4.py`. It reads MySQL and writes only to `analysis_code/outputs/RESULTS_MODEL4`. Earlier scripts, their results and database records are not modified.

## Model and Inputs

Both targets use StandardScaler followed by Ridge regression with alpha 10.0, fixed before running this experiment. Scaling is fitted separately inside each training window. Predictions are clipped at zero.

The target is requests per actual opening day. The fitted daily-rate prediction is multiplied by the forecast month's planned opening days to obtain monthly request counts.

Predictors are:

- Previous month's requests per opening day.
- Requests per opening day two months ago.
- Mean daily request rate over the previous three completed months.
- Forecast month's planned opening days, bank holidays and opening Mondays.
- Winter, spring and summer indicators, with autumn as the reference category.

Calendar seasons are explicit groups, not discovered clusters. Holiday counts are separate from seasons. Calls, complaints, actual future requests, signposting outcomes and future realised slot bookings are not predictor features.

## Evaluation

For each historical month, fit using only observations completed before it, predict that single month, then advance one month and refit. Lag construction removes the first three training rows. January 2024 therefore has nine usable training observations; later months have progressively more.

The 2024 results are monthly walk-forward development results. The 2025 period was inspected in prior experiments and is labelled a previously inspected walk-forward evaluation, not an untouched independent test. Model 4's one-month horizon differs from Models 1 and 2's fixed-origin 12-month horizon, so score differences do not isolate an algorithm improvement.

The calendar-adjusted seasonal method remains a comparison benchmark only. Both principal Model 4 forecasts are fitted Ridge models. MAE, MSE, RMSE, R-squared, WAPE, bias, tolerance coverage and underforecast frequency are saved. Tolerance means within +/-10% of actual, not classification accuracy or an NHS standard.

## Next-Month Calendar and Updating

The current dataset ends in December 2025, so its next-month demonstration is January 2026, not the next month relative to today's date. `config/model4_next_month_calendar.csv` supplies 21 opening days, one bank holiday and four opening Mondays. This assumes Monday-Friday operation, closure on New Year's Day and no other closures. Holiday date source: [GOV.UK England and Wales bank holidays](https://www.gov.uk/bank-holidays).

When another month is fully complete, refresh its source data and physical monthly KPI table, extend the practice calendar, and update the separate planned-calendar CSV to cover the next month. Then rerun the script. Do not include a partly completed month as if it were a complete demand total. The script does not itself import data or update MySQL.

## Saved Evidence and Limitations

The results folder contains metrics, monthly predictions and errors for both evaluation years, feature values and training cutoffs for each fitted prediction, a next-month forecast, calendar/input snapshots, a chart and run metadata.

Only three years of monthly data are available, so seasonal estimates remain uncertain. The forecast does not include prediction intervals, extra-session recommendations or costs. More features or a different horizon cannot guarantee an accuracy threshold. Keep unfavourable metrics, including weak routine R-squared, in the evaluation.
