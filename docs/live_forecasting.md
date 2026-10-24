# Add Monthly Inputs and Generate a Forecast

## Presentation Workflow

1. Open PracticeHUB with MySQL selected and choose **Monthly inputs**.
2. Enter January 2026's completed same-day/routine clinically indicated request counts and actual calendar totals using the manual entry form.
3. Confirm that the totals cover the whole completed month, then save. Zero requests is allowed; blank requests are not interpreted as zero.
4. The forecast target advances to February 2026. Review its bank-holiday and other planned closures and confirm the opening calendar.
5. Click **Generate forecast**. Both Model 4 Ridge models are actually fitted at that moment, using the original history and the newly saved month.
6. The new predictions and empirical ranges appear on the page. Next-month forecast and Session calculator also use the latest generated run matching those inputs, including after a page reload.

No January demand is prefilled or invented. Enter legitimate completed-month totals from your assignment data. Booked appointments are not a substitute for clinically indicated request counts including those not accommodated.

## Separate Storage

The separate MySQL table `forecast_month_inputs` contains a month primary key, same-day/routine request counts, opening days, bank-holiday closure count, opening Mondays, input source and UTC creation timestamp. The schema is in `database/mysql_forecast_month_inputs.sql`. The app can create this table if absent, but only saving a confirmed manual entry form inserts rows. CSV upload is not available; saved inputs can still be downloaded.

The original patients, requests, appointments, monthly KPIs, calendar and SQLite database are not changed. Consequently, the historical Overview still ends at the original operational cutoff: these analytical totals are not manufactured individual appointment records. SQLite remains read-only; it does not silently receive MySQL inputs.

Inputs must be consecutive after the operational history; new entries cannot duplicate an existing month. Current/incomplete and future months are rejected. Dates, numeric counts, whole numbers and calendar consistency are validated before the transactional insert. Concurrent duplicate inserts are also protected by the primary key. There is no delete facility.

## Correct a Saved Month

In **Monthly inputs**, choose **Correct saved month**, select the month, edit its totals, provide a reason and confirm before clicking **Save correction**. Only the separate forecasting inputs can be corrected, not operational months or month dates. Each correction records its old/new values, reason and UTC timestamp in `forecast_month_input_corrections`, atomically with the update. The correction history is visible in the same tab. Original creation metadata is preserved. Stale edits from another session are rejected.

Changed inputs invalidate the previously generated forecast. Generate the next-month forecast again before using the session calculator. Existing forecast folders remain as historical snapshots; the model's historical reference metrics are unchanged.

## Forecasts and Audit

Each generated run is a separate folder under `data/exports/live_forecasts/`, containing point predictions, bands, the full input snapshot, retrospective calibration errors and run metadata. Existing Model 1-4 result files are never overwritten. The latest run is used only when its history signature matches the currently saved input history. A newly added month invalidates the previous run for next-month planning until a new forecast is generated.

The 2024/2025 reference evaluation metrics remain unchanged. A future forecast cannot have measured accuracy until its actual outcome is available. New interval calibration errors are chronological retrospective forecasts using the supplied historical opening calendars, assumed known ahead; they are not evidence of independently guaranteed prospective coverage.

The calendar defaults for 2026 follow [GOV.UK England and Wales bank holidays](https://www.gov.uk/bank-holidays). Planned closures are user-confirmed. For other years, supply and verify the calendar rather than assuming no holidays. The capacity scenario uses those same planned closures and the existing five GP patterns, retaining the earlier limitations concerning leave, blocking, backlog, within-month matching and resource availability.

## Local-Only Security

This is a local presentation prototype bound to loopback. It reuses your existing MySQL connection and does not expose its credentials in the UI. The only application database inserts are into the separate monthly input table. It has no user authentication or production access controls: do not expose this server publicly or connect it to patient-identifiable data without adding those controls.
