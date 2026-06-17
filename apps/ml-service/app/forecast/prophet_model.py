"""
Attendance trend forecasting using Prophet.
Predicts future attendance percentages based on historical data.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


def forecast_attendance(historical_data: list[dict]) -> dict:
    """
    Forecast attendance for the next 14 days.

    Args:
        historical_data: List of dicts with keys 'date' (YYYY-MM-DD) and 'attendance_pct' (float)

    Returns:
        Dict with:
            - forecast: list of {date, predicted_pct, lower_bound, upper_bound}
            - trend_direction: "improving", "declining", or "stable"
            - next_7d_avg: Predicted average attendance over next 7 days
            - next_14d_avg: Predicted average attendance over next 14 days
    """
    n = len(historical_data)

    # Edge case: less than 14 data points — use linear extrapolation
    if n < 14:
        return _linear_forecast(historical_data)

    # Edge case: all values identical
    values = [d["attendance_pct"] for d in historical_data]
    if max(values) - min(values) < 0.5:
        return _flat_forecast(historical_data, values[0])

    return _prophet_forecast(historical_data)


def _linear_forecast(historical_data: list[dict]) -> dict:
    """Simple linear extrapolation for small datasets."""
    values = [d["attendance_pct"] for d in historical_data]
    n = len(values)

    if n < 2:
        # Single point — flat forecast
        pct = values[0] if values else 75.0
        return _build_flat_response(historical_data, pct)

    # Linear regression via least squares
    x = list(range(n))
    y = values
    x_mean = sum(x) / n
    y_mean = sum(y) / n
    slope = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y)) / max(
        sum((xi - x_mean) ** 2 for xi in x), 1e-10
    )
    intercept = y_mean - slope * x_mean

    last_date = datetime.strptime(historical_data[-1]["date"], "%Y-%m-%d")
    forecast = []
    for i in range(1, 15):
        future_date = last_date + timedelta(days=i)
        predicted = intercept + slope * (n + i - 1)
        predicted = max(0.0, min(100.0, predicted))
        ci_width = 10.0 + i * 0.5  # Increasing uncertainty
        forecast.append(
            {
                "date": future_date.strftime("%Y-%m-%d"),
                "predicted_pct": round(predicted, 2),
                "lower_bound": round(max(0.0, predicted - ci_width), 2),
                "upper_bound": round(min(100.0, predicted + ci_width), 2),
            }
        )

    trend_direction = _determine_trend(forecast)
    next_7 = sum(f["predicted_pct"] for f in forecast[:7]) / 7
    next_14 = sum(f["predicted_pct"] for f in forecast) / 14

    return {
        "forecast": forecast,
        "trend_direction": trend_direction,
        "next_7d_avg": round(next_7, 2),
        "next_14d_avg": round(next_14, 2),
    }


def _flat_forecast(historical_data: list[dict], value: float) -> dict:
    """Flat forecast when all values are identical."""
    return _build_flat_response(historical_data, value)


def _build_flat_response(historical_data: list[dict], value: float) -> dict:
    """Build a flat forecast response."""
    last_date = (
        datetime.strptime(historical_data[-1]["date"], "%Y-%m-%d")
        if historical_data
        else datetime.utcnow()
    )
    forecast = []
    for i in range(1, 15):
        future_date = last_date + timedelta(days=i)
        forecast.append(
            {
                "date": future_date.strftime("%Y-%m-%d"),
                "predicted_pct": round(value, 2),
                "lower_bound": round(max(0.0, value - 5), 2),
                "upper_bound": round(min(100.0, value + 5), 2),
            }
        )
    return {
        "forecast": forecast,
        "trend_direction": "stable",
        "next_7d_avg": round(value, 2),
        "next_14d_avg": round(value, 2),
    }


def _prophet_forecast(historical_data: list[dict]) -> dict:
    """
    Use Prophet for forecasting with weekly seasonality.
    Falls back to linear forecast if Prophet is not installed.
    """
    try:
        from prophet import Prophet

        # Prepare data for Prophet
        df = []
        for d in historical_data:
            dt = datetime.strptime(d["date"], "%Y-%m-%d")
            df.append({"ds": dt, "y": d["attendance_pct"]})

        import pandas as pd

        df = pd.DataFrame(df)

        model = Prophet(
            daily_seasonality=False,
            weekly_seasonality=True,
            yearly_seasonality=False,
            changepoint_prior_scale=0.05,
        )
        model.fit(df)

        # Create future dataframe for 14 days
        future = model.make_future_dataframe(periods=14)
        forecast_result = model.predict(future)

        # Extract the last 14 predictions
        last_historical = len(historical_data)
        forecast = []
        for i in range(last_historical, last_historical + 14):
            row = forecast_result.iloc[i]
            forecast.append(
                {
                    "date": row["ds"].strftime("%Y-%m-%d"),
                    "predicted_pct": round(max(0.0, min(100.0, row["yhat"])), 2),
                    "lower_bound": round(
                        max(0.0, min(100.0, row["yhat_lower"])), 2
                    ),
                    "upper_bound": round(
                        max(0.0, min(100.0, row["yhat_upper"])), 2
                    ),
                }
            )

        trend_direction = _determine_trend(forecast)
        next_7 = sum(f["predicted_pct"] for f in forecast[:7]) / 7
        next_14 = sum(f["predicted_pct"] for f in forecast) / 14

        return {
            "forecast": forecast,
            "trend_direction": trend_direction,
            "next_7d_avg": round(next_7, 2),
            "next_14d_avg": round(next_14, 2),
        }

    except ImportError:
        logger.warning("Prophet not installed, using linear forecast fallback")
        return _linear_forecast(historical_data)
    except Exception as e:
        logger.error(f"Prophet forecasting failed: {e}, using linear fallback")
        return _linear_forecast(historical_data)


def _determine_trend(forecast: list[dict]) -> str:
    """Determine trend direction from forecast data."""
    if len(forecast) < 2:
        return "stable"

    first_half = sum(f["predicted_pct"] for f in forecast[: len(forecast) // 2]) / (
        len(forecast) // 2
    )
    second_half = sum(f["predicted_pct"] for f in forecast[len(forecast) // 2 :]) / (
        len(forecast) - len(forecast) // 2
    )

    diff = second_half - first_half
    if diff > 2:
        return "improving"
    elif diff < -2:
        return "declining"
    else:
        return "stable"