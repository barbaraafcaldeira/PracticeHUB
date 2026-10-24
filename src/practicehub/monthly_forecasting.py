"""One-month-ahead request forecasting with strictly historical demand inputs."""

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

TARGETS = ["same_day_gp_requests", "routine_gp_requests"]
ALPHA = 10.0


def calendar_features(calendar):
    dates = pd.to_datetime(calendar["calendar_date"])
    if dates.duplicated().any() or not dates.sort_values().reset_index(drop=True).equals(
        pd.Series(pd.date_range(dates.min(), dates.max(), freq="D"))
    ):
        raise ValueError("Calendar must contain one complete sequence of daily dates.")
    if dates.min().day != 1 or dates.max() != dates.max() + pd.offsets.MonthEnd(0):
        raise ValueError("Calendar must cover complete months.")
    if not calendar["is_open"].isin([0, 1]).all():
        raise ValueError("is_open must be 0 or 1.")
    frame = calendar.assign(
        month=dates.dt.to_period("M").dt.to_timestamp(),
        bank_holidays=calendar.closure_reason.eq("Bank holiday").astype(int),
        opening_mondays=((dates.dt.weekday == 0) & calendar.is_open.eq(1)).astype(int),
    )
    result = frame.groupby("month").agg(
        opening_days=("is_open", "sum"),
        bank_holidays=("bank_holidays", "sum"),
        opening_mondays=("opening_mondays", "sum"),
    )
    if result.opening_days.le(0).any():
        raise ValueError("Every historical month must have positive opening days.")
    return result


def demand_features(history, calendar, target):
    rates = history[target].reindex(calendar.index) / calendar.opening_days
    result = calendar[["opening_days", "bank_holidays", "opening_mondays"]].astype(float).copy()
    result["previous_month_daily_requests"] = rates.shift(1)
    result["two_months_ago_daily_requests"] = rates.shift(2)
    result["previous_three_month_daily_mean"] = rates.shift(1).rolling(3, min_periods=3).mean()
    # Autumn is the reference category; holiday effects are separate from season.
    result["winter"] = result.index.month.isin([12, 1, 2]).astype(int)
    result["spring"] = result.index.month.isin([3, 4, 5]).astype(int)
    result["summer"] = result.index.month.isin([6, 7, 8]).astype(int)
    return result


def predict_month(history, calendar, forecast_month, target):
    forecast_month = pd.Timestamp(forecast_month)
    cutoff = forecast_month - pd.offsets.MonthBegin(1)
    past = history.loc[history.index < forecast_month].copy()
    if past.empty or past.index.max() != cutoff:
        raise ValueError("The month immediately before the forecast must be completed.")
    if forecast_month not in calendar.index:
        raise ValueError("The forecast month's planned calendar is missing.")
    expected = pd.date_range(past.index.min(), cutoff, freq="MS")
    if not past.index.equals(expected) or not np.isfinite(past[TARGETS].to_numpy()).all():
        raise ValueError("History must contain complete consecutive monthly demand observations.")
    if past[TARGETS].lt(0).any().any():
        raise ValueError("Demand must be non-negative.")
    relevant_calendar = calendar.loc[calendar.index <= forecast_month]
    if not past.index.isin(relevant_calendar.index).all():
        raise ValueError("Historical opening calendar is incomplete.")
    X = demand_features(past, relevant_calendar, target)
    train_index = X.index[(X.index < forecast_month) & X.notna().all(axis=1)]
    if len(train_index) < 9:
        raise ValueError("Need at least 12 historical months (9 after constructing lagged features).")
    if not np.isfinite(X.loc[[forecast_month]].to_numpy()).all():
        raise ValueError("Missing forecast features.")
    model = make_pipeline(StandardScaler(), Ridge(alpha=ALPHA))
    daily_target = past.loc[train_index, target] / calendar.loc[train_index, "opening_days"]
    model.fit(X.loc[train_index], daily_target)
    daily_prediction = max(0.0, float(model.predict(X.loc[[forecast_month]])[0]))
    return daily_prediction * calendar.loc[forecast_month, "opening_days"], {
        "training_start": train_index.min().strftime("%Y-%m-%d"),
        "training_end": train_index.max().strftime("%Y-%m-%d"),
        "training_observations": len(train_index),
        "latest_completed_month": cutoff.strftime("%Y-%m-%d"),
        **X.loc[forecast_month].to_dict(),
    }


def walk_forward(history, calendar, months):
    rows = []
    for month in months:
        for target in TARGETS:
            predicted, evidence = predict_month(history, calendar, month, target)
            common = {
                "kpi_month": month, "Target": target,
                "forecast_origin": month - pd.Timedelta(days=1),
                "horizon_months": 1, "actual_requests": history.loc[month, target],
            }
            rows.append({**common, **evidence, "Method": "Monthly fitted Ridge", "predicted_requests": predicted})
            previous_year = month - pd.DateOffset(years=1)
            if previous_year in history.index:
                benchmark = (history.loc[previous_year, target] / calendar.loc[previous_year, "opening_days"]
                             * calendar.loc[month, "opening_days"])
                rows.append({**common, "Method": "Calendar-adjusted seasonal benchmark", "predicted_requests": benchmark})
    result = pd.DataFrame(rows)
    result["error_requests"] = result.predicted_requests - result.actual_requests
    result["absolute_error_requests"] = result.error_requests.abs()
    return result


def evaluate(predictions):
    rows = []
    for (method, target), group in predictions.groupby(["Method", "Target"], sort=False):
        actual, predicted = group.actual_requests, group.predicted_requests
        error = predicted - actual
        positive = actual.gt(0)
        mse = mean_squared_error(actual, predicted)
        rows.append({
            "Method": method, "Target": target, "MAE": error.abs().mean(),
            "MSE": mse, "RMSE": np.sqrt(mse), "R_squared": r2_score(actual, predicted),
            "WAPE_pct": error.abs().sum() / actual.sum() * 100 if actual.sum() else np.nan,
            "Bias_requests": error.mean(),
            "Within_10pct_months_pct": (error[positive].abs() <= .1 * actual[positive]).mean() * 100,
            "Tolerance_eligible_months": int(positive.sum()),
            "Underforecast_months": int(error.lt(0).sum()), "Evaluated_months": len(group),
        })
    return pd.DataFrame(rows)
