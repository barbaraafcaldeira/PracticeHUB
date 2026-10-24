"""Empirical residual prediction bands for sequential monthly forecasts.

Uses a finite-sample conformal-style order statistic, but does not assert formal
coverage guarantees for dependent time-series residuals from refitted models.
"""

import math

import numpy as np
import pandas as pd


LEVELS = (0.80, 0.90)
MIN_CALIBRATION = 12


def residual_band(point, opening_days, earlier_daily_errors, level):
    if not 0 < level < 1:
        raise ValueError("Coverage level must lie strictly between zero and one.")
    if not math.isfinite(point) or point < 0:
        raise ValueError("Point forecasts must be finite and non-negative.")
    if not math.isfinite(opening_days) or opening_days <= 0:
        raise ValueError("Opening days must be positive and finite.")
    errors = np.asarray(earlier_daily_errors, dtype=float)
    if errors.ndim != 1 or not np.isfinite(errors).all() or (errors < 0).any():
        raise ValueError("Calibration errors must be a finite non-negative vector.")
    n = len(errors)
    if n < MIN_CALIBRATION:
        raise ValueError("Need at least 12 completed out-of-sample calibration errors.")
    rank = math.ceil((n + 1) * level)
    if rank > n:
        raise ValueError("Insufficient calibration errors for a finite band at this level.")
    quantile = float(np.sort(errors)[rank - 1])
    radius = quantile * opening_days
    return {
        "nominal_coverage_pct": level * 100,
        "lower_requests": max(0, math.floor(point - radius)),
        "upper_requests": math.ceil(point + radius),
        "calibration_observations": n,
        "order_statistic_rank": rank,
        "absolute_daily_error_quantile": quantile,
    }


def validate_predictions(predictions):
    required = {"kpi_month", "Target", "actual_requests", "predicted_requests", "opening_days"}
    if not required.issubset(predictions.columns):
        raise ValueError(f"Missing prediction columns: {sorted(required - set(predictions.columns))}")
    if predictions.duplicated(["kpi_month", "Target"]).any():
        raise ValueError("Expected one fitted-model prediction per target and month.")
    for column in ["actual_requests", "predicted_requests", "opening_days"]:
        values = predictions[column].to_numpy(dtype=float)
        if not np.isfinite(values).all() or (values < 0).any():
            raise ValueError(f"Invalid {column} values.")
    if predictions.opening_days.le(0).any() or predictions.kpi_month.isna().any():
        raise ValueError("Missing dates or non-positive opening days.")
    if not predictions.kpi_month.dt.is_month_start.all():
        raise ValueError("Prediction months must use month-start dates.")


def sequential_bands(predictions, evaluation_start, levels=LEVELS):
    validate_predictions(predictions)
    start = pd.Timestamp(evaluation_start)
    records = []
    for target, group in predictions.groupby("Target", sort=False):
        group = group.sort_values("kpi_month")
        pool = []
        pool_dates = []
        for row in group.itertuples(index=False):
            if row.kpi_month >= start:
                for level in levels:
                    band = residual_band(row.predicted_requests, row.opening_days, pool, level)
                    lower, upper = band["lower_requests"], band["upper_requests"]
                    covered = lower <= row.actual_requests <= upper
                    alpha = 1 - level
                    score = (upper - lower + 2 / alpha * max(lower - row.actual_requests, 0)
                             + 2 / alpha * max(row.actual_requests - upper, 0))
                    records.append({
                        "kpi_month": row.kpi_month, "Target": target,
                        "point_forecast": row.predicted_requests,
                        "actual_requests": row.actual_requests,
                        "opening_days": row.opening_days, **band,
                        "calibration_start": min(pool_dates), "calibration_end": max(pool_dates),
                        "covered": covered, "band_width_requests": upper - lower,
                        "interval_score": score,
                    })
            # Append only after this month's prediction interval has been made.
            pool.append(abs(row.actual_requests - row.predicted_requests) / row.opening_days)
            pool_dates.append(row.kpi_month)
    return pd.DataFrame(records)


def future_bands(predictions, next_forecast, levels=LEVELS):
    validate_predictions(predictions)
    if next_forecast.duplicated(["forecast_month", "Target"]).any():
        raise ValueError("Duplicate next-month target forecasts.")
    if set(next_forecast.Target) != set(predictions.Target):
        raise ValueError("Next-month forecast targets differ from historical targets.")
    records = []
    for row in next_forecast.itertuples(index=False):
        if row.forecast_month.day != 1:
            raise ValueError("Forecast month must use a month-start date.")
        past = predictions[(predictions.Target == row.Target) & (predictions.kpi_month < row.forecast_month)]
        if past.empty or past.kpi_month.max() + pd.offsets.MonthBegin(1) != row.forecast_month:
            raise ValueError("Need errors through the month immediately before the forecast.")
        errors = (past.actual_requests - past.predicted_requests).abs() / past.opening_days
        for level in levels:
            band = residual_band(row.predicted_requests, row.opening_days, errors, level)
            records.append({
                "forecast_month": row.forecast_month, "Target": row.Target,
                "point_forecast": row.predicted_requests, "opening_days": row.opening_days,
                **band, "calibration_start": past.kpi_month.min(),
                "calibration_end": past.kpi_month.max(),
            })
    return pd.DataFrame(records)


def coverage_summary(bands):
    return bands.groupby(["Target", "nominal_coverage_pct"], as_index=False).agg(
        evaluated_months=("covered", "size"), covered_months=("covered", "sum"),
        observed_coverage_pct=("covered", lambda s: 100 * s.mean()),
        average_band_width_requests=("band_width_requests", "mean"),
        mean_interval_score=("interval_score", "mean"),
    )
