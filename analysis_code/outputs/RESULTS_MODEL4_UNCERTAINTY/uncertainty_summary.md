# Model 4 Forecast Uncertainty

All data and forecasts are synthetic. Model 4's point predictions are unchanged.

## Next-Month Demand Ranges

| Target | Point forecast | Nominal coverage target | Lower requests | Upper requests | Earlier errors used |
|---|---:|---:|---:|---:|---:|
| Same-day GP | 2,323.32 | 80% | 1,927 | 2,719 | 24 |
| Same-day GP | 2,323.32 | 90% | 1,825 | 2,822 | 24 |
| Routine GP | 801.02 | 80% | 612 | 990 | 24 |
| Routine GP | 801.02 | 90% | 568 | 1,034 | 24 |

## Actual Sequential Coverage in 2025

These bands were formed using earlier errors only; the current month's actual was not used to construct its band.

| Target | Nominal target | Months covered | Observed coverage | Mean interval width |
|---|---:|---:|---:|---:|
| Routine GP | 80% | 11/12 | 91.7% | 420.9 |
| Routine GP | 90% | 11/12 | 91.7% | 462.9 |
| Same-day GP | 80% | 9/12 | 75.0% | 842.1 |
| Same-day GP | 90% | 12/12 | 100.0% | 1,106.7 |

## Interpretation

A prediction band describes a plausible range for a future observed count based on historical forecast errors. It is not an accuracy score, a guarantee, or evidence that an upper-end staffing purchase is optimal.

## Limitations

- Empirical, conformal-style prediction bands, not confidence intervals for an average.
- Temporal dependence and refitted models mean no formal exchangeable split-conformal coverage guarantee is claimed.
- Coverage percentages are nominal targets, not forecast accuracy or promises for a particular month.
- Only 12 historical months evaluate each band; one month changes coverage by 8.33 percentage points.
- 2025 was previously inspected; this is exploratory sequential calibration/evaluation, not a fresh independent test.
- 24 completed errors calibrate January 2026; no independent season-specific calibration is possible at this size.
- Bands are separate for each appointment type, not a joint simultaneous interval for total demand.
- Summing type-specific endpoints gives scenarios, not a calibrated combined coverage level.
- Normalising errors by opening days assumes error size scales approximately with the opening calendar.
- January 2026 follows the dataset cutoff; it is not the next month relative to today's date.
- Any capacity gaps retain the earlier no-future-leave and blocked-slot assumptions, not staffing guarantees.

## References

- [Adaptive Conformal Inference Under Distribution Shift](https://arxiv.org/abs/2106.00170). This motivates caution about distribution changes; the script does not implement adaptive conformal inference.
- [Scikit-learn time-series forecasting and uncertainty example](https://scikit-learn.org/stable/auto_examples/applications/plot_time_series_lagged_features.html).
